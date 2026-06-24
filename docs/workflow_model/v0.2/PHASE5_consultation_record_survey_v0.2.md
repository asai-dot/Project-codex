# PHASE5 相談記録ソース(Google Calendar/Docs) read-only 実査

- worker_task_id: W-20260624-190
- generated_at: 2026-06-24
- source_request: docs/workflow_model/REQUEST_v0.2.md
- 一次根拠: docs/workflow_model/v0.2/ALO_OWNER_GRILL_ANSWERS_v0.1.md の G-14
- 前提方針: Box=文書正本 / Salesforce=業務制御塔 / 自然発生データ優先 / Raw・Canonical・Derived 分離

## 接続・宣言（冒頭固定）

- **接続実体 = Google Calendar (read-only) / Google Docs(Drive) (read-only)**。両者ともowner Workspaceに到達・実査済。
- **PII非転載の宣言**: 本成果物には相談メモ本文・氏名・事件内容・金額を一切転載しない。記載は集計値・構造・マスクした命名様式のみ。実査では氏名/事件名を含む値に触れたが、成果物では型(様式)に抽象化した。
- **Notta = 未接続 = 未測定**: Notta API/コネクタは未接続。議事録(Notta)由来の件数・構造は本実査では測定不能。推測で埋めない。
- **read-only 自己宣言**: 呼び出したのは list_calendars / list_events / get_event / Drive search_files / get_file_metadata のみ。**create/update/delete/respond 系は一切呼んでいない**。Docsの `read_file_content` / `download_file_content` も**呼んでいない**（秘匿特権本文の保護）。構造はメタデータ(タイトル・親フォルダ・所有者・更新日・添付URL)のみから判定した。

---

## 1. カレンダー実査（やること1）

### 1.1 到達したカレンダー
list_calendars で10カレンダーを確認。相談に関係するのは owner業務カレンダー `asai@`(主)、所員個別カレンダー(`nakamori@`,`nishimura@`,`takechi@`,`miyazawa@`)、`ALO全体`。実査の主対象は `asai@`。

### 1.2 抽出方法と日付レンジ
`asai@` を `fullText='相談'` で 2025-01-01〜2026-06-24 を走査。相談性の予定が継続的に存在し、本ページ(25件)時点で2026-04末まで到達(nextPageToken残あり=実件数はこれ以上)。本実査は構造把握目的のサンプルとして十分な母集団を観測。

### 1.3 タイトルの命名様式（氏名・事件名はマスク。型のみ）
自然発生の予定タイトルは**専用様式なし=自由記述**で、観測された型は概ね次の混在:

- 型A 新規相談（来所/web）: `<当事者名> 新規相談` / `<当事者名>（新規ご相談）<来所・人数等の補足>`
- 型B 個別相談: `<当事者名> 相談` / `<当事者名>様 別件相談` / `<当事者名>（相談）web（場所）`
- 型C 法律相談(分野付き): `<対象> 法律相談`
- 型D 事務所会議の議題行: `[事務所会議 YYYY-MM-DD] <当事者名>＿<事件分野>相談`（債務整理/クレジット・サラ金/相続/事業整理/企業法務/住宅ローン抵当権 等の分野語が `＿` 区切りで付く案件レビュー行）
- 型E 外部・公益相談(非個別案件): 当番弁護士/区役所/商工会議所/協議会/勉強会「なんでも相談会」等

含意: タイトルは**人間が自由記述**しており、相談(個別案件)と非相談(公益・勉強会・会議議題)が同じ `相談` 語で混在する。後段の合成では型Eを相談記録から除外する判別が要る(語彙だけでは不十分→添付/参加者/分野語の併用が要る)。

### 1.4 参加者数の分布（構造のみ）
- 多くの個別相談予定は attendees 配列が空 or owner単独(self)で、相手方はタイトル文字列にのみ存在(=参加者は構造化されていない)。
- 一部の予定のみ外部相手のメールが attendees に入る(例: 相手方1名 + owner)。メール参加は任意で、相談相手の同定キーとしては**非信頼**。
- 型D(事務所会議の議題行)は `availability=FREE` / `transparency=transparent` の同時刻ブロックが多数並ぶ=実会議ではなく**案件ステータス棚卸しの掲示**用途。

