---
worker_task_id: W-20260624-110
phase: Phase2
title: Salesforce/LEALA read-only 実査（Supabaseミラー経由）
created_at: 2026-06-24
owner: claude-code-worker
source_request: docs/workflow_model/REQUEST_v0.2.md
poc: PoC1
method: read-only SQL survey (SELECT only) against Supabase mirror
connection: Supabase project "asai-dot's Project" (project_id nixfjmwxmgugiiuqfuym), schema dynamic (+ formobj/control), SELECT-only
pii_policy: 集計・構造のみ。body_text/body_raw/subject/redacted_text/display_name/email/phone/organization、room_name・source_label 内の個人名/案件名は値を転載しない。
deliverables:
  - docs/workflow_model/v0.2/PHASE2_salesforce_survey_v0.2.md
---

# Phase2 Salesforce/LEALA read-only 実査 v0.2

前提方針: Box＝文書正本 / SF＝業務制御塔 / 自然発生データ優先 / Raw・Canonical・Derived分離。

## 0. 接続と前提（最重要・先頭明示）

- **接続 = Supabaseミラー（read-only / SELECT専用）**。SF/LEALA の生org・LEALA本体には直結していない。窓口は Supabase project **"asai-dot's Project"**（project_id `nixfjmwxmgugiiuqfuym`, ap-northeast-1）の **`dynamic` スキーマ**（SF/LEALA制御塔ミラー）。関連スキーマ `formobj` / `control` も SELECT 到達。`d1law_taikei`(法体系KOS) は本票対象外として件数のみ把握。
- **read-only 自己宣言**: 本作業は `list_tables` と `execute_sql`(先頭 `select`/`with…select` のみ)だけを使用。INSERT/UPDATE/DELETE/DDL/ALTER/TRUNCATE/COPY/`apply_migration`/`deploy_edge_function`/`create_branch` 等の書込系は **一切呼んでいない**。本番(SF/Box)書込ゼロ。
- **PII非転載**: 全クエリは件数・NULL率・enum分布・日付レンジ・型・構造のみ。本文列(body_text/body_raw/subject/redacted_text/raw_payload)、個人特定列(display_name/primary_email/primary_phone/email_aliases/organization)、および `comms.source_label`・`chatwork_room_case_map.room_name` に含まれる個人名/案件名は **値を出力しない**（観測した事実のみ「PII含有」として注記）。

### 0.1 投入状況サマリ（実測）

| 区分 | テーブル | 行数 | 測定可否 |
|---|---|---|---|
| 実データあり | dynamic.comms | 343 | 測定可 |
| 実データあり | dynamic.comm_party_links | 488 | 測定可 |
| 実データあり | dynamic.parties | 9 | 測定可 |
| 実データあり | dynamic.chatwork_room_case_map | 8 | 測定可 |
| **空（SF同期未実行）** | dynamic.cases | 0 | **未確認(同期待ち)** |
| **空** | dynamic.documents | 0 | **未確認(同期待ち)** |
| **空** | dynamic.comm_versions | 0 | **未確認(同期待ち)** |
| **空** | dynamic.comm_document_links | 0 | **未確認(同期待ち)** |
| **空** | dynamic.unconfirmed_links | 0 | **未確認(human gate空)** |
| **空** | dynamic.id_migration_map | 0 | **未確認** |
| **空** | dynamic.pipeline_runs | 0 | **未確認** |
| **空** | dynamic.llm_disclosure_log | 0 | **未確認** |
| **空** | dynamic.etl_watermarks / etl_dead_letter | 0 / 0 | **未確認** |

### 0.2 測定可能/未確認の線引き

