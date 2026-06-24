---
worker_task_id: W-20260624-160
title: ALO WORKFLOW GAP & PoC PLAN v0.2
created_at: 2026-06-24
owner: claude-code-worker
source_request: docs/workflow_model/REQUEST_v0.2.md (§5-6 / §6 が PoC 要件の正)
premise: Box=文書正本 / Salesforce=業務制御塔 / 自然発生データ優先 / Raw・Canonical・Derived分離
inputs:
  - ALO_WORKFLOW_CURRENT_STATE_v0.2.md (Phase0 構造インベントリ)
  - PHASE1_triage_summary_v0.2.md / PHASE1_question_triage_v0.2.csv (Phase1 245問トリアージ)
  - PHASE2_box_document_lifecycle_v0.2.md (Phase2 Box実査・read-only)
  - ALO_WORKFLOW_EVIDENCE_LEDGER_v0.2.jsonl (Phase2 Gmail 3トレース)
  - ALO_OWNER_GRILL_PACK_v0.1.md (浅井先生裁定パック G-01〜G-20 + §2後続キュー)
  - alo_workflow_event_schema_v0.2.json (イベント封筒スキーマ)
  - W-20260624-110_RESULT.md (SF/LEALA実査 = WORKER_BLOCKED)
pii_policy: 個人名・住所・電話・事件内容・具体的金額は記載しない
status_note: |
  SF/LEALA/Dialpad/Notta/MoneyForward は本環境に接続コネクタが無くBLOCKED(W-110)。
  本書はその前提で「現状観測できた範囲」と「観測できないギャップ」を分離して記述する。
  仮説・観測(confidence付)・人間判断・未確認を混同しない。捏造しない。
---

# ALO 業務フロー ギャップ分析 & PoC 計画 v0.2

前提方針: **Box=文書正本 / Salesforce=業務制御塔 / 自然発生データ優先 / Raw・Canonical・Derived分離**（REQUEST_v0.2 §0）。

本書は v0.2 の done 成果物（Phase0 構造インベントリ / Phase1 トリアージ / Phase2 Box実査・Gmail 3トレース / Grill Pack）を統合し、(1) 目標モデルと現状観測とのギャップ、(2) REQUEST §6 に従った PoC1（相談→受任）/ PoC2（解決→終結）の対象・KPI・close gate、(3) 依存とブロッカー、(4) 次アクションを定義する。

> 読み方の前提: 本書の「現状」は **実査できた範囲の観測**である。SF/LEALA は本環境に接続が無く実査未了（W-110 BLOCKED）であり、SF 依存の記述はすべて `SF実査待ち` と明示する。観測値には confidence、設計案には `仮説/提案・未決` を付し、人間裁定が要る論点は Grill Pack の G-xx を参照する。

---

## 0. 目標モデル（到達目標）の要約

REQUEST §1 の到達目標 = 各業務を **12分解単位**へ分解し、相談流入→受任→事件処理→納品→請求→精算→原本返却→終了報告→既済化を一続きで追跡可能にする。

- **12分解単位**: 1 Trigger / 2 Actor / 3 Input / 4 Action / 5 Decision / 6 Output / 7 State transition / 8 Work item / 9 Evidence / 10 Exception / 11 Finance / 12 Provenance。
- **状態機械**: Phase0 06シートは **5本**（Consultation17 / Matter11 / WorkItem6 / Document10 / Finance9 = 53状態）を実定義。一方 REQUEST・D-005・D-012 は Delivery / Deadline を含む **7本**を前提に言及。5本か7本かは未決（Grill G-05）。本書では「目標=7本（Delivery/Deadline独立化）を推奨案、確定は浅井裁定」として扱う。
- **provenance 分離**: 観測(observed) / AI推定(confidence付) / 人間判断(declared) の3分離。append-only・無効化イベント＋新確定リンク（D-003/D-010）。
- **HITL（人間必須ゲート）**: コンフリ / 受任成立 / 重要方針 / 対外成果物最終送付 / 請求確定 / 預り金・実費精算 / 終結 の7点（D-007 / Grill G-06）。

