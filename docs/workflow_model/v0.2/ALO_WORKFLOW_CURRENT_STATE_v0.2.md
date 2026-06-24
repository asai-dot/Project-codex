# ALO 業務フロー現状インベントリ（CURRENT_STATE）v0.2 — Phase0 骨子

- 作業票: `W-20260624-101`（Phase0 / v0.1構造インベントリ）
- 発注原本: `docs/workflow_model/REQUEST_v0.2.md`
- 入力原本（読むだけ・上書き禁止）: `docs/workflow_model/v0.1/` の4ファイル
  - `浅井法律事務所_業務フロー機械可読化_設計・ヒアリングパック_v0.1.docx`（本文431段落）
  - `浅井法律事務所_業務フロー実査台帳_v0.1.xlsx`（11シート）
  - `alo_workflow_event_schema_v0.1.json`（イベント封筒スキーマ）
  - `alo_workflow_event_example_anonymized_v0.1.json`（匿名化サンプル1件）
- 抽出方法: python3 標準ライブラリ（zipfile + re）のみ。外部依存なし。件数はすべて**実抽出値**（推測なし）。
- 前提方針（REQUEST_v0.2 §1）: Box=文書正本 / Salesforce=制御塔 / 自然発生データ優先 / Raw・Curated・Derived 分離。

> 本書はv0.1原本の**構造インベントリ（棚卸し）**であり、現場実査による検証は未実施。原本では23フローのうち22本が `要確認`、245問すべてが `未回答`、決定14件すべてが `未決` の状態である。どれが仮説でどれが原本記載の確定事実かは末尾「## 仮説 / 確認済事実 / 未決 の分離」で区別する。

---

## 0. 件数サマリ（実抽出値）

| 区分 | 件数 | 出所シート/ファイル |
|---|---|---|
| フロー仮説 | 23本（WF-00〜WF-22） | 01_フロー仮説 |
| ヒアリング質問 | 245問（Q-001〜Q-245） | 02_ヒアリング質問 |
| データソース | 22件（DS-001〜DS-022） | 03_データ取得台帳 |
| 文書種別 | 35件（DOC-001〜DOC-035） | 04_文書種別台帳 |
| イベント候補 | 72件（EV-001〜EV-072） | 05_イベント分類 |
| 状態定義 | 53状態 / 状態機械5本 | 06_状態遷移 |
| SFフィールド対応 | 44行 | 07_SFフィールド対応 |
| 実査証跡サンプル | 9件（EVD-001〜EVD-009） | 08_証跡サンプル |
| 決定/仮説ログ | 14件（D-001〜D-014） | 09_決定事項ログ |
| 用語・選択肢 | 15定義 | 99_用語・選択肢 |

注: 00_概要シートのKPI欄は「要確認フロー: 20」と記載するが、01_フロー仮説の実データでは `要確認` 22本 + `設計済・要検証` 1本（WF-14）= 23本である（KPI欄の集計差異。詳細は §1）。

---

## 1. 23本のフロー仮説（WF-00〜WF-22）

フェーズ A〜E は docx 本文（「相談から終結までの標準フェーズ」表）の大区分。フェーズ列は `大区分/工程名` で表記（工程名は xlsx の各行フェーズ）。

- A. 流入・受入: WF-00〜WF-04
- B. 相談: WF-05〜WF-08
- C. 提案・受任: WF-09〜WF-12
- D. 遂行・納品: WF-13〜WF-18
- E. 解決・終結: WF-19〜WF-22

