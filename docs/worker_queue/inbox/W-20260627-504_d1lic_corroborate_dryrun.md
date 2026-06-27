---
worker_task_id: W-20260627-504
status: queued
priority: P1
owner: claude-code-worker
created_at: 2026-06-27
request: docs/CASE_OBJECT_OVERVIEW_and_production_handoff_20260623.md (P2: D1-LIC 5,475 を実 link 化)
goal: D1-LIC 5,475(解説誌→事件 resolved)を実 link として case_corroborate に流し、L1/L2/L3 分布・multi_source_agree 件数・conflict_review 件数を実数で出す。false_merge=0 維持の自己検査も同時実施。シルバー(candidate)の confidence 分布が初めて実数になる
mode: implementation
requires_systems:
  - scripts/case_corroborate.py / case_bind_guard.py / case_vocab.py
  - D1-LIC crosswalk 解決結果(5,475件・解説誌article ↔ case_observation)
  - NII/D1-Law/最高裁HP 等の判例DB候補(L1 identity 補強の母集合)
depends_on:
allowed_paths:
  - artifacts/caselink/
  - _claude_dispatch/from_worker/
allowed_actions:
  - read_files(D1-LIC crosswalk, 各判例DB observation)
  - ensure_engine(precedent-object-progress から case_corroborate / case_bind_guard / case_vocab を取得)
  - run case_corroborate(assignment, obs_by_id, links)
  - write deliverable(dry-run report + conflict_review 候補リスト)
forbidden_actions:
  - production_db_write
  - salesforce_write
  - box_write_move_rename_delete
  - raw_source_mutation
  - alo_edges_write
  - canonical_promotion
  - claim_support_eligibility
  - reviewed_true_backfill
  - ai_estimate_as_human_decision
  - pii_in_general_artifact
  - human_gate_bypass
  - fill_unknown_with_generalities
  - stall_whole_run_waiting_for_input
exit_criteria:
  - case_corroborate を実 D1-LIC(5,475) と判例DB observation で実行し report を出力
  - L1/L2/L3 件数・multi_source_agree 分布・conflict_review 候補件数を集計
  - false_merge=0 維持を assignment 不変で自己検査(corroborate は assignment を書き換えないことを assert)
  - L2 annotation_corroboration が「事件への言及」を「同一事件」と誤読していないこと(L1への混入なし)を検査
  - 5,475 を完全に流せない場合は処理件数・残・理由を明記して done(部分実行可・blocked ではない)
  - RESULT を done/ に書く
deliverables:
  - artifacts/caselink/d1lic_corroborate_dryrun_report_20260627.json
  - artifacts/caselink/d1lic_conflict_review_candidates_20260627.jsonl
  - _claude_dispatch/from_worker/20260627_d1lic_corroborate_RESULT.md
max_attempts: 2
result_expected_filename: W-20260627-504_RESULT.md
---

# Task — D1-LIC 5,475 corroborate dry-run (③多源コロボの実数化)

DD-CASECORROB-001 accepted は fixture-level しか走っていない。本タスクで初めて **実 D1-LIC 5,475** に通し、(a) L1 identity 補強(NII∩D1∩最高裁HP 等の独立判例源一致), (b) L2 annotation_corroboration(解説誌→事件 が canonical case の要旨補強), (c) conflict_review(同一事件主張だが採番割れ=false split 検出) を実数化する。**シルバー confidence の実数が初めて得られる**。

## 手順
0. engine 準備: 無ければ `git checkout origin/claude/precedent-object-progress-gwb47u -- scripts/case_corroborate.py scripts/case_bind_guard.py scripts/case_vocab.py` で取得。
1. 入力: D1-LIC crosswalk resolved 5,475 を `{lic_article_id, d1_case_id, NII_id?, saikousai_id?, hanrei_times_id?, observation 群}` に整形(商用本文は出さない)。
2. case_bind_guard で **observation → assignment(case_key 仮)** を作る(read-only)。**false_merge=0 を eval で再確認**。
3. links を組む:
   - L1: `(d1_case_id, NII_id, type=caselaw_same_case)` 等(判例DB間の自然キー一致)
   - L2: `(lic_article_id, d1_case_id, type=literature_about_case)` (LIC→事件)
   - L3: 引用ペアがあれば `(case_a, case_b, type=case_cites_case)`
4. `case_corroborate(assignment, obs_by_id, links)` 実行 → confidence 分布と findings:
   - `multi_source_agree` 件数(L1 で独立判例源 ≥2 一致 = identity 補強)
   - `conflict_review` 件数(同一性主張だが採番割れ → false split or crosswalk 誤り疑い)
   - `annotation_corroboration` 件数(L2 で各 case に紐付く解説誌数の分布)
5. **assert: corroborate が assignment を書き換えていない(精度を守ったまま recall 当たりを作る)**。Tier 別の identity_corroboration 内訳(multi/single/non_caselaw_only)を集計。
6. conflict_review 候補(top 100 件・正規化キーのみ)を `d1lic_conflict_review_candidates_*.jsonl` に。これが**人手 review の Q2 拡張 gold 候補**になる。

## Do Not
alo_edges への実 write・canonical 昇格・accepted edge 化(L2/L3 永久に非merge は DD-CASECORROB の原則)・claim_support・商用本文の外部送信。case_corroborate の語彙改変(番頭領分)。
