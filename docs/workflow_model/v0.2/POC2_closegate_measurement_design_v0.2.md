---
worker_task_id: W-20260624-250
title: PoC2（解決〜終結）close gate 計測設計 v0.2
created_at: 2026-06-24
owner: claude-code-worker
source_request: docs/workflow_model/REQUEST_v0.2.md (§6)
poc: PoC2
premise: Box=文書正本 / Salesforce=業務制御塔 / 自然発生データ優先 / Raw・Canonical・Derived分離
inputs:
  - ALO_WORKFLOW_GAP_AND_POC_PLAN_v0.2.md     # W-160 PoC2範囲・close gate10項目素案・各確認データ源
  - ALO_OWNER_GRILL_ANSWERS_v0.1.md            # owner確定 G-09/G-11/G-10/G-15/G-06 ほか
  - ALO_WORKFLOW_CATALOG_v0.2.yaml             # states7本/human_gates(HG-05/06)/metrics(PoC2 KPI)/close_gate_conditions
  - PHASE2_box_document_lifecycle_v0.2.md      # W-111 預り資料/成果物送付/既済/原本
  - PHASE2_salesforce_survey_v0.2.md           # W-110 SFミラー実査(cases/documents 0行・会計系BLOCKED・MF未接続)
  - ALO_WORKFLOW_EVIDENCE_LEDGER_v0.2.jsonl    # Gmail trace3=解決→第三者請求→入金→精算(途中)
  - POC1_measurement_design_v0.2.md            # W-200 様式の参考
pii_policy: 氏名・住所・電話・事件内容・具体的金額は記載しない（型・構造・集計・プレースホルダのみ／規約ルール11）
status_note: |
  接続済 = Box / Gmail / Google Calendar / Google Docs(Drive)。
  未接続 = MoneyForward / 銀行通帳 / Notta / Dialpad（自然発生源が取れない）。
  BLOCKED(SF) = Salesforce/LEALA。W-110 実査で dynamic.cases / dynamic.documents が 0行＝制御塔データ不在。
    会計系(Accounting/Billing/Invoice/Expense/Deposit)・Task/Deadline は専用テーブルすら未到達。ETL起動＋スキーマ拡張が前提。
  本書は「接続済だけで取れる close gate 判定」と「前提待ち(未接続/BLOCKED)」を分離する。捏造禁止。
  owner裁定(G-xx/D-xx)と worker推論を各設計で明示分離。AI推定は Derived・人間未承認に留める（G-19/D-031）。
---

# PoC2（解決〜終結） close gate 計測設計 v0.2

PoC2 スコープ（owner裁定 G-07/G-09/D-009/D-024）= **解決(WF-19) → 最終請求・預り金/実費精算(WF-20) → 原本返却・終了報告(WF-21) → 既済化(WF-22)**。owner裁定 G-09 で **2段クローズ**（①法的終了／②事務クローズ完了=原本返却済・預り金ゼロ・報酬確定）を終端に置くことが確定済。本書は close gate 10条件（catalog `human_gates.close_gate_conditions` / W-160 §3.2）を各「判定データ源・判定方法・測定可否・該当human gate・確信度」付きの計測設計へ落とし、2段クローズの状態表現・金銭確定設計・終了報告判定・PoC2 KPI・着手段取りを定義する。

## 凡例（根拠と確信の分離）

- 根拠タグ: `G-xx`=owner裁定(ALO_OWNER_GRILL_ANSWERS_v0.1)、`D-xx`=決定ログ、`W-xxx`=worker成果物、`Box実査(n)`=PHASE2_box_document_lifecycle §2(n)、`Ledger`=Gmail証跡台帳。`[worker推論]`=本書の設計提案で owner未裁定のもの。
- 測定可否タグ:
  - **接続済**: Box / Gmail / Calendar / Docs(Drive) で今すぐ取得可能。
  - **未接続**: MoneyForward / 銀行通帳 / Notta / Dialpad コネクタ不在（自然発生源が取れない＝未測定）。
  - **BLOCKED(SF)**: Salesforce/LEALA。W-110 実査で `dynamic.cases`/`dynamic.documents` 0行、会計・期限・タスク系は専用テーブル未到達。ETL起動＋スキーマ拡張が前提。
