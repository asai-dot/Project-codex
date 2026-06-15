# DD-FORMOBJ-002 v0.1: 書式オブジェクト ── 独立 first-class オブジェクトとしての再定義

> **id**: DD-FORMOBJ-002 / **version**: v0.1-draft / date: 2026-06-15
> **owner**: 浅井 / **author**: 番頭(リモートClaude)
> **gate**: 設計のみ（DDL・DB書込み・accepted化なし）
> **位置づけ**: DD-FORMOBJ-001（v1.1）/ INTEGRATION / registry は **書式を暗に「文献から構造化するもの」「pipelineの産物」に寄せすぎ**ていた。owner 訂正により、**書式は法令・判例・文献・雑誌・語彙・手続きと並ぶ独立オブジェクト**として定義し直す。本DDが書式オブジェクトの上位定義。001系はその下位（witness読取・語彙・押し引き知識）に再配置する（§6）。

---

## 0. 訂正の要点（なぜ書き直すか）
- 書式は **文献に従属しない**。文献は書式が「観測されやすい一供給源」にすぎない。
- 書式は **手続きにも限定されない**。登記申請・裁判等の提出書式は書式の一部分でしかなく、私人間の売買・賃貸の契約条項のように手続きと直接関わらない書式が多数ある。
- 書式の本質 = **人が何かをするとき、その営みを文書化・記録する産物**。きわめて広い。
- ゆえに **書式は別枠の独立オブジェクト**として切り出す。他オブジェクトとは**関係（エッジ）**で結ぶ。階層・従属にしない。

## 1. オブジェクト宇宙（7つの別個独立 first-class）
```
法令 ・ 判例 ・ 文献 ・ 雑誌 ・ 語彙 ・ 手続き ・ 書式
```
- どれも独立。互いに**グラフ（関係エッジ）**で結ばれるが、どれも他の下に入らない。
- **書式 と 手続き は隣接**するが別物。手続き（特に弁護士関与のもの）は**限定的＝少数**。書式は応用的で広い。
- 書式は **応用オブジェクト**：基底（法令・判例・文献・雑誌・語彙）と手続きから派生・接地するが、実務（弁護士＋AIが選定し内容を埋める）に直結する到達点。

## 2. 書式オブジェクトの同一性（独立・不変）
```text
form_object
  form_uid = alo:form:{uuidv7}      # 不透明・不変。文献item/手続き/ISBN/タイトルから導出しない
  form_kind                         # contract | clause_set | application | record | minutes | notice | petition | internal_doc ...
  practice_domain                   # 売買 | 賃貸借 | 業務委託 | 会社法務 | 労働 | 登記 | 訴訟 | 行政手続 | ...
  canonical_title / title_norm
  identity_status                   # provisional | candidate | resolved | split_required | deprecated_alias
```
- **書式の同一性は「何の営みを記録する書式か（機能・類型）」で決まる**。どの本に載っていたか、どの版かには依存しない。
- 同一書式は**複数の witness**（版違いの本・HP・実務生成物）を持つ。witness は書式を所有しない（§3）。
- DD-LITID と同じ identity 原則：**属性（ISBN・vendor id・title）を主キーに焼かない**。旧 `alo:book:*` 流の昇格でIDを書き換えない。

## 3. 関係エッジ（従属でなく関係）
各エッジは `provenance / confidence / grounding / verified_status` を持つ。
| エッジ | 先 | 意味 |
|---|---|---|
| `witnessed_in` | 文献(biblio_item+toc_node+page_span) / 裁判所HP / 法務局HP / 弁護士実務生成物 | この書式が**観測された場所（多源）**。複数witness可。版検証付き（§8）。 |
| `serves` / `submitted_under` | 手続き | 提出書式のときだけ張る**任意**エッジ。張らない書式も多い。 |
| `required_items_grounded_in` | 法令・規則・行政要求 | **法定記載事項（義務）**の接地。欠落＝瑕疵。 |
| `advised_by` | 文献・解説・実務 | **任意的記載事項（推奨）**・押し引きの接地。 |
| `typed_by` | 語彙（条項機能 term registry） | clause/slot の型付け（shared_term_registry）。 |
| `cites` / `effect_from` | 判例 | 条項の効果・有効性の裏付け。 |
- **biblio_item は `witnessed_in` の一本にすぎない**。〔全訂版〕と記載例集は「同じ書式を目撃した別 witness」。
- 語彙 registry は `typed_by` の一本。法令は `required_items_grounded_in` の一本。**どれも書式の親ではない。**

