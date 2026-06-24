---
worker_task_id: W-20260624-210
title: PoC1 実データ dry-run 結果 v0.2（接続済み4源・read-only・PII非転載）
created_at: 2026-06-24
owner: claude-code-worker
source_request: docs/workflow_model/REQUEST_v0.2.md
design: POC1_measurement_design_v0.2.md (W-200)
join_basis: PHASE5_consultation_record_survey_v0.2.md (W-190, event_id↔doc_id)
blocked_ref: PHASE2_salesforce_survey_v0.2.md (W-110, cases 0行=制御塔データ不在)
premise: Box=文書正本 / Salesforce=業務制御塔 / 自然発生データ優先 / Raw・Canonical・Derived分離
---

# PoC1 実データ dry-run 結果 v0.2

## 0. 冒頭宣言（固定）

- **接続 = Google Calendar / Google Docs(Drive) / Gmail / Box（すべて read-only）**。本 dry-run で呼んだのは `list_events` / `get_event`（Calendar）、`search_files` / `get_file_metadata`（Drive）、`search_threads`（Gmail, metadata/minimal view）、`search_files_keyword` / `get_file_details`（Box）のみ。**書込系（create/update/delete/send/label/upload/move）・本文 download 系（Gmail get_thread FULL_CONTENT / Drive read_file_content / Box get_file_content）は一切呼んでいない**。
- **PII非転載宣言**: 本成果物には相談メモ本文・氏名・住所・電話・事件内容・金額を一切転載しない。記載は集計値・構造・マスクした命名様式・ID/様式のみ。実査では氏名/事件名を含む値（タイトル文字列・件名）に触れたが、成果物では型に抽象化した。
- **サンプル期間・件数**: Calendar = `asai@asai-lo.com` を `fullText='相談'` で **2025-06-01〜2026-06-24** を走査し1ページ **25件** を取得（nextPageToken残あり＝母集団はこれ以上、構造把握には十分）。Gmail = `subject:(相談)` / `subject:(受任通知)` / `subject:(見積)` を同期間で各 50件上限で走査。Box = `委任契約書` / `委任状` / `見積書` のキーワード検索。
- **測定可能 / 前提待ちの線引き（結論先出し）**: 接続済み4源で **構造合成・着手KPIの集計・受任observed側の存在検出** までは実証できた。一方 **相談→見積→契約→受任を1案件に束ねる「共通背骨ID」が4源のどこにも無い** ため、クロス系の確定突合は不能（候補件数どまり）。背骨側（SF cases）は W-110 で 0行＝BLOCKED。Notta/MoneyForward は未接続。→ **自動計測の到達点 = 単一源内の構造・時間集計。前提待ち = クロス系確定突合（SF-ETL/背骨ID整備）・相談実施時間（Notta）・入金（MF）**。

---

## 1. 相談記録の実サンプル合成（やること1）

### 1.1 抽出と判別（W-190 §4.3 一次規則を適用）

`asai@` の `相談` ヒット25件を、W-190 の複合判別ルール（添付Docの有無＋availability/transparency＋分野語）で分類した（**集計のみ・氏名非転載**）:

| 区分 | 件数 | 判別根拠 |
|---|---:|---|
| 個別相談（consultation_record 採用候補） | **14** | DEFAULT予定。うち事件メモDoc添付あり=主シグナル |
| 型D 事務所会議の議題行（除外） | 10 | `availability=FREE` かつ `transparency=transparent` の同時刻ブロック群。description は進捗棚卸し（次回MTG日時・受任通知発送・申立書作成中 等の人手メモ） |
| 型E 公益/無料相談（除外） | 1 | 「遺言・相続センター電話無料相談」=非個別案件 |

→ **個別相談として合成対象に採れたのは 14件（exit目安「10件以上」を充足）**。

### 1.2 consultation_key=event_id による 1相談:N文書 の構築（構造集計）

採用14件について `event.attachments[].fileUrl` から正規表現 `/document/d/(<doc_id>)/` で doc_id を抽出し、Drive `get_file_metadata` で突合した。**結合検証**: 添付fileUrlのdoc_id 2件（横井 様式M / 大平建設 様式M）を get_file_metadata で照会 → タイトル・所有者・親フォルダが完全解決し、**event.attachments.fileUrl の doc_id = Drive file id が一致**することを再確認（本文非参照）。

**構造集計（PII無）**:

