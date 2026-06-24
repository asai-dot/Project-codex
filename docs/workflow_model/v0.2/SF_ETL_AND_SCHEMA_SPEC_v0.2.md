# SF-ETL 要件 ＋ dynamic スキーマ拡張 仕様 v0.2（外部SE向け・接続不要・設計のみ）

- worker_task_id: W-20260624-260
- generated_at: 2026-06-24
- source_request: docs/workflow_model/REQUEST_v0.2.md
- depends_on: W-110(SF実査) / W-180(owner裁定反映) / W-190(consultation_key=event_id) / W-210(源跨ぎ突合0%) / W-240(ETL後検証・受け皿)
- 前提方針: **Box＝文書正本 / Salesforce＝業務制御塔 / 自然発生データ優先 / Raw・Canonical・Derived 分離**

## 0. 本書の性質・宣言（冒頭固定）

- **接続なし＝設計のみ**。本書作成では外部システム(SF/LEALA/Supabase/Box/Gmail/Calendar/MF)へ一切アクセスしていない。`execute_sql`/`apply_migration`/`deploy_edge_function`/`create_branch` 等の Supabase 書込・読取系、Box/Gmail/Calendar の API は呼んでいない。すべて既存の v0.2 所見(W-110/180/190/210)からの**机上設計**。本番DB書込ゼロ・git操作なし。成果物は `docs/workflow_model/v0.2/` 配下のみ。
- **PII非記載**: 本書はスキーマ・型・制約・enum・様式・プレースホルダのみ。氏名/住所/電話/事件内容/金額/案件名は記載しない(規約ルール11)。
- **根拠の区別**: 各設計判断に **owner裁定(G-xx / D-xx)** と **worker推論(W-xxx 所見起点・SE/owner確認要)** を明示。AI推定を人間判断にしない(G-19)。未確定は「**SE/owner確認要**」と明記し、一般論で埋めない。
- **本書のスコープ境界**: 本書は「SE が ETL をターンキーで組むための仕様書(WHAT)」。実際のDDL適用・ETLジョブ実装(HOW)は SE の実装作業であり、本書は適用しない。SQL断片は**設計例**であって本番投入を意味しない。
- **重要な前提の制約**: SF/LEALA の生org項目(API名・データ型・picklist値・リレーション)は W-110 が **Supabaseミラー(read-only)経由**でしか到達できておらず、生orgの項目定義は**未実査**。よって本書の「SF側ソース項目名」は LEALA標準/慣用からの**worker推論であり、SF側の正確なAPI項目名・型・picklist は SE が生orgのスキーマで確定する必要がある(SE確認要)**。本書が確定するのは**ミラー(dynamic)側の受け皿スキーマと結合設計**。

---

## 1. 同期対象の確定（やること1）

REQUEST §3 Phase2 の対象オブジェクト群を、`ledger_v0.2/07_sf_mapping.csv` の4区分で「同期する/しない・どの dynamic テーブルへ」を確定する。区分: **a_asis**=既存テーブルをそのまま使う / **b_addfield**=既存テーブルに項目追加(§2) / **c_newtable**=別表新設(§2.3) / **d_unused**=同期しない。

凡例: 同期=Yes/No、行=既存(W-110で列定義到達済)/新設。

