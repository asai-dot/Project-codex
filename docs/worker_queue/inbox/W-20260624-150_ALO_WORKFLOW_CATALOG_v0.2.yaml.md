---
worker_task_id: W-20260624-150
status: queued
priority: P1
owner: claude-code-worker
created_at: 2026-06-24
request: docs/workflow_model/REQUEST_v0.2.md
poc: 統合
goal: 実査結果を ALO_WORKFLOW_CATALOG_v0.2.yaml に統合する。最低 processes/actors/systems/triggers/events/work_items/decisions/documents/deliveries/states/transitions/finance_events/human_gates/exceptions/evidence_types/metrics の16セクション
mode: implementation
requires_systems:
  - repo
depends_on:
  - W-20260624-130
allowed_paths:
  - docs/workflow_model/v0.2/
allowed_actions:
  - write deliverable
forbidden_actions:
  - production_db_write
  - salesforce_write
  - box_write_move_rename_delete
  - file_move_rename_delete
  - ai_estimate_as_human_decision
  - pii_in_general_artifact
  - raw_source_mutation
  - human_gate_bypass
  - fill_unknown_with_generalities
  - stall_whole_run_waiting_for_input
exit_criteria:
  - 16セクションすべてが存在する
  - 各 process が 12分解単位(Trigger..Provenance)で参照可能
  - human_gates にコンフリ/受任/対外送付/請求確定/精算/終結が含まれる
  - RESULT を done/ または blocked/ に書く
  - 成果物は docs/workflow_model/v0.2/ 配下にのみ書き出す
  - 未確認事項は推測で埋めず queue に積み、確認状態を明示する
deliverables:
  - docs/workflow_model/v0.2/ALO_WORKFLOW_CATALOG_v0.2.yaml
max_attempts: 2
result_expected_filename: W-20260624-150_RESULT.md
---

# Task — ALO_WORKFLOW_CATALOG_v0.2.yaml 統合

発注元: `docs/workflow_model/REQUEST_v0.2.md`（v0.2 指示原本）。前提方針 = Box正本 / SF制御塔 / 自然発生データ優先 / Raw・Canonical・Derived分離。

## Goal
実査結果を ALO_WORKFLOW_CATALOG_v0.2.yaml に統合する。最低 processes/actors/systems/triggers/events/work_items/decisions/documents/deliveries/states/transitions/finance_events/human_gates/exceptions/evidence_types/metrics の16セクション

## Do Not（§2 絶対原則 / §7 禁止事項）
- 本番(SF/Box)を書き換えない・ファイルを移動/改名/削除しない。
- 実物を見ずに一般論で埋めない。不明は `未確認`/`証拠不足`/`浅井聴取要` を明示。
- AI推定を人間の確定判断として記録しない。観測/推定/人間判断を分ける。
- 一般成果物に個人名・住所・電話・事件内容・具体的金額を書かない。
- 「追加情報待ち」で作業全体を止めない。確認不能はキューに積み、他を進める。

# 依存
Phase3(130)反映後。
