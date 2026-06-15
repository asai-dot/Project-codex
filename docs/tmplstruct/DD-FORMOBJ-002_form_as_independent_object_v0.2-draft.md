# DD-FORMOBJ-002 v0.2: 書式オブジェクト ── 独立 first-class オブジェクト設計資料

> **id**: DD-FORMOBJ-002 / **version**: v0.2-draft / **supersedes**: v0.1-draft（監査参照点として凍結）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / date: 2026-06-15
> **gate**: 設計のみ（DDL・DB書込み・single-witnessからのcanonical発番・accepted化なし）
> **改訂理由**: GPT監査 `DDFORMOBJ2_PASS_WITH_NOTES`（2026-06-15）の必須修正5点＋ゲート8件を反映。owner ratify 済。
> **位置づけ**: **書式オブジェクトの一次設計資料**。法令・判例・文献・雑誌・語彙・手続き と並ぶ独立オブジェクト「書式」の定義。001系（FORMOBJ-001 / INTEGRATION / registry）は本DDの下位 machinery（witness読取・型付け・設計知識）として再解釈する。

---

## 0. 中核（監査で確定）
**書式は文献や手続きの下位産物ではなく、独立した first-class オブジェクト。** 親を持たず、関係エッジだけで他オブジェクトに接続する。
この訂正を入れずに001系を進めると「文献witnessの読取成果がそのまま書式canonicalに見え」、版違い・別記載例・同一タイトル異版の誤接続を再発させる（＝本日の事故の構造的原因）。

## 1. オブジェクト宇宙（7つの別個独立 first-class）
```
法令 ・ 判例 ・ 文献 ・ 雑誌 ・ 語彙 ・ 手続き ・ 書式
```
- 書式の本質 = **人の行為・意思表示・記録・提出・通知・合意を文書化する応用オブジェクト**。文献はその観測点の一つにすぎない。
- 手続きに従属させない：訴状・申立書・登記申請書は `serves`/`submitted_under` で手続きに繋ぐ。売買・賃貸借・業務委託・議事録・通知・社内記録は**手続きと無関係に存在**するため手続きFK配下に入れない。
- 「応用」＝基底から**自動導出される意味ではない**。実務慣行・業界慣行・相手方雛形も独立した観測源（監査should）。

## 2. ★4層分離（監査必須#1）
v0.1 の `form_object` 一箱は広すぎた。次の4層を分ける。
| 層 | 定義 | 例 |
|---|---|---|
| **form_object** | 抽象書式 | 株式会社定款 / 売買契約書 / 取締役会議事録 / 登記申請書 |
| **form_variant** | 当事者ポジション・用途・法域・時期・業界・リスク選好による型違い | 買主有利版 / 売主有利版 / 簡易版 / 詳細版 |
| **form_witness** | 文献・Web・実務生成物の**観測例**（版・ページに現れた実物） | 〔全訂版〕p170の製造委託書式 / 記載例集の条項例 / 裁判所HPの様式 |
| **filled_instance** | 実案件で値が埋まった文書 | 個別契約書・申請書・議事録の実物（**業務データ＝知識層から分離**, §6） |

- 同一性は form_object に宿る。variant は同一 form_object 下の型。witness は variant/object の**観測**であって所有しない。
- `gate_form_layer_split`：4層を混在させない。

## 3. 書式オブジェクトの同一性（独立・不変＋判定軸）
```text
form_object
  form_uid = alo:form:{uuidv7}      # 不透明・不変。title/ISBN/item/toc/手続き名/vendor id から導出しない
  identity_status                   # provisional | candidate | resolved | split_required | deprecated_alias
  # ★同一性判定軸(監査必須#3)。「何の営みを記録するか」だけでは粗い
  recorded_act                      # 何の行為・意思表示・提出・記録か
  legal_function                    # 何の法的/実務効果を担うか
  document_role                     # 契約書 | 条項セット | 申請書 | 通知書 | 議事録 | 内部記録 ...
  practice_domain                   # 売買 | 賃貸借 | 業務委託 | 会社 | 労働 | 登記 | 訴訟 | 行政手続 ...
  party_posture                     # 売主側 | 買主側 | 貸主側 | 借主側 | 会社側 | 労働者側 | 中立 ...
  forum                             # 裁判所 | 法務局 | 行政庁 | 私人間 | 社内 ...
  temporal_applicability            # 有効な法令・実務時点
```
これがないと「売買契約書」で 事業譲渡/動産/不動産/買主有利/売主有利/反社込み版 が過度に同一視される。
- `gate_form_id_opaque`：属性をIDに焼かない。

## 4. 関係エッジ（従属でなく関係・source型付き）
各エッジは `provenance_family / confidence / verified_status` を持つ。
| エッジ | 先 | 意味 |
|---|---|---|
| `witnessed_in` | 文献(biblio_item+toc+page) / 裁判所HP / 法務局HP / 実務生成物 | 観測点（多源・§5の同定項目） |
| `serves` / `submitted_under` | 手続き | 提出書式のとき**だけ**の任意エッジ |
| 役割エッジ（非手続書式向け・監査should） | — | `records_act` / `documents_transaction` / `memorializes_agreement` / `notifies` / `authorizes` / `certifies` |
| `required_items_grounded_in` | 法令・規則・行政要求 | 法定記載事項（§7） |
| `advised_by` | 文献・解説・実務 | 任意的記載事項・押し引き（§7） |
| `typed_by` | 語彙（term registry） | clause/slot 型付け |
| `cites` / `effect_from` | 判例 | 条項の効果・有効性 |
- biblio_item は `witnessed_in` の一本。語彙は `typed_by` の一本。法令は `required_items_grounded_in` の一本。**どれも親ではない。**

