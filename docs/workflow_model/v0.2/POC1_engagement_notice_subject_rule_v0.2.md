---
worker_task_id: W-20260624-220
title: PoC1 受任通知 件名様式 標準化ルール案 v0.2（設計のみ・外部システム非アクセス）
created_at: 2026-06-24
owner: claude-code-worker
source_request: docs/workflow_model/REQUEST_v0.2.md
poc: PoC1
depends_on:
  - W-20260624-210   # dry-run: S3受任通知=候補22件・件名非標準で確定不可
inputs:
  - POC1_dryrun_result_v0.2.md            # W-210 S3現状・ノイズ源(所内連絡/外部一般/MF自動通知)
  - POC1_measurement_design_v0.2.md       # W-200 受任=3シグナル/S3定義/KPI-P1-04
  - ALO_OWNER_GRILL_ANSWERS_v0.1.md       # G-01背骨/G-08案件参照/G-10依頼者支払者/G-11受任合成/G-19推定境界
  - alo_workflow_event_schema_v0.2.json   # engagement_signed 等 event_type
  - ALO_WORKFLOW_CATALOG_v0.2.yaml        # metrics KPI-P1-04 / HG-02
premise: Box=文書正本 / Salesforce=業務制御塔 / 自然発生データ優先 / Raw・Canonical・Derived分離
pii_policy: 実件名・氏名・事件内容・金額は記載しない。件名は型・プレースホルダ・正規表現のみ（規約ルール11）。
status_note: |
  本書は設計作業。外部システム（Gmail/SF/Box等）には一切アクセスしていない。
  既存所見（W-210 dry-run / W-200 設計 / owner裁定 G-xx）のみを根拠に件名標準化を設計する。
  owner裁定(G-xx/D-xx)と worker推論[worker推論]を明示分離。AI推定は確定にしない(G-19)。捏造禁止。
---

# PoC1 受任通知 件名様式 標準化ルール案 v0.2

## 0. 冒頭宣言（固定）

- **これは設計作業＝外部システム非アクセス**。本書執筆で Gmail / Salesforce / Box / Drive / Calendar 等のコネクタは**一切呼んでいない**。根拠は既存成果物（W-210 dry-run §3.S3、W-200 設計 §3、owner裁定 G-xx）のみ。
- **PII非記載宣言（規約ルール11）**: 本書には実件名・氏名・住所・電話・事件内容・金額を一切書かない。件名は**型・プレースホルダ・正規表現パターンのみ**で表す。例示はすべて `<...>` のプレースホルダ。
- **問題の所在（W-210 §3.S3 の確定所見）**: Gmail を `subject:(受任通知)` で検索すると候補 **22スレッド**ヒットするが、内訳は所内連絡（asai/nakamori/takechi/nishimura 間）・外部事務所メール・MF自動通知が大半で、**クライアント宛の構造化「受任通知」を確実に判別できない=S3単独の自動検出は確定不可・候補どまり**。件名様式が標準化されていないことが直接原因。
- **本書の目的**: S3（受任通知発送, W-200 §3.1）を**自動検出可能**にするため、(1)標準件名様式、(2)検出ルール＋ノイズ除外、(3)構造化メタと S1/S2 突合点、(4)移行運用、(5)schema_v0.2 / KPI-P1-04 整合を設計する。**受任の「確定」は引き続き人間承認**（HG-02, G-19）であり、本書は検出（候補生成）の精度を上げるだけで、AI/ルール検出を人間判断に昇格させない。
- 根拠タグ: `G-xx`=owner裁定（ALO_OWNER_GRILL_ANSWERS_v0.1）、`D-xx`=決定ログ、`W-xxx`=worker成果物、`[worker推論]`=本書提案で owner未裁定。

---

## 1. 標準件名様式の定義（やること1）

### 1.1 設計方針

