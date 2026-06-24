---
title: SF全権統合 詳細設計 — 状態機械 / 当事者名寄せ / ギャップ定義
version: 0.3
created_at: 2026-06-24
owner: claude-code-worker
basis: ALO_WORKFLOW_CATALOG_v0.2.yaml / 06_state_transitions.csv / 決定ログ D-013..D-033 / SF実フィールド(W-270取込)
premise: Box=文書正本 / Salesforce=制御塔・背骨ID / 自然発生データ優先 / Raw-Canonical-Derived / AI推定は人手承認まで非確定(G-19)
status_legend: confirmed=owner裁定確定 / provisional=未確定(SF実査・追加裁定要)
---

# SF全権統合 詳細設計 v0.3

中心思想: **SF案件ID(sf_record_id)を背骨に全ソースの出来事をぶら下げ、各ライフサイクル段階で declared(SF) vs observed(実物) のズレを常時検知する。** ズレ=入力漏れ/未対応/リスク。

## 1. 状態機械（owner確定 7本）
各状態は declared(SF項目) と observed(実物ソース) の2系統を持つ。

| 機械 | 主要遷移(確定) | declared(SF) | observed | 人手ゲート |
|---|---|---|---|---|
| Consultation | inquiry→identity_checked→conflict_pass→scheduled→consulted→proposal_sent→converted / closed_lost | StageName__c, ConsultationReceptionDate__c, ConsultedDate__c, Probability__c, ReasonForFailure__c | Gmail問合せ/Calendar/Notta/Dialpad初回/委任契約 | HG-01利益相反(必須)/HG-02受任(任意) |
| Matter | onboarding→active→(waiting_client/opponent/court)→resolution_pending→closing→closed | Status__c(着手前/交渉中/裁判中/申立等準備/調停等/事後処理/クローズ), MandatoryDate__c, CloseDate__c | 委任契約書(Box)/裁判所文書/終了報告 | 2段クローズ(G-09/D-024) |
| Document | received→working_draft→approved→sent→filed/accepted / superseded | UploadFolderUrlBox__c 他 | Box正本/Gmail送受 | HG-04対外最終送付(必須) |
| Finance | quote_sent→invoice_sent→acknowledged→paid→reconciled | 着手金/実費/報酬/預り金 各*__c+*Paid__c | MoneyForward請求/通帳(入金の正)/MF電子契約 | HG-05/06金銭確定(必須) |
| Delivery | prepared→dispatched→delivered/received | (送付状態列=要新設 provisional) | Gmail送信/郵便追跡/Box送付書 | HG-04連動 |
| Deadline | registered→met/extended / missed | 正本=SF Deadline(G-20), IsDeadlineActive__c, Deadline__c, ALO_Next_Deadline_At__c | 裁判所期日/期日呼出(Box/Gmail) | 人手承認(登録/延長) |
| WorkItem | open→in_progress/waiting→complete | ALO_Waiting_On__c + SF Task/Chatworkタスク(G-08) | Chatwork/Box作業痕跡 | completion_evidence必須 |

禁止遷移(事故防止・owner確定):
- conflict未passで受任前進禁止(HG-01)
- 承認なしで converted / 請求確定 / 対外sent 禁止
- close gate未通過・原本未返却・預り金残>0 で closed 禁止(2段クローズ G-09/D-024)
- Deadline: 無確認の経過=懈怠 禁止(人・SF・AI多重チェック D-033)
- Raw削除禁止(append-only, old=superseded G-17)

SF Business `Status__c` → Matter状態 マッピング:
- 着手前→onboarding / 交渉中・裁判中・申立等準備・調停等→active(係属) / 事後処理→resolution_pending〜closing / クローズ→closed

## 2. 当事者名寄せ（Identity Fabric）
依頼者≠支払者(G-10/D-013)を分けて持つ。

当事者タイプ(actors確定): client/payer/prospect/opponent/court/insurer/public_body/vendor/staff(lawyer|clerk)