| Process ID | 順序 | フェーズ | 開始トリガー | 主担当 | 判断ゲート | 次状態 | 自動化候補 | 確認状態 |
|---|---|---|---|---|---|---|---|---|
| WF-00 | 0 | A/認知・紹介 | 紹介・HP・セミナー・既存顧客から接点発生 | 弁護士/事務局 | 営業/相談/既存案件連絡の判定 | WF-01 | 自然発生データから流入経路候補 | 要確認 |
| WF-01 | 1 | A/問合せ受付 | 新規連絡を受信 | 事務局 | 相談レコードを作るか | WF-02 | 問い合わせ分類・重複検知 | 要確認 |
| WF-02 | 2 | A/安全連絡・本人関係確認 | 相談候補作成 | 事務局 | 連絡可否・本人確認水準 | WF-03 | 署名・電話番号・既存Account照合 | 要確認 |
| WF-03 | 3 | A/コンフリクト確認 | 当事者・関係者名取得 | 弁護士＋事務局 | pass/fail/escalate | WF-04 | 名称候補生成・既存関係グラフ検索 | 要確認 |
| WF-04 | 4 | A/受入可否・緊急度トリアージ | コンフリクトpass又は緊急例外 | 弁護士 | consult/refer/decline | WF-05 | 期限・分野・不適合候補抽出 | 要確認 |
| WF-05 | 5 | B/相談日程調整 | 相談実施GO | 弁護士/事務局 | 日時/方式/費用合意 | WF-06 | 日程候補生成・確定検知 | 要確認 |
| WF-06 | 6 | B/事前資料依頼・受領 | 相談日時確定 | 事務局＋担当弁護士 | 相談前必須資料が揃ったか | WF-07 | 添付保存・文書種別・不足リマインド | 要確認 |
| WF-07 | 7 | B/相談実施 | 予約時刻到来 | 担当弁護士 | 相談完了/継続/打切り | WF-08 | 参加者・要点・アクション抽出 | 要確認 |
| WF-08 | 8 | B/相談後評価 | 相談完了 | 担当弁護士 | 受任提案/追加相談/非受任 | WF-09 | 論点・不足・次行動候補 | 要確認 |
| WF-09 | 9 | C/見積・提案作成 | 受任提案GO又は顧客から見積依頼 | 担当弁護士＋事務局 | 内部承認 | WF-10 | テンプレート差込・版管理 | 要確認 |
| WF-10 | 10 | C/提案・契約案送付 | 内部承認完了 | 事務局 | 送付先・送付版・期限 | WF-11 | 送付検知・フォロー期限生成 | 要確認 |
| WF-11 | 11 | C/条件調整・契約締結 | 顧客回答 | 担当弁護士＋事務局 | 成立/失注/保留 | WF-12 | 受諾/署名検知・差分比較 | 要確認 |
| WF-12 | 12 | C/案件開設・初期請求 | 受任成立条件充足 | 事務局 | 業務開始可否 | WF-13 | フォルダ/メタデータ/請求自動生成 | 要確認 |
| WF-13 | 13 | D/初期計画・役割分担 | 案件開設 | 担当弁護士＋事務局 | 計画承認 | WF-14 | 議事録から計画候補 | 要確認 |
| WF-14 | 14 | D/継続情報取込 | メール/電話/郵便/会議/資料発生 | 全員 | 紐付け/除外/要確認 | WF-15 | ALO Connect/HITL | 設計済・要検証 |
| WF-15 | 15 | D/調査・起案・作業 | 計画又はイベントから作業発生 | 弁護士/事務局 | 作業完了/レビューへ | WF-16 | 作業セッション自動束ね | 要確認 |
| WF-16 | 16 | D/内部レビュー・承認 | ドラフト完成 | 別弁護士/責任者 | approve/rework/hold | WF-17 | 差分・チェック候補 | 要確認 |
| WF-17 | 17 | D/納品・送付・提出 | 外部送付承認 | 弁護士/事務局 | 送付/提出成功 | WF-18 | 送付証跡の自動取得 | 要確認 |
| WF-18 | 18 | D/応答・進捗・反復 | 外部応答又は期限到来 | 担当者 | 次反復/解決へ | WF-14/WF-19 | observed_state候補生成 | 要確認 |
| WF-19 | 19 | E/解決・成果確定 | 和解/判決/履行/助言完了等 | 担当弁護士 | closing開始可否 | WF-20 | 成果類型・残タスク抽出 | 要確認 |
| WF-20 | 20 | E/最終請求・預り金/実費精算 | closing GO | 弁護士＋事務局長 | financially_reconciled | WF-21 | 計算候補・照合・未収監視 | 要確認 |
| WF-21 | 21 | E/原本返却・終了報告 | 財務と残作業確認 | 弁護士＋事務局 | client_acknowledged | WF-22 | 返却物一覧・送付パック生成 | 要確認 |
| WF-22 | 22 | E/終結・保存・知識化 | 全closing gate通過 | 担当弁護士＋事務局 | close/archive/promote | — | close gate/再利用候補 | 要確認 |