owner裁定: 背骨ID=**SF Matter ID / Consultation ID**（G-01）、依頼者と支払者を**分けて持つ**（G-10）、AI推定は確定にしない（G-19）。これを件名に**機械可読トークン**として埋め込み、自然言語の自由文に依存しない判別を可能にする。トークンは固定接頭辞＋区切り＋鍵括弧付き値で構成し、正規表現で安定抽出できる形にする[worker推論]。

### 1.2 標準件名トークン構成（型・プレースホルダのみ）

```
[受任通知] <案件参照トークン> / <宛先種別トークン>  <自由表題（任意・PII可・抽出対象外）>
```

トークン定義（**実値は使わずプレースホルダ**）:

| トークン | 様式（プレースホルダ） | 値の語彙 | 根拠 |
|---|---|---|---|
| 種別接頭辞 | `[受任通知]` 固定 | 固定文字列（送信種別=正式受任通知の宣言） | [worker推論] / W-200 S3 |
| 案件参照 | `[案件:<SYS>-<ID>]` 例 `[案件:MAT-<id>]` / `[案件:CON-<id>]` | `MAT`=SF Matter Id、`CON`=SF Consultation Id（背骨ID） | G-01 |
| 宛先種別 | `[宛先:<KIND>]` | `client` / `payer` / `third` | G-10（依頼者／支払者分離）/ [worker推論] |
| 自由表題 | 任意。事件名等のPIIを含みうる | 抽出対象外（本文同様に秘匿層） | G-16 / 規約ルール11 |

**完全形の様式例（プレースホルダ）**:

```
[受任通知] [案件:MAT-<matter_id>] [宛先:client] <自由表題>
[受任通知] [案件:CON-<consultation_id>] [宛先:payer] <自由表題>
```

- **背骨ID埋込（G-01）**: 案件参照トークンに `MAT-<id>`（受任後＝Matter確定時）または `CON-<id>`（受任成立前＝Consultation段階で発送する場合）を埋める。これにより件名から直接 schema_v0.2 の `matter_ref` / `consultation_ref`（後述§3, §5）へ解決でき、W-210 §4 で定量化された「源跨ぎ確定突合=0%」を**件名経由で解消する経路**を作る。
- **宛先種別（G-10）**: 保険会社払い等で本人以外が支払う案件があるため、受任通知の宛先が依頼者(client)・支払者(payer)・第三者(third)のいずれかを件名で宣言する。これは KPI 母集団から payer/third 宛を切り分けるために必要。
- **自由表題はPII**: 事件名・当事者名を含みうるため**抽出・記録対象にしない**（秘匿特権保護, G-16）。検出ロジックは接頭辞＋2トークンのみを読む。
- **「実件名は使わない」遵守**: 上記はすべて型。`<matter_id>` 等の実値・実事件名は本書に書かない。

### 1.3 様式の確信度設計

- 標準様式（接頭辞＋案件参照＋宛先種別の3トークン充足）= **確定検出対象**。
- 接頭辞のみ／案件参照欠落 = 旧来非標準扱い＝**候補検出どまり**（§2.4, §4）。

---

## 2. 自動検出ルール（やること2）

### 2.1 標準様式マッチ正規表現（確定区分の前段）

件名文字列に対する抽出パターン[worker推論]（説明用・実装言語非依存。`<id>` 部は実値非記載）:

```
件名接頭辞:    ^\[受任通知\]
案件参照:      \[案件:(?P<sys>MAT|CON)-(?P<id>[A-Za-z0-9._-]+)\]
宛先種別:      \[宛先:(?P<kind>client|payer|third)\]
```

- 3パターンすべてに一致 → 構造化メタ（§3）を充足できる**標準受任通知候補**。
- 接頭辞は一致するが案件参照／宛先種別が欠落 → **非標準（旧来）候補**。

### 2.2 判定条件（確信度区分＝確定／候補）

