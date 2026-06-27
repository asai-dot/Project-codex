<!--
TO BE SUBMITTED to Box gpt_ometsuke/to_gpt (folder 387372772162)
  Expected RESULT in from_gpt (387373353464):
    20260627_phase2_silver_migration_review_DDMIGRATION_RESULT.md
  Builds on: 20260627_phase2_silver_projection_v1_1_DDDESIGN_RESULT.md => PASS_WITH_NOTES
  Box file id: 2312911876330
  Box link: https://asai-lo.app.box.com/file/2312911876330
  Submitted at: 2026-06-27 07:34 PT
-->

---
request_id: 20260627_phase2_silver_migration_review_DDMIGRATION
topic: phase2_bronze_to_silver_projection_migration_review
gate: DDMIGRATION
status: queued
result_expected_filename: 20260627_phase2_silver_migration_review_DDMIGRATION_RESULT.md
audit_kind: sql_migration_review
priority: high
prior_design_pass: 20260627_phase2_silver_projection_v1_1_DDDESIGN_RESULT.md (PASS_WITH_NOTES, 7 notes)
notes_addressed: [N1_depth_comment, N2_high_root_sample, N3_checksum_contract,
                  N4_bencom_composite, N5_status_enum, N6_touched_gate, N7_dryrun_readonly]
related_artifacts_in_repo:
  - tools/toc_silver_projection/migration_silver_projection.sql
  - tools/toc_silver_projection/verify_silver_projection.sql
  - tools/toc_silver_projection/rollback_silver_projection.sql
  - tools/toc_silver_projection/README.md
  - artifacts/phase2_silver_design_20260626/PLAN_PHASE2_v1_2_PASS_NOTES_ADDENDUM.md
  - artifacts/phase2_silver_design_20260626/CHECKSUM_CONTRACT_v1.md
gate_rules: READ_ONLY_STRICT を維持。本REQUESTは static SQL レビューのみ依頼。
            CREATE FUNCTION / ALTER TABLE / manifest INSERT / projection 実行は本監査対象外。
---

# REQUEST 20260627_phase2_silver_migration_review_DDMIGRATION
# SQL / migration / fixture の静的レビュー依頼

## 0. 概要

Phase 2 v1.1 が `DDDESIGN_PASS_WITH_NOTES` を取得（M1-M9 すべて CLOSED、7 blocking notes）。
本REQUESTは v1.2 addendum + checksum contract + SQL草案 + verify/rollback を **静的レビュー**
として送り、CREATE FUNCTION / ALTER TABLE の **apply 前**の最終点検を依頼する。

DB状態: mutation 0 / DDL 0 / 関数作成 0 を維持。

## 1. PASS notes 7件への閉じ方（要約）

| Note | 実装 |
|---|---|
| N1 depth=tree_depth 明文化 | `migration_silver_projection.sql` (D) で `COMMENT ON COLUMN biblio.toc_nodes.depth` |
| N2 high_root_book を sample に | `verify_silver_projection.sql` 6f) でクラス追加 |
| N3 checksum contract 別紙固定 | `CHECKSUM_CONTRACT_v1.md`（列順・NULL sentinel=`\N`・区切り U+001F・sha256 二層） |
| N4 bencom非接触 複合判定 | function 内で before/after 4要素 jsonb 比較 + 自動 RAISE/ROLLBACK |
| N5 status/reason enum | DDL CHECK 制約 `embedding_status IN ('missing','active','stale')` 等 |
| N6 manifest gate condition | `bencom_touched_count INT NOT NULL DEFAULT 0` + 関数末尾 assertion |
| N7 dry-run は read-only | `IF p_dry_run THEN RETURN 戻り値; END IF;` で何も書かない |

## 2. レビュー観点（重要度順）

1. **CTE / WITH RECURSIVE の正しさ**
   - `_silver_tmp` の `parent_ordinal` サブクエリ（per row 相関）は計算量上現実的か（lionbolt 236k 行）
   - `_silver_with_depth` の recursive で cycle 検出 / 終端は保証されるか
   - `_silver_final` の path_arr 連結で深さ爆発（多段木）の上限は要らないか
2. **冪等性**
   - `ON CONFLICT (toc_node_id)` の UPDATE 条件 `IS DISTINCT FROM` は path/title/depth/parent_toc_node_id の4列。embedding_input_hash の差分も UPDATE トリガにすべきか（現状: 上記4列が変わらない限り status を stale にしない）
3. **bencom checksum**
   - `digest(...)` 入力に embedding 列を除外。除外が`equal=true`保証に十分か（embedding が後で生成されても "構造列" 不変なら検出が可）
   - `string_agg` の ORDER BY と `concat_ws(chr(31), ...)` のNULL扱い（concat_ws は NULL を skip するため明示 coalesce 必要 → 採用済み）
4. **権限・search_path**
   - `SECURITY INVOKER` + `SET search_path = pg_catalog, biblio`。bencom 既存行を UPDATE できる権限を持つ呼出元で叩いたとき、本契約はその権限を**実害なし**に保てるか（contract 比較で必ず止まる）
5. **manifest 例外時の整合**
   - `RAISE EXCEPTION` 経路で manifest INSERT がトランザクション全体と ROLLBACK されること（本関数の TX は呼出元）
   - 部分成功で manifest 行が残らないか（残らない設計）
6. **CHECK 制約**
   - 既存 552k 行の `embedding_status` は NULL（追加直後）。CHECK は NULL 許容のため通る。Phase 3 backfill で 'missing'→'active' に上げる前提で問題ないか
7. **verify_silver_projection.sql の網羅性**
   - 9クラス（root/depth2/depth3+/level_gap/multi_root/high_root/long_title/page_null/bencom_negative）で受入監査として十分か
8. **rollback の安全性**
   - source 単位 DELETE は `projection_run_id IS NOT NULL` で bencom 既存（NULL）を保護。十分か

## 3. 期待 RESULT 形式

`from_gpt/20260627_phase2_silver_migration_review_DDMIGRATION_RESULT.md`:

- `DDMIGRATION_PASS`：apply ratify に進めて良い
- `DDMIGRATION_PASS_WITH_NOTES`：apply 前修正必須の blocking notes 列挙
- `DDMIGRATION_MODIFY_REQUIRED`：required_patches 列挙、再投函
- `DDMIGRATION_NEED_MORE`：追加情報要求

## 4. 参照

- migration: `tools/toc_silver_projection/migration_silver_projection.sql`
- verify: `tools/toc_silver_projection/verify_silver_projection.sql`
- rollback: `tools/toc_silver_projection/rollback_silver_projection.sql`
- addendum: `artifacts/phase2_silver_design_20260626/PLAN_PHASE2_v1_2_PASS_NOTES_ADDENDUM.md`
- contract: `artifacts/phase2_silver_design_20260626/CHECKSUM_CONTRACT_v1.md`
- v1.1 design RESULT: Box file 2312572897698