### 1.5 予定本文(description)・添付に「事件メモGoogleDocリンク」が含まれるか（集計）
**含まれる。これが主たる紐付け面である。** 観測パターン:

- **添付(attachments)**: 個別相談予定の多くが `attachments[].fileUrl = https://docs.google.com/document/d/<DOC_ID>/edit` を1〜2個保持。`title` は後述のメモ命名様式。→ event→Doc が**ファイル添付**で成立。
- **description 内リンク**: 一部予定の description に Notta共有URL(`app.notta.ai/share/<uuid>`)とDocリンクが貼られる例を観測(=Notta議事録が予定本文から参照される導線が**人手で**作られている個別事例あり。ただしNotta本体は未接続なので中身は未測定)。
- **description のステータスメモ**: 型Dは description に短い進捗(次回MTG日時、受任通知発送、申立書作成中 等)が人手で書かれる。

get_event を1件実行し、list_events の添付情報が単体取得でも同一(fileUrl=Docリンク)であることを構造確認した(本文は取得せず)。

---

## 2. Google Docs 実査（やること2／metadata中心・本文非転載）

Drive search_files を `title contains 'メモ'`(mimeType=Doc, modifiedTime>2025-01-01) および `title contains 'Gemini によるメモ'` で実査。**本文は一切開いていない**(get/download content未使用)。観測した構造:

### 2.1 命名様式（2系統）
- 様式M(手打ち/予定添付メモ): `メモ - 「<件名>」`。`<件名>` は予定タイトルとほぼ一致(例: 相談の件名や「◯◯様 別件相談」型)。これが G-14 の「カレンダー紐付け事件メモ Googleドキュメント」に対応。
- 様式G(自動生成・議事録系): `<件名> - YYYY/MM/DD HH:MM JST - Gemini によるメモ`。Google Meet/Gemini が会議から自動生成。相談・打合せ・社内会議が混在。

### 2.2 所有者種別・更新日レンジ・親フォルダ（構造）
- 所有者: 大半 `asai@`、一部 所員(`miyazawa@`,`takechi@`)所有で owner に共有(sharedWithMe)。=所有者は**作成者依存でばらつく**。
- 更新日: 2025年〜2026-06(本日)まで連続。直近も活発に生成。
- 親フォルダ(parentId)が**様式で割れる**:
  - 様式M(手打ちメモ)は My Drive ルート相当(`0AKMKCDWAYFI4Uk9PVA`)に loose 保存される例が多い。
  - 様式G(Geminiメモ)は専用フォルダ(`1V-I2-W9vl3-pjgArkaOQuo6sbOKAM-xb`)に集約される傾向。
- いずれも案件単位フォルダで整理されておらず、**Doc単体が事件メモの実体**(専用様式・採番なし)。G-14の「専用様式は運用されていない」と整合。

### 2.3 結合検証
予定の添付 `fileUrl` から抽出した DOC_ID(例 `1qcg-…VEEE`)を get_file_metadata で照会 → 同一タイトルの様式M Doc に解決。**event.attachments.fileUrl の doc_id = Drive file id が一致**することを確認(本文非参照)。

---

## 3. 紐付け方式の特定（やること3）

| 結合面 | 成立 | 結合キー候補 | 信頼度 |
|---|---|---|---|
| (b) 添付ファイル | **主**。個別相談予定の多くが Docを添付 | `calendar.event.attachments[].fileUrl` から正規表現 `/document/d/(<doc_id>)/` 抽出 → `drive.file.id` と突合 | 高（ID完全一致、検証済） |
| (a) 予定本文中のリンク | 補助。一部予定のdescriptionにDoc/Notta共有URL | description内URLから doc_id / notta share uuid 抽出 | 中（任意・不在多い） |
| (c) 命名規則の一致 | 補助/フォールバック | 様式M Doc の `「<件名>」` ≒ 予定 `summary` | 低〜中（自由記述ゆらぎ・同名衝突リスク） |

**結論**: 一次結合は **event_id ↔ doc_id（添付fileUrlのdoc_id経由）**。(a)はNotta議事録への橋渡しに有用だが疎。(c)は(a)(b)が無い予定の救済キー(要 fuzzy)。

---

## 4. 受任シグナルの観測可否（やること4）