- **測定できた実態**は chatwork 由来の通信レイヤ（comms / comm_party_links / parties / chatwork_room_case_map）に限られる。
- 指定オブジェクト群の大半（Consultation/Matter/Account/Contact/Party/Task/Event/Deadline/Procedure/Court/Accounting/Billing/Invoice/Expense/Deposit/TimeCharge/PostalMatter/RequiredDocument/KeepingItem/CaseDocument 等）は、ミラー上に **専用テーブルが存在せず**、`dynamic.cases`/`dynamic.documents` への SF同期(ETL)も未実行。よってこれらの **入力率・値の揺れ・自由記述過積載・状態乖離は現時点で測定不能＝未確認(SF同期待ち)** と正直に明示する。捏造しない。
- 重要観測: `dynamic.cases`(0行)が空であるにも関わらず、`comms.sf_record_type` には `leala__Business__c`(318) / `leala__Consultation__c`(25) が埋まり、`chatwork_room_case_map.sf_record_type` も同2種を参照している。**SFオブジェクト型の参照は通信側に既に存在するが、参照先の cases 実体は未投入**という「キー先行・実体不在」状態。

## 1. モデル実査（dynamic + formobj + control）

### 1.1 dynamic スキーマ テーブル一覧（到達済）

BASE TABLE: cases / comms / documents / parties / comm_party_links / comm_document_links / comm_versions / chatwork_room_case_map / unconfirmed_links / id_migration_map / pipeline_runs / llm_disclosure_log / etl_watermarks / etl_dead_letter。VIEW: timeline_view / v_llm_exportable_timeline。
RLS: dynamic/formobj/control の全BASE TABLEで **RLS無効**（Supabase advisor が critical 指摘）。anon/authenticated に素通しのため、本番運用前に RLS+policy 付与が必須（残課題に計上）。

### 1.2 Raw / Canonical / Derived 分離の実装（v0.2設計との突合）

`dynamic.comms` の列構成は v0.2 の三層分離を **実装済**:

- **Raw層**: `source`, `source_record_key`, `source_url`, `raw_pointer`, `archive_hash`, `raw_payload`(jsonb), `source_meta`(jsonb)。→ provenance/不可逆原本ポインタ。設計の「Raw=source/source_record_key/raw_pointer/archive_hash」と一致。
- **Canonical層**: `ts`, `ts_received`, `account`, `direction`, `subject`, `body_text`, `body_raw`。→ 正規化済本文・時刻。
- **Derived層**: `llm_category`, `llm_summary`, `llm_actions`(jsonb)（LLM派生）、`case_link_status`/`case_link_basis`（案件紐付け派生）、`thread_root_comm_id`/`in_reply_to_comm_id`/`thread_basis`/`thread_confidence`（スレッド復元派生）。→ 設計の「Derived=llm_*/case_link_*/thread_*」と一致。
- **機密/開示統制（HITL・LLM開示）**: `confidentiality_level`(default `client_confidential`), `access_class`(default `all_staff`), `redaction_status`/`redacted_text`/`redaction_hash`/`redaction_updated_at`, `external_llm_policy`(default `allowed_with_logging`)。→ 設計の confidentiality_level/access_class/redaction_status/external_llm_policy を **列レベルで実装済**。
- **開示監査**: `dynamic.llm_disclosure_log`（provider/model/purpose/requested_by/row_refs/payload_hash/redaction_mode/policy_snapshot/output_hash）が存在し、外部LLM開示の追跡を意図。ただし **0行**＝まだ稼働していない。
- **human gate**: `dynamic.unconfirmed_links`（target_table/target_id/proposed_sf_record_*/proposed_by/confidence/reason/status default `pending`/confirmed_by/confirmed_at）が「人手確認待ち」キューとして実装。ただし **0行**＝現状ゲート通過待ちなし（裏返すと自動紐付けの人手検証が一度も発生していない）。
- **id移行**: `dynamic.id_migration_map`(old_id/new_id/source/source_record_key) 実装あり・**0行**。

`dynamic.documents` も同等の三層+統制列（source/source_record_key/raw_pointer/archive_hash/sha256 = Raw、doc_type/title/filename/body_text_extract = Canonical、llm_*/case_link_status = Derived、download_status default `pending`/storage_pointer = Box取込状態）を備えるが **0行**。

