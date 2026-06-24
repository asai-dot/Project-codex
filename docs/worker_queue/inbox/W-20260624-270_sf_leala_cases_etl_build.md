---
worker_task_id: W-20260624-270
status: done
priority: P0
completed_at: 2026-06-24
result: docs/worker_queue/done/W-20260624-270_RESULT.md
owner: claude-code-worker
created_at: 2026-06-24
request: docs/workflow_model/REQUEST_v0.2.md
poc: PoC1
held_reason: Salesforce(LEALA managed package) がセッション未接続。owner が SF API/MCP を接続した時点で inbox へ移し起動。接続まで仕様のみ確定。
goal: Salesforce(leala__Business__c=案件 / leala__Consultation__c=相談 等)を背骨ソースとして dynamic.cases へ取込むETLを構築・実行し、既存 comms(343 chatwork) の sf_record_id を解決、突合不能分は unconfirmed_links で人手確定に回す。W-210「源跨ぎ突合0%」を実測で動かす。
mode: implementation
requires_systems:
  - Salesforce (LEALA managed package, read) ※owner接続後
  - Supabase nixfjmwxmgugiiuqfuym (write: dynamic.cases ほか, apply_migration/execute_sql)
allowed_paths:
  - docs/workflow_model/v0.2/
allowed_actions:
  - read_salesforce(read_only)
  - supabase_write(dynamic schema, owner承認の上)
  - write deliverable
forbidden_actions:
  - salesforce_write
  - pii_in_general_artifact
  - rls_change_without_owner_ok
  - ai_estimate_as_human_decision
  - destructive_sql
exit_criteria:
  - leala__Business__c/Consultation__c 等 → dynamic.cases のフィールドマッピング確定(背骨ID=sf_record_id)
  - cases に行が投入され、comms.sf_record_id が指す案件が解決(解決率を実測)
  - 突合不能/曖昧は unconfirmed_links に候補登録(AI推定は人間承認まで非確定 G-19)
  - 冪等(再実行で重複なし)・etl_watermarks/pipeline_runs に実行記録
  - declared(SF受任ステータス)列の取込、observed との乖離検知の置き場
  - RLS は owner裁定(保留 W-170)を尊重し変更しない(変更時は別途owner承認)
  - PII非記載の成果物(件数・解決率・マッピング仕様のみ)
  - RESULT を done/ または blocked/ に書く
deliverables:
  - docs/workflow_model/v0.2/POC1_sf_leala_cases_etl_result_v0.2.md
max_attempts: 2
result_expected_filename: W-20260624-270_RESULT.md
---

# Task — SF/LEALA → dynamic.cases 取込ETL 構築・実行（SF接続待ちで held）

## 着手前提
**Salesforce(LEALA managed package)がこのセッションに接続されていること。** 現状未接続のため held。owner が接続したら inbox へ移し claim。ライブ実態は `DATA_PLATFORM_LIVE_STATE_v0.2.md` 参照（ミラー=Chatworkのみ・cases 0行・器は成熟・comms に sf_record_id/redaction系あり）。

## やること（SF接続後）
1. **SFオブジェクト棚卸し**: leala__Business__c(案件/Matter)・leala__Consultation__c(相談)・関連(Account/Contact/取引先/担当/状態/日付/流入経路/失注理由)のフィールドを読み取りで確認。
2. **マッピング確定**: SF → dynamic.cases(既存11列)＋必要なら最小限の列追加(owner承認・W-260のうち実DBに無い分のみ)。背骨ID=sf_record_id を主キーに。
3. **取込実行(冪等)**: cases へ upsert、etl_watermarks/pipeline_runs に記録。Raw/Canonical分離。chatwork_room_case_map(8) と comms.sf_record_id(343全件保持) を使って comms↔cases を解決し、解決率を実測(W-210の0%からの改善)。
4. **人手確定ゲート**: 自動解決できない/曖昧な紐付けは unconfirmed_links に proposed として登録(G-19)。自動確定にしない。
5. **declared/observed(G-04)**: SF受任ステータス(declared)を取込み、observed(委任契約書[Box]/受任通知[Gmail])との乖離検知の置き場を用意(突合は後続)。
6. **検証(=W-240の前倒し一部)**: cases投入後の背骨ID解決率・declared分布を集計(PII無)。

## 厳守事項
SF=read-only(書込厲禁)。Supabase書込はowner承認の上・冪等・破壊的SQL禁止。**RLSは保留(W-170)を尊重し変更しない**。PII非記載=件数/解決率/マッピングのみ。AI推定を人間判断にしない。成果物は v0.2 配下のみ。捏造禁止。

## 完了処理
RESULT を `done/W-20260624-270_RESULT.md` 先頭 `WORKER_PASS`/前提未達なら blocked。司令塔戻り値: cases投入件数・背骨ID解決率(before 0%→after)・unconfirmed_links登録数・declared分布・残課題。
