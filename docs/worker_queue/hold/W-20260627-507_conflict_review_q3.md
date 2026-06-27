---
worker_task_id: W-20260627-507
status: hold
priority: P1
owner: claude-code-worker
created_at: 2026-06-27
release_when: W-20260627-504 が PASS で conflict_review 候補 top100 が出ている
depends_on:
  - W-20260627-504
request: docs/HEAD_OPS_CASELINK_SILVER_LOOP_20260627.md (§4.1)
goal: D1-LIC 5,475 corroborate で検出した conflict_review 候補(同一性主張だが採番割れ=false split 疑い)から top100 を Q3 拡張 worksheet として人手裁定可能化(case_review_packet.py を corroborate 拡張で再利用)
mode: implementation
allowed_paths:
  - artifacts/review/
  - artifacts/caselink/
  - _claude_dispatch/from_worker/
allowed_actions:
  - read_files(artifacts/caselink/d1lic_conflict_review_candidates_*.jsonl)
  - ensure_engine(case_review_packet.py)
  - run scripts/case_review_packet.py build (caserev_q3_v0_20260627 frame で)
  - spawn_subagent (conflict 候補の chunked 整形)
  - write deliverable(q3 worksheet + manifest)
forbidden_actions:
  - production_db_write
  - salesforce_write
  - box_write_move_rename_delete
  - raw_source_mutation
  - alo_edges_write
  - canonical_promotion
  - reviewed_true_backfill
  - ai_estimate_as_human_decision
  - pii_in_general_artifact
  - human_gate_bypass
  - merge_canonical_cases
exit_criteria:
  - top100 conflict_review を Q3 worksheet 化(decision 空欄)
  - 各候補に「false_split 疑い理由」(同一外部ID / 同一 docket+forum / 同一NII等の根拠)を 1 行で expected_check に
  - 商用本文を含まない(正規化キーのみ)
  - RESULT を done/ または blocked/ に書く
deliverables:
  - artifacts/review/caserev_q3_conflict_worksheet_20260627.csv
  - artifacts/review/caserev_q3_manifest_20260627.json
  - _claude_dispatch/from_worker/20260627_q3_conflict_build_RESULT.md
max_attempts: 2
result_expected_filename: W-20260627-507_RESULT.md
---

# Task — conflict_review top100 を Q3 worksheet 化(recall 回収の人手裁定)

W-504 で出た「同一事件性が示唆されるのに採番が割れている」候補を人手裁定キューへ。これが accept されれば**false_merge=0 を維持したまま**初の recall 回収(別 case_key だった2件を「実は同じ」と裁定)が走る(canonical 反映は別 GO=HOLD)。

## HEAD OPS 準拠
本タスクは `docs/HEAD_OPS_CASELINK_SILVER_LOOP_20260627.md` の規律に従う(サブエージェント許可・self-check・STOP gate・RESULT 構造・MERTRICS_JSON)。