| # | 対象(SF/LEALA) | 区分 | 同期 | 投入先 dynamic テーブル | 根拠 | 状態 |
|---|---|---|---|---|---|---|
| 1 | Consultation(相談) | a_asis | Yes | `cases`(sf_record_type=`leala__Consultation__c`) | G-01 背骨ID / DS-001 | 既存・要投入(0行) |
| 2 | Matter / Business(受任) | a_asis | Yes | `cases`(sf_record_type=`leala__Business__c`) | G-01 / DS-002 | 既存・要投入(0行) |
| 3 | sf_record_type 判別 | a_asis | Yes | `cases.sf_record_type` | comms343に型参照済(Business318/Consultation25, EV-110) | 既存 |
| 4 | client(依頼者) | a_asis | Yes | `cases.client_party_id`→`parties` | G-10 / DS-005 | 既存 |
| 5 | payer(支払者) | **b_addfield** | Yes | `cases.payer_party_id`(追加)→`parties` | **G-10**(client/payer分離・保険会社払い対応) | §2.1 追加列 |
| 6 | Account / Contact / RelatedContact / OpponentParty | a_asis(近似) | Yes | `parties`(+`comm_party_links.role`) | DS-005 | 既存(法的当事者属性は無→§残課題) |
| 7 | 担当(owner/assignee) | **b_addfield** | Yes | `cases.assignee_*`(追加) | **W-110 Q2**(cases11列に担当無) | §2.1・要owner確認(粒度) |
| 8 | 流入経路(inflow) | **b_addfield** | Yes | `cases.inflow_channel`(追加) | **G-12**(必須〜準必須) / D-030 | §2.1 |
| 9 | 失注理由(loss reason) | **b_addfield** | Yes | `cases.loss_reason`(enum追加) | **G-12**(enum選択式・お断り/失注を区別) / D-030 | §2.1 |
| 10 | 各日付(到達/受理/入金) | **b_addfield** | Yes | `cases.arrival_date`/`acceptance_date`/`payment_date`(追加) | **G-11** / W-110(first/last2点のみ) | §2.1 |
| 11 | 各日付(受付/相談/受任/終了) | **b_addfield** | Yes | `cases.intake_date`/`consultation_date`/`engagement_date`/`closed_date`(追加) | W-110(粒度不足) / PoC1時間KPI | §2.1・要owner確認(SF項目対応) |
| 12 | 変換関係(Consultation→Matter) | **b_addfield**(+任意c) | Yes | `cases.consultation_ref`(追加, 自己参照) | **G-11/G-04**(受任=複数シグナル合成) / Q4 | §2.1・§3 |
| 13 | BoxURL / Boxフォルダ | **b_addfield** | Yes | `cases.box_folder_url`(追加) + `documents.storage_pointer` | G-02 / W-110 | §2.1 |
| 14 | CaseDocument | a_asis | Yes | `documents`(三層+統制列・既存) | DS-008 / G-02 | 既存・要投入(0行) |
| 15 | 受任ステータス(declared) | **b_addfield** | Yes | `cases.engagement_status_declared`(追加) | **G-04**(declared/observed分離) | §2.1・§4 |
| 16 | Task / Event / Chatter / Office Meeting | **c_newtable** | Yes | **`work_items`**(新設, G-08 4必須項目) | **G-08** / DS-003 / Q3 | §2.3-A・要owner確認(取込粒度) |
| 17 | 次行動・期限・待ち先 | **c_newtable** | Yes | **`work_items`**(新設) | G-08 / W-110(KPI算出不能の主因) | §2.3-A |
| 18 | Deadline / Procedure / JurisdictionCourt | **c_newtable** | Yes | **`deadlines`**(新設, 期限正本=SF) | **G-20**(正本=SF) / D-033 / G-05(7本化) | §2.3-B |
| 19 | Accounting / Billing / Invoice / Expense / Deposit / TimeCharge | **c_newtable** | Yes | **`finance_events`**(新設, client/payer分離) | G-10 / G-11 / DS-007 | §2.3-C・**入金確定の正は通帳(G-11)→SF会計はdeclared扱い** |
| 20 | PostalMatter / RequiredDocument / KeepingItem | **c_newtable** | **要判断** | (新設要否) | DS-008 / Q3 | **SE/owner確認要**(PoC1スコープ外・PoC2/別票で判断) |
| 21 | comms Derived(llm_category/llm_summary) | d_unused→将来b | No(現フェーズ) | `comms`(既存列・稼働ゼロ) | EV-110-llm0 / G-19 | 同期対象外(統制パイプ未起動) |
| 22 | comm_party_links.confidence | d_unused(是正要) | No(SF同期対象でない) | `comm_party_links`(既存) | Q6 | 是正は別票(Q6) |
| 23 | comms.direction | b_addfield(是正要) | No(SF同期対象でない) | `comms`(既存) | Q6 | 是正は別票(Q6) |

**同期しない(d_unused)もの**: #21〜23 は SF-ETL の対象ではない(chatwork通信側の Derived/確度/方向の運用是正であり、別キュー Q6/Q7)。本ETL では touch しない。