### 1.3 指定オブジェクト → ミラー実体 対応表

凡例: 到達=スキーマ到達(列定義あり) / データ=実データ行あり / 状態。

| 指定オブジェクト(SF/LEALA) | ミラー実体 | 到達 | データ | 備考 |
|---|---|---|---|---|
| Consultation | `dynamic.cases`(sf_record_type=`leala__Consultation__c`) | 到達 | **0行・未確認** | comms側参照のみ存在(25) |
| Matter / Business | `dynamic.cases`(sf_record_type=`leala__Business__c`) | 到達 | **0行・未確認** | comms側参照のみ存在(318) |
| Account / Contact | `dynamic.parties`(party_type) | 到達 | 9行(部分) | SFのAccount/Contact水準ではなく通信主体としてのparty。staff:4/unknown:5 |
| Party(相手方/関係者) | `dynamic.parties` + `dynamic.comm_party_links.role` | 到達 | 9 / 488 | role= from/to/replied_to のみ。法律上の当事者属性(原告/被告等)は無 |
| Task / Event / Chatter / Office Meeting | （専用テーブル無し） | **未到達** | — | ミラー化対象外。SF同期で cases 配下に来る想定だが未実装 |
| Deadline / Procedure / JurisdictionCourt | （専用テーブル無し） | **未到達** | — | 同上。期限/手続/管轄裁判所の格納先がミラーに無 |
| Accounting / Billing / Invoice / Expense / Deposit / TimeCharge | （専用テーブル無し） | **未到達** | — | 会計・請求・実費・預り金・タイムチャージの格納先がミラーに無 |
| PostalMatter / RequiredDocument / KeepingItem | （専用テーブル無し） | **未到達** | — | 郵便/必要書類/預り品の格納先がミラーに無 |
| CaseDocument | `dynamic.documents` | 到達 | **0行・未確認** | Box正本との対応は storage_pointer/download_status 列で意図 |
| 変換関係(Consultation→Matter) | （専用テーブル/列 無し） | **未到達** | — | cases に旧→新を結ぶ列が無い。id_migration_map は汎用で0行 |
| BoxURL | `dynamic.documents.source_url`/`storage_pointer`, `comms.source_url` | 到達 | comms:343(全件埋) | documents側は0行で未確認 |
| 担当 | （cases.* に担当列無し） | 部分到達 | **未確認** | cases に owner/担当列が無い。`reviewed_by`(crc) のみ人手レビュー者を保持 |
| 流入経路 | （cases に流入経路列 無し） | **未到達** | **未確認** | Consultation の流入経路相当列がミラーに無 |
| 失注理由 | `chatwork_room_case_map.excluded_reason`(近似) / cases に無 | 部分到達 | **未確認** | 失注理由の正規格納列が cases に無 |
| 各日付(受付/相談/受任/終了) | `dynamic.cases.first_date`/`last_date`/`sf_synced_at` のみ | 到達 | **0行・未確認** | 受付日/相談日/受任日/終了日の個別列が無く first/last の2点のみ |
| 次行動・期限・待ち先 | （専用列/テーブル 無し） | **未到達** | **未確認** | 次行動/期限/待ち先の格納先がミラーに無（PoC1のKPI算出不能） |

`dynamic.cases` 実列（11列）: `sf_record_type`,`sf_record_id`(PK), `case_label`, `case_type`, `status`, `client_party_id`(FK→parties), `first_date`, `last_date`, `comm_count`, `doc_count`, `sf_synced_at`。→ SFのMatter/Consultationの豊富な項目(担当/流入経路/失注理由/各日付/次行動)は **この縮約スキーマには載っていない**。ミラーは「通信を案件に束ねる最小キー」までしか持たない。

### 1.4 主キー / 外部キー（到達済構造）