ソース別キー:
- SF: Account/Contact Id, AccountName/Kana, ChargeLawyer/Clerk/Team(所員), SourcePartner(紹介者) … 依頼者・担当の正
- Gmail: メールアドレス/表示名/ドメイン … 相手方・依頼者の通信実体
- Chatwork: account_id(既存 dynamic.parties 9) … 内部・一部依頼者
- Box: 案件フォルダ名 `頭文字_依頼者_事件名`, `case_summaries/…__SFID.md` … 依頼者↔SF_ID直結

名寄せ規則(信頼度・段階):
1. 所員: @asai-lo.com + SF User↔メール↔Chatwork(閉集合=確実)
2. 依頼者: SF Accountを正、案件往復メール宛先を紐付け
3. 相手方: 案件メールの相手側アドレス/氏名(observed主導→人手確定)
4. payer≠client: 保険会社払い等は別エンティティ(G-10)
5. 曖昧(同名・複数案件「かね正」問題)は SF_ID/フォルダ単位で分離→不能は unconfirmed_links(G-19)

実装テーブル(提案):
- party_identity(canonical: party_id, type, display_name, ...)
- party_alias(party_id, source, source_key, kind=email|sf_account|sf_user|chatwork|box_token, confidence)
- case_party_role(sf_record_id, party_id, role, confidence, basis)

## 3. ギャップ定義（declared vs observed・各段階）
各ルール=SQLビュー＋夜間再計算で要対応リスト化(流入経路アラートの横展開)。重大度 🔴事故/🟠会計/🟡品質/⚪️データ。

| ID | declared(SF) | observed | ギャップ条件 | 重大度 | アクション |
|---|---|---|---|---|---|
| GAP-DEADLINE | active(係属) | SF Deadline | 係属中なのに期限有効=なし | 🔴 | 期限登録督促(懈怠防止) |
| GAP-DDL-MISS | Deadline registered | 期日経過・未met | 期限超過で未対応 | 🔴 | 懈怠アラート |
| GAP-ENGAGE | Matter=受任 | 委任契約書(Box)+受任通知(Gmail) | 受任なのに証跡なし | 🟠 | 証跡/送付漏れ点検 |
| GAP-ENGAGE-LAG | SF未受任/受任日null | 委任契約締結(MF/Gmail) | 実物締結済だがSF未反映 | 🟡 | SF入力遅延是正 |
| GAP-TRUST-CLOSE | クローズ/closing | 預り金残高>0 | 預り金残ったまま終結 | 🟠 | 精算(2段クローズ②ブロック) |
| GAP-CLOSE-EVID | クローズ | 原本返却/終了報告(Box/Gmail) | 終結だが事務クローズ証跡欠落 | 🟡 | 終了報告/原本返却確認 |
| GAP-PAYMENT | invoice_sent | 入金(通帳/MF) | 請求後N日入金なし | 🟠 | 未収督促 |
| GAP-CONSULT-REC | 初回相談日 set | Calendar/Notta/Dialpad | 相談実施記録なし | ⚪️ | 記録補完 |
| GAP-SOURCE | open案件 | — | 流入経路未入力 | ⚪️ | 実装済(44件) |
| GAP-APPEND-ONLY | — | Box削除通知 | 正本が削除された | 🟠 | 復元/監査(削除通知を実検知) |

最重要: 🔴GAP-DEADLINE/DDL-MISS = 弁護過誤リスクの自動検知。owner裁定「徒過防止=人・SF・AIの多重チェック(D-033)」のAI担当部分。

## 4. 実装方針
- 各GAP = cases(+取込後の documents/comms/finance) 上のSQLビュー → 夜間バッチ → 要対応リスト(流入経路アラートで実証済パターン)。
- 人手必須3ゲート(利益相反HG-01/対外送付HG-04/金銭確定HG-05/06)と曖昧紐付けは unconfirmed_links。AI推定は人手承認まで非確定(G-19)。
- 取込順(レバレッジ順): A.SF背骨[済] → B.Box文書(SF_IDリンク) → C.Gmail通信 → D.ギャップエンジン → E.Calendar/Dialpad/MoneyForward → F.ガバナンス(RLS/開示ログ)。
