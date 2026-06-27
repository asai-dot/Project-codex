---
worker_task_id: W-20260627-503
status: queued
priority: P1
owner: claude-code-worker
created_at: 2026-06-27
request: docs/CASE_HUMAN_REVIEW_SAMPLE_FRAME_20260618.md (§6 第2バッチ)
goal: Q2 判例引用(OPAC/CiNii case citation, worksheet 1,648/9 batch)から層化40件+負例control 8件の reviewer worksheet を生成し、judgment-level の decision overlay を 0→N に動かせる状態にする(判定記入は人手・範囲外)
mode: implementation
requires_systems:
  - scripts/case_review_packet.py (Q1配管・再利用)
  - Q2 判例引用キュー実体(OPAC/CiNii citation worksheet)
depends_on:
allowed_paths:
  - artifacts/review/
  - _claude_dispatch/from_worker/
allowed_actions:
  - read_files(Q2 判例引用キュー)
  - ensure_engine(precedent-object-progress から case_review_packet.py 取得)
  - run scripts/case_review_packet.py build (Q2向け sample_seed/strata 微調整可)
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
  - Q2 batch-1(≈183行 = 9バッチの1本)から層化40件+負例control 8件の worksheet を生成
  - collision group 3 を必ず含める(frame §6)
  - worksheet に raw/商用本文を含まない(正規化キー + expected_check のみ)
  - 判定(accept/reject)を一切記入していない
  - Q2 キュー実体を特定できなければ blocked
  - RESULT を done/ または blocked/ に書く
deliverables:
  - artifacts/review/caserev_q2_worksheet_20260627.csv
  - artifacts/review/caserev_q2_manifest_20260627.json
  - _claude_dispatch/from_worker/20260627_caserev_q2_build_RESULT.md
max_attempts: 2
result_expected_filename: W-20260627-503_RESULT.md
---

# Task — 人手レビュー第2バッチ Q2 判例引用 worksheet 生成

frame正本 `docs/CASE_HUMAN_REVIEW_SAMPLE_FRAME_20260618.md` §6 の第2バッチ。Q1 と異なり **judgment-level**(判決単位)＝高価値。configはQ1の `caserev_q1_v0` と分離し `caserev_q2_v0_20260627` を発番(frozen)。

## 手順
0. engine 準備: 無ければ `git checkout origin/claude/precedent-object-progress-gwb47u -- scripts/case_review_packet.py` で取得。
1. Q2 判例引用キュー実体(seed 5,010 → worksheet 1,648・9 batch・P1 3,569/P2 1,427)を Mac 上で特定。**特定不能なら blocked**。
2. batch-1(≈183行)を取得し、collision group(同一引用→複数事件候補の3群)を必ず含めて入力スキーマへ整形:
   `{ref_id, citation_norm, candidate_case_key, forum_code?, decision_date?, case_number_norm?, flags:[batch_p1/collision_group/external_id_only/forum_mismatch/era_ambiguous]}`
3. `case_review_packet.py build` を Q2 用に呼ぶ(必要なら STRATA/expected_check を Q2 文脈で軽く調整。frame_version='caserev_q2_v0_20260627' を刻印)。S-A=batch_p1 主軸/S-COL=collision/S-FM=forum_mismatch/S-ERA=era_ambiguous/S-NEG=負例8。総計40件+負例。
4. worksheet と manifest(frame_version/total/by_stratum/seed/collision_groups_included) を commit。

## Do Not
判定記入(人手専管)・raw本文・canonical/alo_edges/claim_support(HOLD)・case_review_packet.py の写像則改変(STRATA/expected_check の最小限調整は OK、決定語彙・負例ロジックは触らない)。

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