| 指標 | 値 |
|---|---|
| 合成対象（個別相談） | 14件 |
| 添付Docあり | 10件（**添付有り率 = 71%**, 10/14） |
| 添付Docなし（命名fuzzy救済対象） | 4件（web相談・電話相談・来所のみ等） |
| 1相談あたりDoc数=0 | 4件 |
| 1相談あたりDoc数=1 | 8件 |
| 1相談あたりDoc数=2 | 2件（手打ちメモ様式M ＋ Geminiメモ様式G が併存） |
| Doc添付の様式内訳 | 様式M（`メモ - 「<件名>」`）= 7、様式G（`… - YYYY/MM/DD HH:MM JST - Gemini によるメモ`）= 5 |
| description に Notta共有URL（`app.notta.ai/share/<uuid>`）を保持 | 1件（=Notta導線は人手で疎に作られる。本体は未接続=未測定） |

**Raw ptr 例（ID/様式のみ・氏名非転載）**:
- `cal_event_ptr`: event_id=`3ldabguhdmajfip7jh4etbirs8` / 様式=型A新規相談（来所） / occurred_at=2026-04-14 → `doc_ptr`: file_id=`1qcg…VEEE` / 様式M / parentId=`0AKMKCDWAYFI4Uk9PVA`(My Drive root)
- `cal_event_ptr`: event_id=`3igomvikr37c9q2iu004uj4vf2` / 様式=型C法律相談 / occurred_at=2025-10-20 → `doc_ptr`: file_id=`14zf…Pc8`（Geminiメモ様式G） ＋ file_id=`17do…XYA`（手打ちメモ様式M）= **1相談:2文書**
- `cal_event_ptr`: event_id=`0vmlpt4r0ajufhb62m4n6mirbb` / 様式=型A新規相談 / occurred_at=2026-02-03 → `doc_ptr`: file_id=`1CW6…htM` / 様式M

**所見**: W-190 の「event_id↔doc_id（添付fileUrl経由）が一次結合・ID完全一致」が実データで再現。様式Mは My Drive ルートに loose 保存、様式G は専用フォルダ集約という親フォルダの割れも再確認。consultation_key 単位の 1相談:N文書 レコードは接続済み2源（Calendar+Docs）だけで構築可能。

---

## 2. 着手可能KPI実測（やること2／集計のみ・PII無）

サンプル期間 2025-06-01〜2026-06-24。各KPIは **件数・中央値・レンジ** のみ。**重要な実測上の制約を先に明示**: Gmail `subject:(相談)` 200+件の大半が **京都弁護士会 Katal メーリングリスト（当番弁護士/区役所法律相談の交替依頼）= 非個別案件ノイズ**で占められ、個別相談の問合せ受信スレッドは少数。W-190 が指摘した「`相談`語が個別案件と公益活動で混在」が Gmail でも成立。よって件数ベースの分母は「明確に個別案件と判別できたスレッド」に限定し、**判別不能分は突合不能として別計上**した（捏造で埋めない）。

| KPI | 取得源 | 観測できた件数(n) | 集計値 | 突合不能・欠落 |
|---|---|---:|---|---|
| KPI-P1-01 初回応答時間（受信→初回自所返信） | Gmail | n=3（個別案件と判別でき、受信→SENT往復が同スレ内で揃ったもの） | 中央値≈ **数時間〜1日**台、レンジ ≈ 約40分〜約20時間（サンプル極小につき指標は参考値） | 電話初回は Dialpad未接続で**全欠落**。Katalノイズ・所内転送のみのスレッドは分子算出不可 |
| KPI-P1-02 相談確定時間（初回接触→Calendar相談予定確定） | Calendar+Gmail | n=0（確定突合成立せず） | **算出不能** | Calendar相談予定（14件）と Gmail受信スレッドを結ぶ**共通IDが無く**、件名・氏名の fuzzy 一致しか手段がない＝§4 の通り確定不可。受信側が電話だと分母自体が欠落 |
| KPI-P1-03 見積送付時間（相談→見積書送付） | Box+Gmail | n=0（確定突合成立せず） | **算出不能** | `subject:(見積)` 22件の多くが MoneyForward自動通知・所内連絡・他事務所/会派メールで、Box見積PDF発行と Gmail送付を**同一案件IDで結べない**。Box見積書は「案件フォルダ配下の `見積書` フォルダ」として存在は確認（§3）だが相談event との接続キー無し |
| KPI-P1-04 契約成立時間（相談→受任通知/契約Gmail近似） | Gmail | n=0（確定突合成立せず） | **算出不能** | `subject:(受任通知)` 22件はほぼ所内連絡/外部一般メールで、クライアント向け構造化受任通知の確実な検出に至らず（§3.S3）。相談event との接続キーも無い |