---

## 1. ギャップ分析（目標モデル vs 現状観測）

### 1.1 データ源別の実査到達状況（最重要の前提）

| データ源 | 目標での役割 | 実査状況 | ギャップの性質 |
|---|---|---|---|
| **Salesforce / LEALA** | 業務制御塔（案件ID・状態・担当・次行動・期限・人間承認の正本） | **未実査 BLOCKED**（W-110: 本環境にコネクタ無し） | 制御塔そのものが未観測。脊椎ID・状態・入力率・乖離・連携が全て `SF実査待ち`。**PoC1/PoC2 の中核を止める最大ブロッカー** |
| **Box** | 文書正本（版・最終成果物） | **実査済**（Phase2 read-only メタデータ先行・12対象） | 文書の所在・版・フォルダ構造は観測可。だが状態は「フォルダ配置・命名動作語・docx/pdfペア・version」の**弱いシグナル**に埋め込み。到達/受理/入金は△〜× |
| **Gmail** | 進行を示す観測ソース | **実査済**（Phase2 3トレース・匿名抽出） | 受任到達/失注/解決→第三者支払者請求→精算 の3パターンを event 封筒で実証。だが due_at と completion_evidence が全件 null、occurred_at に推定混入 |
| **Dialpad（通話）** | 観測ソース | **接続無し**（W-110 で未接続を確定） | 通話・SMS・録音・transcript イベントが Ledger に未記録。受付・相談・与信連絡の重要区間が欠落 |
| **Notta（文字起こし）** | 観測ソース | **接続無し** | 会議・通話の文字起こしイベント欠落。相談実施(WF-07)・内部会議の要点抽出ができない |
| **MoneyForward（会計）** | 観測ソース（請求・入金） | **未着手/接続無し** | 入金消込・銀行明細が未観測。Finance 状態機械の paid/reconciled の確定元が空白 |
| Google Calendar / Meet | 観測ソース（日程） | 接続あり（本タスクでは未実査） | 日程確定検知は技術的に可だが本 v0.2 では未抽出 |

→ **構造的ギャップ**: 自然発生データ優先の方針に対し、自然発生データの主要源（SF制御塔・Dialpad・Notta・MF）の **4源が未観測/未接続**。観測できたのは Box（文書）と Gmail（メール）の2源のみ。よって現状は「文書とメールから業務を推認」している段階で、**制御塔状態・通話・会計の3本柱が欠落**している。

### 1.2 12分解単位ごとのギャップ

| # | 分解単位 | 現状観測で埋まる度合い | 主なギャップ（不足/未確認） |
|---|---|---|---|
| 1 Trigger | △ | Gmail でメール起点は観測可。電話起点(Dialpad)・SF通知起点が欠落。流入経路の構造化は未確定（G-12） |
| 2 Actor | ○〜△ | Gmail から actor_role 抽出可（事務局/弁護士/依頼候補/保険会社）。SF担当者マスタ未観測 |
| 3 Input | △ | Box 文書・メール添付は観測可。相談票単票の正本形態は未確認（G-14, Box-U1） |
| 4 Action | △ | メール動作（送付/返送）は観測可。内部作業セッションは欠落（Dialpad/Notta無し） |
| 5 Decision | △ | proposal_accepted / no_engagement 等は declared で記録可。だが「人間判断点」の制度化は未（G-06/G-19） |
| 6 Output | ○（Box） | 文書成果物は Box で観測可。docx⇔pdf で確定/配布版を判別可 |
| 7 State transition | △ | Gmail トレースに state_transition + basis(observed/declared) 付与済。**だが正本状態=SF制御塔が未観測。declared/observed 分離(G-04)の declared 側が空白** |
| 8 Work item | × | WorkItem は記録できるが **due_at と completion_evidence_refs が全トレース null**。SF の次行動・期限フィールド未観測（G-08） |
| 9 Evidence | ○（Box/Gmail） | source_native_id・thread_id・file_id で証跡同定可。content_hash は未取得 |
| 10 Exception | △ | 失注(trace2)・精算途中(trace3)は捕捉。例外運用（緊急受任・連絡不能等）は中森/浅井聴取要 |
| 11 Finance | △ | client/payer 分離を Gmail で**強く実証**（G-10）。だが金額・入金消込は MF/SF未観測で空白 |
| 12 Provenance | ○ | ingest_run_id・extractor_version・source_refs・confidence・basis を封筒に実装済。append-only/invalidates も構造あり |

