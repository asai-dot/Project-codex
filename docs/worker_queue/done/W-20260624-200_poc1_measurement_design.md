---
worker_task_id: W-20260624-200
status: queued
priority: P0
owner: claude-code-worker
created_at: 2026-06-24
request: docs/workflow_model/REQUEST_v0.2.md
poc: PoC1
goal: PoC1(相談〜受任)の計測設計を確定する。対象パイプライン(WF-00..12)を運用手順に落とし、KPIごとに 算出式・データ源・現時点の測定可否・受入基準 を定義。受任は「複数シグナル合成(委任状/契約書[Box]・SF相談→受任切替・受任通知[Gmail])で observed を立て declared と突合」で定義。相談記録は W-190 の event_id↔doc_id 結合で合成。
mode: implementation
requires_systems:
  - repo
depends_on:
  - W-20260624-160
  - W-20260624-180
  - W-20260624-190
allowed_paths:
  - docs/workflow_model/v0.2/
allowed_actions:
  - edit_files
  - write deliverable
forbidden_actions:
  - production_db_write
  - pii_in_general_artifact
  - ai_estimate_as_human_decision
  - fill_unknown_with_generalities
  - file_move_rename_delete
exit_criteria:
  - PoC1対象パイプライン(WF-00..12)が運用手順(誰が/何を入力/どのイベント発火/次状態)で記述されている
  - KPI 8本に 算出式・データ源・測定可否(接続/未接続/BLOCKED)・取得方法 がある
  - 受任判定が「複数シグナル合成＋declared/observed突合」で具体化(各シグナルの源と確信度)
  - 相談記録合成が W-190 の結合キー(event_id↔doc_id)とRaw/Canonical/Derivedに沿って定義
  - 受入基準(P0遷移は全件source ref付/曖昧はHITL/open相談のowner・due欠落可視化)が明記
  - RESULT を done/ または blocked/ に書く
  - 成果物は docs/workflow_model/v0.2/ 配下のみ
deliverables:
  - docs/workflow_model/v0.2/POC1_measurement_design_v0.2.md
max_attempts: 2
result_expected_filename: W-20260624-200_RESULT.md
---

# Task — PoC1(相談〜受任) 計測設計

発注元: `docs/workflow_model/REQUEST_v0.2.md` §6。owner裁定 = `ALO_OWNER_GRILL_ANSWERS_v0.1.md`。前提 = Box正本/SF制御塔/自然発生データ優先/Raw・Canonical・Derived分離。

## 入力（done成果物）
- `POC` 範囲と KPI/受入基準の素案: `ALO_WORKFLOW_GAP_AND_POC_PLAN_v0.2.md`(W-160)
- owner確定: `ALO_OWNER_GRILL_ANSWERS_v0.1.md`(G-07 スコープ=相談〜受任 / G-08 タスク必須4項目 / G-11 受任=複数シグナル・入金=通帳+MF / G-12 流入経路・失注enum / G-04 declared/observed)
- catalog(確定後): `ALO_WORKFLOW_CATALOG_v0.2.yaml`(states7本/human_gates3/metrics)
- 相談記録の実体: `PHASE5_consultation_record_survey_v0.2.md`(W-190。結合キー event_id↔doc_id、相談/非相談判別課題)
- イベント語彙: `alo_workflow_event_schema_v0.2.json` / 例: `ALO_WORKFLOW_EVIDENCE_LEDGER_v0.2.jsonl`
- SF実査: `PHASE2_salesforce_survey_v0.2.md`(W-110。cases0行=制御塔データ不在/leala__*キー先行)

## やること
1. **対象パイプライン WF-00..12 の運用記述**: 各ステップを (トリガ / 入力者 / 入力物 / 発火イベント(schema_v0.2のevent_type) / 次状態(7状態機械のどれ) / 必須human gate該当) の表で。流入→相談案件起票→Boxフォルダ作成→相談実施→(相談止まり/受任) を G-07 に沿って。
2. **KPI 8本の計測設計表**: 初回応答/相談確定/見積送付/契約成立までの時間、次行動未設定率、流入経路不明率、失注理由未入力率、イベント未紐付け率。各に [算出式 / 分子・分母の定義 / データ源 / 測定可否(接続済=Calendar・Docs・Box・Gmail / 未接続=Notta・MF / BLOCKED=SF実データ) / 取得方法]。測定不能は「未接続/BLOCKEDにつき定義のみ」と明示(捏造しない)。
3. **受任判定の具体化**(G-11/G-04): observed_受任 を 3シグナル合成で定義—①委任状/委任契約書の受領(Box正本・最強, confidence高) ②SF 相談→受任ステータス切替(SF制御塔) ③受任通知の発送(Gmail)。各シグナルの源・抽出方法・confidence、合議ルール(いずれか/重み)、declared(SF受任ステータス)との突合と乖離検知(G-04)。受任成立ゲートは optional(G-06)だが、確定は人間承認で。
4. **相談記録合成の組込**(W-190): consultation_key=event_id、event_id↔doc_id(添付fileUrl)で 1相談:N文書、Raw=ポインタ/Canonical=consultation_*/Derived=AI限定。相談 vs 非相談(公益/勉強会/会議議題)の判別ルール案(添付有無+参加者+分野語)。Notta未接続は空欄設計。
5. **受入基準**: P0遷移は全件 provenance(source ref)付き / 曖昧は HITL(人間判断) / open相談で owner・due 欠落を可視化 / イベントは全て event_id↔エンティティに紐付け。
6. **計測の段取り**: 接続済み(Calendar/Docs/Box/Gmail)だけで今すぐ取れるKPI と、Notta/MF接続・SF-ETL後に初めて取れるKPI を分けて「着手可能/前提待ち」リスト化。

## 厳守事項
- owner裁定と worker推論を混同しない(各設計に G-xx/D-xx 根拠)。測定不能を一般論で埋めない(未接続/BLOCKED明示)。AI推定は Derived・人間未承認に留める。PII禁止。**git操作なし**。成果物は v0.2 配下のみ。

## 完了処理
RESULT を `done/W-20260624-200_RESULT.md`、1行目 `WORKER_PASS`(exit_criteria充足)。worker_task_id 記載。無理なら blocked/。
司令塔への戻り値: (a)PASS/BLOCKED (b)成果物パス (c)パイプライン記述の網羅(WF数) (d)KPI8本の測定可否内訳(着手可能/前提待ち) (e)受任判定ロジックの確定可否 (f)今すぐ計測着手できるKPIの数 (g)残課題(接続前提)。本文全文は貼らない。
