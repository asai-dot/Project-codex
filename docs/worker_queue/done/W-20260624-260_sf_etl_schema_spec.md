---
worker_task_id: W-20260624-260
status: queued
priority: P0
owner: claude-code-worker
created_at: 2026-06-24
request: docs/workflow_model/REQUEST_v0.2.md
poc: PoC1
goal: SF-ETL(最優先ブロッカー)を外部SEがターンキーで実行できるよう、SF/LEALA→Supabase dynamic ミラーの ETL要件＋dynamicスキーマ拡張仕様を確定する。W-110で判明した cases 11列縮約・必須列欠落・leala__*キー先行・cases/documents 0行 を埋める設計。接続不要(既存所見からの設計)。
mode: implementation
requires_systems:
  - repo
depends_on:
  - W-20260624-110
  - W-20260624-180
  - W-20260624-210
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
  - SFから同期すべきオブジェクト/項目が REQUEST対象群と owner裁定に沿って列挙されている
  - dynamic.cases ほかの スキーマ拡張仕様(追加列・型・制約・背骨ID)が定義
  - 背骨ID(SF Matter/Consultation Id)の comms/documents/相談記録 への伝播設計がある
  - 変換関係(Consultation→Matter)・流入経路・失注理由(enum)・各日付・担当・BoxURL・payer分離 が反映
  - ETL運用(冪等・watermark・dead_letter・id_migration・人手確認=unconfirmed_links)の要件
  - W-240(ETL後検証)との接続、W-170(RLS)のデプロイ注意
  - PII非記載・接続不要
  - RESULT を done/ または blocked/ に書く
deliverables:
  - docs/workflow_model/v0.2/SF_ETL_AND_SCHEMA_SPEC_v0.2.md
max_attempts: 2
result_expected_filename: W-20260624-260_RESULT.md
---

# Task — SF-ETL 要件＋dynamic スキーマ拡張 仕様（SE向け・接続不要）

## 背景(W-110実査)
SF/LEALA は Supabase `dynamic` スキーマにミラーされるが、`dynamic.cases` は **11列縮約**(sf_record_type/sf_record_id/case_label/case_type/status/client_party_id/first_date/last_date/comm_count/doc_count/sf_synced_at)で、owner裁定に必要な **担当/流入経路/失注理由/各日付(到達・受理・入金)/変換関係(Consultation→Matter)/BoxURL/payer(支払者)** の列が無い。さらに **cases/documents は 0行(ETL未実行)**、comms.sf_record_type には `leala__Business__c`/`leala__Consultation__c` の**キーだけ先行**。会計/期限/タスク系は専用テーブル未到達。→ SE が ETL を正しく組めるよう仕様を確定する。**外部システム非アクセス**(設計のみ)。

## 入力(docs/workflow_model/v0.2/ を読むだけ)
- PHASE2_salesforce_survey_v0.2.md(W-110, dynamic現行スキーマ・縮約・キー先行・control層)
- ALO_OWNER_GRILL_ANSWERS_v0.1.md(G-01背骨ID/G-11受任シグナル・入金/G-12流入経路・失注enum/G-10 client·payer/G-04 declared·observed)
- ledger_v0.2/07_sf_mapping.csv(SF対応4区分: そのまま使う/項目追加/別表新設/使わない) と 03_data_sources.csv
- ALO_WORKFLOW_CATALOG_v0.2.yaml(states/systems) / REQUEST_v0.2.md(対象オブジェクト群の正)
- POC1_dryrun_result_v0.2.md(W-210, 源跨ぎ突合0%=背骨ID不在の定量) / W-20260624-240_post_sf_etl_validation.md(検証の受け皿)

## やること
1. **同期対象の確定**: REQUEST対象群(Consultation/Matter/Account/Contact/Party/Task/Event/Deadline/Procedure/Court/Accounting/Billing/Invoice/Expense/Deposit/TimeCharge/PostalMatter/RequiredDocument/KeepingItem/CaseDocument/変換関係/BoxURL/担当/流入経路/失注理由/各日付/次行動・期限・待ち先)を、07_sf_mappingの4区分で「同期する/しない・どのdynamicテーブルへ」を確定。
2. **dynamic スキーマ拡張仕様**: `cases` への追加列(担当=assignee/流入経路=inflow_channel/失注理由=loss_reason(enum: 当方お断り/先方失注/受任に至らず/その他)/到達日・受理日・入金日/変換元consultation_ref/box_folder_url/payer_party_id)を 列名・型・NULL可否・制約付きで。会計/期限/タスクを別表新設する場合のテーブル定義案も。
3. **背骨ID伝播**: SF Matter/Consultation Id(G-01)を cases主キーに据え、comms/documents/相談記録(consultation_key=event_id, W-190)へ sf_record_id を伝播する設計。W-210 の源跨ぎ0%が解決する結合経路を図示(Calendar event ↔ SF Consultation ↔ Box/Gmail)。
4. **declared/observed(G-04)**: SF受任ステータス(declared)列と、observed(委任契約書/受任通知)の格納先・乖離検知の置き場。
5. **ETL運用要件**: 冪等・watermark(既存etl_watermarks)・dead_letter・id_migration_map・人手確認(unconfirmed_links)・同期頻度・初回バックフィルの段取り。Raw/Canonical/Derived分離に沿う。
6. **接続**: W-240(ETL後検証)が何を検証するかに対応する受入条件。**W-170(RLS無効)** をデプロイ前提注意として記載(ETL本番化時にRLS方針の決定が要る)。

## 厳守事項
外部システム非アクセス(設計のみ)。PII非記載=スキーマ/様式/プレースホルダのみ(規約ルール11)。owner裁定とworker推論を区別(根拠 G-xx/D-xx)。未確定は「SE/owner確認要」と明示し一般論で埋めない。AI推定を人間判断にしない。**git操作なし**。成果物は v0.2 配下のみ。捏造禁止。

## 完了処理
RESULT を `done/W-20260624-260_RESULT.md` 先頭 `WORKER_PASS`(exit_criteria充足)。worker_task_id記載。無理なら blocked/。
司令塔戻り値: (a)PASS/BLOCKED (b)成果物パス (c)同期対象確定の網羅 (d)スキーマ拡張仕様(追加列数・新設表) (e)背骨ID伝播設計の可否 (f)ETL運用要件の有無 (g)残課題(SE/owner確認要点)。本文全文は貼らない。
