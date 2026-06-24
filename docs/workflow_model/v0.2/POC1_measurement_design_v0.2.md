---
worker_task_id: W-20260624-200
title: PoC1（相談〜受任）計測設計 v0.2
created_at: 2026-06-24
owner: claude-code-worker
source_request: docs/workflow_model/REQUEST_v0.2.md (§6)
poc: PoC1
premise: Box=文書正本 / Salesforce=業務制御塔 / 自然発生データ優先 / Raw・Canonical・Derived分離
inputs:
  - ALO_WORKFLOW_GAP_AND_POC_PLAN_v0.2.md   # W-160 PoC範囲・KPI素案
  - ALO_OWNER_GRILL_ANSWERS_v0.1.md          # owner確定 G-01..G-20
  - ALO_WORKFLOW_CATALOG_v0.2.yaml           # states7本/human_gates3/metrics
  - PHASE5_consultation_record_survey_v0.2.md # W-190 相談記録(Calendar/Docs)実査
  - alo_workflow_event_schema_v0.2.json      # event_type語彙
  - ALO_WORKFLOW_EVIDENCE_LEDGER_v0.2.jsonl  # Gmail 3トレース
  - PHASE2_salesforce_survey_v0.2.md         # W-110 SFミラー実査(cases 0行)
pii_policy: 氏名・住所・電話・事件内容・具体的金額は記載しない（型・構造・集計のみ）
status_note: |
  SF/LEALA/Notta/MoneyForward/銀行通帳/Dialpad は本環境に接続コネクタ無くBLOCKED/未接続。
  接続済 = Google Calendar / Google Docs(Drive) / Box / Gmail。
  本書は「接続済だけで取れる計測」と「前提待ち(未接続/BLOCKED)」を分離する。捏造禁止。
  owner裁定(G-xx/D-xx)と worker推論を各設計で明示分離。AI推定は Derived・人間未承認に留める。
---

# PoC1（相談〜受任） 計測設計 v0.2

PoC1 スコープ（owner裁定 G-07 / D-008）= **新規流入 → 相談案件(Consultation)起票 → Boxフォルダ作成 → 相談実施 →〈相談止まりなら完了／受任に至れば受任まで〉**。実害小・件数多・回転速が選定理由。「受任」=「じゅにん」。本書は本スコープ（WF-00..12）を運用手順へ落とし、KPI 8本の計測設計・受任判定ロジック・相談記録合成・受入基準・着手段取りを定義する。

## 凡例（根拠と確信の分離）

- 根拠タグ: `G-xx`=owner裁定(ALO_OWNER_GRILL_ANSWERS_v0.1)、`D-xx`=決定ログ、`W-xxx`=worker成果物。`[worker推論]`=本書の設計提案で owner未裁定のもの。
- 測定可否タグ:
  - **接続済**: Google Calendar / Google Docs(Drive) / Box / Gmail のいずれかで今すぐ取得可能。
  - **未接続**: Notta / MoneyForward / 銀行通帳 / Dialpad コネクタ不在（自然発生源が取れない）。
  - **BLOCKED(SF)**: Salesforce/LEALA。W-110 実査で `dynamic.cases` 0行＝制御塔データ不在、かつ縮約スキーマに担当/流入経路/失注理由/各日付/次行動の列が無い。ETL起動＋スキーマ拡張が前提。
- provenance basis: `observed`（自然発生データ観測・confidence付） / `declared`（人間が宣言した状態の正本＝主にSF） / `human_decision`（人間承認） / `ai_estimated`（Derived・人間未承認、確定にしない G-19/D-031）。

---

## 1. 対象パイプライン WF-00..12 運用記述（やること1）

7状態機械（owner裁定 G-05/D-022 で確定）= consultation / matter / work_item / document / finance / delivery / deadline。PoC1 の主機械は **consultation**（17状態）。`発火イベント` は `alo_workflow_event_schema_v0.2.json` の event_type コアenum。`next_state` は consultation 機械の状態（特記したもののみ他機械）。`human gate` は G-06 確定の必須3点＋optional。