### 1.3 状態機械・ゲート・層分離のギャップ

- **状態機械の本数不整合**（Phase0 検出 / G-05）: 実定義5本 vs 言及7本。Delivery（送付→到達→受理）は現状 Document(sent/filed/accepted)＋Finance に分散、Deadline は Matter(waiting_court) に内包。Box実査でも「送付→到達→受理」は日付＋動作語で Document機械では△止まり。**独立2本へ昇格するかは浅井裁定（G-05）**。
- **declared/observed 二層化の片肺**（G-04）: Ledger は basis を付与済だが、declared（人間宣言状態）の正本である **SF が未観測**のため、乖離検知（observed が declared に先行 等）は現状実装できない。
- **Raw/Canonical/Derived の境界未明文**（G-16）: Box実査で `_alo_case_summary.md`/`_alo_dir.json`(Derived) が Raw と共存する**萌芽**を確認。だが3層の境界定義・`old`廃版（G-17）・`~BROMIUM`セキュア層（G-18）の扱いは未確定。
- **HITLゲート未確定**（G-06）: 7ゲート案は REQUEST と整合するが、承認者ロール・例外（緊急受任等）は浅井裁定待ち。

### 1.4 質問トリアージから見たギャップ（Phase1）

- 245問中 **未回答245**（実査・聴取未着手）。`回答済・証跡あり` は P0 で **0件**（捏造しない方針）。
- P0 58問の内訳: 暫定回答・追加検証要 42 / 浅井聴取必須 11 / 中森聴取必須 3 / 外部SE確認必須 2。
- 区分別: 実データから回答可能 133（うち多くが **SF実査待ち**）/ 実物サンプル確認30（Box・一部実査済）/ 設計判断51（owner裁定）/ 担当者聴取28（運用実態、コンフリ・例外）。
- → **ギャップの大半は「SF実査の解消」と「owner裁定（Grill 20問）」の2つに収斂**する。

---

## 2. PoC 1 — 相談→受任

### 2.1 対象フロー

`問合せ受信 → 本人関係確認 → コンフリクト確認 → 受入可否トリアージ → 日程調整 → 事前資料受領 → 相談実施 → 追加質問 → 見積 → 契約案送付 → 最終確認 → 受任`（WF-01〜WF-12 / REQUEST §6 PoC1）。

- happy path 教師データ: Gmail trace1（相談→契約書案送付→合意→受任成立→第三者支払者請求）。
- sad path 教師データ: Gmail trace2（スポット相談 → 受任非到達／失注）。

### 2.2 測定 KPI（REQUEST §6 準拠）

