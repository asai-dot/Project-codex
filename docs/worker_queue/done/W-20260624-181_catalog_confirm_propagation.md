---
worker_task_id: W-20260624-181
status: queued
priority: P1
owner: claude-code-worker
created_at: 2026-06-24
request: docs/workflow_model/REQUEST_v0.2.md
poc: PoC1
goal: W-180で決定ログに反映したowner裁定(G-01..G-20)を、catalog/ledgerの field-level pending:owner_grill マーカーまで伝播し confirm_status を確定化する。併せて「事件ウェブ」表記を owner訂正後の「事件メモ」に直す。
mode: implementation
requires_systems:
  - repo
depends_on:
  - W-20260624-180
allowed_paths:
  - docs/workflow_model/v0.2/
allowed_actions:
  - edit_files
  - write deliverable
forbidden_actions:
  - production_db_write
  - file_move_rename_delete
  - ai_estimate_as_human_decision
  - pii_in_general_artifact
  - overwrite_decided_log
  - fill_unknown_with_generalities
exit_criteria:
  - grillで回答済みの論点に付いた pending:[owner_grill] が解消(confirmed化 or owner裁定に沿って修正)
  - 他の pending理由(sf_survey/staff_interview/box_followup)は残す(owner_grillだけを外す)
  - owner裁定で否定/変更された項目は確定値に修正(例: 受任成立ゲートは optional)
  - 「事件ウェブ」表記が全て「事件メモ(カレンダー紐付けGoogleDoc)」に訂正済み
  - YAML safe_load / CSV csv.reader でパース可能
  - RESULT を done/ または blocked/ に書く
deliverables:
  - docs/workflow_model/v0.2/ALO_WORKFLOW_CATALOG_v0.2.yaml (pending伝播・確定化)
  - docs/workflow_model/v0.2/ledger_v0.2/03_data_sources.csv (事件メモ訂正ほか)
  - docs/workflow_model/v0.2/PHASE4_owner_decisions_applied_v0.2.md (事件メモ訂正・伝播サマリ追記)
max_attempts: 2
result_expected_filename: W-20260624-181_RESULT.md
---

# Task — catalog の owner確定 伝播 + 事件メモ訂正

## 背景
W-180 は決定ログ(D-001..033)・状態機械7本・人間ゲート3マストを確定したが、catalog/ledger の
**field-level `pending: [owner_grill]` マーカー(約30箇所)** が未伝播で provisional のまま残っている。
owner は20問すべてに回答済みなので、これらを確定化する。

## 一次入力（owner裁定＝真実）
- `docs/workflow_model/v0.2/ALO_OWNER_GRILL_ANSWERS_v0.1.md`（確定回答。**「事件メモ」表記が正**）
- `docs/workflow_model/v0.2/ledger_v0.2/09_decision_log.csv`（D-022..033 = 反映済みowner裁定。整合の基準）
- `docs/workflow_model/v0.2/PHASE4_owner_decisions_applied_v0.2.md`

## やること
1. `ALO_WORKFLOW_CATALOG_v0.2.yaml` を走査し、`pending: [owner_grill]` を含む要素を全て点検：
   - 対応するG-xxがgrillで回答済み(ほぼ全部)なら **owner_grill を pending から除去**し、回答に沿って `confirm_status: confirmed` 等に更新。
   - `pending: [owner_grill, sf_survey]` のように**他の理由が併記**されている場合は **owner_grill だけ外し、sf_survey/staff_interview/box_followup は残す**(confirm_status は provisional のまま、理由を1つに減らす)。
   - owner裁定で**変更/否定**された項目は確定値へ修正。特に:
     - 受任成立ゲート / 終結ゲート = **optional**(G-06: 必須は利益相反・対外文書最終送付・金銭確定の3つのみ)。「受任成立=人間必須ゲート」の注記を optional に直す。
     - 流入経路(G-12)=必須〜準必須で確定 / 失注理由(G-12)=enum選択式で確定 / PoC1スコープ(G-07)=相談〜受任で確定 / WorkItem必須(G-08)=担当・期限・案件・次アクションで確定 / client·payer分離(G-10)=確定 / 相談票(G-14)·終了報告書(G-15)=専用様式なしで確定。
   - 各更新の根拠に `source/decision: D-0xx` を付す。確定/未確定の混同禁止。
2. `03_data_sources.csv`(DS-014 ほか) と `PHASE4_owner_decisions_applied_v0.2.md` の **「事件ウェブ」→「事件メモ(カレンダー予定に紐づくGoogleドキュメント)」** を全て訂正。「要最終確認」は owner確認済(2026-06-24)に更新。
3. 反映後、YAML safe_load と全CSV csv.reader でパース確認。`pending:[owner_grill]` の残数を数え、残っていれば理由を明記(本来ゼロのはず。SF実査等の別理由で残すものは pending理由を owner_grill 以外にしてあること)。

## 厳守事項
- 決定ログ(09)の既存行は**上書きしない**(本タスクは主に catalog 側の伝播。09は参照基準)。
- owner裁定と worker推論を混同しない。各確定に D-0xx/G-xx 根拠。PII禁止。**git操作なし**。成果物は v0.2 配下のみ。
- owner裁定が無い純設計事項(中森聴取/外部SE/SF実査依存)は確定化せず、その pending理由を残す。

## 完了処理
RESULT を `done/W-20260624-181_RESULT.md`、1行目 `WORKER_PASS`(exit_criteria充足)。worker_task_id 記載。無理なら blocked/。
司令塔への戻り値: (a)PASS/BLOCKED (b)成果物パス (c)解消した pending:owner_grill 件数 / 残した件数と残存理由内訳 (d)受任成立・終結ゲートをoptionalに直したか (e)事件ウェブ→事件メモ 訂正箇所数 (f)パース自己確認結果 (g)残課題。本文全文は貼らない。