| WF | フェーズ | トリガ | 入力者(actor) | 入力物 | 発火イベント(event_type) | 次状態(machine.state) | 必須human gate | 計測接続性 |
|---|---|---|---|---|---|---|---|---|
| WF-00 | 認知・紹介(流入) | 紹介/HP/セミナー/既存顧客の接点発生 | 弁護士/事務局 | 接点シグナル, 流入経路情報 | （system_log / email） | consultation.new | — | 接続済(Gmail)/一部 BLOCKED(SF流入経路列無) |
| WF-01 | 問合せ受付 | 新規連絡を受信 | 事務局 | 問合せ(メール/電話/フォーム) | `inquiry_received` | consultation.inquiry | — | 接続済(Gmail) / 電話初回は 未接続(Dialpad) |
| WF-02 | 安全連絡・本人関係確認 | 相談候補作成 | 事務局 | 連絡先, 本人識別情報 | `consultation_candidate_created`, `safe_contact_confirmed`, `party_identified` | consultation.identity_checked | — | 接続済(Gmail) / 確定は BLOCKED(SF) |
| WF-03 | コンフリクト確認 | 当事者・関係者名取得 | 弁護士＋事務局 | 当事者名, 関係者名, 相手方名 | `conflict_check_requested`, `conflict_check_completed` | consultation.conflict_pass/fail | **HG-01 利益相反(マスト①, G-06)** | BLOCKED(SF) ＝ declared正本/最小データ G-13 |
| WF-04 | 受入可否・緊急度トリアージ | コンフリpass又は緊急例外 | 弁護士 | 事案概要, 期限, 分野 | `triage_completed` | consultation.triaged | —（緊急受任は事後コンフリ例外 EXC-urgent_bypass） | BLOCKED(SF) |
| WF-05 | 相談日程調整 | 相談実施GO | 弁護士/事務局 | 候補日時, 相談方式, 費用条件 | `consultation_date_options_sent`, `consultation_scheduled` | consultation.scheduled | — | **接続済(Calendar/Gmail)** |
| WF-06 | 事前資料依頼・受領 | 相談日時確定 | 事務局＋担当弁護士 | 必須資料リスト, 受領資料 | `document_requested`, `document_received`, `document_classified` | document.received | — | 接続済(Box/Gmail) |
| WF-07 | 相談実施 | 予約時刻到来 | 担当弁護士 | 相談予約, 事前資料 | `consultation_started`, `consultation_completed`, `advice_recorded` | consultation.consulted | — | 部分: 予定/メモ=接続済(Calendar/Docs) / 議事録本体=未接続(Notta) |
| WF-08 | 相談後評価（相談止まり判定点） | 相談完了 | 担当弁護士 | 相談記録, 論点 | `followup_question_received`, `post_consult_decision_recorded` | consultation.followup / closed_lost | —（失注理由 enum G-12/D-030） | BLOCKED(SF) ＝失注enum正本 |
| WF-09 | 見積・提案作成 | 受任提案GO又は見積依頼 | 担当弁護士＋事務局 | 費用条件, 提案テンプレート | `quote_requested`, `proposal_created`, `proposal_approved_internal` | finance.quote_draft | — | 接続済(Box発行日) |
| WF-10 | 提案・契約案送付 | 内部承認完了 | 事務局 | 承認済提案, 送付先 | `proposal_sent`, `proposal_followup_due` | finance.quote_sent | — | 接続済(Gmail/Box) |
| WF-11 | 条件調整・契約締結（受任分岐） | 顧客回答 | 担当弁護士＋事務局 | 顧客回答, 修正要望 | `proposal_revision_requested`, `proposal_accepted`, `proposal_rejected`, `engagement_signed` | consultation.converted / closed_lost | **HG-02 受任成立=optional(G-06)** 確定は人間承認 | 接続済(Gmail/Box) + 確定は BLOCKED(SF declared) |
| WF-12 | 案件開設・初期請求 | 受任成立条件充足 | 事務局 | 締結済契約, 案件メタデータ | `consultation_converted_to_matter`, `matter_workspace_created`, `retainer_invoice_sent` | matter.onboarding | — | BLOCKED(SF背骨ID) + 接続済(Box/Gmail) |

