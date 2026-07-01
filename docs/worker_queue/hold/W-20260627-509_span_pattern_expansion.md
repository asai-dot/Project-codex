---
worker_task_id: W-20260627-509
status: hold
priority: P1
owner: claude-code-worker
created_at: 2026-06-27
release_when: W-20260626-501 が PASS かつ span 取りこぼし型 ≥5 が報告されている
depends_on:
  - W-20260626-501
request: docs/HEAD_OPS_CASELINK_SILVER_LOOP_20260627.md (§4.1)
goal: CASELINK L5 dry-run で報告された span 取りこぼし型を case_citation_span.py の正規表現拡張案 + 単体テスト追加案に整理し head に渡す(実装は head・worker は型分類と test fixture 生成)
mode: analysis
allowed_paths:
  - artifacts/caselink/
  - _claude_dispatch/from_worker/
allowed_actions:
  - read_files(L5 dry-run report の span_miss セクション)
  - spawn_subagent (citation 書式の型クラスタリング)
  - write deliverable(span pattern proposal + test fixture)
forbidden_actions:
  - production_db_write
  - salesforce_write
  - box_write_move_rename_delete
  - raw_source_mutation
  - canonical_promotion
  - alo_edges_write
  - pii_in_general_artifact
  - human_gate_bypass
  - design_change_to_case_citation_span   # ← head 領分
exit_criteria:
  - 取りこぼし型を ≤20 件の代表パターン(書式の型のみ・本文不要)に集約
  - 各パターンに正規表現拡張案と test fixture(入力/期待出力)を付与
  - 実装はしない(diff 案のみ)
  - RESULT を done/ または blocked/ に書く
deliverables:
  - artifacts/caselink/span_pattern_proposal_20260627.json
  - _claude_dispatch/from_worker/20260627_span_pattern_RESULT.md
max_attempts: 2
result_expected_filename: W-20260627-509_RESULT.md
---

# Task — span 取りこぼし型 → 正規表現拡張案 + test fixture

case_citation_span.py が拾えない引用書式の型を出し、head が実装するための diff 案と test fixture を作る。**実装は head**(span 正規表現の設計は番頭領分)。

## HEAD OPS 準拠
本タスクは `docs/HEAD_OPS_CASELINK_SILVER_LOOP_20260627.md` の規律に従う(サブエージェント許可・self-check・STOP gate・RESULT 構造・MERTRICS_JSON)。
