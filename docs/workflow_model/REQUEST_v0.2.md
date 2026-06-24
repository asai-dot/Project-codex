# REQUEST — 浅井法律事務所・業務フロー機械可読化 v0.2 作成指示（原本・無改変）

> 本ファイルは浅井さんから受領した v0.2 作成指示の **原本** です。ワーカーへの発注はこの
> 指示を分解した `docs/worker_queue/inbox/W-20260624-*.md` 群で行います。台帳・作業票が
> 指示と食い違った場合は **本ファイルが正** とします（v0.1 は `../v0.1/` に保全、上書き禁止）。

前提方針: **Box＝文書正本、Salesforce＝業務制御塔、自然発生データ優先、Raw／Canonical／Derived分離。**

---

あなたは、浅井法律事務所の実際の業務を、将来AI・ワークフローエンジン・Salesforce・ALO Connect が処理できる形へ構造化する担当者です。

添付の次の4ファイルを v0.1 原本として使用してください（本リポジトリでは [`../v0.1/`](../v0.1/)）。

- `浅井法律事務所_業務フロー機械可読化_設計・ヒアリングパック_v0.1.docx`
- `浅井法律事務所_業務フロー実査台帳_v0.1.xlsx`
- `alo_workflow_event_schema_v0.1.json`
- `alo_workflow_event_example_anonymized_v0.1.json`

v0.1 を上書きせず、**実物・実データによる裏付けを追加した v0.2** を作成してください。

## 1. 到達目標
各業務を次の単位に分解する: 1 Trigger / 2 Actor / 3 Input / 4 Action / 5 Decision / 6 Output /
7 State transition / 8 Work item / 9 Evidence / 10 Exception / 11 Finance / 12 Provenance。
最終的に **相談流入→受任→事件処理→成果物納品→請求→精算→原本返却→終了報告→既済化** を
一続きで追跡できる状態にする。

## 2. 絶対原則
- Salesforce = 案件ID・申告状態・担当・次行動・期限・人間承認の制御塔。
- Box = 文書本体・版・最終成果物の正本。
- Gmail / Dialpad / Notta / Calendar / 郵便 / Box更新 / MF 等 = 進行を示す観測ソース。
- 元メール・元録音・元文書を破壊・改変しない。
- 観測事実・AI推定・人間判断を混同しない。
- 新規手入力は、自然発生データから取得できない判断・承認に限定。
- コンフリ・受任成立・重要方針・対外成果物・請求確定・預り金精算・終結は **人間必須ゲート**。
- 不明事項を一般論で埋めない。`未確認` / `証拠不足` / `浅井聴取要` を明示。
- 一般成果物に個人名・住所・電話番号・事件内容・具体的金額を記載しない。

## 3. 作業順序
- **Phase 0**: v0.1 構造確認（23フロー / 245問 / 22データソース / 35文書種別 / 72イベント /
  53状態 / SFフィールド対応 / 設計仮説・未決）を一覧化。感想で止めずに進む。
- **Phase 1**: 245問を `実データから回答可能` / `既存資料から回答可能` / `実物サンプル確認で回答可能` /
  `担当者聴取が必要` / `設計判断が必要` に分類。浅井先生へ聞く前に既存資料・実データで埋める。
  P0 58問は全件 `回答済・証跡あり` / `暫定回答・追加検証要` / `浅井聴取必須` / `中森聴取必須` /
  `外部SE確認必須` のいずれかに。空欄禁止。
- **Phase 2**: 実査（**read-only**）。
  - Salesforce/LEALA: Consultation / Matter(Business) / Account・Contact・RelatedContact・OpponentParty /
    Task・Event・Chatter・Office Meeting / Deadline・Procedure・JurisdictionCourt /
    Accounting・Billing・Invoice・Expense・Deposit・TimeCharge /
    PostalMatter・RequiredDocument・KeepingItem・CaseDocument / 変換関係 / BoxURL / 担当 / 流入経路 /
    失注理由 / 受付日・相談日・受任日・終了日 / 次行動・期限・待ち先 相当項目。
    本番の変更・項目追加・Flow変更・DDL変更は禁止。入力率・値の揺れ・自由記述過積載・状態と実態の乖離を確認。
  - Box: メタデータ先行、本文は層化サンプルのみ。優先12対象（電話受付/業務マニュアル/書式ひな形/
    相談票/委任契約書/見積書/請求書/預り資料/成果物送付/業務終了報告書/既済フォルダ構造/進行中フォルダ構造）。
    作成・レビュー・確定・PDF化・送付・到達・受理・返却・廃版の各状態を区別。
  - Gmail 等: 本文転載せず業務イベントのみ匿名抽出。最低3トレース（受任到達例 / 失注例 /
    解決→第三者支払者請求→入金→精算→終了報告例）。各トレースを日時順に event_type/source/
    actor_role/matter_ref/document_ref/work_item/decision/state_before/state_after で記録。