**ファネル要約（G-07）**: 流入(WF-00)→相談案件起票(WF-01/02)→Boxフォルダ作成(WF-06前後で案件フォルダ生成)→相談実施(WF-07)→相談後評価(WF-08)で **相談止まり=closed_lost / 受任=WF-09..12 経由で converted**。受任判定の詳細は §3。

**human gate 反映（G-06/D-023）**: PoC1区間のマスト必須は **HG-01 利益相反(WF-03)** のみ。HG-02 受任成立(WF-11) は owner裁定で「置けるが必須ではない」=optional。ただし本書受入基準(§5)では「受任の確定は人間承認」とし、AI/observed合成だけで自動converted化しない（G-19/D-031）。

---

## 2. KPI 8本 計測設計表（やること2）

KPI定義は owner裁定（catalog metrics.poc1, G-07/G-08/G-12）で確定済。**現状値の算出可否**を接続性で分ける。測定不能は「定義のみ・前提待ち」と明示し、一般論で埋めない。

### 2.1 時間系KPI（4本）

| KPI | 算出式 | 分子/分母の定義 | データ源（理想／現状） | 測定可否 | 取得方法 |
|---|---|---|---|---|---|
| KPI-P1-01 初回応答までの時間 | `first_response_at − inquiry_received_at` の中央値/分布 | 各相談1件＝1観測。分子=最初の応答送信時刻−問合せ受信時刻 | 理想: SF受付日時+Gmail/Dialpad / 現状: Gmail送受時刻 | **接続済(Gmail)** ＝メール起点のみ算出可。電話初回は **未接続(Dialpad)** で欠落 | Gmail `search_threads`/`get_thread` で受信→最初の自所アドレス送信のタイムスタンプ差。電話起点は当面 Gmail に限定と明示 |
| KPI-P1-02 相談確定までの時間 | `consultation_scheduled_at − inquiry_received_at` | 分子=相談予約確定時刻−受信時刻 | 理想: SF相談日+Calendar / 現状: Calendar event.start + Gmail受信 | **接続済(Calendar/Gmail)** ＝予定作成で確定検知可。SF相談日(declared)正本は BLOCKED(SF) | Calendar `list_events`(相談型予定)の作成/start と Gmail受信を event_id↔thread で突合。受信側が Gmail のため初回が電話だと分母欠落 |
| KPI-P1-03 見積送付までの時間 | `proposal_sent_at − consultation_completed_at` | 分子=見積/契約案送付時刻−相談完了時刻 | Box見積PDF発行日 + Gmail送付時刻 | **接続済(Box/Gmail)** ＝発行・送付とも観測可 | Box `get_file_details`(見積PDF created/version) と Gmail送付を突合。相談完了時刻は WF-07(Calendar/Notta)依存=Notta未接続時は Calendar予定終了で近似 |
| KPI-P1-04 契約成立までの時間 | `engagement_signed_at − proposal_sent_at` | 分子=受任成立時刻−見積送付時刻 | Gmail(trace1 0102→0104実証) + SF受任日 | **接続済(Gmail)で近似可** / 確定は BLOCKED(SF declared受任日) | Gmail で proposal_sent→engagement_signed の thread 内タイムスタンプ。確定時刻は §3 受任判定の合議結果に従い、SF切替日が正本 |

### 2.2 比率系KPI（4本）