| 区分 | 充足条件 | provenance basis（schema） | 後段処理 |
|---|---|---|---|
| **確定（検出として確定）** | (a)§2.1 の3トークン全一致 ＋ (b)§2.3 ノイズ除外を全通過 ＋ (c)差出人=自所ドメイン ＋ (d)宛先に外部受信者を含む（client/payer/third 宛の送信である構造） | `observed`（送信観測） | S3 の高confidence observed として §5 の `engagement_signed` 候補に接続。**ただし受任の確定遷移は HG-02 人間承認**（§4.4） |
| **候補（要人間確認）** | 接頭辞一致だが案件参照欠落、または旧来非標準件名で `subject:(受任通知)` ヒット | `observed`（低confidence） | HITL キューへ。人間が案件参照を補完・承認して初めて採用（§4） |

注: 上記は**検出（候補生成）の確信度**であり、**受任成立の確定ではない**。受任の確定は §3シグナル合成＋HG-02 人間承認（G-11/G-19, W-200 §3.2）。AI/ルール検出を人間判断にしない（forbidden: ai_estimate_as_human_decision）。

### 2.3 ノイズ除外条件（W-210 §3.S3 で実観測された3ノイズ源・差出人/宛先/構造で除外）

W-210 が S3 候補22件のノイズ源として挙げた **(i)所内連絡、(ii)外部一般メール、(iii)MF自動通知** を、**本文に依らず差出人・宛先・件名構造のヒューリスティクス（構造のみ）で除外**する[worker推論]:

| ノイズ源 | 除外条件（構造のみ・本文非依存） | 根拠 |
|---|---|---|
| (i) 所内連絡 | **差出人と全受信者がともに自所ドメイン**（asai/nakamori/takechi/nishimura 等、自所メンバー間のみ）＝外部受信者ゼロ → 受任通知の宛先(client/payer/third)が成立しないため除外 | W-210 §3.S3「所内連絡が大半」 |
| (ii) 外部一般メール | **差出人が自所ドメインでない**（外部事務所等からの受信）→ 受任通知は自所が**発送**するものゆえ、受信メールは S3 の発送シグナルにならない。受信側は除外（または別カテゴリ）| W-210 §3.S3「外部事務所メールが大半」 |
| (iii) MF自動通知 | **差出人が MoneyForward 等の自動通知アドレス／no-reply 系**、かつ件名が自動通知様式 → 受任通知でなく会計通知のため除外 | W-210 §2 KPI-P1-04 注「MoneyForward自動通知」/ §3 補足 |

- いずれも**本文（FULL_CONTENT）を読まずに**、差出人ドメイン・受信者構成・件名構造のみで判定（dry-run の read-only/本文非download 方針と整合, W-210 §0）。
- 補助除外: W-210 §3 補足の Box 由来自動通知・Chatwork 系 ToDo 通知も、差出人が自動通知アドレスのため (iii) と同型で除外。

### 2.4 検出フロー（要約）

```
subject:(受任通知) でヒット
  └→ ノイズ除外(§2.3: 所内連絡/外部一般/MF自動通知 を差出人・宛先・構造で除去)
        └→ §2.1 標準3トークン全一致?
              ├ Yes ＋ §2.2(c)(d) 充足 → 確定検出（高confidence observed・S3）
              └ No（接頭辞のみ/旧件名）  → 候補（HITLキューで人間が案件参照補完・承認, §4）
```

---

## 3. 構造化メタ（やること3）

### 3.1 受任通知が持つべき構造化メタ

§2.1 抽出結果から組み立てる（PIIの自由表題は含めない）:

| メタ項目 | 値の語彙 | 取得元 | 根拠 |
|---|---|---|---|
| 案件参照 `case_ref` | `{system: salesforce, object_type: Matter|Consultation, record_id: <id>}` | 件名 `[案件:<SYS>-<id>]` | G-01（背骨ID） |
| 宛先種別 `recipient_kind` | `client` / `payer` / `third` | 件名 `[宛先:<KIND>]` | G-10 |
| 送信種別 `notice_kind` | `formal_engagement_notice`（正式受任通知）/ `non_standard_candidate`（旧来候補） | 接頭辞＋3トークン充足可否 | [worker推論] |
| 送信観測時刻 `sent_at` | メール送信タイムスタンプ（構造メタのみ） | Gmail メタ（本文非参照） | W-200 §3.1 S3 |
| 確信度区分 `detection_confidence` | `confirmed_detection` / `candidate` | §2.2 | [worker推論] |