- `cases` PK=(sf_record_type, sf_record_id); FK client_party_id→parties.party_id。
- `comms` PK=comm_id。`documents` PK=doc_id。`parties` PK=party_id。
- `comm_party_links` PK=(comm_id, party_id, role); FK→comms, parties。
- `comm_document_links` PK=(comm_id, doc_id, link_type); FK→comms, documents。
- `comm_versions` PK=(comm_id, version_no); FK→comms。
- `chatwork_room_case_map` PK=(room_id, valid_from)（時系列有効区間 valid_from/valid_to を持つ SCD型）。
- 注: `comms.sf_record_type/sf_record_id` は cases への **FK制約が無い**（cases 0行でも comms に SF型値が入れられている＝整合性は論理のみ・DB制約で担保されていない）。
- `control` 系は releases/source_snapshots/ingest_jobs/ingest_job_batches/release_artifacts/active_release_pointer が相互FKで「取込→リリース→有効化」を制御。

### 1.5 control / formobj（参考到達）

- `control`: source_snapshots(15) / releases(1) / ingest_jobs(9) / ingest_job_batches(25) は **法体系KOS・書誌・人名典拠系のETL**(cinii/ndl/nichibenren/bencom-library/golden_term_card 等) に占有されており、**SF案件オブジェクトのリリース/取込実績は皆無**。→ §0.2 の「SF同期未実行」を制御層側からも裏付け。
- `formobj`: form_object(2)/form_variant(3)/form_witness(7)/requisite(18)/form_edge(3)。書式オブジェクトの provenance(provenance_family/verified_status/source_confidence)・identity_status(`provisional`)・evidence(form_witness の content_hash/section_path/extraction_method) を持ち、v0.2 の evidence/provenance/human_gate 設計と整合的だが、本票の指定オブジェクト群(案件・会計・通信)とは別系統。

## 2. 投入実査（埋まっている所だけ・集計のみ）

### 2.1 dynamic.comms（343行, ts: 2018-12-19 .. 2026-05-18）

| 指標 | 観測 |
|---|---|
| source | chatwork:343（**100% chatwork**。Gmail/Dialpad/SF Activity等は0） |
| direction | internal:343（**全件 internal**。default値のまま、in/out未分類） |
| case_link_status | room_inherited:343（**全件 room経由の継承**。`unknown`は0） |
| case_link_basis | room_inherited:343 |
| sf_record_type | leala__Business__c:318 / leala__Consultation__c:25（型は付与済） |
| sf_record_id | 343/343 充填（全件 何らかのSF idを参照） |
| thread_basis | self_root:288 / chatwork_rp_tag:55 |
| thread_confidence | 0.00:288 / 1.00:55（中間値なし＝二値運用） |
| thread_root_comm_id | 0/343（**未設定**。スレッド木は基準のみで根が未解決） |
| subject | 0/343（chatworkに件名概念なく未使用） |
| body_text | 343/343（PII含有・値は非転載） |
| llm_category / llm_summary | 0 / 0（**Derived LLM列は未稼働**） |
| confidentiality_level | client_confidential:343（全件） |
| external_llm_policy | allowed_with_logging:343（全件） |
| redaction_status | not_redacted:343（**全件未マスク**） |
| access_class | all_staff:343（全件） |
| source_label | 5 distinct room（**PII: 個人名/案件名含有・非転載**） |
| distinct chatwork_room_id | 5 |

所見:
- **状態と実態の乖離**: `case_link_status='unknown'` は **0%**。一見「全件案件紐付け済」に見えるが、紐付けは `room_inherited`(チャットルーム→案件の人手確定 chatwork_room_case_map を継承)に依存し、その紐付け元 cases 実体は0行。**「状態は確定的(room_inherited)だが参照先実体が無い」乖離**が定量的に確認できる(343/343)。
- `direction` が全件 default `internal` のまま＝**自由記述ではないがdefault過積載**。送受信方向の実態(対依頼者/対外)が未分類で、PoC1の「初回応答時間」「対外/内部」分解には使えない。
- redaction/LLM派生列はスキーマだけ在り稼働実績ゼロ＝統制パイプライン未起動。