| KPI | 算出式 | 分子/分母の定義 | データ源（理想／現状） | 測定可否 | 取得方法 |
|---|---|---|---|---|---|
| KPI-P1-05 次行動未設定率 | `(担当/期限/案件/次アクションのいずれか欠落のWI数) / (open/waiting状態の全WI数)` | owner裁定 G-08/D-011: WorkItem必須4項目=担当/期限/案件/次アクション。＋Chatworkタスク(DS-023)対応 | 理想: SF次行動・期限フィールド / 現状: Ledger で due_at 全件null | **BLOCKED(SF)** ＝定義のみ。現行入力率はSF実査要 | SF ETL後 cases/Task の owner/due/next_action 充足率。Chatwork連携(DS-023)も突合。**現状は前提待ち** |
| KPI-P1-06 流入経路不明率 | `(流入経路が空/不明の相談数) / (全相談数)` | owner裁定 G-12/D-030: 流入経路=必須〜準必須（紹介案件は記載済）。EXC-source_unknown | 理想: SF流入経路フィールド | **BLOCKED(SF)** ＝定義確定・現状値は前提待ち。SFミラーに流入経路列が無く新設要(W-110 Q2) | SF ETL+スキーマ拡張後に未入力件数を集計。**定義のみ・前提待ち** |
| KPI-P1-07 失注理由未入力率 | `(enum未選択の失注数) / (全失注数)` | owner裁定 G-12/D-030: 失注理由=enum選択式 `①当方お断り②先方失注/離脱③受任に至らず④その他`。「お断り」と「失注」を必ず区別。自由記述必須化はしない | 理想: SF失注理由enumフィールド | **BLOCKED(SF)** ＝定義確定・現状値は前提待ち。trace2 で「失注 vs 相談完了」区分が未確定 | SF ETL+enum列新設後に未選択率を集計。**定義のみ・前提待ち** |
| KPI-P1-08 イベント未紐付け率 | `(背骨IDに解決しないイベント数) / (全イベント数)` | owner裁定 G-01/D-001: 背骨=SF Matter ID（およびConsultation ID）。EXC-unlinked_event | 全イベントの matter_ref/consultation_ref 解決率 | **接続済(部分)＋BLOCKED(SF)** ＝接続源(Calendar/Gmail/Box/Docs)内の event↔doc/thread 紐付けは今すぐ測定可。SF背骨IDへの最終解決は BLOCKED | 接続源では §4 の event_id↔doc_id 結合で「相談記録内の未紐付け率」を先行測定可。SF背骨ID解決率は ETL後 |

**KPI測定可否内訳**: 接続済で**今すぐ着手可能=4本**（KPI-P1-01/02/03/04、いずれも時間系。01は電話分欠落・近似明示）。加えて KPI-P1-08 は接続源内の部分計測のみ着手可（SF背骨解決は前提待ち）。**前提待ち=4本**（KPI-P1-05 次行動未設定率 / 06 流入経路不明率 / 07 失注理由未入力率 はBLOCKED(SF)、08 のSF背骨解決部分も前提待ち）。詳細は §6。

> 注: 「相談実施までの時間」「相談実施の所要・要点」を厳密化するには **Notta未接続**が効く。現状は Calendar 予定の start/end で近似し、議事録本体由来の値は「未接続＝未測定」と明示する（捏造しない）。

---

## 3. 受任判定の具体化（やること3 / G-11・G-04）

owner裁定 G-11: **受任は単一の正なし → 複数シグナル合成**。受任到達自体は SF が相談到達の正だが、受任は「委任状・委任契約書の受領(Box正本/最強)・SFの相談→受任切替・受任通知の発送」で合成する。G-04: declared/observed を分けて持ち突合。

### 3.1 observed_受任 を構成する3シグナル

| # | シグナル | データ源 | 抽出方法 | basis | confidence | 接続性 |
|---|---|---|---|---|---|---|
| S1 | 委任状/委任契約書の受領 | **Box（文書正本・最強, G-02）** | Box `search_files_keyword`/`get_file_details` で委任契約書相当の文書種別＋version 確定（docx⇔pdf確定版）。file_id+version_id を source_ref に固定 | observed | **高**（正本受領=最強シグナル, G-11明記） | 接続済(Box) |
| S2 | SF 相談→受任ステータス切替 | **Salesforce（制御塔, G-01）** | cases.status の Consultation→Matter/受任 への遷移、`consultation_converted_to_matter` 相当。declared の正本 | declared | 高（制御塔の宣言値） | **BLOCKED(SF)** ＝cases 0行・変換関係列無し(W-110 Q4)。ETL後 |
| S3 | 受任通知の発送 | **Gmail** | 受任通知メールの送信を `search_threads` で検知（trace1:engagement系）。送信時刻＝observed | observed | 中（送信は強いが文面分類に余地） | 接続済(Gmail) |

補助（確定に使わない）: Calendar 型D議事録行 description の「受任通知発送」等の進捗語（W-190 §4）は **Derived の補助観測**に留め、受任の確定判断には用いない（自由記述・非信頼）。