- provenance basis: `observed`（自然発生データ観測・confidence付） / `declared`（人間が宣言した状態の正本＝主にSF） / `human_decision`（人間承認） / `ai_estimated`（Derived・人間未承認、確定にしない G-19/D-031）。
- 確信度（本表内）: **高**=接続済で確定的に判定可 / **中**=接続済だが間接シグナル(動作語・フォルダ移動)依存 / **低**=前提待ち（接続/ETL後に初めて判定可）。

---

## 1. close gate 10項目 マッピング表（やること1）

各項目を [判定データ源 / 判定方法 / 測定可否 / 該当human gate / 確信度] で列挙。10項目は catalog `human_gates.close_gate_conditions.conditions`（owner裁定 G-09/D-014/D-024/D-027 で confirmed）に一致。

| # | close gate 項目 | 判定データ源（理想） | 判定方法 | 測定可否 | 該当human gate | 確信度 |
|---|---|---|---|---|---|---|
| 1 | 未完WorkItem無 | SF(Task/次行動) + event台帳の WorkItem.status 集計 + Chatworkタスク(DS-023, G-08) | matter_ref配下の全WorkItemで status∈{open,in_progress,waiting,blocked,review} が0件を判定（SM-work_item の complete/cancelled 以外が残らない）。WI必須4項目=担当/期限/案件/次アクション(G-08/D-011) | **BLOCKED(SF)** ＝Task専用テーブル未到達。接続済(Gmail)で観測したWIは部分集計のみ。Ledger trace3 は open/waiting/in_progress のWIが残存＝未通過の実例 | — (gate前提条件) | 低 |
| 2 | 残期限無 | SF Deadline(正本, G-20/D-033) + Calendar 突合 | SM-deadline 配下の全Deadlineが met/extended（registered/未到来 が残らない）。期限の正本=SF、徒過防止=人/SF/AI多重チェック(G-20) | **BLOCKED(SF)** ＝Deadline専用テーブル未到達(W-110 §1.3)。Calendarは接続済だが期限正本ではない | — (gate前提条件) | 低 |
| 3 | 最終請求確定 | Box 請求書PDF(発行, Box実査(7)) + SF Billing/Invoice + 請求書発行管理簿(v5) | 最終請求書PDFの発行(確定版)＋台帳記帳を確定とする。発行=Box観測可、確定(請求額の正本)=会計/SF | **△ 接続済(Box)で発行は観測可** / 確定は **BLOCKED(SF)+未接続(MF)** | HG-05 報酬確定(マスト③, G-06) | 中 |
| 4 | 未収扱い確定 | MoneyForward会計(入金消込) + 銀行通帳(正, G-11) + SF | 最終請求に対し入金消込済 or writeoff(未収/貸倒)が確定。入金の正=通帳(DS-024)、MF(DS-016)突合 | **未接続(MF/通帳)＋BLOCKED(SF)** ＝測定不能（未接続=未測定）。会計専用テーブル未到達(W-110) | HG-05/HG-06 金銭の確定(マスト③) | 低 |
| 5 | 預り金・実費精算済 | SF Deposit/Expense + MF + Gmail精算連絡(Ledger trace3) | trust_deposit残高=ゼロ かつ expense差引・refund送金が確定(SM-finance reconciled)。精算判断点はGmailで観測、確定は会計/SF | **△ 接続済(Gmail)で精算判断点は観測**(trace3:0304 立替金差引判断) / 確定は **BLOCKED(SF)+未接続(MF/通帳)** | HG-06 預り金・実費精算/振替(マスト③) | 中 |
| 6 | 預り原本 返却済 or 保管理由 | Box `4 預かり資料`フォルダ + 返却受領書(ひな形v5, Box実査(8)) | 預り資料の受領(預り証)→保管→返却(返却受領書)のライフサイクルをBoxフォルダ＋書式で判定。返却済 or 明示的保管理由のいずれか | **○ 接続済(Box)** ＝受領→保管→返却がフォルダ＋書式で観測可(Box実査(8)＝区別可○) | — (gate前提条件) | 高 |
| 7 | 最終成果物送付済 | Box `1-2 通信（送）` + 送付書 + 追跡番号記録表(v8, Box実査(9)) | 最終成果物が通信(送)フォルダへ配置＋送付書あり＝送付済。到達は追跡番号記録表で間接 | **△ 接続済(Box)で「送った」まで** / 到達(受理)は追跡表で間接(Box実査(9)＝送付○・到達△) | HG-04 対外成果物の最終送付(マスト②, G-06) | 中 |
| 8 | 終了報告送付済 | （専用様式なし G-15/D-027）→ Box成果物送付 or Gmail報酬請求(金額確定)通知 | owner裁定: 専用書類でなく **「成果物送付 or 報酬請求の通知が出ている」で判定**（§4 詳細）。Box `1-2 通信（送）`の成果物送付 or Gmailの請求通知の検出 | **接続済(Box/Gmail)** ＝判定設計が成立。標準ひな形依存を解消(G-15でBox-U2解消) | HG-04(成果物送付経路) | 中 |
| 9 | Box正本確定 | Box file_id+version_id(G-02) + 既済フォルダ配置(Box実査(11)) | 最終成果物・契約書等の正本が Box file_id+version_id で同定済、かつ既済フォルダ配置。docx⇔pdf確定版で確定/配布版判別 | **○ 接続済(Box)** ＝既済配置・version同定は観測可。SF背骨ID(G-01)紐付けは BLOCKED(SF) | — (gate前提条件) | 高(正本同定) / 低(SF紐付け) |
| 10 | SF終了状態が人間承認済 | SF(declared 終了状態 + 承認者) = 人間承認(G-06/G-19) | SM-matter が closed(②事務クローズ完了)へ遷移し、承認者(declared/human_decision)が記録済。AI/observedの自動既済化を禁止 | **BLOCKED(SF)** ＝cases 0行・終了状態/承認者列が縮約スキーマに無(W-110)。declared承認の正本がSF側で空白 | HG-07 終結(optional, G-06/G-09) | 低 |

