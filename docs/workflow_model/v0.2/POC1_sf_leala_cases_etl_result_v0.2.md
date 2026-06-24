---
worker_task_id: W-20260624-270
phase: PoC1
title: SF/LEALA → dynamic.cases 取込ETL 構築・実行 結果
created_at: 2026-06-24
owner: claude-code-worker
project: Supabase nixfjmwxmgugiiuqfuym (alo / asai-dot's Project), schema dynamic
connection: Salesforce 本番 (leala-3392.lightning.force.com) / External Client App "ALO_Knowledge_DB" JWT Bearer flow (read-only 利用)
pii_policy: 件数・解決率・入力率・マッピングのみ。氏名/案件名/本文は非転載。
---

# PoC1 — SF/LEALA → dynamic.cases ETL 結果 v0.2

## 0. 結論（実測）
- **背骨ID解決率: 0% → 100%**（comms 343件すべての `sf_record_id` が投入後 `cases` に解決）。W-210「源跨ぎ突合0%」を実測で解消。
- `dynamic.cases` 投入: **leala__Business__c 782件 / leala__Consultation__c 235件（計1,017件）**（before 0行）。
- 取込は冪等（`cases(sf_record_type, sf_record_id)` upsert、再実行で重複なし）。
- 毎日 03:00 JST 自動同期（pg_cron `sf-sync-nightly`）＝常駐パイプライン稼働。

## 1. 接続方式（恒久・headless）
```
Salesforce(本番) ──JWT Bearer(証明書署名)──▶ Supabase Edge Function `sf-sync`
                                              ├ 認証情報は Vault (sf_jwt_private_key / sf_consumer_key / sf_username / sf_login_url)
                                              ├ SOQL 取得 → dynamic.cases へ upsert
                                              └ pg_cron + pg_net で定期起動
```
- External Client App `ALO_Knowledge_DB`（種別ローカル/有効/事前承認済、スコープ api+full+refresh_token、JWTベアラー有効、証明書 `CN=alo-knowledge-db` 有効期限2029-06）。
- 証明書/秘密鍵は本タスクで再生成しSF側へ再アップロード。秘密鍵は Supabase Vault に格納（リポジトリ・成果物に非記載）。鍵はローテーション可能。
- セッション(AI)→SF はネットワークポリシーで遮断。**同期はSupabase内（Edge Function）で実行**＝安全分離。

## 2. フィールドマッピング（SF → dynamic.cases）
背骨ID = `sf_record_id`(SF Id, 主キー)。全項目は `sf_raw`(jsonb) に保持し、KPI用に型付き列を追加。

| dynamic.cases | leala__Business__c | leala__Consultation__c |
|---|---|---|
| status | leala__Status__c(進捗度) | leala__StageName__c(進捗度) |
| name / case_label | Name(件名) | Name(件名) |
| charge_lawyer_id / clerk_id / team_id | ChargeLawyer/Clerk/Team__c | 同左 |
| source / source_middle / source_partner_id | leala__Source/SourceMiddle/SourcePartner__c | 同左 |
| case_category | leala__CaseCategorySingle__c | 同左 |
| mandatory_date(受任日) | leala__MandatoryDate__c | — |
| reception_date / consulted_date | — | ConsultationReceptionDate / ConsultedDate__c |
| close_date / expected_close_date | CloseDate / ExpectedCloseDate__c | 同左(終了日/受任予定日) |
| reason_for_failure(失注) / reason_not_reach / detailed_reason_closing | — | ReasonForFailure / ReasonWhyNotReachConsultation / DetailedReasonForClosing__c |
| probability(受任確度) | — | leala__Probability__c |
| consultation_converted | — | leala__ConsultationConverted__c |
| consultation_ref(変換元) | leala__Consultation__c | — |
| next_deadline_at / waiting_on / outcome | ALO_Next_Deadline_At / ALO_Waiting_On / ALO_Outcome__c | — |
| box_folder_url | leala__UploadFolderUrlBox__c | 同左 |
| account_name | leala__AccountName__c | DisplayName__c |
| earnings | Earnings__c | — |
| sf_created_date / sf_last_modified | CreatedDate / LastModifiedDate | 同左 |
| sf_raw(jsonb) | 取得項目一式 | 取得項目一式 |

棚卸し: `leala__Business__c`=118項目 / `leala__Consultation__c`=88項目（全件 `dynamic.sf_object_fields` にキャッシュ）。

## 3. declared/observed と入力率（PII無・比率のみ）
declared=SF受任ステータス(status)を取込。observed(委任契約[Box]/受任通知[Gmail])との乖離検知は `sf_raw`+今後の突合で実装（置き場確保済）。

| 指標(入力率) | Business(782) | Consultation(235) |
|---|---|---|
| 流入経路 source | **13.6%** | 64.3% |
| 担当弁護士 | 98.8% | 94.9% |
| 受任日 / 初回相談日 | 84.4% | 46.4% |
| 終結日 | 90.7% | 75.3% |
| 失注理由 | — | **8.1%** |
| 受任確度 | — | 34.9% |
| ALO 待ち先 / 次回期限 | 4.0% / 1.0% | 8.1% / 34.9% |
| Box連携URL | **0.0%** | 0.0% |

所見: ①受任案件の流入経路が86%空白＝マーケ計測の最大欠損 ②`ALO_*`(待ち先/次回期限)は作成済だがほぼ未運用 ③`UploadFolderUrlBox__c` 全件空＝SF側Box連携が未稼働。→ 改善KPIの出発点。

## 4. 残課題（queue化推奨）
- **Q-ETL1 [運用記録]**: 既存 `etl_watermarks`/`pipeline_runs` ではなく簡易 `sf_sync_runs` に記録した。正式テーブルへの統一と増分(LastModifiedDate watermark)同期化。
- **Q-ETL2 [参照解決]**: charge_lawyer_id/team_id 等は SF Id のまま。User/Team 名称解決(別オブジェクト取込)が必要。
- **Q-ETL3 [unconfirmed_links]**: 今回 comms↔cases は既存 human-gate(chatwork_room_case_map)由来の sf_record_id 直結で100%解決のため新規曖昧リンク0件。今後 Gmail/Box 由来の自動紐付け時に proposed 登録運用。
- **Q-ETL4 [RLS]**: 保留(W-170)を尊重し未変更。本番公開前に dynamic 全BASE TABLE へ RLS+policy 必須。
- **Q-ETL5 [observed突合]**: 委任契約(Box)/受任通知(Gmail)との declared-observed 乖離検知の実装。
- **Q-ETL6 [sf_raw列拡張]**: 現状は curated 24/25項目を取得。需要に応じSOQL field list拡張(全118/88へ)。

## 5. 冪等・安全性
- SF: read-only(SOQL/describe のみ、書込なし)。
- Supabase書込: cases upsert(主キー衝突=更新)・破壊的SQL無し・RLS不変更。
- 本番DDL/同期起動は human(owner)が Supabase SQL Editor で実行（セーフティ分担）。runbook: `supabase/functions/sf-sync/runbook.sql`。
- 秘密情報はVaultのみ。成果物・ソースに非記載。
