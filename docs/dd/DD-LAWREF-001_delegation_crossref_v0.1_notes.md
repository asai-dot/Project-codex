# DD-LAWREF-001 設計ノート v0.1 — 法令間「接続軸」（委任チェーン・条文間参照・行政解釈レイヤ）

> **status**: draft notes（問題提起＋方向づけのみ。accepted DD ではない。production/accept は
> GPT お目付け役 gate ＋ owner ratify を経る）/ **owner**: 浅井 / **author**: Project-codex (claude-code remote)
> **recorded_at**: 2026-06-23 / **gate(予定)**: `DDLAWREF`
> **depends_on**: DD-LAWTIME-001（形式軸）/ DD-LAWSUBTRANS-001（実質軸・assertion overlay）/
> `35_link_layer`(`alo_edges`)
> **要旨**: 実務家の問題提起「e-Gov は法律までで、その下の政令・省令との"接続"が無い」を一次情報で
> 検証した。結論は **前提の精密化**：e-Gov は政令・省令・規則の**全文 XML は持っている**。
> 欠けているのは**テキストではなく「接続」**——①法律→政令→省令の**委任チェーン**、②条文間の
> **参照グラフ**、③**告示・通達・ガイドライン**の行政解釈レイヤ——であり、これは**政府自身が
> 「今後の課題」と公式に認めている**。よって法令オブジェクトに、形式軸・実質軸に次ぐ**第三の軸＝
> 接続軸**を立てる。

---

## §1. 何が本当に欠けているか（一次情報で裏取り）

### 1.1 前提の訂正：テキストは在る
e-Gov 法令検索/法令 API は **憲法・法律・政令・勅令・府省令・規則** を格納する（整備基準日:
法律・政令等 2015-08-01、府省令・規則 2016-10-01）。**政令・省令・規則の全文 XML は API で取得できる。**
法令 API v2（2025-03-14）では条文単位取得・時点取得・改正履歴・JSON 出力も追加。法令標準 XML は v3。
→ 「e-Gov は法律までしか扱えない」は**テキスト面では不正確**。問題はその先にある。

出典:
- 法令種別と法令 ID（e-Gov 法令データドキュメント） https://laws.e-gov.go.jp/docs/law-data-basic/607318a-lawtypes-and-lawid/
- 法令 API Version2 リリース告知 / Swagger https://laws.e-gov.go.jp/api/2/swagger-ui
- 法令標準 XML スキーマ v3 https://laws.e-gov.go.jp/docs/law-data-basic/419a603-xml-schema-for-japanese-law/

### 1.2 本当に欠けているもの＝「接続」（政府も未提供と明言）
| 欠落レイヤ | 構造化データ提供 | 典拠 |
|---|---|---|
| ① 法律→政令→省令の**委任チェーン** | **無し** | 法令 ID は**法令単位**の識別子に留まり、**条項単位の識別子が未整備**。「文章同士を紐付けたデータの蓄積に役立つため整備が期待される」と公式に位置づけ |
| ② 条文間の**参照・引用関係グラフ** | **未提供**（XML 本文に参照文言はあるが解決済みリンク/グラフは無い） | 同上。諸外国は条項単位 URI で文書間リンクを実現、と比較 |
| ③ **告示・通達・ガイドライン・パブコメ** | **無し**（所管ページへのリンク集のみ） | デジタル庁が「統一的な DB が存在しない告示」の構造化を今後の課題と明記 |

出典:
- 山内匠「法令データの現状と法令分野へのデジタル技術適用の展望」ANLP 2024 https://anlp.jp/proceedings/annual_meeting/2024/pdf_dir/E4-3.pdf
- 「法令」×「デジタル」の取組（デジタル庁 2025-06） https://www.digital.go.jp/assets/contents/node/basic_page/field_ref_resources/7f49ac76-91f1-44ba-91bd-2114973fcc61/f1e3c434/20250606-policies_legal-practice_outline_01.pdf
- 所管法令・告示・通達 | e-Gov ポータル https://www.e-gov.go.jp/laws-and-secure-life/law-in-force.html

> **実務上の含意**: 「この省令の根拠はどの法律のどの条の委任か」「委任の範囲を超えていないか（委任の
> 限界）」「ある条文を読むとき連動して効く下位法令・参照条文は何か」——これは実務家が日々問うのに、
> e-Gov でも既存 OSS でも**機械可読では答えられない**。法律実務の中核的問いがデータ化されていない。

---

## §2. 法令オブジェクトにおける位置づけ（第三の軸）

| 軸 | 担当 | 問い |
|---|---|---|
| 形式軸 | DD-LAWTIME-001 | いつ公布/施行/改正/廃止。どの時点でどの条文版が有効か |
| 実質軸 | DD-LAWSUBTRANS-001 | その改廃で意味・要件・効果・射程が変わったか。誰がどう評価したか |
| **接続軸（本ノート）** | **DD-LAWREF-001** | **どの法令/条文が、どの法令/条文と、どう繋がるか**（委任・参照・読替・授権） |

- 接続軸は DD-SUBTRANS の `depends_on` にある **`35_link_layer`（`alo_edges`）** の正式な引き取り先。
- **形式/実質の分離原則を踏襲**：①委任・参照の**形式事実**（「○○法第 n 条が政令に委任」「条文 A が条文 B を
  引用」＝官報/XML から確定できる）は機械提示してよい。②委任の**限界・趣旨・実質的射程**（「この省令は
  委任の範囲内か」等の**評価**）は DD-SUBTRANS 同様、**出典付き・順位付きの assertion** とし断定しない。