- カレンダー側: 型D議事録行の description に「受任通知発送」「申立書作成中」等の進捗語が**人手で**現れる例を観測。ただしこれは自由記述の痕跡であり、**受任の構造化シグナル(委任契約締結フラグ・受任通知の正式記録)ではない**。観測=断片的・非信頼。
- Docs側(メタデータのみ): 受任を示す構造化メタは観測できない(専用様式・ステータス項目なし)。
- **判定: 受任(委任契約・受任通知)の確かなシグナルは Calendar/Docs では構造的に観測できない。** → **Gmail(受任通知メール)/Box(委任契約書正本)/Salesforce(案件ステータス=制御塔) 側に依存**と明示。カレンダーの進捗語はせいぜい Derived の補助観測に留め、受任の確定判断には使わない。

---

## 5. 合成設計メモ（やること5）— Raw/Canonical/Derived

相談記録(Consultation record)を **Notta議事録(未接続)＋手打ちメモ(様式M)＋事件メモ/議事録Doc(様式G)** から合成する最小設計。schema(`alo_workflow_event_schema_v0.2.json`)・catalog(`ALO_WORKFLOW_CATALOG_v0.2.yaml`)と整合させる。

### 5.1 束ねるキー
- 一次キー: **consultation_key = カレンダー event_id**（相談イベントの自然な単位）。
- 結合: event_id →(添付fileUrl doc_id)→ メモDoc。複数Doc(手打ち+Gemini)が1イベントに付くため **1相談 : N文書**。
- Notta: 接続後は description/添付の notta share uuid を `notta_session_id` として同 consultation_key に束ねる(現状は**未接続=空**)。
- 案件昇格時: 既存 schema の `consultation_converted_to_matter` で `matter_ref` に接続(SF/Box側ID)。

### 5.2 Raw / Canonical / Derived 配置

- **Raw(原本ポインタのみ・本文非取り込み)**:
  - `cal_event_ptr`: calendarId + event_id + htmlLink + updated
  - `doc_ptr[]`: drive file_id + title + owner + modifiedTime + parentId（**本文は格納しない=秘匿特権**。Boxを正本とする方針に沿い、原本はGoogle側に残しポインタ参照）
  - `notta_ptr`: share uuid（未接続のため現状null）
- **Canonical(正規化メタ。PIIは別アクセス制御層)**:
  - consultation_record: { consultation_key(event_id), occurred_at(event.start), channel(来所/web/電話を様式から導出), source_refs=[Raw ptrs], matter_ref(任意) }
  - event語彙へのマッピング: `consultation_scheduled`(予定作成) / `consultation_started`/`consultation_completed`(実施) / `advice_recorded`(メモDoc生成) を envelope化。provenance に Raw ptr を必須記載。
- **Derived(要約・分類)**:
  - 相談分野(型Dの `＿<分野>` 語からの分類候補)、受任見込みフラグ(description進捗語からの**観測・人間未承認**)、相談→受任リードタイム等。
  - **AI推定は Derived 限定**、`confidence` 付・人間未承認(human gate前)。受任確定はここで判断しない(§4)。

### 5.3 既存資産との整合
- event_type は schema_v0.2 のコアenum(`consultation_*`,`advice_recorded`,`consultation_converted_to_matter` 等)に既に存在 → 新規イベント型の追加不要。
- 秘匿特権本文を取り込まない設計は catalog 前提(Box=正本/Raw・Canonical・Derived分離)と整合。本文要約が必要なら Derived 層で別アクセス制御の上、原本ポインタ経由で実施。

### 5.4 残課題
1. **Notta未接続**: 議事録本体(件数・構造・session_id)未測定。コネクタ要。
2. 相談 vs 非相談(公益/勉強会/会議議題)の判別ルール: タイトル語彙だけでは不可、添付有無・参加者・分野語の併用ルールが要設計。
3. 添付なし予定の救済: 命名fuzzy(c)の閾値・同名衝突対策。
4. 受任の確定シグナル: Gmail/Box/SF 連携が前提(本実査範囲外)。SF実査(W-110)はコネクタ不在でBLOCKED継続。
5. 件数の母集団確定: 本実査はサンプル(25件/1ページ)。全期間の正確な相談件数集計は追加ページング走査が要る(構造判定には十分)。
