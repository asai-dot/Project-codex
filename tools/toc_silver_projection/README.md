# toc_silver_projection — Phase 2 Bronze→Silver projection（SCAFFOLD）

> 状態: **SCAFFOLD（NOT APPLIED）**。本ディレクトリの SQL はすべて owner ratify 後の
> apply gate 経由でのみ実行される。design は **DDDESIGN_PASS_WITH_NOTES**（v1.1 監査）取得済。

## 目的

`biblio.bib_toc`（ブロンズ・フラット）→ `biblio.toc_nodes`（シルバー・リッチ）への
ソース非依存射影。これにより:

- lionbolt の 236,674 ノードを path_text 検索・将来 embedding の対象に
- legallib 投入後は同関数を `p_source='legal-library'` で呼ぶだけで吸収
- 弁コム既存 552,544 行は **触らない**（Phase 2.5 で別途）

## ファイル

| ファイル | 内容 |
|---|---|
| `migration_silver_projection.sql` | (A) `toc_nodes` 列追加（v1.2）+ (B) `toc_projection_run` manifest + (C) `fn_project_toc_silver()` 本体 + (D) `depth=tree_depth` COMMENT |
| `verify_silver_projection.sql` | 適用後の検証クエリ集（parent欠落=0 / depth整合 / bencom非接触 / 9クラス acceptance sample）|
| `rollback_silver_projection.sql` | 撤去手順（run単位 / source単位 / 完全撤去）|

## ゲート進行

| Step | 内容 | gate | DB |
|---|---|---|---|
| **DONE** | v1.1 design 監査 → **DDDESIGN_PASS_WITH_NOTES** | DDDESIGN | 0 |
| **DONE** | v1.2 addendum + SQL草案 + checksum contract + 本SCAFFOLD | review | 0 |
| **NEXT** | migration review 監査再投函 | migration_review | 0 |
| | apply ratify（CREATE FUNCTION / ALTER TABLE / manifest テーブル） | apply gate | DDL のみ |
| | dry-run（manifest INSERT 無し、戻り値 JSON のみ）| run gate | 0 |
| | 本番 run（`p_source='lionbolt'`, `p_dry_run=false`） | run gate | INSERT のみ |
| | acceptance sample 検証・メトリクス記録 | review | 0 |
| | legallib 投入後、`p_source='legal-library'` で同関数 | run gate | INSERT のみ |

## v1.2 で何が変わったか（PASS notes 反映）

1. `toc_nodes.depth` を `tree_depth` として `COMMENT ON COLUMN` で明文化（note #1）
2. acceptance sample に `high_root_book_root` クラス追加（note #2）
3. `CHECKSUM_CONTRACT_v1`（別紙）に従い列順・NULL sentinel・hash 方式を固定（note #3）
4. bencom 非接触は 4要素複合判定（rows / key_set_sha256 / aggregate_sha256 / touched_count）、不一致で自動 ROLLBACK（note #4）
5. `embedding_status` / `embedding_stale_reason` を CHECK制約 enum に（note #5）
6. manifest に `bencom_touched_count NOT NULL DEFAULT 0`、!=0 で関数が RAISE（note #6）
7. dry-run は manifest INSERT しない（read-only に保つ）（note #7）

## 参照

- `artifacts/phase2_silver_design_20260626/PLAN_PHASE2_BRONZE_TO_SILVER_v1_1.md` — v1.1 本体
- `artifacts/phase2_silver_design_20260626/PLAN_PHASE2_v1_2_PASS_NOTES_ADDENDUM.md` — v1.2 差分
- `artifacts/phase2_silver_design_20260626/CHECKSUM_CONTRACT_v1.md` — bencom非接触契約
- `artifacts/phase2_silver_design_20260626/PROFILING_REPORT_20260627.md` — 実データ根拠