- これらは schema_v0.2 の `consultation_ref` / `matter_ref`（RecordRef）と `extracted_facts` に格納できる（§5）。**PII（自由表題）は Canonical のPIIアクセス制御層に分離**（G-16）。

### 3.2 S1（委任契約書[Box正本]）・S2（SFステータス）との突合点

W-200 §3 の受任3シグナル（S1=Box委任契約書/委任状=最強・observed、S2=SF相談→受任切替=declared、S3=受任通知発送=observed）に対し、本標準件名は**S3 の精度を上げ、案件参照トークンで S1/S2 と確定突合できる接続点を作る**:

| 突合区間 | 突合キー | 現状（W-210）| 標準化後 |
|---|---|---|---|
| S3受任通知 ↔ S1委任契約書[Box] | 件名 `case_ref` の `<id>` ↔ Box フォルダの SF Object Id（W-210 §4: Box `[ALO-DIR]` に `sf:a0A5h00000…` を持つ案件フォルダが部分的に存在）| 0%（接続キー無し） | 件名に背骨IDが入れば **SF Object Id 経由で Box 案件フォルダと突合可**（背骨ID整備が前提）|
| S3受任通知 ↔ S2 SFステータス | 件名 `case_ref` の `MAT/CON-<id>` ↔ SF Matter/Consultation Id | 0%（W-210 §4 源跨ぎ0%）| 件名IDが SF Id そのものゆえ **declared(S2)と直接突合**（SF-ETL後に稼働）|
| S3 ↔ 相談event(Calendar) | `case_ref` が `CON-<id>` の場合 consultation_ref へ | 0%（fuzzyのみ）| consultation_key↔SF Consultation Id の解決表があれば突合可 |

- **突合点の意義**: W-210 §4 で「源跨ぎ確定突合=0%、手段は件名・氏名 fuzzy のみ」と定量化された限界に対し、**件名へ背骨IDを構造的に埋めること**が S1/S2/S3 を 1案件IDで貫通させる現実的経路。ただし Box側 SF Object Id・SF cases 実体は **BLOCKED(SF)／背骨ID整備待ち**であり、件名標準化は「突合できる**形を用意する**」段階（実突合は SF-ETL 後）。

---

## 4. 移行運用案（やること4）

### 4.1 現行の非標準件名の扱い

- 既存の非標準件名（W-210 の候補22件相当）は**遡及的に件名変更しない**（送信済メールは append-only 原則 G-03 と整合・改変しない）。
- 既存分は §2.2 の**候補（candidate）**として扱い、人間が案件参照を補完・承認したものだけを採用（§4.3）。AI/ルールでは確定にしない（G-19）。

### 4.2 移行期の二重運用（新規＝確定 / 旧＝候補→人間確認）

| 対象 | 件名 | 検出区分 | 処理 |
|---|---|---|---|
| 移行後の新規受任通知 | 標準様式（§1.2, 3トークン）で**発送時に付与** | **確定検出**（§2.2 確定）| 自動で高confidence observed（S3）として記録。受任確定は HG-02 |
| 移行前/移行期の旧件名 | 非標準 | **候補**（§2.2 候補）| HITLキューで人間が案件参照を確認・補完。確認済のみ採用 |

- 移行期は両系統を並走（dual-run）。新規標準分のS3自動検出率が一定に達した後、運用を標準様式へ一本化する[worker推論]。

### 4.3 運用導入手順（発送側のルール化）

1. 受任通知発送テンプレートの件名を §1.2 標準様式に変更（発送者が `[案件:<SYS>-<id>]` `[宛先:<KIND>]` を必ず付す）。背骨ID(SF Matter/Consultation Id)は SF 上で確定済の値を貼る（G-01）。
2. 自由表題（PII）は従来どおり末尾に付してよい（抽出対象外）。
3. 移行期間中は旧件名分を §4.2 候補として HITL レビュー。

