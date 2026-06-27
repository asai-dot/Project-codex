---
worker_task_id: W-20260626-502
status: queued
priority: P1
owner: claude-code-worker
created_at: 2026-06-26
request: docs/WORKER_TASK_PACKET_caserev_q1_build_20260626.md
goal: Q1 法令参照候補(D1KOS↔OPAC statute ref, 281/P1 77, risk flag既付与)を入力に case_review_packet.py で人手レビュー第一バッチの worksheet を生成し、decision overlay 0→N を動かせる状態にする(判定記入は人手・範囲外)
mode: implementation
requires_systems:
  - branch claude/precedent-object-progress-gwb47u の scripts/case_review_packet.py
  - Mac 上の Q1 法令参照レビューキュー実体(merged_review_queue / D1KOS報告系)
depends_on:
allowed_paths:
  - artifacts/review/
  - _claude_dispatch/from_worker/
allowed_actions:
  - read_files(Q1 法令参照キュー)
  - ensure_engine(precedent-object-progress ブランチから scripts/case_review_packet.py を取得)
  - run scripts/case_review_packet.py build
  - write deliverable(worksheet csv 正規化キーのみ + manifest)
forbidden_actions:
  - production_db_write
  - salesforce_write
  - box_write_move_rename_delete
  - raw_source_mutation
  - ai_estimate_as_human_decision
  - pii_in_general_artifact
  - human_gate_bypass
  - fill_unknown_with_generalities
  - stall_whole_run_waiting_for_input
exit_criteria:
  - caserev_q1_worksheet(層化 S-A/B/C/D/E + 負例control 8, decision 全空欄)と manifest を出力している
  - worksheet に raw/商用本文を含めていない(正規化キー + expected_check のみ)
  - 判定(accept/reject)を一切記入していない(人手専管)
  - Q1キュー実体を特定できなければ blocked(探した場所・件数を明記)
  - RESULT を done/ または blocked/ に書く
deliverables:
  - artifacts/review/caserev_q1_worksheet_20260626.csv
  - artifacts/review/caserev_q1_manifest_20260626.json
  - _claude_dispatch/from_worker/20260626_caserev_q1_build_RESULT.md
max_attempts: 2
result_expected_filename: W-20260626-502_RESULT.md
---

# Task — 人手レビュー第一バッチ Q1 worksheet 生成（L-RV / S5）

詳細発注は `docs/WORKER_TASK_PACKET_caserev_q1_build_20260626.md`、frame正本 `docs/CASE_HUMAN_REVIEW_SAMPLE_FRAME_20260618.md`、手順 `docs/REVIEWER_GUIDE_caserev_q1_20260626.md`。**worksheet 生成まで。判定は人手専管。**

## 手順
0. **engine 準備**: 無ければ `git fetch origin claude/precedent-object-progress-gwb47u` →`git checkout origin/claude/precedent-object-progress-gwb47u -- scripts/case_review_packet.py app/data/case_identity/caserev_q1_sample_candidates.jsonl` 取得 → `python3 scripts/test_case_review_packet.py` green 確認。
1. **Q1 法令参照候補(281)を特定**。frame §1/§3 の strong 281(P1 77/P2 135/P3 69)・risk flag(cross_root/multi_law_token/suffix/provisional_kos/p1_top_root_aligned は既付与)。**確信を持って特定できなければ blocked**。
2. **入力スキーマへ整形** `caserev_q1_candidates.jsonl`(1行=1候補・**正規化キーのみ・商用/raw本文除外**): `{ref_id, law_name, article, d1kos_node, article_side_root, taxonomy_root, flags:[...]}`。既存 risk flag を flags に。
3. `python3 scripts/case_review_packet.py build caserev_q1_candidates.jsonl artifacts/review/caserev_q1_worksheet_20260626.csv` → 層化(S-A全件/S-B・E各10/S-C・D全件)+負例control 8。
4. manifest `artifacts/review/caserev_q1_manifest_20260626.json`: `{frame_version, total_candidates, by_stratum, negative_control_n, seed}`。
5. worksheet(decision空欄)と manifest を commit。RESULT に件数・stratum分布・キュー出所を記す。

## Do Not
判定(accept/reject)の記入＝人手専管。raw/商用本文を worksheet に入れない。canonical/alo_edges/claim_support/reviewed=true 反映(全HOLD)。case_review_packet/frame の設計改変(番頭領分)。

---
## HEAD OPS 準拠(本タスク共通)
本タスクは `docs/HEAD_OPS_CASELINK_SILVER_LOOP_20260627.md` の規律に従う。要点:
- **サブエージェント許可**: chunked work(500-1000件単位の並列)・independent search(入力場所特定)・adversarial verify(自己refute)で `Agent` を使ってよい。HOLD境界の判断は singleton(分散しない)。allowed_paths/forbidden_actions はサブエージェントも継承。
- **self-check**: RESULT 末尾に必須メトリクス節を出す:
  ```
  ## MERTRICS_JSON
  {"records_in":N,"records_processed":N,"elapsed_sec":N,
   "key_metrics":{...task固有...},
   "subagent_calls":N,"halts":N,"blocked_reason":null|str}
  ```
- **STOP gate**: §9 のいずれかに該当したら自走停止 → head に判定依頼(部分実行でOK、強行しない)。EMERGENCY(forbidden違反/PII露出/捏造数値疑惑)は即時 blocked + owner 通知。
- **RESULT 構造**: `WORKER_PASS|WORKER_PASS_WITH_NOTES|WORKER_BLOCKED|WORKER_FAIL`(先頭行) → 要約3行 → 主要メトリクス → 完了/未完了内訳 → 次手提案(head が hold/ から該当タスクを queue するため)。
- **検収**: head は HEAD_OPS §3.2 の self-check 値を見て label を確定し、PASS で対応する hold/W-NNN を queue へ。