| KPI | 定義 | 観測元（理想 / 現状） | 現状測定可否 |
|---|---|---|---|
| 初回応答までの時間 | 問合せ受信→最初の応答 | 理想: SF受付日時＋Gmail/Dialpad / 現状: Gmail のみ | △（電話初回はDialpad無しで欠落） |
| 相談確定までの時間 | 受信→相談日時確定 | 理想: SF相談日＋Calendar / 現状: 未抽出 | × → SF/Calendar実査要 |
| 見積送付までの時間 | 受任提案→見積送付 | Box見積PDF日付＋Gmail送付 | △（Box発行日は観測可） |
| 契約成立までの時間 | 見積送付→受任成立 | Gmail（trace1 で 0102→0104 を実証）＋SF受任日 | △（Gmailで近似可、確定はSF） |
| 次行動未設定率 | WorkItem に owner/due 欠落の割合 | 理想: SF次行動・期限 / 現状: Ledger で due_at 全件null | × → SF実査で現状入力率測定要 |
| 流入経路不明率 | Consultation で流入経路が空/不明の割合 | 理想: SF流入経路フィールド | × → SF実査＋必須化裁定(G-12) |
| 失注理由未入力率 | 失注時に失注理由が空の割合 | 理想: SF失注理由フィールド | × → SF実査＋必須化裁定(G-12)。trace2 で「失注 vs 相談完了」区分が未確定 |
| イベント未紐付け率 | 脊椎ID(matter_ref)に紐づかないイベント割合 | 全イベントの matter_ref 解決率 | △（Gmailは仮ID `matter:trace1`、本番はSF脊椎IDに解決要） |

### 2.3 受入基準（PoC1）

- **P0遷移は全件 source ref 付き**: Consultation 状態機械の各遷移（inquiry_received → … → engagement_signed）が `source.native_id` または `decision.evidence_refs` を持つこと（Ledger は実装済の形）。
- **曖昧は HITL へ**: confidence が閾値未満／basis=observed のみの重大遷移（受任成立・コンフリ pass）は `review.status=pending` で人間承認に回し、自動確定しない（G-06/G-19）。
- **open 相談の owner・due 欠落を可視化**: status=open/waiting の WorkItem で owner または due_at が欠落するものを一覧化（現状 trace1〜2 全 WI が due_at null = 可視化対象）。

### 2.4 前提（PoC1 を成立させる解消事項）

- **SF実査（W-110）の解消が必須**。脊椎ID（Consultation.Id/Matter.Id, G-01）、流入経路・失注理由の現行入力率（G-12）、次行動・期限フィールド（G-08）、受付/相談/受任日の粒度が SF未観測のままでは、KPI の半数（相談確定/次行動未設定率/流入経路不明率/失注理由未入力率）が測定不能。
- Dialpad 接続が無いと「電話初回応答」が欠落するため、初回応答時間は当面 Gmail 起点に限定する旨を明示。

---

## 3. PoC 2 — 解決→終結

### 3.1 対象フロー

`解決 → 履行確認 → 最終報酬計算 → 請求 → 入金確認 → 預り金・実費精算 → 原本返却 → 成果物納品 → 終了報告 → 既済化`（WF-19〜WF-22 / REQUEST §6 PoC2）。

- 教師データ: Gmail trace3（自賠責/任意保険が第三者支払者・解決→入金見込み→入金受領→立替金差引→精算判断→診断書/振込先確認）。trace3 は **精算途中で gate 未通過**の実例（diagnosis/口座待ち, 終了報告書送付は未確認）。

### 3.2 close gate（10項目）と確認データ源

各項目を「**どのデータ源で確認するか**」付きで列挙（REQUEST §6 / D-014 / Grill G-09）。