**KPI実測の到達点**: 単一スレッド内で受信→返信が完結する **KPI-P1-01 のみ部分実測可（n極小・電話分欠落明示）**。KPI-P1-02/03/04 は「相談event（Calendar）」と「メール/文書（Gmail/Box）」を**横断する突合が前提**で、その背骨IDが無いため **dry-run では算出不能**（§4で定量化）。これは設計 W-200 §6.1 の楽観（接続済み4本=今すぐ着手可）に対する**実データでの補正所見**: 単一源完結のKPIは取れるが、源を跨ぐ時間KPIは背骨ID整備を待つ。

---

## 3. 受任 observed 検出（やること3）

| シグナル | 源 | 検出方法 | 検出結果（件数・本文非転載） |
|---|---|---|---|
| **S1 委任契約書/委任状（Box正本・最強）** | Box | `search_files_keyword` で様式名ヒット | **検出可**。`委任契約書` という名の**フォルダ**が案件フォルダ配下に複数存在（例: 案件「53 寒水」「14 K製作所」「46 なぎなた」直下）。`委任状` は **専用フォルダ＋実ファイル多数**（`委任状.doc/.docx/.pdf`、`訴訟委任状` `謄写委任状` `執行委任状` 等の派生様式、テンプレ系 `TS_/TE_委任状.docx`）。**観測＝S1は構造として確かに存在**。ただしキーワード全文検索の totalCount（委任契約書≈18.9万 等）は書籍スキャン等の無関係コーパスを含むノイズで、**件数の母数としては使えない**（フォルダ/様式名の構造ヒットが信号） |
| **S3 受任通知（Gmail）** | Gmail | `subject:(受任通知)` 件名様式ヒット | resultCountEstimate=**22スレッド**。ただし内訳は所内連絡（asai/nakamori/takechi/nishimura 間）・外部事務所メールが大半で、**クライアント宛の構造化「受任通知」と確実に判別できるものは limited**。件名様式が標準化されておらず、S3単独の自動検出精度は低い＝**確定不可・候補どまり**（設計 §3.2 と整合） |
| S2 SF 相談→受任切替（declared正本） | Salesforce | — | **BLOCKED（前提待ち）**。W-110: `dynamic.cases` 0行・変換関係(Consultation→Matter)を結ぶ列も無し。declared側は実体不在 |

**補足（自然発生の受任シグナル痕跡）**: (a) 型D 事務所会議議題行の description に「4/3 受任通知発送（8社）」等の進捗語を観測（=Derived補助観測、確定には使わない／W-190 §4 と整合）。(b) Gmail に Box通知（`noreply@box.com`、本文にBoxパス「2相談/ろ_株式会社Rosnes_法律相談 …請求書（法律相談料）.pdf」）、Chatwork系ToDo通知（「受任案件『…＿事業整理相談』に関連するToDoが作成されました」）が自然発生で流れている。これらは**将来の自動検出の素材**だが、いずれも相談event と結ぶ共通IDを持たない。

**受任 observed 検出の判定**: **S1（Box委任契約書/委任状）= 構造として検出可・存在確認できた**。**S3（Gmail受任通知）= ヒットはするが件名様式非標準で確定不可（候補件数22）**。S2 は前提待ち。→ observed側の素材は接続済みで観測可能だが、**確定（converted）には人間承認（HG-02）が必要**（設計受入基準と整合、AI推定を確定にしない）。

---

## 4. クロス系突合の限界 定量化（やること4）

**目的**: 相談(Calendar) → 見積(Box) → 契約/受任通知(Gmail) → 受任契約書(Box) を **1案件に束ねる**際、共通背骨ID（SF Matter Id / Consultation Id, owner裁定 G-01）が無いと何%が突合でき/できないか。

| 結合区間 | 共通ID（理想） | 現状の接続済みデータに存在するか | 確定突合できた割合 |
|---|---|---|---|
| 相談event ↔ 事件メモDoc | event_id↔doc_id（添付fileUrl） | **あり**（自然発生・ID完全一致） | **約71%**（添付あり10/14）。残29%は添付なしで命名fuzzy救済どまり=確定不可 |
| 相談event ↔ Gmail問合せ/見積/受任通知 | 共通案件ID | **無し**（Calendarに案件ID列なし、Gmailは件名・差出人のみ） | **0%**（確定突合ゼロ）。fuzzy候補のみ |
| Box文書（見積書/委任契約書）↔ 相談event | 共通案件ID | **無し**。Box側は `[ALO-DIR]` 記述に `sf:a0A5h00000…`(SF Object Id) を持つフォルダがある一方、`sf:N/A_ADMIN` / `SF_ID:未設定` のものも混在 | **0%**（相談event側にSF Idが無く接続点が無い） |
| 全区間を1案件IDで貫通 | SF Matter/Consultation Id | **無し**（背骨そのものが不在） | **0%** |