**マッピング網羅サマリ**: 10項目すべてに判定データ源・判定方法・測定可否・human gate該当・確信度を割当済。測定可否内訳 = **接続済で今すぐ判定着手可=3項目（#6 原本返却 / #9 Box正本確定[正本同定部分] / #8 終了報告[成果物送付/請求通知の検出]）＋ 接続済で部分(送付まで)判定可=2項目（#3 請求発行 / #7 成果物送付）**、**前提待ち（BLOCKED/未接続）=#1,#2,#4,#5(確定),#10、および #3/#9 の確定/SF紐付け部分**。

> 注（worker推論／W-110整合）: W-160 §3.2 は SF を「未観測 BLOCKED」と表現したが、W-110 実査ではSFは Supabaseミラー経由で **スキーマ到達済・データ0行（cases/documents=未確認・同期待ち）**、会計/期限/タスク系は **専用テーブル未到達**であることが判明している。本書では両者を区別し「BLOCKED(SF)＝ETL未実行＋スキーマ拡張前提」として統一表記する。

---

## 2. 2段クローズの状態表現（やること2）

owner裁定 G-09/D-024（catalog `states.two_stage_close` で confirmed）= **①法的終了／②事務クローズ完了** の2段。順序 = 案件終了 → 原本返却 → 預り金ゼロ → クローズ。適用機械 = matter / finance / document（＋deadline）。

### 2.1 機械別の終端状態と担当 gate

| 機械 | 終端に向かう状態(catalog states) | 2段クローズでの役割 | 担当する close gate項目 | 担当human gate |
|---|---|---|---|---|
| **matter** (SM-matter) | resolution_pending → **closing(①法的終了)** → **closed(②事務クローズ完了)** | ①closing=案件が実体的に終了(WF-19)。②closed=②全充足後の終結(WF-22) | #10 SF終了状態が人間承認済 | HG-07 終結(optional) |
| **finance** (SM-finance) | invoice_sent → acknowledged → part_paid/paid/overdue → **reconciled** | ②事務クローズの「預り金ゼロ・報酬確定」を担う。reconciled=金銭の確定 | #3 最終請求確定 / #4 未収扱い確定 / #5 預り金・実費精算済 | HG-05 報酬確定 / HG-06 精算・振替(マスト③) |
| **document** (SM-document) | approved → sent → filed → **accepted** / **superseded** | ②事務クローズの「成果物送付・正本確定」を担う | #7 最終成果物送付済 / #9 Box正本確定 | HG-04 対外成果物の最終送付(マスト②) |
| **delivery** (SM-delivery) | prepared → dispatched → delivered → received | document送付の到達・受理の独立表現(G-05独立化) | #7(到達/受理側) / #8(成果物送付経路) | HG-04 |
| **deadline** (SM-deadline) | registered → **met/extended** (missed=徒過) | ②事務クローズの「残期限無」を担う(G-05/G-20独立化) | #2 残期限無 | — |