確認状態内訳: `要確認` 22本 / `設計済・要検証` 1本（WF-14）。`回答済`/`確定` は0本。

---

## 2. 245問のヒアリング質問（モジュール別・優先度・回答状態）

総数 245問（Q-001〜Q-245）。

### モジュール別件数（全13モジュール）

| モジュール | 件数 |
|---|---|
| 00_設計原則・統治 | 16 |
| 01_流入・問合せ受付 | 20 |
| 02_本人関係・コンフリ・トリアージ | 17 |
| 03_日程調整・事前準備 | 16 |
| 04_相談実施・相談後評価 | 18 |
| 05_見積・提案・受任契約 | 21 |
| 06_料金・請求・入出金 | 26 |
| 07_案件計画・日常処理 | 21 |
| 08_文書・成果物・納品 | 22 |
| 09_連絡・チャネル統合 | 15 |
| 10_裁判所・期限・提出 | 12 |
| 11_成果・終結・知識化 | 23 |
| 12_例外・品質・セキュリティ | 18 |
| **合計** | **245** |

### 優先度別

| 優先度 | 件数 |
|---|---|
| P0（正本・重大ゲート・法務/金銭/期限リスク） | 58 |
| P1（PoC成立に必要） | 90 |
| P2（最適化・将来拡張） | 97 |
| **合計** | **245** |

### 回答状態別

| 回答状態 | 件数 |
|---|---|
| 未回答 | 245 |
| 調査中 / 回答済 / 保留 / 対象外 | 0 |

→ 全質問が `未回答`。実査・浅井聴取はこの時点で未着手。

---

## 3. 22のデータソース（DS-001〜DS-022）

### システム別件数

| システム | 件数 |
|---|---|
| Salesforce | 8 |
| Box | 2 |
| Money Forward | 2 |
| Gmail | 1 |
| Dialpad | 1 |
| Notta | 1 |
| Google Calendar / Meet | 1 |
| MINTS/Teams/FAX/郵便 | 1 |
| NAS/複合機/ScanSnap | 1 |
| Chatwork/Slack | 1 |
| Google Docs/Sheets | 1 |
| HP/フォーム/アクセス解析 | 1 |
| Box Events/Admin logs | 1 |
| **合計** | **22** |

### 一覧

| Source ID | システム | 対象オブジェクト/場所 |
|---|---|---|
| DS-001 | Salesforce | leala__Consultation__c（相談） |
| DS-002 | Salesforce | leala__Matter__c / leala__Business__c（受任案件） |
| DS-003 | Salesforce | Task / Event / Chatter / Office Meeting |
| DS-004 | Salesforce | ALO_DerivedEvent__c |
| DS-005 | Salesforce | RelatedContact / OpponentParty / Account / Contact |
| DS-006 | Salesforce | Deadline / JurisdictionCourt / Procedure |
| DS-007 | Salesforce | Accounting / Billing / Invoice / Expense / TimeCharge / Deposit |
| DS-008 | Salesforce | PostalMatter / RequiredDocument / KeepingItem / CaseDocument |
| DS-009 | Box | ★LEALA 配下の相談・受任・既済フォルダ |
| DS-010 | Box | マニュアル・書式・ひな形・終了報告 |
| DS-011 | Gmail | 全所員メール（外部/内部） |
| DS-012 | Dialpad | 通話・SMS・録音・transcript |
| DS-013 | Notta | 会議/通話再文字起こし |
| DS-014 | Google Calendar / Meet | 全所員カレンダー |
| DS-015 | Money Forward | MF請求書 |
| DS-016 | Money Forward | MF会計/銀行明細 |
| DS-017 | MINTS/Teams/FAX/郵便 | 裁判所・対外提出証跡 |
| DS-018 | NAS/複合機/ScanSnap | スキャン投入ログ |
| DS-019 | Chatwork/Slack | 例外的外部・所内連絡 |
| DS-020 | Google Docs/Sheets | 困りごとログ・AI日報・週次全件おろし |
| DS-021 | HP/フォーム/アクセス解析 | 問い合わせ前後の流入 |
| DS-022 | Box Events/Admin logs | ファイル操作監査 |