### 3.2 合議ルール [worker推論：owner未裁定の閾値は要確定]

owner裁定は「複数シグナル合成」までで、重み/閾値は未裁定。本書の提案（前提待ち裁定対象）:

- **observed_受任=true（候補）の成立条件**: S1（Box委任契約書受領）が在れば単独でも observed 受任候補（最強・confidence高, G-11）。S1不在時は S2+S3 の2つ以上で候補化。S3単独は候補化のみで確定不可。
- **confidence 合成**: S1=高、S2=高(declared)、S3=中。複数一致で加点、source_ref を全件 provenance に保持。
- **確定（converted への遷移）**: observed_受任候補は **人間承認（HG-02）で確定**。HG-02 は owner裁定で optional(G-06)だが、本書受入基準は「受任の確定は人間承認」とし、AI/observed合成だけで自動 converted 化しない（G-19/D-031）。

### 3.3 declared/observed 突合と乖離検知（G-04/D-004）

- **declared_受任** = SF 受任ステータス（S2、制御塔の宣言値, BLOCKED で現状空白）。
- **突合**: 同一 consultation_key/matter_ref で observed_受任（S1/S3合成）と declared_受任（S2）を並べる。
- **乖離パターンと検知**:
  - observed先行（Box委任契約書受領あり・SF切替なし）→ **SF未入力疑い**を可視化、HITLキューへ。
  - declared先行（SF受任切替あり・Box正本/Gmail通知なし）→ **正本未保管疑い**を可視化。
  - 双方一致 → confidence最大・HG-02承認で確定。
- **現状の制約**: declared側(SF)が BLOCKED のため、乖離検知は **接続後に初めて稼働**。現状は observed側（Box/Gmail）のみ構築可。

**受任判定ロジックの確定可否**: 設計（3シグナル定義・源・抽出・confidence・declared突合・人間承認確定）は **確定**。ただし(a)合議の重み/閾値はowner未裁定[worker推論]、(b)declared側S2はBLOCKED(SF)で実稼働は前提待ち。よって**ロジックは確定・実稼働は部分（observed側のみ着手可、突合はSF接続後）**。

---

## 4. 相談記録合成の組込（やること4 / W-190）

W-190 実査（Google Calendar/Docs read-only）に基づく。一次結合 = **event_id ↔ doc_id（添付fileUrlのdoc_id経由）**、ID完全一致・検証済（W-190 §3）。

### 4.1 束ねるキーと多重度

- **consultation_key = カレンダー event_id**（相談イベントの自然単位, W-190 §5.1）。
- 結合: `calendar.event.attachments[].fileUrl` から正規表現 `/document/d/(<doc_id>)/` で doc_id 抽出 → `drive.file.id` と突合（信頼度=高）。
- **1相談 : N文書**（手打ちメモ様式M + Geminiメモ様式G が1イベントに付く）。
- 補助結合: (a) description内のDoc/Notta共有URL（信頼度中・疎）、(c) 命名一致 `「<件名>」≒event.summary`（信頼度低・fuzzy救済）。
- Notta: 接続後に description/添付の notta share uuid を `notta_session_id` として同 consultation_key へ束ねる（**現状=未接続=空欄設計**）。
- 案件昇格: `consultation_converted_to_matter` で `matter_ref`（SF/Box側ID）へ接続。

### 4.2 Raw / Canonical / Derived 配置（owner裁定 G-16/D。本文非取り込み=秘匿特権保護）

- **Raw（原本ポインタのみ・本文非格納）**:
  - `cal_event_ptr`: calendarId + event_id + htmlLink + updated
  - `doc_ptr[]`: drive file_id + title + owner + modifiedTime + parentId（**本文は格納しない**。Box=正本方針に沿い原本はGoogle側に残しポインタ参照）
  - `notta_ptr`: share uuid（**未接続のため現状 null＝空欄**）
- **Canonical（正規化メタ。PIIは別アクセス制御層）**:
  - `consultation_*`: { consultation_key(event_id), occurred_at(event.start), channel(来所/web/電話を様式から導出), source_refs=[Raw ptrs], matter_ref(任意) }
  - event語彙マッピング（schema_v0.2に既存・新規型不要）: `consultation_scheduled`(予定作成) / `consultation_started`・`consultation_completed`(実施) / `advice_recorded`(メモDoc生成)。provenance に Raw ptr を必須記載。