---

## §3. データモデルの方向（Akoma Ntoso を範に）

Akoma Ntoso（OASIS LegalDocML v1.0）は**委任専用要素を持たず**、(1) `<ref>`（`@href`→eId/URI で宛先を一意化）、
(2) `<analysis>` 内の `<activeRef>`（自分が及ぼす参照）/`<passiveRef>`（自分が受ける参照）、(3) ローカル
**オントロジー**（`<TLCConcept>` 等で「授権/委任」概念を定義）で表現する。米 USLM・EU ELI も「URI＋関係
メタデータ」方式。→ **専用タグでなく「参照＋関係メタデータ＋オントロジー」**が世界の収束解。

出典: Akoma Ntoso v1.0 Part1 Vocabulary（OASIS） https://docs.oasis-open.org/legaldocml/akn-core/v1.0/akn-core-v1.0-part1-vocabulary.html / AKN4UN Management of Modifications https://unsceb-hlcm.github.io/part1/index-167.html

### 本 DD の edge 型（案・統制語彙）
`alo_edges` の関係種に以下を足す（lawtime/subtrans の `article_path` 規約を共有）:
- `delegates_to`（授権：法律条文 → 政令/省令。AKN activeRef 相当）/ 逆 `delegated_by`
- `references` / `referenced_by`（条文間引用。解決済みリンク）
- `reads_as`（読替規定：委任先で語 X を Y と読み替える＝委任構造の実質。下記 OSS 部品と接続）
- `implements`（下位法令が上位委任を具体化）/ `authority_basis`（根拠条文）
> いずれも **形式事実 edge**（XML/官報から確定）。委任の**限界評価**等は DD-SUBTRANS の assertion へ。

---

## §4. OSS 戦略（そのまま採用 / 修正採用 / 自前）

調査結論: **委任チェーン・法令間参照グラフを構造化提供する OSS は発見できず**。取得・パース層は既製を
修正採用し、接続グラフは自前構築する（MILESTONE §9 の「公的機関・汎用ツールに作れない事務所の判断資産」
という戦略的位置づけと一致）。

| 候補 | 採否 | 用途・評価 |
|---|---|---|
| **aluqas/gitlaw-jp**（MIT, Python） | **そのまま採用（取得層）** | e-Gov API から**政令・省令含む全種別**を改正履歴付き取得（`--all-law-types`）。DD-LAWTIME の時点データ取得に即戦力 |
| **takuyaa/ja-law-parser**（MIT, Python） | **修正採用（パース層）** | 標準 XML→型付きモデル。憲法〜府省令対応。**単一法令内のみ＝委任/参照は自前で上乗せ** |
| **yamachig/Lawtext**（MIT, TS） | **修正採用（参照抽出）** | 最も成熟・活発。**条文参照・定義語解析を持つ**→参照 edge の初期抽出器に価値大。委任チェーンは未対応 |
| **japanese-law-analysis/analysis_yomikae**（Rust） | **部品的に修正採用** | **読替規定解析**＝委任先での語の読替＝**委任の実質に最も近い既製資産**。`reads_as` edge の種に |
| **lwhb/lawhub** | 参考のみ | 差分追跡の発想は近いが「正当性無保証・機械更新」。設計参照に留める |
| e-Gov MCP ラッパ各種 | 補助 | API アクセスの LLM 接続には便利だが付加価値なし |
| **委任/参照グラフ本体** | **自前構築** | OSS 不在。AKN 流（ref＋activeRef/passiveRef＋オントロジー）を範に codex の edge/assertion として実装 |

---

## §5. 精度（PLAN_lawobject_precision）との接続

接続軸は精度プランの **L4（同定の地盤：article_path 正規化＋lawtime 接続）を一段強くする**:
- 委任/参照を張るには**条項単位の正準 URI（article-level identity）が前提**。L4 の crosswalk と同じ土台を共有。
- 参照解決（Lawtext 由来）の正否は L1 評価ハーネスで pattern 単位 P/R を測れる（新 task: `lawref`）。
- 行政解釈レイヤ（告示・通達）は DD-SUBTRANS の `source_type`（`ministry_commentary` 等）と tier 体系に乗る。

---

## §6. 次アクション（このノートの宿題・未着手）
1. e-Gov 法令 API v2 OAS の**全文確認**（本調査は一部 HTTP 403 で未取得）→ 条文単位取得・改正履歴の
   正確なエンドポイント仕様を確定。
2. gitlaw-jp / ja-law-parser / Lawtext / analysis_yomikae のライセンス・最新性を実機で再確認
   （本調査のスター数・更新日は閲覧時点の概数）。
3. `alo_edges` への接続軸 edge 型の DDL 案（DD-LAWTIME/SUBTRANS と同じ append-only・gate 様式）。
4. 「委任の限界」評価を DD-SUBTRANS の assertion 型として持てるかの整理（形式 edge と評価 assertion の境界）。
5. 本ノートを GPT お目付け役 gate `DDLAWREF` に投函 → owner ratify で DD 昇格。

## §7. 不確実な点（推測で埋めない）
- v2 OAS 本文・OASIS 逐語定義の一部は環境側 HTTP 403 で未取得（機能差分はリリース告知＋複数二次情報の一致に基づく）。
- `jstatutree`（自治体例規の木構造系として言及される候補）は**実在/所在を一次確認できず**。
- 各 OSS のスター数・最終更新日は閲覧時点の概数。GitHub メタデータの API 確認は本セッションのスコープ外。