---

## 4. 35の文書種別（DOC-001〜DOC-035）

総数 35件。各行に方向・工程・役割/層が付与されている。

### 方向（inbound/outbound/internal）別

| 方向 | 件数 |
|---|---|
| internal | 10 |
| outbound | 10 |
| inbound | 6 |
| outbound/internal | 4 |
| inbound/final | 2 |
| inbound/internal | 1 |
| outbound/final | 1 |
| final | 1 |
| **合計** | **35** |

### 工程別

| 工程 | 件数 |
|---|---|
| 相談前 | 6 |
| 遂行 | 6 |
| 終結 | 5 |
| 受任 | 3 |
| レビュー | 3 |
| 解決 | 3 |
| 相談 | 2 |
| 受任前 | 2 |
| 相談後 / 相談前〜受任後 / 全期間 / 受任後 / 終結後 | 各1（計5） |
| **合計** | **35** |

### 役割/層別（主な層）

役割/層は計28種の細分値（raw=3, decision record=2, work product=2, curated=2, package manifest=2, outcome document=2 ほか、各1の値が多数）。代表値: raw（3）、record/communication/form/checklist/proposal/contract/invoice/draft/approval/final deliverable/filed deliverable/acknowledgement/reconciliation/closing report 等。35件合計。

---

## 5. 72のイベント候補（EV-001〜EV-072）

総数 72件。封筒は `event_id, occurred_at, captured_at, actor, matter_ref, source_native_id, confidence, review_status` ほか（§9スキーマ参照）。訂正原則は全件 append-only（無効化＋新イベント）。

### 分類別件数

| 分類 | 件数 | 分類 | 件数 |
|---|---|---|---|
| 財務 | 9 | 流入 | 2 |
| 提案 | 8 | 本人関係 | 2 |
| 終結 | 6 | コンフリ | 2 |
| 作業 | 5 | 相談後 | 2 |
| 日程 | 4 | 納品 | 2 |
| 連絡 | 4 | 品質 | 2 |
| レビュー | 4 | トリアージ | 1 |
| 資料 | 3 | 計画 | 1 |
| 相談 | 3 | 文書 | 1 |
| 受任 | 3 | 提出 | 1 |
| 期限 | 3 | 契約変更 | 1 |
| | | 解決 | 1 |
| | | 知識化 | 1 |
| | | 運用 | 1 |

合計 72（24分類）。

---

## 6. 53の状態定義（状態機械別）

総数 53状態。**v0.1の06_状態遷移シートには5本の状態機械のみが定義されている。**

| 状態機械 | 状態数 | 状態コード |
|---|---|---|
| Consultation | 17 | new, inquiry, identity_checked, conflict_pending, conflict_pass, conflict_fail, triaged, scheduling, scheduled, consulted, followup, proposal_pending, proposal_sent, decision_pending, engagement_pending, converted, closed_lost |
| Matter | 11 | onboarding, active, waiting_client, waiting_opponent, waiting_court, drafting, review, filing, resolution_pending, closing, closed |
| WorkItem | 6 | open, in_progress, waiting, blocked, review, complete |
| Document | 10 | received, classified, working_draft, internal_review, client_review, approved, sent, filed, accepted, superseded |
| Finance | 9 | quote_draft, quote_sent, invoice_draft, invoice_sent, acknowledged, part_paid, paid, overdue, reconciled |
| **合計** | **53** | |