**背骨ID不在の定量的影響**:
- **源内（Calendar↔Docs）突合 = 71% 成立**（自然発生のevent_id↔doc_idのおかげ）。
- **源を跨ぐ（Calendar↔Gmail↔Box）確定突合 = 0%**。手段は件名・氏名の fuzzy 一致のみで、これは **候補件数の提示にとどめ確定にしない**（Do Not 厳守。fabricate_cross_links 禁止）。
- 背骨側の実体: Box の `[ALO-DIR]` メタには SF Object Id を持つ案件フォルダが**部分的に**存在するが、相談 Calendar event 側に対応キーが無く、かつ SF cases ミラーは **0行（W-110 BLOCKED）** で背骨テーブル自体が空。よって「相談→受任を貫く1案件ビュー」は現状**自動生成不能**。

→ **これが「SF-ETL 起動＋背骨ID（Matter/Consultation Id）整備が要る」根拠**。背骨が入れば、源内71%＋源跨ぎ0%が、案件ID解決率に置き換わって上昇する見込み（KPI-P1-08 の本測定が初めて可能になる）。

---

## 5. 判定（やること5）— 自動計測の到達点と前提待ち

### 5.1 接続済み4源で「今、自動計測できる」もの（dry-run で実証）

- **相談記録の構造合成**: consultation_key=event_id の 1相談:N文書 を構築。添付有り率71%・Doc数分布・様式M/G内訳まで集計可（§1）。
- **受任 observed 側の存在検出**: Box の委任契約書/委任状フォルダ・様式（S1）、Gmail受任通知候補（S3, 22件）の検出（§3）。
- **KPI-P1-01 初回応答時間の部分実測**（単一スレッド完結分のみ、n極小・電話欠落明示）（§2）。
- **源内（Calendar↔Docs）紐付け率 = 71%**（KPI-P1-08 の源内部分先行測定）（§4）。

### 5.2 前提待ち（dry-run で算出不能と確認）

| 項目 | ブロッカー | 区分 |
|---|---|---|
| KPI-P1-02/03/04（相談確定/見積送付/契約成立 時間） | 相談event↔Gmail/Box を結ぶ**背骨ID不在**＝確定突合0% | 前提待ち（SF-ETL/背骨ID） |
| クロス系1案件ビュー（相談→見積→契約→受任の貫通） | 同上＋SF cases 0行 | 前提待ち（SF-ETL）= **BLOCKED** |
| KPI-P1-05/06/07（次行動未設定/流入経路不明/失注理由未入力 率） | SF cases 0行・該当列が縮約スキーマに無 | 前提待ち = **BLOCKED**（W-110） |
| 受任 declared側（S2）・declared/observed 乖離検知 | SF cases 0行・変換関係列無 | 前提待ち = **BLOCKED** |
| 相談実施時間の厳密化・議事録要点 | Notta コネクタ未接続 | 前提待ち（未接続） |
| 入金確定・消込 | MoneyForward/銀行通帳未接続（PoC2寄り） | 前提待ち（未接続） |
| KPI-P1-01 の電話初回分 | Dialpad未接続 | 前提待ち（未接続） |

### 5.3 結論

**PoC1 計測設計（W-200）は、接続済み4源で「単一源内の構造合成・存在検出・単一スレッド完結の時間集計」までは実データで実証できる。** しかし設計 §6.1 が「今すぐ着手可能」と置いた時間KPI 4本のうち、**実際に単一源で完結し算出できるのは KPI-P1-01 のみ**で、KPI-P1-02/03/04 は源を跨ぐ突合が前提のため **共通背骨ID不在により dry-run では算出不能**だった。これは設計の楽観に対する実データ補正であり、**「SF-ETL 起動＋背骨ID（Matter/Consultation Id）整備」がクロス系計測の最優先ブロッカー**であることを定量（源跨ぎ確定突合=0%）で裏付けた。Notta（相談実施時間）・MoneyForward（入金）は未接続として前提待ち、SF declared 側は W-110 の BLOCKED 継続。**受任の確定は人間承認**を維持し、observed合成・fuzzy候補を自動確定にしない方針を厳守した。

---

*生成: W-20260624-210 PoC1 実データ dry-run。接続=Calendar/Docs/Gmail/Box（read-only）。書込なし・本文download なし・git操作なし。PII非転載（集計/構造/マスクのみ）。背骨ID無き突合は候補件数どまり（確定にしない）。未接続(Notta/MF/Dialpad)・BLOCKED(SF)は前提待ちと明示。捏造なし。*
