# A0 — biblio 暫定モデル ↔ ALO 本体モデル 接続契約（Phase A の前提・必読）

> status: contract (実装前の合意文書) / 起案 2026-06-03 / owner: 浅井
> 由来: ROADMAP_alo_next.md への owner レビュー（80点・条件付き採用）の差し戻し指示を確定したもの。
> 関連: `docs/ROADMAP_alo_next.md`(v2) / `docs/session_record_20260602.md`(v8) / 20_architecture / 35_link_layer。

## §0 方針決定（今ここで決める唯一のこと・確定）
> **当面 `biblio.* / authority.* / control.*`（codex実体）を「作業用実体（working substrate）」として育てる。
> ただし恒久正本（canonical body）は将来の ALO本体 `cases / statutes / alo_works / alo_persons /
> alo_terms / alo_hubs / alo_entity_links / alo_edges / fingerprints` 側に置く。**

含意（この契約の存在理由）:
- `biblio.terms`（語彙）/`biblio.bib_records`（書誌）/`biblio.bib_terms`（リンク）は **ALO本体への供給源
  （feedstock）であって、ALO本体ではない**。
- よって `biblio.*` に積むものはすべて、将来 `alo_*` へ移送できる形（crosswalk付き・出所付き・弱リンクは弱いまま）で
  入れる。**「仮の本体」化を物理的に防ぐ**のが A0 の目的。

## §1 crosswalk（暫定ID ↔ 将来ALO URI 対応表）= A0-1
`biblio.*` の各行に、将来の `alo_*` エンティティ/URI への対応を持たせる。提案テーブル（**DDLは提案・未適用**。
配置/命名は codex/花岡 と合意の上で）:

```sql
-- 提案: control.entity_crosswalk （統治レイヤに置く＝供給源→本体の移送台帳）
CREATE TABLE control.entity_crosswalk (
  crosswalk_id   bigserial PRIMARY KEY,
  local_schema   text NOT NULL,              -- 例 'biblio'
  local_table    text NOT NULL,              -- 'terms' / 'bib_records' / 'bib_terms'
  local_id       text NOT NULL,              -- 'egovcard:子会社' / 'alo:book:isbn:...' / (bib_id,term_id)
  future_entity  text NOT NULL,              -- 'alo_term'/'alo_hub'/'alo_work'/'alo_edge'/'fingerprint'
  future_uri     text,                       -- 'alo:term:jp_statutory_definition:子会社' / 'alo:book:isbn:...'
  mapping_status text NOT NULL DEFAULT 'unresolved'  -- unresolved|candidate|approved|deprecated
                 CHECK (mapping_status IN ('unresolved','candidate','approved','deprecated')),
  basis          text NOT NULL,              -- 'egov_anchor'/'ndl_subject'/'manual'/'dedup'/'isbn'
  release_id     text,                        -- → control.releases
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (local_schema, local_table, local_id, future_entity)
);
```
運用: `biblio.*` に投入する各バッチで、対応する crosswalk 行も起こす（mapping_status=candidate）。将来 `alo_*` を
立てたら approved にし、移送。これで「どの暫定行がどの本体に化けるか」が常に追える＝二重管理を移行で解消可能にする。

将来URIの当てはめ（仕様 `20_architecture` §5 / `35_link` に整合）:
- 語彙 → `alo:term:{scheme_id}:{source_item_key}`（例 `alo:term:jp_statutory_definition:子会社`）、hub は `alo:hub:{slug}`。
- 書誌 → `alo:book:isbn:{isbn13}`（蔵書は既に alo_uri を bib_id に採用済＝そのまま future_uri）。
- リンク → `alo_edges`（後述の弱リンクは edge_type を弱い語彙にマップ）。

## §2 bib_terms は「弱い主題リンク」— 強いエッジと混ぜない = A0-2
蔵書 `ndl_subjects / genre / tags`（将来は巻末索引/TOC）から語彙へ張るリンクは、最初は**粗い主題関連**であり、
**「その文献がその論点を支持/解釈している」という強い関係ではない**。`alo_edges` の `interprets / doctrine /
evaluates`（明示・論理前提）と**絶対に混ぜない**（混ぜるとAIが文献の論点支持を過大評価する）。

弱リンクの関係語彙（relation）:
```text
book_subject_matches_term   -- ndl_subjects が term に一致
book_tagged_with_term       -- tags が term に一致
book_about_term             -- genre/分類が term 圏に対応
toc_mentions_term           -- (Phase C) TOC見出しに term が出現
```
これらは将来 `alo_edges` に移す際、**弱い edge_type（例 about/subject_of、weight低、assertion_mode=vendor_implicit）**
にのみマップ可。`interprets/doctrine` への昇格は人手 or 本文根拠が要る（別途）。

### bib_terms リンクの保持項目 = A0-3
実 `biblio.bib_terms` は現状 `(bib_id, term_id)` の2列のみ＝弱リンクの根拠を持てない。**提案**: 豊富なメタを別表に持つ
（薄い結合表 bib_terms は将来の canonical join 用に温存し、根拠付きリンクは side table へ）:

```sql
-- 提案: biblio.bib_term_links （根拠付き弱リンク。codex/花岡 と要合意）
CREATE TABLE biblio.bib_term_links (
  bib_id          text NOT NULL,             -- → biblio.bib_records
  term_id         text NOT NULL,             -- → biblio.terms
  relation        text NOT NULL,             -- §2 の弱relation語彙
  match_basis     text NOT NULL,             -- 'ndl_subject'/'genre'/'tag'/'toc'
  source_field    text NOT NULL,             -- 'ndl_subjects'/'genre'/'tags'/'toc.text'
  source_value    text NOT NULL,             -- マッチ元の生値
  normalized_value text,                     -- 正規化後（NFKC等）
  confidence      numeric(4,3) NOT NULL,     -- 一致の強さ
  status          text NOT NULL DEFAULT 'suspect'  -- suspect|provisional|canonical
                  CHECK (status IN ('suspect','provisional','canonical')),
  release_id      text,
  evidence_json   jsonb NOT NULL DEFAULT '{}',
  created_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (bib_id, term_id, relation)
);
```

## §3 554 canonical と 5,638 unreviewed を混ぜない = A0-4
- 現 `biblio.terms` 554件は **canonical（浅井承認済）**。ここに未レビューの 5,638（gated high&unreviewed）を
  **無印で混ぜてはならない**。
- 取り扱い（案1採用・実務的）:
  - **案1**: `biblio.terms` に入れる場合は `raw.canonical_status` / `term_status` で `provisional|unreviewed` を**必須**にし、
    **検索・リンク生成は既定で canonical のみ**（unreviewed を混ぜない制約・VIEW）。
  - 案2: `biblio.term_candidates` を別に設け、承認分だけ `biblio.terms` へ昇格。
- **5,638 はまず投入せず read-only 候補辞書として一致率測定**（A3）。投入する場合も上記の status 明示が条件。

## §4 検索ベンチ50件は「今・Phase A 着手前」に作る = A0-5（差し戻し指示で前倒し）
理由: **投入前ベースラインは今しか測れない**（語彙554・蔵書6,524・`bib_terms`未投入の現状）。
- ベンチ雛形: `docs/search_bench/baseline_queries.template.md`（本コミットで作成）。
- 50件は**浅井の実務相談類型**から作る（owner主導）。各クエリに期待到達（概念/条文/蔵書）と測定指標
  （見出し語ヒット率・条文到達率・関連蔵書到達率・誤ヒット率）。
- 実行は Phase D でよいが、**ベースライン測定は bib_terms 投入前に1回**走らせる。

## §5 実装ガードレール（全 Phase 共通・A0-7）
- destructive import 禁止（生は非改変）。
- **source 単位で rollback 可**（`DELETE … WHERE source=…`）。冪等（`ON CONFLICT DO NOTHING`）。
- 全投入は `control.releases`（validation/approval、approved_by、rollback_target）に記録し、
  **candidate→machine-gated→provisional→canonical** の梯子を通す。
- 大容量投入は psql（Session pooler / 一時ロール）。SQLエディタは ~340KB 上限。「データ投入プレイブック」に従う。

## §6 改訂 Phase 順（A0 と reorder を反映）
```text
A0  本契約（crosswalk / 弱リンク定義 / candidate分離 / ガードレール）を確定 ← まずここ
A1  検索ベンチ50件をベースラインとして作成・現状測定（bib_terms 未投入の今）
A2  554 terms と 蔵書 subject/genre/tags の一致率を read-only 測定
A3  5,638 high&unreviewed を「投入せず」候補辞書として read-only 一致率測定
A4  554版 vs 5,638版 の差分比較（どちらで橋を張るか決める）
A5  精度許容なら bib_term_links に suspect/provisional 投入（§2弱relation・§3メタ付き）
A6  サンプル監査/人手レビュー後、一部だけ canonical 化（release承認）

B1  条見出し・見出し→条リンクを「弱い statute_term_link」としてDB化
B2  asai-bookshelf × bencom-library の重複候補を抽出（TOCチャンク化より前に）
B3  重複に fingerprint/work_identifier 相当の crosswalk を作る（§1）
C1  その後 bencom TOC → chunk（同一文献の重複チャンクを避ける）

D   合流＋検索ベンチ実行（投入前後比較で価値を実測）
E   ALO本体（cases/statutes/alo_edges/CaseBundle/MCP）— owner/花岡主導、本2軸は feedstock
```

## §7 受け入れ・禁止（owner確定）
- 採用: 可（A0 を噛ませる条件で）。
- 禁止: **5,638 未レビュー語彙を canonical と同列に扱うこと**。弱主題リンクを強いエッジ(interprets/doctrine)に混ぜること。
- 優先: 検索ベンチ50件の先行作成 / bib_terms の弱リンク化 / 将来URI crosswalk。