| # | close gate 項目 | 確認データ源（理想） | 現状観測可否 |
|---|---|---|---|
| 1 | 未完 WorkItem 無 | SF（Task/次行動）＋ event 台帳の open/waiting 集計 | × SF未観測。Ledger では trace3 に open/waiting/in_progress の WI が残存 |
| 2 | 残期限無 | SF Deadline（正本, G-20）＋ Calendar 突合 | × SF Deadline 未観測 |
| 3 | 最終請求確定 | Box 請求書PDF（発行）＋ SF Billing/Invoice ＋ 請求書発行管理簿(v5) | △ Box発行は観測可、確定はSF/台帳 |
| 4 | 未収扱い確定 | MF会計（入金消込）＋ SF | × MF/SF未観測 |
| 5 | 預り金・実費精算済 | SF Deposit/Expense ＋ MF ＋ Gmail精算連絡 | △ Gmailで精算判断点は観測（trace3 0304）、確定は SF/MF |
| 6 | 預り原本 返却済 or 保管理由 | Box `4 預かり資料` フォルダ＋返却受領書(ひな形v5) | ○ Box で受領→保管→返却のライフサイクル観測可（Phase2 (8)） |
| 7 | 最終成果物送付済 | Box `1-2 通信（送）`＋送付書＋追跡番号記録表(v8) | △ Box で「送った」まで、到達は追跡表で間接 |
| 8 | 終了報告送付済 | Box 業務終了報告書（**標準ひな形の有無が未確認 G-15**）＋ Gmail送付 | × 標準ひな形未確認。終了は既済フォルダ移動で弱表現 |
| 9 | Box 正本確定 | Box file_id+version_id（G-02）＋ 既済フォルダ配置 | ○ 既済配置は明確、正本ID紐付けはSF連携(G-01)に依存 |
| 10 | SF終了状態が人間承認済 | SF（declared 終了状態 + 承認者）= 人間必須ゲート(G-06) | × SF未観測。HITL承認の正本がSF側で空白 |

### 3.3 受入基準（PoC2）

- 10項目すべてに「確認データ源」が割り当たり、各項目が pass/未通過を判定できること（上表で割当済）。
- 既済化（既済フォルダ移動）は **10 gate 通過の結果**として行い、移動が先行しないこと（Box実査: 現状は移動で終了を弱表現 → 制御塔側 gate へ昇格）。
- 終結は **人間必須ゲート**（G-06 の7点に「終結」含む）。SF終了状態の declared 承認なしに自動既済化しない。

### 3.4 前提（PoC2 を成立させる解消事項）

- **SF実査（W-110）解消が必須**: 10 gate のうち 6項目（#1,#2,#4,#5(確定),#10、#3の確定）が SF/MF 未観測で判定不能。
- **業務終了報告書の標準ひな形（G-15, Box-U2）の確定**が #8 の前提。
- **MoneyForward 接続**が #4 未収・#5 精算の入金消込確定の前提。

---

## 4. 依存とブロッカー

### 4.1 W-110（SF/LEALA実査）BLOCKED が止めるもの

W-110 RESULT = `WORKER_BLOCKED`（本環境に SF/LEALA/Dialpad/Notta/MF コネクタ無し）。これが PoC に与える影響:

- **PoC1 で止まるもの**: 脊椎ID解決（G-01）、流入経路・失注理由の現行入力率と必須化判断（G-12）、次行動・期限フィールドの現状（G-08）、受付/相談/受任日の粒度。→ KPI 8本中 **4本（相談確定/次行動未設定率/流入経路不明率/失注理由未入力率）が測定不能**、2本が△。
- **PoC2 で止まるもの**: close gate 10項目中 **6項目（#1未完WI/#2残期限/#4未収/#5精算確定/#10 SF承認、#3確定）が判定不能**。終結の HITL 承認の正本（SF declared 状態）が空白。
- **両 PoC 共通**: declared/observed 分離（G-04）の declared 側が空白 → 乖離検知が実装できない。Dialpad/Notta 欠落で通話・会議イベントが Ledger から欠落（別実査票要）。

→ 結論: **SF実査の解消は PoC1/PoC2 双方の必要条件**。Box+Gmail だけでは「文書とメールからの推認」に留まり、制御塔状態・期限・入金消込・人間承認の正本が取れない。

### 4.2 Grill 20問のうち PoC 設計を左右するもの

