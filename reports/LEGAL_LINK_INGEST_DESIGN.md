# 法令リンク DB 投入 設計・データ品質分析（書込み前レビュー）

- 日付: 2026-06-06
- 状態: **分析と設計のみ。DB への書込みは一切行っていない（read-only 調査）。**
- 目的: 「抽出した条文・判例リンクを、汚いデータを入れずに、どの形で投入するのが
  一番きれいか」を、本番 DB の実データと既存設計規約に基づいて整理する。
- 関連: PR #8 / `reports/REAL_DATA_FINDINGS.md`

---

## 0. 結論（先に）

**このまま truth テーブルへ一括 INSERT するのは NG。** ただし本 DB には既に
「**claim / evidence / adjudication + release governance**」という汚染防止の作法が
確立されており、**それに乗せれば安全に投入できる**。具体的には:

1. 抽出結果は **claim（候補辺）＋ evidence（根拠スパン）** として staging に入れ、
   `confidence` で `claim_status` を振る（high→accepted 候補 / medium→candidate /
   low→needs_review 以下）。
2. **accepted のみ** を `serving` ビューで公開（既存 `serving.publication_author_claim_*`
   と同じ）。
3. 投入は `control.source_snapshots` → `ingest_jobs` → `releases(validation/approval)` に
   登録し、**承認制・ロールバック可能**にする。
4. **bib_toc 本体・bib_records は一切変更しない**（リンクは別テーブルの辺として持つ）。

この設計なら「汚いデータが truth に混ざる」ことは構造的に起きない。

---

## 1. 既存 DB から読み取った設計規約（これに合わせる）