> 重要な差異（要確認）: 作業票・REQUEST文中およびv0.1の決定ログ（D-005, D-012）では「Delivery」「Deadline」を含む7状態機械が前提として言及されているが、**06_状態遷移シートには Delivery / Deadline の状態機械が独立して定義されていない**（実定義は上記5本のみ）。Delivery は Document機械（sent/filed/accepted）と Finance に分散、Deadline は Matter機械（waiting_court 等）に内包されている。Delivery/Deadline を独立状態機械化するかは未決（§8 / D-012参照）。

---

## 7. Salesforceフィールド対応（現行→目標概念）

07_SFフィールド対応シートに44行のマッピング。現行 `leala__Consultation__c` 等のフィールドを、event / work item / decision / finance / provenance の目標概念へ接続する。重点は「自由記述欄の過積載」と「日付のみの粒度不足」の解消。

### 重要度内訳

| 重要度 | 件数 |
|---|---|
| 最高 | 13 |
| 高 | 19 |
| 中 | 11 |
| 低〜中 | 1 |
| **合計** | **44** |

### 評価（現行充足度）内訳

| 評価 | 件数 |
|---|---|
| 既存（そのまま流用可） | 25 |
| 新設系（新設 / 新設/関連 / 新設/既存組合せ 等） | 9 |
| 要分解 | 3 |
| 不足 | 2 |
| 既存だが粗い/混在/主観/要台帳 | 各1（計4） |
| 要定義 | 1 |
| **合計** | **44** |

要点: 主キー（Consultation.Id / Matter.Id）は「そのまま」流用が基本（D-001）。Stage/Source/Category 等は既存だが、event・task・provenance への接続と分解が中心課題。`source native refs → provenance_refs` 等は新設候補。

---

## 8. 設計仮説・未決事項（09_決定事項ログ D-001〜D-014）

総数 14件。**全件 `未決`**。区分内訳: 仮説 7件 / 提案 6件 / 既存原則 1件。決定者・決定日は全件空欄。

| Decision ID | 内容（要旨） | 区分 | 状態 |
|---|---|---|---|
| D-001 | SF Consultation/Matter ID を業務レコードの脊椎とする | 仮説 | 未決 |
| D-002 | Box file_id/version_id を文書同一性の正本とする | 仮説 | 未決 |
| D-003 | Gmail/Dialpad/Notta/Calendar/郵便等を append-only 観測イベントで保持 | 仮説 | 未決 |
| D-004 | declared_state と observed_state を分離 | 仮説 | 未決 |
| D-005 | 案件/作業/文書/財務/期限の状態機械を分離 | 仮説 | 未決 |
| D-006 | 新規手入力は取得不能な判断・承認に限定 | 既存原則 | 未決 |
| D-007 | コンフリ/受任成立/最終送付/終結/請求精算は人間必須承認 | 仮説 | 未決 |
| D-008 | 第1 PoC は相談→受任ファネル | 提案 | 未決 |
| D-009 | 第2 PoC は解決→最終請求→返却→終了報告→既済化 | 提案 | 未決 |
| D-010 | 訂正は raw 削除でなく無効化イベント＋新確定リンク | 仮説 | 未決 |
| D-011 | WorkItem に owner/due/status/waiting_on/completion_evidence 必須化 | 提案 | 未決 |
| D-012 | 成果物送付は Document状態と Delivery event を分離 | 提案 | 未決 |
| D-013 | finance で client_party と payer_party を分離 | 提案 | 未決 |
| D-014 | close gate は未完Task/期限/最終請求/預り金実費/原本返却/終了報告を確認 | 提案 | 未決 |

各決定には「未解決論点」が併記されている（例: D-002=共有リンクでなくID取得可否、D-010=個人情報削除要求時の例外）。

### 参考: イベント封筒スキーマ（alo_workflow_event_schema_v0.1.json）

- title: `ALO Workflow Event Envelope`、プロパティ25個。
- 必須8項目: `schema_version, event_id, event_type, occurred_at, captured_at, source, matter_ref, provenance`。
- 主要プロパティ: event_category, effective_at, consultation_ref, actor, counterparties, summary, state_transition, work_item, document_refs, decision, finance, deadlines, extracted_facts, confidence, review, invalidates_event_ids, extensions。
- 匿名化サンプル（example）1件が同25キー構成で添付。

