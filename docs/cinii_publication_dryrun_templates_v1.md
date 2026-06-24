# CiNii→authority.publication dry-run 雛型 v1 (2026-06-23)

> **本番非破壊。すべて `staging_cinii` スキーマ限定で実行する。**
> `authority.*` への INSERT/UPDATE は Owner ratify まで一切しない（HANDOFF §5）。
> これは実装の出発点となる雛型であり、列名・正規化は実装時に最終確認すること。

---

## Phase 0 — 法律ISSNフィルタ＆規模計測（read-only, パイプライン側）

CiNii detail (~638,021 JSON) を法律ISSNで絞り、対象件数とNRID歩留まりを測る。

```python
# pseudocode (no DB write)
legal_issn = load_jsonl("kaken_law_scholars/legal_journal_issn_filter.jsonl")  # ~150誌
legal_issn = { normalize_issn(x["issn"]) for x in legal_issn }

n_total = n_legal = n_with_author_nrid = 0
hit_nrids = set()
for f in iter_json("cinii_batch/detail/*.json"):
    n_total += 1
    issns = extract_issns(f["publication"]["publicationIdentifier"])   # ISSN/PISSN/LISSN
    if not (issns & legal_issn):
        continue
    n_legal += 1
    nrids = [pid["identifier"] for c in f.get("creator",[])
                                for pid in c.get("personIdentifier",[])
                                if pid["@type"] == "NRID"]
    if nrids:
        n_with_author_nrid += 1
        hit_nrids.update(normalize_nrid(n) for n in nrids)   # 13桁化

report = dict(total=n_total, legal=n_legal,
              legal_with_author_nrid=n_with_author_nrid,
              distinct_author_nrid=len(hit_nrids))
# → これが dry-run 対象件数と NRID 歩留まりの実測（未測定の唯一の数字）
```

DB側で hit_nrids が person に当たる率（ハードjoin上限）:

```sql
-- staging に流した hit_nrids を temp に入れて確認（read-only）
SELECT count(*) AS joinable_persons
FROM authority.person_history ph
WHERE ph.history_type = 'scholar_nrid'
  AND ph.history_value = ANY (:hit_nrids);   -- 13桁文字列配列
```

---

## Phase 1 — staging スキーマ（本番非破壊）

```sql
CREATE SCHEMA IF NOT EXISTS staging_cinii;

CREATE TABLE staging_cinii.publication (
  publication_id     text PRIMARY KEY,        -- 'cinii:'||crid
  crid               text NOT NULL,
  publication_type   text DEFAULT 'journal_article',
  title              text,
  title_normalized   text,
  container_title    text,
  volume             text,
  issue              text,
  publication_year   int,
  publisher          text,
  issn_matched       text,                    -- 採用した法律誌ISSN
  source_system      text DEFAULT 'cinii_research',
  raw_payload        jsonb                     -- L0退避(編成指針 Raw First)
);

CREATE TABLE staging_cinii.publication_author_evidence (
  author_evidence_id text PRIMARY KEY,        -- 'cinii:'||crid||':'||ordinal
  publication_id     text NOT NULL REFERENCES staging_cinii.publication,
  evidence_type      text DEFAULT 'cinii_creator',
  ordinal            int  NOT NULL,
  author_raw         text,                    -- foaf:name
  author_normalized  text,
  affiliation_raw    text,
  nrid_raw           text[],                  -- creator.personIdentifier[@type=NRID] 全部
  nrid_selected      text,                    -- 代表ID選別後の1件(§4)
  evidence_payload_json jsonb,                -- creator 全体
  evidence_strength  numeric
);

CREATE TABLE staging_cinii.publication_author_claim (
  author_claim_id    text PRIMARY KEY,
  publication_id     text NOT NULL,
  person_id          text,                    -- 解決できた場合のみ
  primary_evidence_id text,
  claim_status       text,                    -- accepted/needs_review/candidate
  confidence         numeric,
  decision_method    text,                    -- nrid_exact/nrid_resolved/name_journal/name_only
  trust_tier         text                     -- high/medium/low
);
```

---

## Phase 2 — 投入（staging。CRID冪等 UPSERT）

publication / evidence はパイプラインが Parser 出力から UPSERT:

```sql
INSERT INTO staging_cinii.publication AS p (publication_id, crid, title, title_normalized,
       container_title, volume, issue, publication_year, publisher, issn_matched, raw_payload)
VALUES (:pubid, :crid, :title, :title_norm, :container, :vol, :issue, :year, :publisher, :issn, :raw)
ON CONFLICT (publication_id) DO UPDATE
  SET title=EXCLUDED.title, raw_payload=EXCLUDED.raw_payload;   -- 冪等
```

---

## Phase 3 — NRID突合 → claim生成（staging内、trust_tierはしご）

```sql
-- (a) NRID完全一致 → high/accepted
INSERT INTO staging_cinii.publication_author_claim
  (author_claim_id, publication_id, person_id, primary_evidence_id,
   claim_status, confidence, decision_method, trust_tier)
SELECT e.author_evidence_id||':claim', e.publication_id, ph.person_id, e.author_evidence_id,
       'accepted', 0.95, 'nrid_exact', 'high'
FROM staging_cinii.publication_author_evidence e
JOIN authority.person_history ph
  ON ph.history_type='scholar_nrid' AND ph.history_value = e.nrid_selected
WHERE e.nrid_selected IS NOT NULL;

-- (b) NRIDなし・氏名+収録誌ISSN候補 → low/candidate（自動acceptしない）
--     name_normalized + issn_matched での候補生成。person解決は保留(person_id NULL可)。
-- (c) 氏名only → candidate固定（同名多発のため accepted 禁止）
```

> 代表ID選別(§4/§6-2): `nrid_raw` が複数のとき、creator.@id(研究者CRID)優先で `nrid_selected` を1件に。
> 選別判断は `resolution_log` 相当に記録（staging では `staging_cinii.resolution_note`）。

---

## Phase 4 — 受入ゲート（dry-run レポート、read-only集計）

```sql
-- 1) CRID一意（重複0が合格）
SELECT count(*)-count(DISTINCT publication_id) AS dup FROM staging_cinii.publication;

-- 2) 著者なし論文率（<10%）
SELECT round(100.0*sum(CASE WHEN e.publication_id IS NULL THEN 1 ELSE 0 END)/count(*),2) AS pct_no_author
FROM staging_cinii.publication p
LEFT JOIN (SELECT DISTINCT publication_id FROM staging_cinii.publication_author_evidence) e USING (publication_id);

-- 3) NRID claim の person解決率
SELECT count(*) FILTER (WHERE person_id IS NOT NULL)::float/NULLIF(count(*),0) AS resolve_rate
FROM staging_cinii.publication_author_claim WHERE decision_method='nrid_exact';

-- 4) name_only 自動accept = 0件（合格）
SELECT count(*) FROM staging_cinii.publication_author_claim
WHERE decision_method='name_only' AND claim_status='accepted';

-- 5) trust_tier 分布（暴走検知）
SELECT trust_tier, count(*) FROM staging_cinii.publication_author_claim GROUP BY trust_tier;
```

---

## Phase 5 — 本投入（Owner ratify 後のみ）

dry-run レポートを Owner が承認 → staging から `authority.*` へ誌単位バッチで反映。
ロールバック手順（バッチ単位の delete キー = source_system+issn_matched）を用意してから実行。

**ここまでは設計・staging のみ。`authority.*` への書込は本フェーズで初めて、かつ Owner ratify 後に行う。**