- **Phase 3**: 実査台帳の9シート更新（フロー仮説の確認済/修正/棄却/例外分離、質問の回答・根拠・証拠ID、
  データ取得台帳の主キー・結合キー、文書のライフサイクル、イベントの検知元・重複排除・確定方法・承認要否、
  状態遷移を Consultation/Matter/WorkItem/Document/Delivery/Finance/Deadline で分離、SF対応の4区分、
  証跡サンプル追加、決定事項ログは追記のみ）。

## 4. 浅井先生へのグリル資料
既存資料・実データで回答できない質問だけを抽出し `ALO_OWNER_GRILL_PACK_v0.1.md` を作成。
各質問に 質問 / 現仮説 / 確認済証拠 / 推奨回答案 / 選択肢 / 回答で変わる設計 / 回答者 / 優先度 /
具体例 / 例外ケース を付す。「Aを正本としBは観測に留める理解でよいか。例外はCか」のように短時間で
裁定できる形に。最初は P0 から **20問以内**、残りは後続キューに全保持。

## 5. 最終成果物
1. `浅井法律事務所_業務フロー実査台帳_v0.2.xlsx`
2. `ALO_WORKFLOW_CURRENT_STATE_v0.2.md`
3. `ALO_WORKFLOW_CATALOG_v0.2.yaml`
4. `ALO_WORKFLOW_EVIDENCE_LEDGER_v0.2.jsonl`
5. `ALO_OWNER_GRILL_PACK_v0.1.md`
6. `ALO_WORKFLOW_GAP_AND_POC_PLAN_v0.2.md`
7. `alo_workflow_event_schema_v0.2.json`
8. `alo_workflow_event_examples_v0.2.jsonl`
9. `CHANGELOG_v0.2.md`

`ALO_WORKFLOW_CATALOG_v0.2.yaml` は最低限 processes / actors / systems / triggers / events /
work_items / decisions / documents / deliveries / states / transitions / finance_events /
human_gates / exceptions / evidence_types / metrics を収録。

## 6. 最初のPoC
- **PoC 1 相談→受任**: `問合せ受信→本人関係確認→コンフリ→トリアージ→日程調整→資料受領→相談→
  追加質問→見積→契約案→最終確認→受任`。KPI: 初回応答/相談確定/見積送付/契約成立までの時間、
  次行動未設定率、流入経路不明率、失注理由未入力率、イベント未紐付け率。
- **PoC 2 解決→終結**: `解決→履行確認→最終報酬計算→請求→入金確認→預り金・実費精算→原本返却→
  成果物納品→終了報告→既済化`。close gate: 未完WorkItem無 / 残期限無 / 最終請求確定 / 未収扱い確定 /
  預り金・実費精算済 / 預り原本 返却済or保管理由 / 最終成果物送付済 / 終了報告送付済 / Box正本確定 /
  SF終了状態が人間承認済。

## 7. 禁止事項
実物を見ず一般論で回答 / 245問をもっともらしい文章で一括充填 / SF・Box本番データの書換 /
ファイルの移動・改名・削除 / AI推定を人間の確定判断として記録 / 個人情報・事件内容の一般成果物転載 /
「追加情報待ち」で作業全体を停止 / 調査できる事項を浅井先生へ質問 / フロー図だけ作って完了扱い。

## 8. 完了条件
P0 58問が全件分類・処理済 / 全フロー行に確認状態と証拠 / 全データソースに主キーと結合先 /
主要文書にライフサイクル定義 / 主要イベントに検知元・重複排除・確定方法 / 状態遷移に遷移条件と禁止遷移 /
3本以上の匿名 End-to-End トレース / JSON Schema に対しイベント例が検証可能 /
仮説・確認済事実・未決事項が非混同 / 浅井先生への質問が実査後に残った論点だけ /
v0.1 を上書きせず v0.2 と CHANGELOG を作成。

確認不能事項はキューに積み、他の実査・整理を継続。棚卸しで止まらず、上記成果物が揃うまで進める。