## 5. witness の同定項目（監査必須#5・本日事故の再発防止）
`form_witness` は次を持つ：
```text
form_witness
  source_type        # biblio_item | web | court | registry | internal_generated | uploaded_sample
  source_identifier  # biblio_item_id / URL / Box file id / citation
  edition_or_version # ★版（タイトル一致のみ禁止）
  page_span / toc_node / section_path
  extraction_method / extracted_at / extractor_version
  content_hash / fingerprint
  source_confidence
  provenance_family  # ★同一供給元の再配信を独立witnessに数えないため必須
```
- `gate_witness_edition_verified`：witnessリンクは版/fingerprint検証必須。
- `gate_witness_multi_source`：単一witness真実視・同一provenance_familyの多数決禁止。

## 6. 機械可読な内容構造＋記載事項の二層
```jsonc
clause {
  no, title, witness_canonical_text,   // ★001の"canonical"は witness読取の正準化に降格(監査必須#2)
  function_ref → 語彙 term,
  slots: [{id, type, required}],
  obligations|rights,
  requisite_class,                     // §7
  requisite_grounding,                 // §7
  design_options: [{ axis_type, choice, effect, favors_role, tightness,
                     source_type, authority_weight, legal_basis }]  // ★出所と権威を型付け(監査should)
}
```

## 7. ★記載事項の細分（監査必須#4）
**必須(mandatory)の接地源を「法令」だけに狭めない**：
```text
requisite_class:
  statute_required               # 法令上必須
  regulation_or_rule_required    # 省令・規則・通達・登記実務・裁判所規則で必須/実質必須
  forum_required                 # 提出先（裁判所・法務局・行政庁）要求
  validity_required              # 欠けると効力・有効性に影響
  enforceability_required        # 欠けると執行・登記・届出・主張立証に影響
  advisable                      # 文献・実務上推奨
  optional_design                # 依頼者ポジション次第の設計選択
```
**欠落警告も一律「瑕疵」にしない**：
```text
defect_kind:
  invalidity | rejection_by_forum | registration_defect | evidentiary_weakness | risk_warning
```
- `gate_mandatory_grounded`：mandatory系は法令/forum/規則に接地（観測のみ不可）。
- `gate_advisory_source_typed`：advisable/design は source_type＋authority/provenance 必須。
- `required_items_grounded_in` は条文 version / effective_date / jurisdiction / forum rule を持つ（監査should）。

## 8. filled_instance の分離（監査必須#5）
- 実案件で埋めた契約書・申請書・議事録は**機微な業務データ**。抽象書式・variant・witness と同じレイヤに置かない。
- 内部実務生成物を witness に使う場合も `redacted / abstracted / approved` ゲートを通す。
- `gate_filled_instance_separated`。

## 9. 既存001系の再配置（並行canonical禁止・命名降格）
| 旧 | 新しい呼称・位置 |
|---|---|
| FORMOBJ-001 canonical | **`witness_canonicalization`（form_witnessの読取正準化）**。書式の正本ではない |
| template map | `witness_cluster` / `form_candidate_cluster` |
| compare_templates | `variant_or_witness_comparison` |
| shared_term_registry | `typed_by` 語彙サポート |
| clause_design_knowledge | `advised_by` の設計知識（書式同一性ではない） |
- `gate_no_parallel_canonical`：001のcanonical成果物を002のcanonical form_objectとして扱わない。

## 10. ゴール＝弁護士＋AI 共同利用ループ
```（必要なら）手続き選定 → 書式選定 → 内容充填```
AI支援：書式地図の提示／**記載事項チェック（法定欠落＝defect_kind別の警告＋任意推奨）**／押し引き提示（effect・favors）／witnessからの復元／機能term横断比較。

## 11. ゲート一覧（次版で強制）
- `G_FORM_FIRST_CLASS` / `G_FORM_LAYER_SPLIT` / `G_NO_PARALLEL_CANONICAL` / `G_FORM_ID_OPAQUE` / `G_WITNESS_EDITION_VERIFIED` / `G_MANDATORY_GROUNDED` / `G_ADVISORY_SOURCE_TYPED` / `G_FILLED_INSTANCE_SEPARATED`

## 12. owner 決定事項（v0.2）
| ID | 決定 |
|---|---|
| D-O1 | 書式は独立 first-class（7オブジェクト並列）— 採用 |
| D-O2 | 親なし・関係エッジのみ — 採用 |
| D-O3 | form_uid = alo:form:{uuidv7} 不透明・不変 — 採用 |
| D-O4 | 記載事項＝法定（細分）／任意の二層＋defect_kind — 採用 |
| D-O5 | 001系は witness/型付け/設計知識の下位へ降格（canonical語を降格）— 採用 |
| D-O6 ★ | 4層分離（form_object/variant/witness/filled_instance）— 採用 |

## 13. 次（リリース境界内）
1. **最小実証（非機微な公的書式）**：定款の絶対的記載事項＝**会社法27条**に接地した mandatory 記載事項を1書式で（設計のみ）。
2. 既存 e2e（製造委託）を4層・記載事項細分に載せ替え。
- HOLD：DDL／DB／production mapping／single-witnessからのcanonical発番／タイトルのみ照合／filled_instance投入。

## 14. 改訂履歴
- v0.2-draft（2026-06-15）：監査 `DDFORMOBJ2_PASS_WITH_NOTES` 反映。4層分離、同一性判定軸、記載事項細分＋defect_kind、001 canonical降格、filled_instance分離、witness同定項目、8ゲート。owner ratify 済。一次設計資料として確定。
- v0.1-draft（2026-06-15）：独立オブジェクト観の初版（監査提出・凍結）。