- **Derived（要約・分類）= AI限定・人間未承認**:
  - 相談分野（型Dの `＿<分野>` 語からの分類候補）、受任見込みフラグ（description進捗語からの observed・人間未承認）、相談→受任リードタイム。
  - **AI推定は Derived 限定・confidence付・人間未承認（G-19/D-031）**。受任確定はここで判断しない（§3.2）。

### 4.3 相談 vs 非相談の判別ルール案 [worker推論：要検証]

W-190 §1.3 で、同一の「相談」語が個別案件と公益/勉強会/会議議題（型E・型D）に混在＝語彙だけでは判別不可。複合ルール案:

| 判定 | 添付(Doc) | 参加者 | タイトル分野語 | 扱い |
|---|---|---|---|---|
| 個別相談（採用） | あり（事件メモDoc添付） | 当事者がタイトル/attendees | 当事者名＋相談語 | consultation_record に採用 |
| 会議議題行（型D, 除外） | なし or 棚卸し掲示 | availability=FREE/transparent ブロック | `[事務所会議...]＿<分野>` | 案件ステータス掲示＝相談記録から除外 |
| 公益/勉強会（型E, 除外） | なし | 外部団体/当番 | 当番弁護士/区役所/商工会議所/協議会/勉強会 | 非個別案件＝除外 |

- **一次規則**: 事件メモDoc添付あり（§4.1 結合成立）を個別相談の主シグナルとし、型D（FREE/transparent掲示）・型E（公益語彙）を除外。添付なし個別相談の救済は命名fuzzy(c)＋閾値[要設計]。
- Notta未接続のため議事録本体の件数・構造は **空欄設計**（未測定）。

---

## 5. 受入基準（やること5）

PoC1 の合格条件。owner裁定（G-06/G-19/D-023/D-031）と整合。

1. **P0遷移は全件 provenance(source ref) 付き**: consultation 機械の各遷移（inquiry_received → … → converted/closed_lost）が `source.native_id` または `decision.evidence_refs` を持つこと（Ledger は実装済の封筒形）。source_ref 欠落の遷移は不合格。
2. **曖昧は HITL（人間判断）へ**: confidence 閾値未満／basis=observed のみの重大遷移（受任成立 HG-02・コンフリ pass HG-01）は `review.status=pending` で人間承認に回し、自動確定しない（G-06/G-19/D-031）。AI推定を確定（human_decision）に昇格させない（forbidden: ai_estimate_as_human_decision）。
3. **open相談の owner・due 欠落を可視化**: status=open/waiting の WorkItem で owner または due_at が欠落するものを一覧化（owner裁定 G-08 の必須4項目＝担当/期限/案件/次アクションに対応）。現状 Ledger は全WI due_at=null＝全件可視化対象。
4. **イベントは全て event_id↔エンティティに紐付け**: 全イベントが consultation_key（event_id）または背骨ID（SF matter_ref/consultation_ref, G-01）へ解決すること。接続源内（Calendar/Gmail/Box/Docs）の未紐付け率は §4 結合で先行測定、SF背骨解決は接続後（KPI-P1-08）。
5. **受任の確定は人間承認**: §3.2 の observed合成だけで converted へ自動遷移させない。HG-02 は optional だが「確定は人間承認」を受入基準として固定（worker推論。owner裁定 G-06 の optional と矛盾せず、G-19 の確定境界に従う）。

---

## 6. 計測の段取り（やること6）

接続済（Calendar/Docs/Box/Gmail）だけで今すぐ取れるものと、未接続/BLOCKED解消後に初めて取れるものを分離。

### 6.1 今すぐ着手可能（接続済のみで取れる）