**同期対象の網羅性**: REQUEST列挙の全対象(Consultation/Matter/Account/Contact/Party/Task/Event/Deadline/Procedure/Court/Accounting/Billing/Invoice/Expense/Deposit/TimeCharge/PostalMatter/RequiredDocument/KeepingItem/CaseDocument/変換関係/BoxURL/担当/流入経路/失注理由/各日付/次行動・期限・待ち先)を上表で網羅。確定: a_asis 5 / b_addfield 11(列群) / c_newtable 4表(うち1表=#20は要否判断保留) / d_unused 3。

---

## 2. dynamic スキーマ拡張仕様（やること2）

### 2.0 現行 `dynamic.cases`(W-110実測・11列)

PK=(sf_record_type, sf_record_id)。現列: `sf_record_type`, `sf_record_id`, `case_label`, `case_type`, `status`, `client_party_id`(FK→parties), `first_date`, `last_date`, `comm_count`, `doc_count`, `sf_synced_at`。
→ owner裁定に必要な 担当/流入経路/失注理由/各日付/変換関係/BoxURL/payer の列が無い。以下を**追加**する。

### 2.1 `cases` への追加列(ALTER TABLE 設計案・13列)

凡例: NULL可否は **初期投入後の定常状態**を示す(初回バックフィル時は SF未入力により多くがNULL=実態。NOT NULL制約は将来運用で固める候補は注記)。

| # | 列名 | 型 | NULL | 既定 | 制約/enum | 由来・根拠 |
|---|---|---|---|---|---|---|
| 1 | `assignee_party_id` | uuid (or text) | YES | NULL | FK→`parties`(party_id) | 担当(owner裁定G-06/G-08で担当は必須項目)。**SF担当の同定キー(User Id vs party)はSE確認要** |
| 2 | `assignee_label` | text | YES | NULL | — | 担当の表示用(PII最小・原則party_id優先)。SF同期の生値保持用 |
| 3 | `inflow_channel` | text | YES | NULL | CHECK in enum or `inflow_channels`参照表 | **流入経路(G-12 必須〜準必須)**。値域はSF picklist次第→**enum値はSE/owner確認要** |
| 4 | `loss_reason` | text | YES | NULL | **CHECK in ('declined_by_us','lost_to_other','not_engaged','other')** | **失注理由(G-12 enum)**。①当方お断り=declined_by_us ②先方失注/離脱=lost_to_other ③受任に至らず=not_engaged ④その他=other。**「お断り」と「失注」を区別(G-12)** |
| 5 | `arrival_date` | date | YES | NULL | — | 到達日(G-11 相談到達=SF が正) |
| 6 | `acceptance_date` | date | YES | NULL | — | 受理日(G-11) |
| 7 | `payment_date` | date | YES | NULL | — | 入金日。**注: 入金の真実の源は通帳+MF突合(G-11)。SF入金日はdeclared扱い**(§4) |
| 8 | `intake_date` | date | YES | NULL | — | 受付日。SF対応項目はSE確認要 |
| 9 | `consultation_date` | date | YES | NULL | — | 相談日。PoC1時間KPI(P1-02)前提 |
| 10 | `engagement_date` | date | YES | NULL | — | 受任日(declared)。observed側はsignals表(§4)で突合 |
| 11 | `closed_date` | date | YES | NULL | — | 終了日。2段クローズ(G-09)の事務クローズ日とは別概念→**SE/owner確認要**(法的終了/事務クローズの対応) |
| 12 | `consultation_ref` | text | YES | NULL | FK→`cases.sf_record_id`(自己参照, Matter行→元Consultation Id) | **変換関係 Consultation→Matter(G-11/Q4)**。Matter行に元相談Idを保持。NULL=直受任 or 未変換 |
| 13 | `box_folder_url` | text | YES | NULL | — | 案件Boxフォルダ(BoxURL, G-02)。folder_id を含むURL様式 |
| 14 | `payer_party_id` | uuid (or text) | YES | NULL | FK→`parties`(party_id) | **支払者(G-10 client/payer分離)**。保険会社払い等。NULL=clientと同一 |
| 15 | `engagement_status_declared` | text | YES | NULL | CHECK in (SF picklist相当) | **受任ステータス declared(G-04)**。SFの相談→受任切替の生状態。**picklist値はSE確認要** |

注:
- 自己参照FK `consultation_ref` は PK が複合(type, record_id)である点に注意。実装は **record_id 文字列参照**とし、type は暗黙に Consultation を指す設計とするか、`(consultation_ref_type, consultation_ref_id)` の2列にするか **SE実装判断**(本書推奨: record_id 単独参照+type暗黙、id衝突が無い前提。SF Id はグローバル一意のため成立見込み・SE確認要)。
- `assignee_party_id`/`payer_party_id` の型は既存 `client_party_id` の型に合わせる(W-110で party_id は parties PK。型は uuid か text かを既存DDLに合わせる=**SE確認**)。
- enum を CHECK で固めるか参照表(lookup table)にするかは流入経路の値の安定性次第。**失注理由は owner裁定で4値固定(G-12)のため CHECK 推奨**。流入経路は値が増える想定→参照表が無難(SE判断)。

### 2.2 追加列のRaw/Canonical/Derived層位置づけ(G-16)

- 上記追加列は基本 **Canonical層**(SF生値の正規化ミラー)。
- SF生レコードの原本は **Raw層**として `cases` に `sf_raw_payload`(jsonb, 追加推奨) + `sf_source_url`(SFレコードURL) を持たせ、不可逆ポインタを残す(comms/documentsのraw_payload設計と平仄)。**SE確認要**(cases にRaw列を持たせるか、別 raw ステージング表に置くか)。
- declared/observed 乖離(§4)・KPI比率は **Derived層**(派生ビュー or 別表)で算出。`cases` 本体には declared を素直に持ち、observed・乖離は §4 の別表/ビューで表現(G-04)。

### 2.3 別表新設(c_newtable)テーブル定義案

#### A. `dynamic.work_items`(Task/Event/次行動・期限・待ち先 / G-08)

owner裁定 G-08: タスク必須4項目=**担当 / 期限 / 案件 / 次アクション**。Chatworkタスク(DS-023)とも項目を揃える。

| 列 | 型 | NULL | 制約 | 備考 |
|---|---|---|---|---|
| `work_item_id` | uuid | NO | **PK** | 生成id |
| `source` | text | NO | CHECK in ('salesforce','chatwork') | 取込元(G-08でChatwork対応づけ) |
| `source_record_key` | text | NO | UNIQUE(source, source_record_key) | SF Task/Event Id or Chatwork task_id(冪等キー) |
| `case_sf_record_type` | text | YES | — | FK部分→cases(type) |
| `case_sf_record_id` | text | YES | **FK→cases**(type,record_id) | 案件(G-08必須)。NULL=未紐付け(human gate候補) |
| `assignee_party_id` | uuid | YES | FK→parties | 担当(G-08必須) |
| `due_date` | date | YES | — | 期限(G-08必須) |
| `next_action` | text | YES | — | 次アクション(G-08必須・PII最小/様式) |
| `waiting_on` | text | YES | — | 待ち先 |
| `item_type` | text | YES | CHECK in ('task','event','chatter','office_meeting') | 種別 |
| `status` | text | YES | — | 進行状態(SF picklist相当・SE確認) |
| `sf_raw_payload` | jsonb | YES | — | Raw層原本 |
| `sf_synced_at` | timestamptz | YES | — | 同期時刻 |

注: G-08「4点必須」は**業務ルール上の必須**であり、ETL初回投入時はSF実値が欠けうる(=未設定率KPI P1-05の測定対象)。よって DB制約上は NULL許容とし、**未設定は欠落として観測**する(NOT NULLで弾くと実態を歪める)。owner裁定の「必須」はアプリ層/入力ゲートで担保(SE/owner確認要)。

#### B. `dynamic.deadlines`(Deadline/Procedure/JurisdictionCourt / G-20・G-05 7本化)

| 列 | 型 | NULL | 制約 | 備考 |
|---|---|---|---|---|
| `deadline_id` | uuid | NO | **PK** | |
| `source_record_key` | text | NO | UNIQUE | SF Deadline Id(冪等キー) |
| `case_sf_record_type` | text | YES | — | |
| `case_sf_record_id` | text | YES | **FK→cases** | 案件 |
| `deadline_type` | text | YES | CHECK in ('procedure','court','filing','other') | 手続/管轄/提出 等(SE確認) |
| `due_at` | timestamptz | YES | — | 期限。**正本=SF(G-20)** |
| `procedure_label` | text | YES | — | 手続名(様式) |
| `court_label` | text | YES | — | 管轄裁判所(JurisdictionCourt, PII最小) |
| `status` | text | YES | — | 未着手/対応中/徒過/完了(SE確認) |
| `sf_raw_payload` | jsonb | YES | — | Raw |
| `sf_synced_at` | timestamptz | YES | — | |

注: 期限の徒過防止は人・SF・AIの多重チェック(G-20)。AI推定の徒過警告は候補止まり(G-19)。

#### C. `dynamic.finance_events`(Accounting/Billing/Invoice/Expense/Deposit/TimeCharge / G-10・G-11)

| 列 | 型 | NULL | 制約 | 備考 |
|---|---|---|---|---|
| `finance_event_id` | uuid | NO | **PK** | |
| `source` | text | NO | CHECK in ('salesforce','moneyforward','bank_passbook') | 源(G-11突合のため複数源前提) |
| `source_record_key` | text | NO | UNIQUE(source, source_record_key) | 冪等キー |
| `case_sf_record_type` | text | YES | — | |
| `case_sf_record_id` | text | YES | **FK→cases** | 案件 |
| `event_kind` | text | YES | CHECK in ('billing','invoice','expense','deposit','time_charge','payment_received') | 会計イベント種別 |
| `payer_party_id` | uuid | YES | FK→parties | **支払者(G-10)**。clientと別人格を許容 |
| `amount_status` | text | YES | CHECK in ('declared','observed_passbook','reconciled') | **入金の真実=通帳, declared=SF/MF(G-11)** |
| `occurred_on` | date | YES | — | 発生日(金額値は本書記載せず=PII。列は持つ) |
| `currency` | text | YES | default 'JPY' | |
| `sf_raw_payload` | jsonb | YES | — | Raw |
| `sf_synced_at` | timestamptz | YES | — | |

注: **金額そのもの**(amount数値列)はテーブルには必要だが本書には値を書かない(PII)。`amount` 列(numeric)を持つ点のみ明記。入金確定の正本は銀行通帳(G-11, DS-024)→SF/MFは declared/突合先。消込は `amount_status='reconciled'` で表現。通帳/MF取込は未接続コネクタ(C1)=本ETLスコープ外・将来。

#### D. (保留) PostalMatter / RequiredDocument / KeepingItem

**SE/owner確認要**。PoC1スコープ外(相談→受任)。PoC2(解決→終結, W-250 closegate)で「預り原本返却」「必要書類」が close 条件に絡むため、**PoC2着手時に新設要否を判断**。本ETLでは新設しない(過剰設計回避)。

---

## 3. 背骨ID伝播（やること3）

### 3.1 背骨ID = SF Matter Id / Consultation Id(G-01)

- `cases` PK=(sf_record_type, sf_record_id) を**背骨ID**として確定(W-110で既にPK)。`sf_record_id` が SF Matter/Consultation Id。owner裁定 G-01。
- W-210 の定量: 源跨ぎ確定突合=**0%**(背骨ID不在)。源内 Calendar↔Docs は event_id↔doc_id で**71%**成立。→ 背骨IDを各源に伝播すれば源跨ぎ突合が解決する。

### 3.2 伝播設計(各テーブルへ sf_record_id を持たせる)

| テーブル | 背骨ID列 | 現状(W-110) | 伝播設計 |
|---|---|---|---|
| `cases` | PK(sf_record_type, sf_record_id) | PKは在る・0行 | ETLで実体投入(§5) |
| `comms` | `sf_record_type` / `sf_record_id` | 値は付与済(Business318/Consultation25)だが**FK制約無**(論理のみ) | ETL後 cases投入で参照先実体が埋まる。**FK制約追加を検討**(SE確認: 既存値の整合確認後に付与) |
| `documents` | (case参照列) | 0行・storage_pointer/download_status は在る | ETLで `case_sf_record_id` 相当を投入。Box正本=file_id+version_id(G-02)を storage_pointer に |
| `work_items`/`deadlines`/`finance_events`(新設) | `case_sf_record_id`(FK→cases) | — | §2.3で定義済 |
| 相談記録(consultation_key=event_id, W-190) | **新規対応列が要** | Calendar event 側にSF Id列無(W-210で確定突合0%の主因) | §3.3 |

### 3.3 相談記録(Calendar event)↔SF Consultation の接続(W-190/W-210)

- W-190: 相談記録は `consultation_key = event_id`(Calendar)で 1相談:N文書(添付fileUrl経由 doc_id)を束ねられる(源内71%)。
- 問題: Calendar event 側に SF Consultation Id 列が無い→源跨ぎ0%(W-210)。
- **設計**: `dynamic.unconfirmed_links`(既存 human gate表)+ 確定後の正規対応表で接続する。具体的には:
  - **(a)** 新規 `dynamic.consultation_event_map`(新設・任意) or 既存 `unconfirmed_links` を使い、`consultation_key(event_id)` ↔ `cases.sf_record_id(Consultation)` の対応を **人手確定(G-19: AI推定は候補止まり)** で持たせる。
  - **(b)** 自動マッチ(件名fuzzy/日付近接)は `unconfirmed_links` に `proposed_sf_record_*` として積み、status=pending→人手 confirmed で確定(W-110の human gate実装に沿う)。
  - **(c)** SF Consultation 側に Calendar event_id を持つ項目があれば(LEALA運用次第)それを正キーに使う方が確実→**SF生org項目の有無はSE確認要**。無ければ(a)(b)の人手ゲート経路。

### 3.4 結合経路図(背骨ID解決後・テキスト図)

```
                         [SF 背骨ID]
                    cases.sf_record_id
              (Consultation Id / Matter Id, G-01)
                            │
        ┌───────────────────┼───────────────────────┬──────────────┐
        │                   │                       │              │
   consultation_ref     comms.sf_record_id      documents       work_items
   (Matter→元相談)       (chatwork通信)         .case_*(Box正本) deadlines
        │                   │                  storage_pointer  finance_events
        │                   │                  =file_id+ver(G-02)  .case_*
        │                   │
   ┌────┴─────┐        (FK化候補)
   │ Calendar │
   │ event_id │──[unconfirmed_links / consultation_event_map]──→ cases(Consultation)
   │(W-190)   │     人手確定ゲート(G-19・候補→confirmed)
   └────┬─────┘
        │ attachments.fileUrl → doc_id (源内71%, W-190/W-210)
   ┌────┴─────┐
   │ Google   │
   │ Docs     │   ← 事件メモ(様式M/G)
   │(事件メモ)│
   └──────────┘

   Gmail(受任通知/見積/問合せ) ─[件名・差出人 fuzzy=候補のみ, W-210/W-220]→
        └─ 確定接続は (SF Idがメール側に無いため) unconfirmed_links 経由の人手確定 or
           Box通知/Chatwork ToDo通知に含まれる案件参照を抽出(候補)→人手confirmed
```

- **解決機序**: 背骨ID(cases.sf_record_id)が投入されれば、comms(値は既存)・documents・work_items/deadlines/finance_events はすべて `sf_record_id` で **DB結合可能**になる。W-210で0%だった「相談→見積→契約→受任」貫通は、(1)Calendar↔SF Consultation を人手確定ゲートで結び、(2)SF Consultation→Matter を `consultation_ref` で結べば、案件ID解決率として上昇する見込み(実測は W-240)。
- **伝播設計の可否(結論)**: **可**。既存PK(cases)・既存値(comms.sf_record_id)・既存human gate(unconfirmed_links/id_migration_map)を土台に、新設表へFKを張り、Calendar↔SF だけ人手確定ゲートを足せば成立する。Gmail↔SF は SF Id を持たないため恒久的に候補→人手確定(自動確定にしない, G-19)。

---

## 4. declared / observed 分離と乖離検知（やること4・G-04）

owner裁定 G-04: declared(入力状態)と observed(実態)を分けて持ち突合。受任は単一の正なし→複数シグナル合成(G-11): 委任契約書/委任状受領=Box正本(最強・G-02) / SF相談→受任切替(declared) / 受任通知の発送(Gmail)。

### 4.1 declared の格納

- `cases.engagement_status_declared`(§2.1 #15): SFの相談→受任切替の生ステータス。
- `cases.engagement_date`(declared受任日)・`cases.payment_date`(declared入金日, 真実は通帳)・`finance_events.amount_status='declared'`。

### 4.2 observed の格納先(新設 `dynamic.engagement_signals`)

| 列 | 型 | NULL | 制約 | 備考 |
|---|---|---|---|---|
| `signal_id` | uuid | NO | PK | |
| `case_sf_record_id` | text | YES | FK→cases | 背骨ID(未確定時NULL→human gate) |
| `signal_type` | text | NO | CHECK in ('mandate_contract_box','mandate_letter_box','engagement_notice_gmail','sf_status_switch') | S1委任契約書/委任状[Box最強]/S3受任通知[Gmail]/SF切替(G-11/W-210) |
| `source` | text | NO | CHECK in ('box','gmail','salesforce') | |
| `source_ref` | text | YES | — | Box file_id+version_id / Gmail message_id 等(正本ポインタ, G-02) |
| `observed_at` | timestamptz | YES | — | シグナル観測時刻 |
| `confidence` | numeric | YES | — | 機械抽出確度(候補, G-19) |
| `confirmed_by` | text | YES | — | 人手確定者(NULL=未確定=候補) |
| `confirmed_at` | timestamptz | YES | — | |

注: observed の「確定」は**人間承認**を経る(G-19・G-06受任成立は置けるが必須でないゲート)。S3受任通知Gmailは件名様式非標準で精度低(W-210/W-220)→候補止まり。S1 Box委任契約書/委任状=最強だが confirmed まで候補(G-19)。

### 4.3 乖離検知の置き場(Derived層・ビュー)

- **`dynamic.v_engagement_declared_observed_diff`**(派生ビュー・新設): `cases.engagement_status_declared`(declared) と `engagement_signals` から導く observed_受任状態を突合し、乖離フラグ(declared=受任 but observed無 / observed=受任 but declared未切替 等)を算出。
- KPI-P1-07(declared/observed乖離率, W-240)の算出基盤。実測は W-240(ETL後・実データ)。
- 乖離は**フラグであり自動確定でない**(G-19)。乖離検出→人手レビュー(unconfirmed_links と同様のゲート思想)。

---

## 5. ETL運用要件（やること5・Raw/Canonical/Derived分離 G-16）

W-110で**スキーマ実装済・0行**の運用テーブルを土台に組む: `etl_watermarks`(0) / `etl_dead_letter`(0) / `id_migration_map`(0) / `unconfirmed_links`(0) / `pipeline_runs`(0) / `llm_disclosure_log`(0)。「dynamic向けSF-ETLが一度も走っていない」(W-110 §3)状態を、以下要件で起動する。

### 5.1 冪等性(idempotency)

- **upsert キー** = SF Id(sf_record_id) / 新設表は `source_record_key`(UNIQUE)。同一レコードの再取込は INSERT…ON CONFLICT DO UPDATE で冪等に。重複行を作らない。
- 削除検知: SF側削除/マージは物理削除でなく `sf_deleted_at`(soft delete列, cases追加推奨・SE確認)で表現(append/履歴保全 G-03・G-17 退避思想)。

### 5.2 watermark(増分同期)

- 既存 `dynamic.etl_watermarks` を使用。オブジェクト種別ごとに `LastModifiedDate`(SF)相当の最終取込時刻を保持し、次回は `WHERE SystemModstamp > watermark` で増分取得。
- 初回は watermark 未設定→全件バックフィル(§5.6)。以後は増分。

### 5.3 dead_letter(失敗隔離)

- 既存 `dynamic.etl_dead_letter` を使用。変換/制約違反/FK解決不能(例: case未投入のwork_item)レコードは dead_letter に隔離し、本流を止めない。再処理可能に source_record_key と error を保持。

### 5.4 id_migration_map(id移行/変換関係)

- 既存 `dynamic.id_migration_map`(old_id/new_id/source/source_record_key) を使用。
- 用途: (a)旧システムid→SF Id の移行、(b)**Consultation→Matter 変換**の補助(主たる変換関係は `cases.consultation_ref`§2.1で持つが、id付け替え履歴は id_migration_map に残す)。G-03 履歴保全。

### 5.5 人手確認(unconfirmed_links = human gate)

- 既存 `dynamic.unconfirmed_links`(target_table/target_id/proposed_sf_record_*/proposed_by/confidence/reason/status default pending/confirmed_by/confirmed_at)。
- ETL自動マッチで確度が閾値未満/曖昧な紐付け(Calendar event↔SF Consultation §3.3、Gmail↔案件)は **confirmed にせず pending で積む**(G-19: AI推定は人間承認まで確定にしない)。人手 confirmed 後に正規テーブルへ反映。
- W-110: 現状0行=自動紐付け検証が未起動。ETL起動で初めてこのゲートが稼働する。

### 5.6 初回バックフィルの段取り

1. **依存順投入**: `parties`(既存9行+SF Account/Contact補完) → `cases`(Consultation→Matter順, consultation_ref解決のため) → `documents` → `work_items`/`deadlines`/`finance_events`/`engagement_signals`。FK解決順を守る(逆順だと dead_letter 増)。
2. **watermark 空**でフル取得→件数照合→ watermark セット→以後増分。
3. **comms 既存値の整合**: comms.sf_record_id(343件)が cases 投入後に解決するか照合。解決しないものは unconfirmed_links/dead_letter で可視化(W-110のキー先行・実体不在の解消確認)。
4. **PII方針**: バックフィル時も本文/氏名等の不要転載をしない。Raw層原本(sf_raw_payload)は jsonb で保持するが、一般成果物には出さない。

### 5.7 同期頻度

- **増分**: 日次 or 数時間毎(owner/SE運用判断)。期限(deadlines)は徒過防止(G-20)上、相対的に高頻度が望ましい→**SE/owner確認要**。
- **初回**: フルバックフィル1回(§5.6)。
- pipeline_runs(既存0行)に各実行のメタ(開始/終了/件数/結果)を記録し可観測性を確保。

### 5.8 Raw/Canonical/Derived 分離の遵守(G-16)

- **Raw**: `sf_raw_payload`(jsonb)・`sf_source_url`・source_record_key。不可逆原本ポインタ(comms/documents設計と平仄)。
- **Canonical**: §2.1/§2.3 の正規化列(日付・enum・FK)。
- **Derived**: declared/observed乖離ビュー(§4.3)・KPI比率。元レコードを書き換えず派生で算出(G-03 append-only)。

---

## 6. 接続：W-240(ETL後検証)受入条件 と W-170(RLS)注意（やること6）

### 6.1 W-240(ETL後検証)受入条件への対応マップ

W-240 の exit_criteria に本仕様が何で応えるか:

| W-240 受入条件 | 本仕様の対応 |
|---|---|
| dynamic.cases に行が入っている(0行ならBLOCK) | §5.6 初回バックフィルで Consultation/Matter 投入。投入後に W-240 が SELECT で確認 |
| 背骨ID解決率(相談event↔SF↔Box↔Gmail)を実測・W-210比較 | §3.2/§3.3/§3.4 の伝播設計と結合経路が解決機序。consultation_ref + unconfirmed_links 経路で源跨ぎが結べる |
| declared↔observed 乖離率(KPI-P1-07)実測 | §4 declared列 + engagement_signals + 乖離ビューが算出基盤 |
| 比率系KPI(次行動未設定/流入経路不明/失注理由未入力)実測 | §2.1 inflow_channel/loss_reason、§2.3-A work_items(next_action/due/assignee/case) が分母分子の格納先 |
| PII非転載・read-only・候補どまり | 本仕様は PII列を持つが値は出さない設計。W-240はSELECTのみ |

→ W-240 は本仕様通りにETLが投入された前提で、上記列を SELECT して NULL率・乖離率・解決率を実測する。**本仕様の追加列/新設表が無いと W-240 のKPIは算出不能**(W-110/W-210で実証済の前提待ち)。

### 6.2 W-170(RLS無効)デプロイ前提注意

- W-110 §1.1: dynamic/formobj/control 全BASE TABLE で **RLS無効**(Supabase advisor critical)。anon/authenticated に素通し。
- **本ETL本番化のデプロイ前提**: 新設表(work_items/deadlines/finance_events/engagement_signals)・cases追加列はいずれも **依頼者秘匿情報/会計/当事者**を含む。RLS無効のまま本番投入すると秘匿情報が素通しになる。
- **必須注意(SE/owner裁定要)**: ETL本番起動の**前に** RLS方針(有効化+policy付与, access_class/confidentiality_level 既存設計の活用)を決定・適用すること。本書はスキーマ設計のみで RLS policy は定義しない(Q5・別票)。**RLS未決のまま本番ETLを走らせないこと**をデプロイ前提注意として明記。

---

## 7. 残課題（SE/owner確認要点・一般論で埋めない）

1. **SF生org項目の正**(SE確認): 本書のSF側ソース項目名・型・picklist値(inflow_channel/loss_reason以外のenum、engagement_status_declared、各日付のSF対応項目、Calendar event_idを持つSF項目の有無)は**ミラー経由のworker推論**。SE が生orgスキーマで確定要。
2. **担当の同定キー**(owner/SE確認): assignee を SF User Id で持つか parties に正規化するか。party_id型(uuid/text)を既存DDLに合わせる。
3. **consultation_ref のFK実装**(SE): 複合PK下の自己参照(record_id単独 vs type+id 2列)。
4. **PostalMatter/RequiredDocument/KeepingItem 新設要否**(owner/SE): PoC2(W-250 closegate)で「預り原本返却」等に絡む→PoC2着手時判断。本ETLでは新設せず。
5. **closed_date と2段クローズ(G-09)の対応**(owner): 法的終了/事務クローズの2段を date 1列で足りるか、2列要るか。
6. **入金確定の正(G-11)**: SF/MFは declared、真実は通帳。通帳/MF取込は未接続コネクタ(C1)=本ETLスコープ外。finance_events.amount_status で declared/observed/reconciled を区別する設計のみ提示。
7. **RLS方針(Q5/W-170)**: 本番ETL前に必須決定(§6.2)。本書では未定義。
8. **comms.sf_record_id のFK制約付与**(SE): cases投入後、既存343値の整合確認の上で付与可否判断。
9. **同期頻度**(owner/SE): 期限系の高頻度要否(G-20徒過防止)。
10. **comms.direction / comm_party_links.confidence 是正(Q6)**: 本ETL対象外。別票。

---

*生成: W-20260624-260。外部システム非アクセス(設計のみ・本番未接触)。PII非記載(スキーマ/様式/プレースホルダのみ)。owner裁定(G-xx/D-xx)とworker推論(SE/owner確認要)を区別。未確定は明示。AI推定を人間判断にしない(G-19)。git操作なし。成果物は v0.2 配下のみ。捏造なし。*
