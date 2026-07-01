---
worker_task_id: W-20260627-508
status: hold
priority: P1
owner: claude-code-worker
created_at: 2026-06-27
release_when: W-20260627-505 が PASS かつ baseline で false_merge > 0 の case_key リストがある
depends_on:
  - W-20260627-505
request: docs/HEAD_OPS_CASELINK_SILVER_LOOP_20260627.md (§4.1)
goal: gold baseline で false_merge>0 になった case_key を分析し、G6(cross-source conflict)強化条件 / G1-G5 の追加ガード条件を head 向け実装提案にする(設計改変は head 単独・worker は分析のみ)
mode: analysis
allowed_paths:
  - artifacts/caselink/
  - _claude_dispatch/from_worker/
allowed_actions:
  - read_files(gold + bind_guard 出力)
  - spawn_subagent (pattern クラスタリング)
  - write deliverable(false_merge_postmortem_proposal)
forbidden_actions:
  - production_db_write
  - salesforce_write
  - box_write_move_rename_delete
  - raw_source_mutation
  - canonical_promotion
  - alo_edges_write
  - claim_support_eligibility
  - reviewed_true_backfill
  - pii_in_general_artifact
  - human_gate_bypass
  - design_change_to_bind_guard   # ← worker は実装しない。head 領分
exit_criteria:
  - false_merge ペアの代表クラスタ(誤統合パターン)を分類(例: era_mismatch / branch_collision / external_id_typo)
  - 各クラスタごとに「ガード追加案」(G6 拡張 / new G7 / fp_guard 等)を頻度付で
  - 実装はしない。head に向けた diff 提案のみ
  - RESULT を done/ または blocked/ に書く
deliverables:
  - artifacts/caselink/false_merge_postmortem_20260627.json
  - _claude_dispatch/from_worker/20260627_false_merge_postmortem_RESULT.md
max_attempts: 2
result_expected_filename: W-20260627-508_RESULT.md
---

# Task — false_merge>0 ケースの誤統合パターン抽出 + ガード強化提案

baseline で false_merge=0 が崩れた case_key を見て、誤統合パターンをクラスタリング → ガード追加案を head に渡す。**実装は head**(case_bind_guard の設計改変は番頭領分)。

## HEAD OPS 準拠
本タスクは `docs/HEAD_OPS_CASELINK_SILVER_LOOP_20260627.md` の規律に従う(サブエージェント許可・self-check・STOP gate・RESULT 構造・MERTRICS_JSON)。