### 参考: 実査証跡サンプル（08_証跡サンプル EVD-001〜EVD-009、全9件 `確認済`）

Box/Gmail/プロジェクト資料から抽出した9件の業務パターン（個人名・事件内容・金額は不掲載）。例: EVD-003=法テラス相談票が相談スキーマの強い既存資源、EVD-005=相談→提案→契約調整が1メールスレッドに連続、EVD-006=client と payer の分離実態、EVD-007=終結が財務/原本/残作業/送付パックの複合gate。

---

## 仮説 / 確認済事実 / 未決 の分離

本書の各記述を、原本v0.1での区分に従って明示的に分離する（混同防止）。

### A. 確認済事実（v0.1原本に確定記載 — 棚卸しとして転記した実数・構造）

これらは「v0.1原本にこう書かれている」という事実であり、Phase0で抽出・検算した実数。**業務の現場実態として確定したという意味ではない。**

- フロー仮説は23本（WF-00〜WF-22）、A〜E の5フェーズに区分されている。
- ヒアリング質問は245問、13モジュール、P0=58/P1=90/P2=97。
- データソースは22件（うち Salesforce 8件）。
- 文書種別は35件。
- イベント候補は72件、24分類。
- 状態定義は53状態で、**06シートには5状態機械のみ**（Consultation/Matter/WorkItem/Document/Finance）が定義されている。
- SFフィールド対応は44行（既存25/新設系9 ほか）。
- 決定/仮説ログは14件。
- 実査証跡サンプル9件は原本で `確認済`（個人情報なし／空様式／構造のみ等の匿名化前提）。
- イベント封筒スキーマの必須8項目とプロパティ25個。

### B. 仮説（v0.1が「仮説」「提案」と明示している、未検証の設計案）

- 23フローの構造・トリガー・担当・ゲート・次状態（22本が `要確認`、回答済0本）。WF-14のみ `設計済・要検証`。
- 各WFの「自動化候補」列（自動化の方向性の仮説）。
- 状態機械の分離方針および各状態コード（D-005=仮説）。
- 決定ログ D-001〜D-014（仮説7/提案6/既存原則1）。すべて決定者・決定日が空欄。
- Delivery/Deadline を独立状態機械にするか（D-012 は提案、06シート未定義）。

### C. 未決 / 未確認（Phase0時点で埋められない — 推測で補完しない）

- 245問すべて `未回答`（実査・浅井聴取は未着手）。回答状態の `調査中/回答済/保留/対象外` は0件。
- 決定14件すべて `状態=未決`、決定者・決定日 空欄。
- **状態機械の本数不整合**: D-005/作業票は「案件/作業/文書/財務/期限」または7機械（Delivery/Deadline含む）を前提に言及するが、06シート実定義は5機械のみ。Delivery/Deadline の独立化要否は未確認 → 浅井/外部SE聴取要。
- **KPI集計差異**: 00_概要の「要確認フロー=20」と 01シート実データ「要確認22＋設計済・要検証1」が不一致（原本内の集計差異） → 要確認。
- 各データソースの実取得可否・権限・更新頻度の実証（DS台帳の「現状」列は計画値であり実査未済）。
- 文書種別の役割/層28種の細分値の確定（curated/derived境界など）。

### 次工程へ積むキュー（推測で埋めず確認要）

1. P0質問58問の実査・浅井聴取（特に 06_料金・請求 26問、11_成果・終結 23問が密度高）。
2. 状態機械の本数確定（5本か7本か / Delivery・Deadline の扱い）。
3. 00_概要 KPI と各シート実データの集計差異の解消。
4. データソース22件の実取得可否・権限・provenance ID貫通の実証（PoC1=相談→受任 / PoC2=解決→終結 が候補）。

---

*生成: Phase0 構造インベントリ。v0.1原本は読むだけ・無改変。新規の個人情報は一切追加していない（v0.1は匿名化済み）。*