### 4.4 受任成立ゲート HG-02（optional）での人間承認接続

- HG-02（受任成立）は owner裁定で **optional**（置けるが必須でない, G-06 / catalog gates HG-02 `required:false`）。だが W-200 受入基準5 は「**受任の確定は人間承認**」を固定（G-19/D-031）。
- 接続: §2 で**確定検出**された標準受任通知は「高confidence の observed S3」だが、これ単独で `converted` へ自動遷移させない。S1/S2 との合成（W-200 §3.2）＋ **HG-02 の人間承認** を経て初めて受任確定（`consultation.converted` / `engagement` 機械）。
- 候補（旧件名）は HITL で `review.status=pending` → 人間が承認/補完して `approved`（schema HumanReview）。**AI/ルール検出を human_decision に昇格させない**（forbidden 厳守）。

---

## 5. 整合（やること5）

### 5.1 schema_v0.2 へのマッピング

標準受任通知の確定検出を、schema_v0.2（alo_workflow_event_schema_v0.2.json）のイベント封筒へマッピング:

| schema フィールド | 値 | 由来 |
|---|---|---|
| `event_type` | **`engagement_signed`**（コアenum, L58）。受任通知発送の S3 観測として記録（受任成立の確定は §5.2 の人間承認遷移）| schema enum / catalog EV-028 |
| `source.source_kind` | `email` | schema SourceRef enum |
| `source.native_id` | Gmail メッセージ/スレッドID（メタのみ） | — |
| `matter_ref` / `consultation_ref` | 件名 `[案件:MAT-<id>]`→`matter_ref`、`[案件:CON-<id>]`→`consultation_ref`（RecordRef: system=salesforce）| §3.1 / G-01 |
| `state_transition` | `{state_machine: engagement|consultation, to_state: ..., basis: observed}`（検出時）。確定遷移は `basis: human_decision`（HG-02承認時）| schema StateTransition（basis enum に observed/declared/human_decision あり）|
| `confidence` | §2.2 区分に対応する数値（確定検出=高、候補=低）| schema confidence(0–1) |
| `review.status` | 候補=`pending` / 人間承認後=`approved`（HG-02）| schema HumanReview |
| `extracted_facts` | `{recipient_kind, notice_kind, detection_confidence}`（§3.1, PII非含）| schema extracted_facts(自由object)|
| `provenance.source_refs` | Gmail メタ参照（必須・最低1件）| schema Provenance |

- **新規 event_type は不要**: `engagement_signed` で受任通知発送（S3観測）を表現でき、x-接頭辞自由型も使わない。受任の「成立確定」は `state_transition.basis=human_decision` ＋ `review.status=approved` で表す（observed のままでは確定にしない, G-19）。

### 5.2 KPI-P1-04（契約成立までの時間）が標準化後に測定可能になる道筋

KPI-P1-04 定義（catalog L1496 / W-200 §2.1）= `engagement_signed_at − proposal_sent_at` の中央値/分布。computable_from=[DS-001, DS-002]、confirm_status=provisional。

W-210 §2 の実測結果: **KPI-P1-04 は n=0・算出不能**。理由は「`subject:(受任通知)` 22件はほぼ所内連絡/外部一般で、クライアント向け構造化受任通知を確実に検出できず（分子の `engagement_signed_at` が取れない）」＋「相談event との接続キー無し」。

本標準化が測定可能化する道筋:

