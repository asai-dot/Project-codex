---
worker_task_id: W-20260624-250
status: queued
priority: P0
owner: claude-code-worker
created_at: 2026-06-24
request: docs/workflow_model/REQUEST_v0.2.md
poc: PoC2
goal: PoC2(解決→終結)の計測設計を接続不要で確定する。close gate 10項目を各「判定データ源・判定方法・測定可否(接続済/未接続/BLOCKED)・人間ゲート該当」でマッピングし、2段クローズ(法的終了/事務クローズ完了)・入金確定(通帳+MF)・預り金精算・原本返却・報酬確定の判定設計と PoC2 KPIを定義する。
mode: implementation
requires_systems:
  - repo
depends_on:
  - W-20260624-160
  - W-20260624-180
  - W-20260624-200
allowed_paths:
  - docs/workflow_model/v0.2/
allowed_actions:
  - edit_files
  - write deliverable
forbidden_actions:
  - production_db_write
  - external_system_access
  - pii_in_general_artifact
  - ai_estimate_as_human_decision
  - fill_unknown_with_generalities
  - file_move_rename_delete
exit_criteria:
  - close gate 10項目それぞれに 判定データ源・判定方法・測定可否・人間ゲート該当 がある
  - 2段クローズ(①法的終了/②事務クローズ完了)が finance/document/matter/deadline 状態機械で表現
  - 入金確定(通帳=正+MF突合)・預り金精算・原本返却・報酬確定 の判定設計がある
  - PoC2 KPIに 算出式・データ源・測定可否(接続済=Box/Gmail | 未接続=MF/通帳 | BLOCKED=SF) がある
  - 終了報告=専用様式なし(G-15)を「成果物送付 or 報酬請求通知」で判定する設計
  - PII非記載・接続不要(既存所見からの設計)
  - RESULT を done/ または blocked/ に書く
deliverables:
  - docs/workflow_model/v0.2/POC2_closegate_measurement_design_v0.2.md
max_attempts: 2
result_expected_filename: W-20260624-250_RESULT.md
---

# Task — PoC2(解決→終結) close gate 計測設計（接続不要）

## 背景・前提
owner裁定(G-09)で**2段クローズ**(①法的終了／②事務クローズ完了=原本返却・預り金ゼロ・報酬確定)が確定。close gate 10条件(W-160)を、各「判定データ源」付きで実装可能な計測設計に落とす。**外部システム非アクセス**(W-160/W-110/W-111/W-112/owner裁定 からの設計)。入金=通帳が正+MoneyForward突合(G-11)、依頼者/支払者分離(G-10)、終了報告=専用様式なし(G-15)。

## 入力(docs/workflow_model/v0.2/ を読むだけ)
- ALO_WORKFLOW_GAP_AND_POC_PLAN_v0.2.md(W-160, PoC2対象WF-19..22・close gate10項目素案・各確認データ源)
- ALO_OWNER_GRILL_ANSWERS_v0.1.md(G-09 2段クローズ/G-11 入金=通帳+MF/G-10 client·payer/G-15 終了報告様式なし/G-06 金銭確定=人間必須ゲート)
- ALO_WORKFLOW_CATALOG_v0.2.yaml(states finance/document/deadline/matter・human_gates HG-05/06・metrics PoC2 KPI)
- PHASE2_box_document_lifecycle_v0.2.md(預り資料/成果物送付/既済フォルダ/原本)
- PHASE2_salesforce_survey_v0.2.md(会計系=cases0行でBLOCKED・MF未接続)
- ALO_WORKFLOW_EVIDENCE_LEDGER_v0.2.jsonl(trace3=解決→第三者請求→入金→精算)
- POC1_measurement_design_v0.2.md(W-200, 様式の参考)

## やること
1. **close gate 10項目マッピング表**: 各項目(未完WorkItem無/残期限無/最終請求確定/未収扱い確定/預り金実費精算済/預り原本 返却済or保管理由/最終成果物送付済/終了報告送付済/Box正本確定/SF終了状態が人間承認済)に [判定データ源 / 判定方法 / 測定可否(接続済Box・Gmail / 未接続MF・通帳 / BLOCKED SF) / 該当human gate / 確信度]。
2. **2段クローズの状態表現**: ①法的終了(matter機械)／②事務クローズ完了(finance=預り金ゼロ・報酬確定／document=原本返却・成果物送付／deadline=残期限無 が全充足)。遷移条件・禁止遷移・どの機械がどの gate を担うか。
3. **金銭の確定設計**(G-11/G-10/HG-05/06): 入金=銀行通帳(正)+MoneyForward突合の判定フロー、預り金精算(ゼロ化)・実費・報酬確定、依頼者/支払者分離(保険会社払い等)。人間必須ゲート(金銭確定)での承認接続。MF/通帳未接続=測定不能を明示。
4. **終了報告の判定**(G-15): 専用様式なし→「成果物の送付 or 報酬請求(金額確定)通知が出ている」で「終了報告済」を判定する設計。Box成果物送付/Gmail通知の検出。
5. **PoC2 KPI**: close gate未通過滞留率/終了報告送付率/預り金精算完了までの時間/報酬確定までの時間 等に 算出式・データ源・測定可否。今接続済み(Box/Gmail)で取れる分と MF/通帳/SF 待ちの分を仕分け。
6. **着手可能/前提待ちの線引き**(PoC1 W-210に倣う): 接続済みで今できる close gate 判定と、MF/通帳/SF-ETL 後に初めてできる判定を明示。

## 厳守事項
外部システム非アクセス(設計のみ)。PII非記載=様式/プレースホルダ/構造のみ(規約ルール11)。owner裁定とworker推論を区別(根拠 G-xx/D-xx)。AI推定を人間判断にしない。未接続(MF/通帳)・BLOCKED(SF)は明示し一般論で埋めない。**git操作なし**。成果物は v0.2 配下のみ。捏造禁止。

## 完了処理
RESULT を `done/W-20260624-250_RESULT.md` 先頭 `WORKER_PASS`(exit_criteria充足)。worker_task_id記載。無理なら blocked/。
司令塔戻り値: (a)PASS/BLOCKED (b)成果物パス (c)close gate10項目マッピングの網羅 (d)2段クローズの状態表現可否 (e)金銭確定設計の有無 (f)PoC2 KPIの測定可否内訳(接続済/前提待ち) (g)残課題。本文全文は貼らない。