document系の「原本返却(#6)」は SM-document/SM-delivery の受領系で表現し、Box `4 預かり資料`のライフサイクル(受領→保管→返却)で観測する（Box実査(8)）。

### 2.2 遷移条件・禁止遷移

- **①法的終了の起点**: WF-19 `outcome_reached`（和解/判決/履行/助言完了等）で matter が closing へ。basis=human_decision（担当弁護士）。Ledger trace3:0303 `resolution_in_settlement` がこの区間の observed 実例。
- **②事務クローズ完了の充足条件（AND）**: `finance.reconciled`（#3+#4+#5: 報酬確定 AND 預り金ゼロ AND 未収扱い確定）**AND** `document原本返却済`(#6) **AND** `document最終成果物送付済`(#7) **AND** `終了報告送付済`(#8) **AND** `Box正本確定`(#9) **AND** `deadline残期限無`(#2) **AND** `未完WorkItem無`(#1)。これら全充足 → matter が closed へ遷移可能。
- **禁止遷移（owner裁定 G-09 順序 / W-160 §3.3）**:
  - 既済化（既済フォルダ移動）を **10 gate 通過の結果**として行い、移動が先行しないこと。Box実査(11)で「現状は既済フォルダ移動で終了を弱表現」＝制御塔(SF)側 gate へ昇格させる。`matter→closed` は #1〜#10 全充足前は禁止。
  - **②法的終了(closing)前に②事務クローズ(closed)へ飛ばさない**: closing を経ずに closed 不可。
  - **金銭未確定での自動 closed 禁止**: finance が reconciled 未到達（HG-05/HG-06 人間承認なし）で closed 不可（G-06 マスト③）。
  - **AI/observed の自動既済化禁止**: #10 の declared 終了状態＝人間承認(HG-07/G-19)なしに自動 closed 化しない。observed 先行は HITLキューへ。
- **乖離検知（G-04/D-004）**: observed（Box既済フォルダ移動済・成果物送付済）が declared（SF closed 承認）に先行する場合＝「SF未終結のまま実務終了」を可視化。逆に declared 先行（SF closed だが Box成果物/原本返却の証跡なし）＝「事務クローズ未完での法的終了宣言」を可視化。**declared側(SF)が BLOCKED のため乖離検知は接続後に稼働**。

---

## 3. 金銭の確定設計（やること3 / G-11・G-10・HG-05/06）

owner裁定: **入金=銀行通帳(DS-024)が真実の源(正本)＋MoneyForward会計(DS-016)と突合**(G-11/D-029)。**依頼者/支払者を分けて持つ**(G-10/D-013)。**金銭の確定（報酬確定・預り金精算・振替）は人間必須ゲート**(G-06 マスト③ / HG-05・HG-06)。

### 3.1 入金確定フロー（通帳=正 + MF突合）

| 段階 | 内容 | データ源 | basis | 測定可否 |
|---|---|---|---|---|
| F1 請求発行 | 最終請求書PDFの発行＋台帳記帳 | Box請求書PDF(Box実査(7)) + 請求書発行管理簿(v5) | observed | **接続済(Box)** |
| F2 請求送付 | 請求通知の送付（依頼者 or 第三者支払者宛） | Gmail(Ledger trace1:0105 損保宛着手金請求) | observed | **接続済(Gmail)** |
| F3 入金予定/受付 | 支払者からの入金予定・受付の外部通知 | Gmail(trace1:0106 `payment_acknowledged_external` / trace3:0302 `payment_pending_external`) | declared(外部宣言) | **接続済(Gmail)** ＝外部受付の観測のみ |
| F4 入金実体 | 実入金の着金 | **銀行通帳(正, DS-024)** | observed | **未接続(通帳)＝測定不能** |
| F5 入金消込・突合 | 通帳着金 ↔ MF会計 ↔ 請求 の3点突合で消込確定 | **MoneyForward(DS-016)** ↔ 通帳 ↔ Box/SF請求 | human_decision(承認) | **未接続(MF/通帳)＋BLOCKED(SF)＝測定不能** |

**測定不能の明示**: F4/F5（実入金・入金消込）は **MF/銀行通帳ともに未接続のため機械的入金消込は未測定**（catalog finance_events.payment_master.capture_gap と整合）。Ledger でも trace1:0106 / trace3:0304 のコメントに「実入金日・入金消込は別系統で確認要」と明記。**接続済(Gmail)で取れるのは F1〜F3（請求発行・送付・外部受付通知）まで**であり、F4以降は前提待ち。一般論で埋めない。

### 3.2 預り金精算（ゼロ化）・実費・報酬確定

- **預り金ゼロ化(#5)**: SM-finance の trust_deposit（受領）→ expense（実費差引）→ refund（残金返金）の収支で trust残高=ゼロを確定。Ledger trace3 が実例（`自賠責入金 − 弊所立替金 = 依頼者送金残額`, trace3:0304 reconciliation_basis）。Box側は預り金見積/領収(Box実査(6)(8))で観測可、確定は会計/SF。
- **実費**: expense(FE-expense) を MF会計/SFで記帳。**未接続(MF)＋BLOCKED(SF)で確定値は未測定**、Box領収書PDFで個別実費の発行は部分観測可。
- **報酬確定(#3)**: 最終請求額の確定。Box請求書PDF発行は観測可、額の正本は会計/SF。
- いずれも **金額はPII方針(規約ルール11)により非記載**（プレースホルダ・型・収支構造のみ）。Ledger も `amount: null`・`amount_note: 金額はPII方針により非記載` で一貫。

### 3.3 依頼者/支払者分離（G-10/D-013）

- catalog finance_events.client_payer_split（confirmed）= `client_party_id` / `payer_party_id` を分離保持。Ledger で強く実証: trace1=弁護士費用特約で **損保が第三者支払者**(party:trace1:payer_insurer)・法人が依頼者、trace3=自賠責/任意保険が支払者(party:trace3:payer_insurer)・個人が依頼者。
- 金銭確定設計への含意: 請求先(payer)と精算返金先(client)が別エンティティになり得るため、#3請求は payer 宛・#5精算返金は client 宛で別管理。入金消込(F5)は payer からの着金、refund(#5)は client への送金。EXC-client_payer_split で例外管理。

### 3.4 金銭確定の人間ゲート承認接続（HG-05/HG-06）

- HG-05 報酬確定 / HG-06 預り金・実費精算/振替（承認者=弁護士＋事務局長, basis=human_decision, required=true マスト③ / catalog human_gates.gates）。
- 接続: SM-finance の `reconciled` 遷移は **HG-05+HG-06 の人間承認を必須**とし、observed（Box発行・Gmail受付）や AI推定だけで自動 reconciled 化しない（G-19/D-031 forbidden: ai_estimate_as_human_decision）。Ledger trace3:0304 の「送金タイミング(事件処理完了前後)は人間判断(弁護士)に依存」が HG-06 の自然発生実例。
- **承認の正本格納先**: 現状 BLOCKED(SF) ＝承認者・承認時刻の declared 正本がSF側で空白(W-110)。接続後に reconciled 承認レコードを記録。

---

## 4. 終了報告の判定（やること4 / G-15）

owner裁定 G-15/D-027（Box-U2 解消）: **業務終了報告書の専用ペーパーは書いていない**。実体は①成果物そのもの（判決・契約書等）が報告を兼ねる ②報酬請求のお手紙が終了報告を兼ねる ③判決案件等では書かないこともある。→ close gate #8「終了報告済」は専用書類でなく **「成果物送付 or 報酬請求(金額確定)の通知が出ている」で判定**。

### 4.1 判定ロジック（「終了報告済」= OR 判定）

`終了報告済(#8) = (A 最終成果物送付済) OR (B 報酬請求通知済)`

| 経路 | 検出シグナル | データ源 | 抽出方法 | basis | 接続性 |
|---|---|---|---|---|---|
| A 成果物送付 | 最終成果物が依頼者宛に送付 | **Box `1-2 通信（送）`**(Box実査(9)) + Gmail送付 | Box: 通信(送)フォルダへの最終成果物配置＋送付書(`YYYYMMDD＋送付＋内容`)。Gmail: 成果物添付/案内の送信検知。Ledger trace3:0305 `deliverable_sent`(確認事項連絡=成果物送付系)が観測実例 | observed | **接続済(Box/Gmail)** |
| B 報酬請求通知 | 報酬請求(金額確定)の通知送付 | **Gmail** + Box請求書PDF(Box実査(7)) | Gmail: 請求書添付/請求案内の送信検知（Ledger trace1:0105 `invoice_sent`=請求送付の観測実例）。Box: 請求書PDF発行＋台帳。金額はPII非転載 | observed | **接続済(Box/Gmail)** |

- **判定の成立**: A/B いずれかの送付イベント(document.lifecycle_state=sent / finance invoice_sent)が matter_ref 配下に存在すれば #8 を pass 候補とする。両経路とも接続済(Box/Gmail)で検出可＝**専用ひな形なしでも判定設計が成立**（G-15でBox-U2解消）。
- **確信度=中の理由[worker推論]**: 「成果物送付」と「報酬請求」のどちらが終了報告を兼ねるかは案件類型で異なり（G-15 ③判決案件は書かないことも）、送付の意図分類（中間送付 vs 最終報告）に余地が残る。最終/中間の区別は SM-document の最終成果物フラグ・案件状態(closing以降)との組合せで補強する[要検証]。AI推定の分類は Derived・人間未承認に留める（G-19）。
- **未接続の影響**: 電話での口頭報告(Dialpad未接続)・Notta議事録での報告は検出不能＝当面 Box/Gmail の送付イベントに限定する旨を明示（捏造しない）。

---

## 5. PoC2 KPI 計測設計（やること5）

KPI定義は owner裁定（catalog metrics.poc2, G-07/G-09/D-024）で確定済。**現状値の算出可否**を接続性で分ける。測定不能は「定義のみ・前提待ち」と明示。

| KPI | 算出式 | 分子/分母の定義 | データ源（理想／現状） | 測定可否 | 取得方法 |
|---|---|---|---|---|---|
| KPI-P2-05 close gate未通過滞留率 | `(①法的終了済かつ②事務クローズ未完で滞留中のmatter数) / (①法的終了済の全matter数)` | 分子=closing到達済だが #1〜#10 未充足で closed 未到達のmatter。分母=closing以降の全matter | 理想: SF matter状態+10gate判定 / 現状: 接続済gate(#6/#9/#7/#8/#3発行)のみ部分判定 | **△ 接続済で部分**（接続済gateの未充足は検出可）／ **BLOCKED(SF)で母集団(matter状態)確定は前提待ち** | 接続済(Box/Gmail)で #6/#7/#8/#9 の未充足matterを先行列挙。母集団=SF matter状態は ETL後 |
| KPI-P2-04 終了報告送付率 | `(終了報告済(§4 A or B)のmatter数) / (①法的終了済の全matter数)` | 分子=成果物送付 or 報酬請求通知が出ているmatter(§4)。分母=closing以降 | 成果物送付(Box `1-2 通信（送）`) + 報酬請求通知(Gmail/Box請求書) | **接続済(Box/Gmail)＝分子は今すぐ算出可** / 分母(母集団)は BLOCKED(SF) | §4 判定で分子を集計。分母 closing到達母集団は SF matter状態に依存＝部分は前提待ち |
| KPI-P2-02 預り金/実費精算完了率 | `(trust残高ゼロ確定のmatter数) / (預り金受領ありの全matter数)` | 分子=trust_deposit−expense−refund=0 が HG-06承認済。分母=預り金受領実績あり | SF Deposit/Expense + MF + Gmail精算連絡 | **BLOCKED(SF)+未接続(MF/通帳)** ＝定義のみ。Gmailで精算判断点は観測可(trace3)だが確定値は不能 | MF/通帳接続＋SF会計ETL後に収支ゼロを集計。**前提待ち** |
| KPI-P2-03 原本返却完了率 | `(原本返却済 or 保管理由ありのmatter数) / (預り原本ありの全matter数)` | 分子=返却受領書あり or 明示保管理由。分母=`4 預かり資料`に原本受領実績あり | Box `4 預かり資料` + 返却受領書(v5) | **○ 接続済(Box)** ＝受領→保管→返却がフォルダ＋書式で判定可(Box実査(8)) | Box `4 預かり資料`配下の受領ロット/返却受領書を集計。**今すぐ着手可** |
| KPI-P2-01 最終請求確定までの時間 | `final_invoice_confirmed_at − outcome_reached_at` の中央値/分布 | 分子=最終請求確定時刻−解決時刻 | 理想: SF/会計確定日 / 現状: Box請求書PDF発行日 + 解決(Gmail/SF) | **△ 接続済(Box)で発行日近似** / 確定(額の正本)は BLOCKED(SF)+未接続(MF)。解決時刻はGmail近似 | Box請求書PDF created/version と解決イベント(Gmail trace3:outcome系)の時刻差。確定額の正本は前提待ち |
| KPI-P2-06 未収率 | `(入金消込未了で滞留の請求額/件数) / (全最終請求)` | 分子=overdue/writeoff確定。分母=最終請求発行済 | MF会計(入金消込) + 銀行通帳(正) + SF | **未接続(MF/通帳)＋BLOCKED(SF)** ＝測定不能（入金消込が取れない） | MF/通帳接続後に overdue 集計。**前提待ち** |
| KPI-P2-07 declared/observed乖離率 | `(observed終結とdeclared終結が乖離するmatter数) / (closing到達の全matter数)` | 分子=Box既済移動/成果物送付(observed)とSF closed承認(declared)が不一致。分母=closing以降 | observed(Box/Gmail) ↔ declared(SF) | **接続済(observed側)構築可** / 突合は **BLOCKED(SF declared)で前提待ち** | observed側(Box既済・成果物送付)を先行構築。declared(SF closed)接続後に突合(§2.2乖離検知) |

**KPI測定可否内訳**:
- **接続済で今すぐ着手可能**: KPI-P2-03 原本返却完了率（Box）／ KPI-P2-04 終了報告送付率の**分子**（Box/Gmail, §4）／ KPI-P2-05 滞留率の**接続済gate部分**（#6/#7/#8/#9）／ KPI-P2-01 の Box発行日近似／ KPI-P2-07 の observed側構築。
- **前提待ち（未接続/BLOCKED）**: KPI-P2-02 精算完了率（MF/通帳/SF会計）／ KPI-P2-06 未収率（MF/通帳）／ KPI-P2-01・P2-05 の確定/母集団部分（SF）／ KPI-P2-04 の分母(closing母集団, SF)／ KPI-P2-07 の突合(SF declared)。
- **未接続由来の未測定（仮説で埋めない）**: 入金確定時間・入金消込率・実費確定値は MF/銀行通帳未接続のため未測定（catalog metrics.measurement_gap と整合）。

---

## 6. 計測の段取り（やること6 / PoC1 W-210 に倣う）

接続済（Box/Gmail/Calendar/Docs）だけで今すぐ取れる close gate 判定と、未接続(MF/通帳)/BLOCKED(SF)解消後に初めて取れる判定を分離。

### 6.1 今すぐ着手可能（接続済のみで取れる）

| 項目 | 取得源 | 備考 |
|---|---|---|
| #6 預り原本 返却済or保管理由 | Box | `4 預かり資料`の受領→保管→返却を書式＋フォルダで判定（確信度=高） |
| #9 Box正本確定（正本同定部分） | Box | file_id+version_id・既済フォルダ配置・docx⇔pdf確定版（SF背骨紐付けは前提待ち） |
| #8 終了報告送付済 | Box + Gmail | §4 OR判定（成果物送付 or 報酬請求通知）。専用ひな形不要 |
| #7 最終成果物送付済（送付まで） | Box | `1-2 通信（送）`への配置＋送付書。到達は追跡表で間接 |
| #3 最終請求確定（発行まで） | Box | 請求書PDF発行＋管理簿。額の確定は前提待ち |
| KPI-P2-03 原本返却完了率 | Box | 今すぐ算出可 |
| KPI-P2-04 終了報告送付率（分子） | Box + Gmail | §4 判定で分子算出可 |
| KPI-P2-05 滞留率（接続済gate部分） | Box + Gmail | #6/#7/#8/#9 の未充足matterを先行列挙 |
| KPI-P2-07 乖離検知（observed側） | Box + Gmail | observed終結シグナルの構築 |

→ **今すぐ判定着手できる close gate = 3項目（#6/#8/#9）完全＋2項目（#3/#7）部分**。今すぐ算出着手できる KPI = KPI-P2-03 完全＋KPI-P2-04/05/07 部分。

### 6.2 前提待ち（接続・ETL後に初めて取れる）

| 項目 | 前提（解消事項） | ブロッカー |
|---|---|---|
| #1 未完WorkItem無 | SF ETL起動＋Task/次行動の現行入力＋Chatworkタスク対応(DS-023) | BLOCKED(SF) W-110 |
| #2 残期限無 | SF ETL＋Deadline専用テーブル新設(W-110 Q3, catalog SM-deadline c_newtable) | BLOCKED(SF) W-110 |
| #4 未収扱い確定 | MF/銀行通帳接続＋入金消込＋会計ETL | 未接続(MF/通帳)＋BLOCKED(SF) |
| #5 預り金・実費精算済（確定） | SF Deposit/Expense ETL＋MF/通帳接続で収支ゼロ確定 | 未接続(MF/通帳)＋BLOCKED(SF) |
| #3 最終請求確定（額の正本） | SF Billing/Invoice ETL＋MF突合 | BLOCKED(SF)＋未接続(MF) |
| #10 SF終了状態が人間承認済 | SF cases投入＋終了状態/承認者列＋HG-07承認記録 | BLOCKED(SF) W-110 |
| #9 のSF背骨ID紐付け | SF背骨ID(Matter Id, G-01)へのBox正本解決＋変換関係列(Q4) | BLOCKED(SF) W-110 |
| KPI-P2-02 精算完了率 / P2-06 未収率 | MF/通帳接続＋SF会計ETL | 未接続(MF/通帳)＋BLOCKED(SF) |
| 入金確定フロー F4/F5（実入金・消込） | 銀行通帳＋MoneyForward接続 | 未接続(MF/通帳) |
| KPI-P2-07 declared/observed突合 | SF closed 承認(declared)の投入 | BLOCKED(SF) |
| 終了報告 最終/中間の分類閾値 | 設計検証＋owner裁定 | [worker推論]要検証 |

---

## 7. owner裁定 / worker推論 / 未確認 の分離（混同防止）

- **owner裁定（確定・根拠付）**: 2段クローズ①法的終了/②事務クローズ完了(G-09/D-024)、close gate10条件(D-014/D-024/D-027)、入金=通帳が正+MF突合(G-11/D-029)、依頼者/支払者分離(G-10/D-013)、金銭の確定=人間必須マスト③/HG-05・HG-06(G-06/D-023)、終了報告=専用様式なし→成果物送付or報酬請求通知で判定(G-15/D-027)、7状態機械(G-05/D-022)、期限正本=SF・徒過防止多重チェック(G-20/D-033)、AI推定の確定境界=人間承認で確定・推定のまま(G-19/D-031)、Box正本(G-02)、SF背骨ID(G-01)。
- **worker推論（本書提案・owner未裁定）**: 終了報告 #8 の最終/中間送付の分類閾値(§4)、close gate の機械別担当割当の細部(§2.1)、KPI滞留率の母集団近似(§5)。→ owner承認で確定化すべき候補。
- **未確認 / BLOCKED**: SF/LEALA 会計・期限・タスク・終了状態の全項目（W-110: cases/documents 0行・縮約スキーマ・会計/Deadline/Task 専用テーブル未到達）、MoneyForward/銀行通帳（未接続＝入金消込・実費・報酬確定値が未測定）、Notta/Dialpad（未接続＝口頭報告・議事録が未検出）、原本返却の全期間母集団（Box実査はサンプル）、終了報告の案件類型別の兼用パターン（G-15 ③判決案件で書かない例）。

*生成: v0.2 PoC2 close gate計測設計（W-20260624-250）。本番 SF/Box/MF 非アクセス・書込なし・git操作なし。PII不記載（様式/プレースホルダ/構造のみ・規約ルール11）。owner裁定/worker推論/未確認を分離。測定不能は未接続(MF/通帳)・BLOCKED(SF)を明示し一般論で埋めない。捏造なし。*