1. **分子の特定（最優先・本書で解消する部分）**: 標準件名（§1.2）＋検出ルール（§2）により、**正式な受任通知発送を確定検出**でき、その `sent_at` が `engagement_signed_at` の observed 近似として安定取得できる。W-210 で「確実に検出できない」とされた分子が、標準化後は確定検出分について算出可能になる。
2. **分母の特定（proposal_sent_at）**: 同一 `case_ref`（件名背骨ID）で `proposal_sent`（提案送付, EV-023）と紐付け。提案送付メールにも同様の案件参照トークンを付せば（横展開）、`proposal_sent_at` も同案件IDで突合でき、`engagement_signed_at − proposal_sent_at` が**案件単位で算出可能**になる。
3. **段階的測定可能性**:
   - 標準化新規分のみ → KPI-P1-04 を**確定検出分について算出可能**（移行期の部分測定, §4.2）。
   - 旧件名分 → 候補どまりで人間補完後に算入（捏造で埋めない）。
   - declared 正本（SF受任日, W-200 §2.1 注「確定はSF切替日」）→ **BLOCKED(SF)／SF-ETL 後**。observed(本書) と declared(SF) の突合は §3.2 の通り背骨ID整備待ち。
4. **結論**: 本書の件名標準化は KPI-P1-04 の **分子(engagement_signed_at)を「検出不能」から「確定検出分は observed で算出可能」に引き上げる**。これにより、W-200 §6.1 が「今すぐ着手可」と置きながら W-210 で n=0 だった KPI-P1-04 が、**標準様式運用開始後の新規分について段階的に測定可能**となる。確定値（SF declared 突合）は SF-ETL 後。

---

## 6. owner裁定 / worker推論 / 前提待ち の分離

- **owner裁定（確定・根拠付）**: 背骨ID=SF Matter/Consultation Id（G-01）、依頼者/支払者分離（G-10）、受任=複数シグナル合成・S1=Box最強（G-11）、AI推定は人間承認で確定（G-19/D-031）、3層分離（G-16）、HG-02=optional（G-06）、event_type に `engagement_signed` 存在（schema）、KPI-P1-04 定義（catalog metrics）。
- **worker推論（本書提案・owner未裁定＝承認で確定化すべき候補）**: 件名トークン構成（§1.2 接頭辞・案件参照・宛先種別の具体様式）、検出正規表現（§2.1）、確信度区分の閾値（§2.2）、ノイズ除外ヒューリスティクスの具体条件（§2.3）、移行期 dual-run の一本化判断基準（§4.2）、提案送付への案件参照トークン横展開（§5.2-2）。
- **前提待ち / BLOCKED**: S1↔S3・S2↔S3 の**実突合**は Box側 SF Object Id 整備・SF cases 実体（W-110 cases 0行=BLOCKED）・背骨ID整備待ち。KPI-P1-04 の declared 確定値（SF受任日）は SF-ETL 後。旧件名の遡及補完は人間レビュー工数に依存。

---

## 7. 残課題

1. **owner裁定要**: 件名トークンの最終様式（接頭辞文字列・区切り・トークン名）と確信度閾値（§2.2）の確定。
2. **背骨ID整備（最優先ブロッカー, W-210 §4 と同根）**: 件名にSF Matter/Consultation Id を埋めるには、発送時点で SF 側 ID が確定・参照可能である必要。SF-ETL 起動が前提。
3. **横展開**: 同方式を `proposal_sent`（見積/契約案送付）・他対外メールにも適用すれば、KPI-P1-03/04 の分子分母が件名IDで揃う（[worker推論]・要設計）。
4. **検出精度の実測**: 本書は設計のみ（外部非アクセス）。標準化導入後に確定/候補の検出率・誤除外率を実データで検証する別作業が必要（捏造で埋めない）。
5. **宛先種別の運用**: payer/third 宛受任通知の発生頻度・KPI母集団からの扱い（G-10 起因）を運用で確定。

---

*生成: W-20260624-220 受任通知件名標準化ルール案。設計のみ＝外部システム非アクセス（Gmail/SF/Box等を一切呼んでいない）。PII（実件名）非記載＝プレースホルダ・正規表現・型のみ（規約ルール11）。owner裁定(G-xx)/worker推論を分離。AI/ルール検出を人間判断に昇格させない（受任確定は HG-02 人間承認, G-19）。git操作なし。成果物は v0.2 配下のみ。捏造なし。*