### 2.2 dynamic.comm_party_links（488行）

| 指標 | 観測 |
|---|---|
| role | from:343 / to:90 / replied_to:55 |
| link_basis | chatwork_account_id:343 / chatwork_to_tag:90 / chatwork_rp_tag:55 |
| confidence | 488/488 充填、range 1.00..1.00（**全件 confidence=1.0**） |
| distinct comm | 343（comms全件に最低1リンク） |
| distinct party | 9 |

所見: link_basis は全て chatwork メタ由来(account_id/to_tag/rp_tag)で機械抽出。confidence が全件1.0＝**信頼度の分散が無く、確度モデルが実質機能していない**(自動付与の固定値)。法的当事者role(原告/被告/相手方代理人等)は無く、通信上のfrom/to/replied_toのみ。

### 2.3 dynamic.parties（9行）

| 指標 | 観測 |
|---|---|
| party_type | unknown:5 / staff:4（**過半が unknown**） |
| primary_chatwork_id | 9/9 充填 |
| primary_email | 0/9（**未充填**） |
| organization | 0/9（未充填） |

所見: 主体は chatwork_id でのみ同定。**5/9が party_type=unknown**＝名寄せ・属性付与が未完。SF Account/Contact との突合は未実施(cases 0行のため不能)。display_name 等PIIは非転載。

### 2.4 dynamic.chatwork_room_case_map（8行 = human gate の唯一の実体）

| 指標 | 観測 |
|---|---|
| link_status | confirmed:5 / mixed:2 / inferred_unreviewed:1 |
| link_basis | human_review:8（**全件 人手レビュー**） |
| sf_record_type | leala__Business__c:7 / leala__Consultation__c:1 |
| sf_record_id 充填 | 5/8（**3件は案件id未確定**） |
| reviewed_at | 8/8（全件レビュー時刻あり） |
| confidence | range 0.86..1.00 |
| mixed_flag=true | 0（mixed は link_status側でのみ表現） |

所見: ここだけが human gate(human_review)の実働実体。**8roomのうち sf_record_id 確定は5、未確定3(mixed2+inferred_unreviewed1)**＝「1room=1案件」が崩れる *mixed*(複数案件混在)が2件、未レビュー推論1件。これは v0.2 の「room→case は人手確定ゲート」の妥当性と、混在ルームという例外パターンの実在を裏づける。comms(5 distinct room)はこの8マップ定義を継承して case_link を得ている。

## 3. 空テーブル実査（0行の事実記録 = 未確認の線引き）

以下は **スキーマ到達済・データ未投入**。SFオブジェクト水準の入力率・状態乖離は **SF同期(ETL)未実行のため現時点で測定不能＝未確認**:

- `dynamic.cases`(0) … Consultation/Matter/Business の実体。**未確認**。
- `dynamic.documents`(0) … CaseDocument/BoxURL対応。**未確認**。
- `dynamic.comm_versions`(0) … 通信の版管理。**未確認**。
- `dynamic.comm_document_links`(0) … 通信⇔文書連結。**未確認**。
- `dynamic.unconfirmed_links`(0) … human gate待ち行列。空＝**人手検証待ち案件なし(=自動紐付け検証が未起動)**。
- `dynamic.id_migration_map`(0) … 変換関係(旧→新id)。**未確認**。
- `dynamic.pipeline_runs`(0) / `etl_watermarks`(0) / `etl_dead_letter`(0) … ETL運用記録。空＝**dynamic向けSF-ETLが一度も走っていない**ことの直接証拠。
- `dynamic.llm_disclosure_log`(0) … LLM開示監査。空＝外部LLM開示が記録上ゼロ。

