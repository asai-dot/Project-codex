---
worker_task_id: W-20260627-506
status: hold
priority: P1
owner: claude-code-worker
created_at: 2026-06-27
release_when: W-20260627-503 が PASS かつ Q2 worksheet に reviewer 記入 (decisions_made >= 24/40) が完了
depends_on:
  - W-20260627-503
request: docs/HEAD_OPS_CASELINK_SILVER_LOOP_20260627.md (§4.1)
goal: Q2 記入済 worksheet を tally し judgment-level の Tier B 自動化条件(per-stratum false-positive・collision_group の機械判定可否)を抽出する。Tier B precision 0.95 を満たす自動 accept 条件の候補を出す(canonical 反映なし・提案のみ)
mode: analysis
allowed_paths:
  - artifacts/review/
  - artifacts/caselink/
  - _claude_dispatch/from_worker/
allowed_actions:
  - read_files(artifacts/review/caserev_q2_worksheet_*)
  - ensure_engine(case_review_packet.py)
  - run scripts/case_review_packet.py tally
  - spawn_subagent (chunked stratum 分析)
  - write deliverable(tier_b_auto_accept_proposal)
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
  - fill_unknown_with_generalities
exit_criteria:
  - decisions_made >= 24 (worksheet 40件のうち6割以上)
  - negative_control.healthy = true
  - tier_b_auto_accept_proposal.json(stratum別の機械化可否ヒューリスティクス)
  - RESULT を done/ または blocked/ に書く
deliverables:
  - artifacts/caselink/q2_tally_report_20260627.json
  - artifacts/caselink/tier_b_auto_accept_proposal_20260627.json
  - _claude_dispatch/from_worker/20260627_q2_tally_RESULT.md
max_attempts: 2
result_expected_filename: W-20260627-506_RESULT.md
---

# Task — Q2 tally + Tier B 自動化条件抽出

W-503 で生成した worksheet に reviewer が記入したら本タスク起動。Tier B(外部ID/fuzzy のみの跨ぎ候補)を機械 accept してよい条件を、judgment-level の実データで初めて出す。canonical/alo_edges 反映なし=提案のみ。

## 手順
1. `case_review_packet.py tally artifacts/review/caserev_q2_worksheet_*.csv` で tally。
2. stratum 別 false-positive(reject率)を算出。S-A(batch_p1) / S-COL(collision_group) / S-FM(forum_mismatch) / S-ERA(era_ambiguous) / S-NEG(負例)。
3. **自動 accept 条件の候補**:
   - S-A reject率 < 5% かつ negative healthy なら「batch_p1 単独で auto-accept 可」候補。
   - S-COL は collision_group の sub-pattern 別(同事件番号→複数事件 vs 同タイトル→複数事件)で分けて再集計。
   - S-FM(forum_mismatch) reject率が高ければ「forum一致を auto条件に必須」。
   - S-ERA(era_ambiguous) は元号正規化のバグ検出。reject 内訳を見て CASEID-002 への follow-up を提案。
4. proposal は実装提案のみ(diff 案 / 影響範囲 / 想定 precision)。**実装は head が判断**。

## HEAD OPS 準拠
本タスクは `docs/HEAD_OPS_CASELINK_SILVER_LOOP_20260627.md` の規律に従う(サブエージェント許可・self-check・STOP gate・RESULT 構造・MERTRICS_JSON)。
