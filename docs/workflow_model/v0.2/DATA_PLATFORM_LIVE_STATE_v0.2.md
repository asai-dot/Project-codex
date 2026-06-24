# ALO データ基盤 ライブ実査メモ（司令塔フィールドノート）

- 記録: 2026-06-24 / 記録者: Claude司令塔（Supabase MCP 読み取り専用で直接確認）
- 位置づけ: W-110(SFミラー実査)・W-260(SF-ETL仕様) を **実DBのグラウンドトゥルース**で補正する一次記録。PII非記載（スキーマ・件数・ソース名のみ）。

## 0. 最重要サマリ
- **ミラー本体は Supabase プロジェクト `nixfjmwxmgugiiuqfuym`（"asai-dot's Project"）**。もう一方 `vlsunmqpjhzbhipiehzs`（"alo-connect"）の `dynamic` は**空**（0テーブル）。
- **現在ミラーに取り込まれているソースは Chatwork のみ**（`dynamic.comms` 343件・全件 `source='chatwork'`・期間 2018-12-19〜2026-05-18）。
- **Salesforce/LEALA・Gmail・Box・Calendar は未取込**。`dynamic.cases`（案件マスタ）= **0行**＝ W-210「源跨ぎ突合0%」の根因。
- `leala__Business__c` / `leala__Consultation__c` は **Salesforce の managed package（名前空間 `leala__`）カスタムオブジェクト** → **LEALAデータは Salesforce 内**。Salesforce接続で背骨(cases)取得可能。

## 1. dynamic スキーマ 14テーブル 実件数
| table | rows | 備考 |
|---|---|---|
| comms | 343 | 全件 chatwork・全件 sf_record_id 有・全件 case_link_status 有 |
| comm_party_links | 488 | comms↔parties 連結（稼働） |
| parties | 9 | 当事者マスタ |
| chatwork_room_case_map | 8 | Chatworkルーム→案件 対応（cases連結の橋） |
| **cases** | **0** | **案件マスタ未ロード＝背骨欠落** |
| documents | 0 | 文書未取込（Box未連携） |
| comm_document_links | 0 | |
| unconfirmed_links | 0 | 人手確定ゲート（器のみ） |
| pipeline_runs | 0 | ETL実行記録なし |
| etl_watermarks | 0 | 取込ウォーターマークなし |
| etl_dead_letter | 0 | |
| id_migration_map | 0 | |
| comm_versions | 0 | |
| llm_disclosure_log | 0 | 外部LLM開示ログ（器のみ） |

## 2. 器（スキーマ）の評価 — W-260想定より成熟
- **`comms`(40列)** は単なる縮約でなく高機能: `source/source_record_key/source_url/raw_pointer/archive_hash`(Raw証跡)・`sf_record_type/sf_record_id/case_link_status/case_link_basis`(背骨連結＋根拠)・`thread_root_comm_id/in_reply_to_comm_id/thread_confidence`(スレッド復元)・**`confidentiality_level/external_llm_policy/redaction_status/redacted_text/redaction_hash/access_class`(秘匿・PII統制が内蔵)**・`llm_category/llm_summary/llm_actions`(派生)・`chatwork_*`・`raw_payload`。
- **`documents`(31列)** も同等に整備（Box取込先として即利用可）。
- **`unconfirmed_links`** は W-260設計とほぼ同形で既存: `target_table/target_id/proposed_sf_record_id/proposed_by/confidence/reason/status/confirmed_by/confirmed_at`（＝AI候補→人手確定 G-19 の器が実在）。
- `cases`(11列) は薄いサマリ: `sf_record_type/sf_record_id/case_label/case_type/status/client_party_id/first_date/last_date/comm_count/doc_count/sf_synced_at`。
- → **W-260の「cases に15列追加・4表新設」は要再評価**: 多くの属性は既存器（comms/documents/unconfirmed_links）に存在。真の欠落は「**ソース未取込（特にSF/LEALA・Box・Gmail）**」。

## 3. ETL機構の所在
- **Supabase Edge Function = 0個**。pg_cron 等の取込ジョブも痕跡なし（pipeline_runs/etl_watermarks 空）。
- **本リポジトリにETL実装なし**（grep 53ヒットは全て分析ドキュメント、実装コード0）。
- → 343件Chatworkを入れた取込は**外部の単発ジョブ**。SF/LEALA・Box・Gmail取込は**未構築**。

## 4. セキュリティ
- `dynamic` 14テーブル全て **RLS無効**（Supabase advisor が `critical` 判定）。中身は**実クライアントの約8年分Chatwork通信**＝実PII。anon/authenticated キーで全行読み書き可能。
- owner裁定(2026-06-24): **当面 保留・受容継続（W-170）**。本番ETL拡大・外部公開前に RLS方針確定が必須。

## 5. owner裁定（2026-06-24）と次段取り
- **背骨(cases)取込経路 = Salesforce/LEALA API をセッションに接続**（owner選択）。接続後、司令塔が leala__Business__c/Consultation__c → `dynamic.cases` 取込ETLを構築し、comms(343) の sf_record_id を解決、unconfirmed_links で人手確定。
- 現状 **Salesforce 未接続**（接続済: Box/Gmail/Drive/Calendar/Supabase/GitHub）。→ owner が Salesforce 接続を追加した時点で W-270 を起動。
- RLS = 保留（W-170継続）。