各指定オブジェクトの判定（スキーマ到達/データ未投入の区別）は §1.3 対応表に集約済。**未到達(専用テーブルすら無い)** = Task/Event/Deadline/Procedure/Court/Accounting/Billing/Invoice/Expense/Deposit/TimeCharge/PostalMatter/RequiredDocument/KeepingItem/変換関係/流入経路/次行動・期限・待ち先。

## 4. v0.2モデルとの主要乖離・残課題（queue化推奨）

### 4.1 主要乖離 Top（v0.2/Phase0設計 vs ミラー実体）

1. **SF同期(ETL)未実行＝制御塔データ不在**: 指定オブジェクトの大半が cases/documents 0行 or 専用テーブル無しで、SF=業務制御塔の前提が **ミラー上では空**。PoC1のKPI(初回応答/相談確定/見積/契約 時間、次行動未設定率、流入経路不明率、失注理由未入力率、イベント未紐付け率)は **算出不能=未確認**。
2. **cases スキーマが縮約しすぎ**: 担当/流入経路/失注理由/受付日・相談日・受任日・終了日(個別)/次行動・期限・待ち先 を保持する列が `dynamic.cases`(11列) に存在しない。SFの該当項目をミラーするなら **スキーマ拡張が必要**。変換関係(Consultation→Matter)を結ぶ列も無い。
3. **状態と実態の乖離が定量化**: comms は case_link_status=room_inherited 100%・confidence全件1.0・direction全件internal default で「確定的に見えるが実体/分散が無い」。room_case_map は 8中3room が案件未確定(mixed/未レビュー)。Derived(llm_*)・redaction・disclosure_log は列のみで稼働ゼロ。「状態フラグが実態を表していない」典型。

### 4.2 残課題 queue（確認状態つき）

- **Q1[SF同期]**: dynamic.cases/documents への SF/LEALA ETL を起動し、Consultation/Business 実体を投入 → 入力率・状態乖離の実測を可能に。担当=外部SE/ETL運用。状態=未着手・要起動。
- **Q2[スキーマ拡張可否]**: cases に 担当/流入経路/失注理由/受付日・相談日・受任日・終了日/次行動・期限・待ち先 列を足すか、SF側を正としミラーは最小キーに留めるかの **設計判断**。状態=設計判断必要(浅井/外部SE裁定要)。
- **Q3[未到達オブジェクトのミラー方針]**: Task/Event/Deadline/Procedure/Court/会計各種/Postal/RequiredDoc/KeepingItem をミラー対象にするか否か。状態=設計判断必要。
- **Q4[変換関係]**: Consultation→Matter の実装(cases間リンク or id_migration_map活用)を定義。状態=未確認。
- **Q5[RLS/セキュリティ]**: dynamic/formobj/control 全BASE TABLE が **RLS無効**(Supabase advisor critical)。本番運用前に RLS+policy 付与必須。状態=要対応(運用ブロッカー)。
- **Q6[confidence/direction運用]**: comm_party_links.confidence 全件1.0・comms.direction 全件internal default の是正(実値投入 or 算出ロジック)。状態=未確認。
- **Q7[Derived/統制パイプライン起動]**: llm_category/llm_summary, redaction_status, llm_disclosure_log が稼働ゼロ。HITL/LLM開示統制の実起動とログ記録。状態=未起動。
- **Q8[mixedルーム例外]**: chatwork_room_case_map の mixed(2)/inferred_unreviewed(1) の人手確定運用フロー。状態=human gate運用要定義。

## 5. read-only 証明

使用ツール: `mcp__…__list_tables`(verbose=false) と `mcp__…__execute_sql`(全クエリ先頭 `select`/`with…select`)のみ。書込系(INSERT/UPDATE/DELETE/DDL/ALTER/TRUNCATE/COPY、apply_migration、deploy_edge_function、create_branch、merge/reset_branch 等)は **一切呼んでいない**。本番SF/Box書込ゼロ・ファイル移動/改名/削除なし・git操作なし。成果物は `docs/workflow_model/v0.2/` 配下のみ。