| Grill | 論点 | 左右する PoC 設計 |
|---|---|---|
| G-01 脊椎ID | matter_ref 主キー定義 | PoC1/2 全イベントの紐付け・イベント未紐付け率KPI |
| G-04 declared/observed | 状態の二層化 | PoC1/2 の状態遷移・乖離KPI |
| G-05 状態機械5/7本 | Delivery/Deadline 独立化 | PoC2 close gate #2残期限・#7成果物送付の構成 |
| G-06 人間必須ゲート | 7ゲートと承認者 | PoC1 受任成立 / PoC2 終結の HITL 受入基準 |
| G-08 WorkItem必須項目 | owner/due/evidence 必須化 | PoC1「次行動未設定率」/ PoC2 #1未完WI |
| G-09 close gate構成 | 10条件の確定 | PoC2 全体（本書 §3.2 の10項目そのもの） |
| G-10 client/payer分離 | finance スキーマ | PoC2 請求・入金・精算（trace1/3で実証） |
| G-12 流入経路/失注理由 | 必須化 | PoC1「流入経路不明率/失注理由未入力率」KPI |
| G-14 相談票正本形態 | SF正本 vs Box単票 | PoC1 入力源・Consultationスキーマ |
| G-15 終了報告書ひな形 | 標準化と close gate必須 | PoC2 close gate #8 |
| G-16/G-17/G-18 層分離 | Raw/Canonical/Derived・old・BROMIUM | PoC2 #9 Box正本確定の判定ロジック |
| G-20 期限正本 | SF Deadline 正本 | PoC2 #2残期限・懈怠防止 |

→ 20問中 **12問が PoC1/2 の対象・KPI・close gate を直接左右**する。残り（G-02,03,07,11,13,19 ほか）も間接的に関与。

---

## 5. 次アクション（順路）

推測で埋めず、確認手段の順に並べる。

1. **グリル回答**（浅井先生 §1 の20問 / 中森 §2-C / 外部SE §2-D）— 特に PoC を左右する G-01,04,05,06,08,09,10,12,14,15,20 を優先裁定。
2. **SF実査の解消（W-110 BLOCKED 解除）**— (a) read-only 接続付与 / (b) 外部SE が実査結果を `PHASE2_salesforce_survey_v0.2.md` 相当で持込 / (c) 匿名化 CSV/メタデータ・エクスポート添付、のいずれか。併せて Dialpad/Notta/MF の接続（別実査票）。
3. **W-130（実査台帳 v0.2 反映）**— Phase2 所見＋SF実査結果を 9シートへ反映（フロー確認状態・質問回答・主キー/結合キー・状態遷移7機械・SF対応4区分・決定ログ追記）。※W-130 は depends_on=W-110/111/112 のため SF実査解消後に着手可。
4. **再 catalog（CATALOG_v0.2.yaml）**— states/transitions/close gate/KPI を裁定結果で確定し、PoC1/2 を機械可読に固定。
5. **PoC 計測の実装**— SF＋Box＋Gmail（＋Calendar/MF/Dialpad/Notta が接続後）から KPI・close gate を自動集計。

---

## 6. 仮説 / 観測 / 人間判断 / 未確認 の分離（混同防止）

- **観測（実査済・confidence付）**: Box 12対象のライフサイクル所見（Phase2）、Gmail 3トレースの event（trace1 受任到達/trace2 失注/trace3 精算途中）。client/payer 分離は trace1/3 で強く実証。
- **仮説 / 提案・未決**: 状態機械7本化（D-005/G-05）、close gate 10項目（D-014/G-09）、HITL 7ゲート（D-007/G-06）、KPI 定義は REQUEST §6 由来だが運用閾値は未確定。
- **人間判断（裁定待ち）**: Grill §1 の20問。AI推定を確定判断にしない（G-19）。
- **未確認 / BLOCKED**: SF/LEALA 全項目（W-110）、Dialpad/Notta/MF イベント、相談票単票形態（Box-U1/G-14）、終了報告書ひな形（Box-U2/G-15）、`~BROMIUM`（Box-U4/G-18）、入金消込の正本（Box-U3/G-11）。

*生成: v0.2 統合（GAP & PoC PLAN）。本番 SF/Box 非アクセス・書込なし。PII 不記載。観測/仮説/人間判断/未確認を分離。捏造なし。*
