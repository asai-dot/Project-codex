---
worker_task_id: W-20260627-505
status: queued
priority: P1
owner: claude-code-worker
created_at: 2026-06-27
request: docs/CASE_OBJECT_OVERVIEW_and_production_handoff_20260623.md (P1: gold set 実構築)
goal: NII∩D1 12,661 正例と各ハード負例4型(same_number_diff_forum / merged_sibling_docket / provisional_no_natural_key / era_decision_date_mismatch)を実 corpus から抽出して案件gold集合を生成し、case_eval で①〜⑤の baseline 精度(false_merge_rate, precision_by_tier, B-cubed, bind結果との突合)を初めて実数で出す
mode: implementation
requires_systems:
  - scripts/case_eval.py / case_bind_guard.py / case_vocab.py
  - 実 NII corpus (hanrei.ttl 65,855件) + D1-Law 観測群 + 各判例DB observations
  - app/data/case_identity/case_eval_gold_template.jsonl (スキーマ正本)
depends_on:
allowed_paths:
  - artifacts/caselink/
  - app/data/case_identity/  # gold 実体ファイル書出
  - _claude_dispatch/from_worker/
allowed_actions:
  - read_files(NII hanrei.ttl, D1-Law observations, 各判例DB)
  - ensure_engine(precedent-object-progress から case_eval / case_bind_guard / case_vocab 取得)
  - run case_eval(gold, pred)
  - write gold jsonl + baseline report
forbidden_actions:
  - production_db_write
  - salesforce_write
  - box_write_move_rename_delete
  - raw_source_mutation
  - alo_edges_write
  - canonical_promotion
  - claim_support_eligibility
  - ai_estimate_as_human_decision
  - pii_in_general_artifact
  - human_gate_bypass
  - fill_unknown_with_generalities
  - stall_whole_run_waiting_for_input
exit_criteria:
  - case_eval_gold_real.jsonl(正例 12,661 + 各ハード負例 ≥30 件)を生成
  - case_eval(gold_real, pred) を実行し baseline report 出力
  - false_merge_rate / per-Tier precision / B-cubed F / unsure_rate を算出
  - 既存テンプレ(case_eval_gold_template.jsonl)のスキーマ厳守(observation_id/true_case_key/forum_code/decision_date/case_number_norm/external_id/hard_negative_type/source/note)
  - 12,661 を完全抽出できない場合は処理件数・残・理由を明記して done(部分実行可)
  - RESULT を done/ に書く
deliverables:
  - app/data/case_identity/case_eval_gold_real_20260627.jsonl
  - artifacts/caselink/case_eval_baseline_report_20260627.json
  - _claude_dispatch/from_worker/20260627_gold_set_realbuild_RESULT.md
max_attempts: 2
result_expected_filename: W-20260627-505_RESULT.md
---

# Task — gold set 実構築 + ① baseline 計測(自己無矛盾→実 baseline)

DD-CASEEVAL-001 accepted は合成 fixture 6行で「自己無矛盾」を確認しただけ。本タスクで初めて **NII∩D1 一致 12,661 正例**と各ハード負例4型(机上検証で確定済の hard_negative_type 集合)を実 corpus から抽出し、①計測を **実 baseline** に格上げする。これが揃って初めて、②③④⑤の精度議論が「自己整合」から「現実」になる。**シルバー(candidate)の精度を磨く前提条件**。

## 手順
0. engine 準備: `git checkout origin/claude/precedent-object-progress-gwb47u -- scripts/case_eval.py scripts/case_bind_guard.py scripts/case_vocab.py app/data/case_identity/case_eval_gold_template.jsonl`。
1. **正例 12,661 抽出**: NII hanrei.ttl と D1-Law observations を `(forum_code, decision_date, case_number_norm)` で内結合 → 一致した 12,661 を正例とする。各正例は 2 observation(NII側 / D1側)が同じ true_case_key を共有する形で gold jsonl に出力。
2. **ハード負例 4 型を各 ≥30 件**(計 ≥120):
   - `same_number_diff_forum`: 事件番号一致だが forum 異なるペア(東京地裁 vs 大阪地裁 など)
   - `merged_sibling_docket`: 同一事件の併合 docket(case_number_norm が連番違い・同日同forum)
   - `provisional_no_natural_key`: jufu または case_number_norm=null の観測
   - `era_decision_date_mismatch`: 事件番号の元号と decision_date の元号が西暦上 1 年ずれる(平成31/令和元)
3. gold スキーマ厳守(`observation_id/true_case_key/forum_code/decision_date/case_number_norm/external_id/hard_negative_type/source/note`)。商用本文・PIIは出さない。
4. case_bind_guard で pred(assignment) を作り、case_eval(gold_real, pred, tiers) で baseline 算出:
   - `false_merge` / `false_merge_rate`(0 維持の検査)
   - `per_tier_precision` (Tier A の実測。目標 0.99 との差)
   - `bcubed_precision/recall/F`
   - `unsure_rate`
5. baseline report(JSON)に分布・上位の誤りパターン(混同行列の代表ケース)を含める(キーのみ、本文なし)。
6. **重要**: false_merge>0 の case_key を列挙(将来の review or G6 強化の起点)。

## Do Not
alo_edges 反映・canonical 昇格・claim_support・NII/D1 の生本文を含めた gold 出力(正規化キーのみ)。case_eval の指標定義改変(番頭領分)。