## 4. 機械可読な内容構造（書式の中身）＝弁護士＋AI が使う本体
```jsonc
form_object.content {
  sections: [ { heading, clauses: [...] } ],
  clauses: [{
    no, title,
    text,                         // 文字面（witnessから復元）
    function_ref → 語彙 term,      // typed_by
    slots: [{id, type, required}],// 意味型slot（埋める欄）
    obligations|rights,
    requisite_class,              // ★二層：mandatory(法定) | advisable(任意) | structural
    requisite_grounding,          // mandatory→法令/規則 ; advisable→文献/実務 (gate: 観測のみ不可)
    design_options: [{axis_type, choice, effect, favors_role, tightness, legal_basis}] // 押し引き
  }]
}
```
**記載事項の二層**（owner 中核）:
- **法定記載事項 (mandatory)**：法令・規則・行政要求に**接地必須**（`required_items_grounded_in`）。AIは欠落を**瑕疵として警告**。
- **任意的記載事項 (advisable)**：文献・解説・実務が出どころ（`advised_by`）。押し引き（tighten/loosen）＋ favors_role。

## 5. ゴール＝弁護士＋AI 共同利用ループ
```
（必要なら）手続きを選ぶ → 書式を選ぶ → 内容を埋める
```
AI が機械可読書式で支援すること:
- **地図提示**：この営み/類型にどんな書式があるか（多源 witness を束ねて）。
- **記載事項チェック**：法定欠落の警告＋任意推奨の提示（§4 二層）。
- **押し引き提示**：条項の選択肢を effect・favors付きで（design_options）。
- **復元**：witness から書式テキストを起こす（文字面再現は副産物）。
- **横断**：機能 term で書式横断の比較・ギャップ検出。
→ 「文献から書式を作る」ではなく、**実務に直結する応用オブジェクトを機械可読に立てる**。

## 6. 既存成果の再配置（捨てない・親子を正す）
| 既存 | 新しい位置づけ |
|---|---|
| FORMOBJ-001 snapshot/canonical（S1-S3, form_snapshot.v1） | `witnessed_in` エッジ＝**文献 witness の読取・正準化**の実装 |
| shared_term_registry（語彙） | `typed_by` エッジの語彙（独立オブジェクト=語彙） |
| clause_design_knowledge（押し引き・解説接地） | `advised_by` の**任意的記載事項**知識 |
| template map / compare_templates | 複数 `witnessed_in` の集約＋**書式同一性の束ね**（版違いは別 witness） |
| **法定記載事項（法令接地）** | **新規。これが手薄だった**＝`required_items_grounded_in` の整備が次の山 |
| DD-LITID（文献同定） | `witnessed_in` の**文献witness側のID/版検証**に使う（書式の親ではない） |

## 7. 書式 vs 手続き（隣接だが別・確認）
- 手続き＝弁護士関与の公的手続き中心で**限定的・少数**。原オブジェクト寄り。
- 書式＝広い応用記録物。`serves` で手続きに繋がる場合もあるが、**繋がらない書式が多数**（私契約・社内記録・取引手順）。
- ゆえに「手続きFK配下に書式」も誤り。書式は独立。

## 8. 同定・witness 検証の原則（今日の事故の教訓）
- 書式IDは不透明・不変。**witness（文献の版）が変わっても書式IDは不変**。
- `witnessed_in` の文献リンクは **版検証付き**（DD-LITID の asset alignment / fingerprint を借用）。**タイトル一致のみのリンク禁止**（=今日、別版の記載例集を全訂版に誤接続した事故の再発防止）。
- 同一 provenance（同じ供給元データの再配信）を独立 witness として多数決に数えない。

## 9. ゲート（設計のみ）
- `gate_form_id_opaque` — 属性（ISBN/vendor/title/手続き名）を form_uid に焼かない。
- `gate_form_not_subordinate` — 書式を文献/手続きの FK 配下に置かない（独立＋エッジ）。
- `gate_witness_multi_source` — 単一 witness を真実視しない。版違いは別 witness。
- `gate_witness_edition_verified` — witness リンクは版検証必須（タイトル一致のみ禁止）。
- `gate_mandatory_grounded_in_law` — 法定記載事項は法令・規則に接地必須。
- `gate_advisable_grounded_in_source` — 任意的記載事項は文献・実務に接地（観測のみ付与不可）。

## 10. owner 決定事項（v0.1）
| ID | 問い | 提案 |
|---|---|---|
| D-O1 | 書式は独立 first-class か | **Yes。法令・判例・文献・雑誌・語彙・手続きと並列。** 採用 |
| D-O2 | 書式の親 | **無し。関係エッジのみ**（witnessed_in/serves/grounded_in/typed_by/cites） |
| D-O3 | form_uid | `alo:form:{uuidv7}` 不透明・不変（DD-LITID と同原則） |
| D-O4 | 記載事項 | **法定（法令接地・義務）／任意（文献接地・推奨）の二層** |
| D-O5 | 既存001系 | 破棄せず**下位（witness読取・語彙・押し引き）に再配置** |

## 11. 次
1. 本DDを監査へ（書式独立オブジェクト観の妥当性確認）。
2. `required_items_grounded_in`（法定記載事項←法令）の最小実証を1書式で（例：定款の絶対的記載事項=会社法27、又は登記申請書式の法定事項）。← 手薄な所を埋める。
3. 既存 e2e（製造委託）を本オブジェクト観に載せ替え（witnessed_in 多源／法定・任意の二層）。