| 観点 | 本 DB の作法（実在） |
|---|---|
| 不確実な抽出関係 | `authority.publication_author_claim`（claim）＋ `_evidence`＋ `_claim_evidence` junction |
| claim_status | CHECK `('candidate','accepted','rejected','ambiguous','needs_review')` |
| 確信度 | `confidence numeric CHECK 0..1`、`evidence_strength numeric 0..1`、`trust_tier`、`decision_method` |
| 公開面 | `serving.publication_author_claim_accepted / _current`（accepted のみ） |
| 保留リンク | `dynamic.unconfirmed_links`（確認前リンクの前例あり） |
| 既存 biblio リンク | `biblio.bib_terms(bib_id, term_id)`（FK 2 本）|
| provenance | `control.source_snapshots`（box/github/hash/row_count）|
| 投入ジョブ | `control.ingest_jobs`（rows_inserted/updated/**rejected**, error_summary）|
| リリース | `control.releases`（validation_status / approval_status / previous / rollback）|
| 共通列 | text 主キー(意味ID)、`*_normalized`、`metadata_json jsonb '{}'`、`created_at/updated_at timestamptz utc`、snake_case |

→ **新規テーブルもこの規約に厳密に合わせる**（confidence は numeric、status は CHECK、
serving ビューで accepted のみ公開、control に provenance 登録）。

---

## 2. データ品質の実測（投入可否の根拠）

対象: `biblio.bib_toc` のうち条文/判例を含む **22,908 ノード / 2,059 書誌**。
うち article|case ノード **12,253 件**に `legal_links.py` を実行した実測:

### 2.1 条文参照（statute_ref）
- 抽出 **589 件**（high 347 / medium 197 / **low 45**）、曖昧法令名 0。
- 条番号まで解決 58.9%、うち **e-gov 定義突合 121 件**（最も強い辺）。
- **重要（high precision / low recall）**: 「第○条」を含む ~10,211 ノードのうち、
  リンク化したのは 555 ノードのみ。残り **~9,600 ノードは「法令名が隣接しない裸の条番号」**
  （その書籍が主題とする法令の条で、法令名は書誌側にある）。**これらは推測せず
  あえてスキップ**しており、誤った law_id を撒かない。→ truth を汚さない設計上の美点。

### 2.2 低 confidence = 実際の誤検出（gate で除去できることの実証）
low 45 件は、まさに複合語に埋もれた偽陽性だった:
- `医療法人` 中の「医療法」（社会/社団/財団 **医療法人** ＝法人類型で、医療法という法律ではない）
- `最高人民法院` / `高級人民法院` 中の「民法」（中国の裁判所名）
- `旧民法` / `新民法`、`株式会社法` 中の「会社法」

→ **confidence=low を accepted から外せば、汚れは構造的に排除される**（FP ≒ low に集中）。

### 2.3 判例参照（case_citation）
- 抽出 **1,544 件**、court 100% / era 100% 解析成功。最も clean な投入候補。
- 注意: 同一判例が複数ノードから引用される（辺は node→case で多対一。case 本体は
  `cite_key` で正規化・重複排除）。

### 2.4 重複・多法令
- ノード内の同一 (law, article) 二重出現 12 件 → 辺キーで自然に collapse。
- 1 ノードに複数法令 9 件 → それぞれ別辺（正しい）。

成果物: `out_real/legal_link_quality_metrics.csv`、`out_real/legal_links_real.jsonl`。

---

## 3. 提案スキーマ（claim/evidence/serving パターンの踏襲）

> すべて **新規テーブル**。既存 `biblio.bib_toc` / `bib_records` は不変。
> 下記は設計案であり **未適用**（DDL は承認後に `apply_migration` で投入）。

### 3.1 次元（参照先 = 引用グラフのターゲット node）
```
legal.statute_law      (law_id PK, law_name, source='egov', ...)          -- e-gov 法令
legal.statute_article  (law_id, article, uri, has_egov_definition bool,
                        PK(law_id, article), FK law_id)                    -- e-gov 条
legal.case_citation    (case_cite_id PK, cite_key UNIQUE, court, era,
                        year, month, day, raw_text, ...)                   -- 判例 node
```
- `legal.statute_law` / `statute_article` は本リポジトリの `data/egov/*.jsonl`
  （154 法令）から生成。これは「辞書（master）」なので claim ではなく直接投入可
  （ただし control.source_snapshot に登録）。

### 3.2 根拠（evidence）
```
biblio.toc_legal_evidence (
  evidence_id PK,
  bib_id, ordinal        FK->bib_toc(bib_id,ordinal),  -- どのノードか
  match_text,                                          -- マッチした原文字列（例 "民法第七百九条"）
  char_start, char_end,                                -- スパン（再現性）
  source_field default 'toc_text',
  extractor_version,                                   -- legal_links.py の版（冪等性）
  evidence_payload_json jsonb default '{}',
  created_at )
```

### 3.3 claim（辺）
```
biblio.toc_legal_ref_claim (
  claim_id PK,
  bib_id, ordinal              FK->bib_toc,            -- 引用元（source node）
  ref_type CHECK('statute','case'),
  -- target（どちらか一方）
  law_id, article              FK->legal.statute_article,   -- statute のとき
  case_cite_id                 FK->legal.case_citation,     -- case のとき
  primary_evidence_id          FK->toc_legal_evidence,
  confidence numeric CHECK 0..1,
  trust_tier text,                                     -- high/medium/low（人間可読）
  claim_status CHECK('candidate','accepted','rejected','ambiguous','needs_review'),
  decision_method text default 'rule:legal_links@<ver>',
  review_note text,
  created_at, updated_at,
  UNIQUE(bib_id, ordinal, ref_type, law_id, article, case_cite_id)  -- 冪等・重複防止
)
```

### 3.4 公開面（accepted のみ）
```
serving.toc_legal_ref_current  -- view: claim_status='accepted' のみを join 整形
```

---

## 4. 投入ゲート（confidence → claim_status の写像）

| 抽出 confidence | 条件 | claim_status（初期） | 公開(serving) |
|---|---|---|---|
| high | 条番号あり（民法709条 等） | `accepted` | ○ |
| high かつ e-gov 定義突合 | `article_in_egov=true` | `accepted`（trust_tier=top） | ○ |
| medium | 裸の法令名（語境界あり） | `candidate` | ×（要レビュー） |
| low | 短法令名が漢字に埋没 | `needs_review`（既定で除外） | × |
| 判例 court&era 完備 | 100% 該当 | `accepted` | ○ |
| 裸の条番号（法令名なし） | ~9,600 ノード | **投入しない** | × |

- **既定方針（推奨）**: 初回投入は **high（条番号あり）＋ 判例** のみ `accepted`。
  medium は `candidate` として残し、目検サンプリング後に昇格。low は投入対象から外す
  （または `needs_review` で保留し、誤検出 KPI のモニタ用に保持）。
- これにより serving に出るのは **約 347 条文辺 ＋ 1,544 判例辺**（実測）= 高純度。

---

## 5. 投入手順（governance に乗せる）

1. `control.source_snapshots` に抽出スナップショットを登録
   （storage_system='github', artifact_path=PR の `out_real/...`, content_hash, row_count）。
2. `control.ingest_jobs`（job_kind='append_import', target='biblio.toc_legal_ref_claim'）を起票、
   `rows_seen/inserted/rejected` を記録。
3. evidence → claim の順に **冪等 UPSERT**（UNIQUE 制約 + `on conflict do nothing/update`）。
4. `control.releases`（release_kind='other'/'toc', validation_status, approval_status）で
   **検証 → 承認** を通してから `serving` を有効化（active_release_pointer）。
5. 失敗時は previous_release_id へ **rollback**。

---

## 6. 検証クエリ（投入前後の検収ゲート）

- 投入前（staging 上）:
  - `select claim_status, count(*) from ... group by 1`（分布が想定通りか）
  - low/medium の目検 50 件（`医療法人`/`人民法院` 系が accepted に漏れていないこと）
  - FK 整合: 全 `law_id,article` が `legal.statute_article` に存在するか
- 投入後:
  - 孤児辺ゼロ（bib_id,ordinal が bib_toc に実在）
  - serving 件数 ＝ accepted 件数
  - 冪等性: 同じ抽出を再投入して rows_inserted=0

---

## 7. やってはいけないこと（汚染源の明示）

- ❌ 裸の条番号ノード（~9,600）を書誌主題から **推測補完**して law_id を付与する
  （誤 law_id の温床）。やるなら別 ref_type='inferred' + needs_review で隔離。
- ❌ `bib_toc.text` や `bib_records` を書き換える（リンクは別テーブルの辺で持つ）。
- ❌ low confidence を accepted にする（医療法人/人民法院 が混入）。
- ❌ master 辞書（legal.statute_law）を claim と混在させる。

---

## 8. 著者正規化（idea B）の投入も同様の作法で

- `author_normalize` の `author_key` を `biblio.authors.normalized_key` に**上書きしない**。
- 代替案: `authority.person_alias`（alias_kind='normalized_key_v2', source_system='alo:author_normalize'）
  に **alias として追記**し、既存値は保全。名寄せは person への claim 経由。
- これも source_snapshot + ingest_job 登録の上で実施。

---

## 9. 番頭への確認事項（書込み前の判断）

1. 初回 accepted を **「high（条番号）＋判例」に限定**でよいか（推奨）。medium/low の扱い。
2. 次元テーブルの schema 名: `legal.*` 新設でよいか、`biblio.*` 配下に置くか。
3. e-gov 条辞書（`legal.statute_article`）は 154 法令分の **master 直接投入**でよいか。
4. RLS ポリシー（既存テーブルは rls_enabled=true）の付与方針。
5. 判例 node の正規化粒度（現状 court/era/年月日。事件番号・出典は次段）。