| 項目 | 取得源 | 備考 |
|---|---|---|
| KPI-P1-01 初回応答までの時間 | Gmail | メール起点のみ。電話初回は欠落（Dialpad未接続）と明示 |
| KPI-P1-02 相談確定までの時間 | Calendar + Gmail | 予定作成で確定検知。SF相談日(declared)は前提待ち |
| KPI-P1-03 見積送付までの時間 | Box + Gmail | 発行日・送付時刻とも観測可 |
| KPI-P1-04 契約成立までの時間 | Gmail | proposal_sent→engagement_signed の近似。確定はSF切替日 |
| 相談記録合成（§4） | Calendar + Docs(Drive) | event_id↔doc_id 結合・Raw/Canonical/Derived 構築。1相談:N文書 |
| 受任 observed側（§3 S1/S3） | Box + Gmail | 委任契約書受領(S1)・受任通知発送(S3)の observed 合成 |
| KPI-P1-08（部分） | Calendar/Gmail/Box/Docs | 接続源内の event↔doc/thread 未紐付け率のみ |
| 相談 vs 非相談 判別（§4.3 一次規則） | Calendar + Docs | 添付有無＋参加者＋分野語の複合ルール |

→ **今すぐ計測着手できるKPI = 4本**（KPI-P1-01/02/03/04）。＋KPI-P1-08 は接続源内の部分計測のみ着手可。受任 observed側・相談記録合成も着手可。

### 6.2 前提待ち（接続・ETL後に初めて取れる）

| 項目 | 前提（解消事項） | ブロッカー |
|---|---|---|
| KPI-P1-05 次行動未設定率 | SF ETL起動＋cases に担当/期限/次行動列の現行入力率測定 | BLOCKED(SF) W-110 |
| KPI-P1-06 流入経路不明率 | SF ETL＋流入経路列の新設（縮約スキーマに無, Q2） | BLOCKED(SF) W-110 |
| KPI-P1-07 失注理由未入力率 | SF ETL＋失注理由 enum列の新設。trace2 の失注/相談完了区分の確定 | BLOCKED(SF) W-110 |
| KPI-P1-08 イベント未紐付け率（SF背骨解決） | SF背骨ID(Matter/Consultation Id)へのイベント解決＝ETL＋変換関係列(Q4) | BLOCKED(SF) W-110 |
| 受任 declared側（S2）・declared/observed乖離検知 | SF cases 投入＋相談→受任切替の実体 | BLOCKED(SF) W-110 |
| 相談実施時間の厳密化・議事録要点 | Notta コネクタ接続 | 未接続(Notta) |
| 受任判定の合議重み/閾値の確定 | owner裁定（本書 §3.2 提案の承認） | owner裁定待ち |
| 受任判定の閾値・命名fuzzy閾値 | 設計検証 | [worker推論]要検証 |

> 入金確定・入金消込（PoC2寄り）は MoneyForward/銀行通帳未接続で本PoC1範囲外かつ前提待ち（G-11: 入金=通帳が正・MF突合）。

---

## 7. owner裁定 / worker推論 / 未確認 の分離（混同防止）

- **owner裁定（確定・根拠付）**: PoC1スコープ(G-07/D-008)、7状態機械(G-05/D-022)、human gate マスト3点(G-06/D-023)、受任=複数シグナル合成(G-11)、declared/observed分離(G-04/D-004)、流入経路必須・失注enum(G-12/D-030)、WorkItem必須4項目(G-08/D-011)、AI推定の確定境界=人間承認で確定・推定のまま(G-19/D-031)、3層分離(G-16)、相談票=専用様式なし→Calendar/Docs/Notta合成(G-14/D-026)。
- **worker推論（本書提案・owner未裁定）**: 受任合議の重み/閾値(§3.2)、相談vs非相談の複合判別ルール(§4.3)、命名fuzzy閾値、受入基準5「受任確定は人間承認」の固定。→ いずれも owner承認で確定化すべき候補。
- **未確認 / BLOCKED**: SF/LEALA 全項目（W-110: cases 0行・縮約スキーマ・変換関係列無）、Notta/MoneyForward/銀行通帳/Dialpad（未接続）、trace2 の失注/相談完了区分、相談件数の全期間母集団（W-190 はサンプル25件）。

*生成: v0.2 PoC1計測設計（W-20260624-200）。本番 SF/Box 非アクセス・書込なし・git操作なし。PII不記載。owner裁定/worker推論/未確認を分離。測定不能は未接続/BLOCKEDを明示。捏造なし。*
