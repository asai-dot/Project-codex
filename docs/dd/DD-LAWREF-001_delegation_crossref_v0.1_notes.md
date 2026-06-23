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

## §4. OSS 戦略 — **ゼロイチを避け、既存を踏み台に**（owner 方針 2026-06-23）

> **owner 方針**: 委任/参照グラフを**ゼロイチで自前構築しない**。同じ痛みの legaltech/法律家は多く、
> 公開された先行事例がある。**既存を参考・修正採用し、その上に上乗せ**する。
> v0.1 ノートの「接続グラフは自前構築」は、狙い撃ち再調査で**部分的に反証された**ため下記に改める。

### 4.1 再調査の結論（v0.1 からの修正）
| 軸 | v0.1 の結論 | 改訂後 |
|---|---|---|
| **参照グラフ（`references`）** | 「OSS 不在・自前」 | **踏み台あり＝格下げ**。本体は **Lawtext**（条文参照解析）。略称名寄せは analysis_law_reference / `jplaw_text` を部品流用。＝ゼロイチではない |
| **委任チェーン（`delegates_to`/`implements`）** | 「自前」 | **公開物は依然不在**だが、**参照層の typed subset** として参照抽出の上に乗せる＝ゼロイチではない。`reads_as`(読替) を委任の実質手掛かりに |

> **訂正注（2026-06-23, src 精読）**: v0.1 改訂時に `analysis_law_reference` を「参照抽出器とほぼ確定」と
> 書いたのは **Cargo.toml 依存からの推定に基づく過大評価**だった。ソースを読むと**略称辞書ビルダー**
> （条文参照も委任も抽出しない・法令名取得は未実装）。参照抽出の本体は **Lawtext** が担う、と訂正。
> ＝「現物を読む前に採用判断しない」(look-before-adopt) を実地で適用した結果。

### 4.2 取得・パース・参照抽出（踏み台にする既製物）
| 候補 | 採否 | 用途・評価 |
|---|---|---|
| **aluqas/gitlaw-jp**（MIT, Python） | **そのまま採用（取得層）** | e-Gov API から**政令・省令含む全種別**を改正履歴付き取得（`--all-law-types`）。DD-LAWTIME の時点取得に即戦力 |
| **takuyaa/ja-law-parser**（MIT, Python） | **修正採用（パース層）** | 標準 XML→型付きモデル。憲法〜府省令対応。単一法令内のみ |
| **yamachig/Lawtext**（MIT, TS） | **修正採用（参照抽出の本体）** | 最成熟・活発。条文参照・定義語解析を持つ→`references` edge の**主たる初期抽出器**。analysis_law_reference が参照抽出器でなかったため、参照本体はここが担う |
| **japanese-law-analysis/analysis_law_reference**（Rust, MIT, 2023, 金子尚樹） | **限定採用（部品：略称解決の前処理）** | **src 精読で実体確定（2026-06-23）**: 名前に反し**条文間参照も委任も抽出しない**。やっているのは法令 XML から**略称定義**（「…第十三号。以下「○○改正法」という。」）を正規表現で拾い **法令番号→略称** 辞書を作るだけ。法令名取得ループは `main.rs` で `// TODO` 未実装、`get_law_name.rs` は空、0★/8commits。→ **参照解決の前処理（被参照法令名の名寄せ）部品**としてのみ価値。**依存の `jplaw_text`（XML→条文テキスト＋Article 構造）・`listup_law`（法令一覧）の方がパース層部品として再利用価値が高い** |
| **japanese-law-analysis/analysis_yomikae**（Rust, MIT） | **部品的に修正採用** | 読替規定解析＝委任先での語の読替＝委任の実質に最も近い既製資産。`reads_as` edge の種に |

### 4.3 参考にする可視化・先行事例（そのままは使わないが発想/検証に）
| 事例 | 位置づけ | 出典 |
|---|---|---|
| **可視化法学 / lawvis**（芝尾幸一郎・個人） | **参考のみ**（＝owner が X で見た「作った人」の正体とほぼ確定）。法令間参照を Gephi でネットワーク可視化。ただし**粒度が法令単位で条文単位でない**ため edge 素材には粗い | https://www.lawvis.info/ ・ X:@lawvis ・ https://note.com/ichigaya_houmu/n/n543526879679 |
| **JaLII RefVis**（名大 法情報研究センター／佐野智也・角田系） | **参考のみ**。明治民法各条を Jaccard 類似度で参照可視化。機械的参照解決でなく**文字列類似ベース** | https://www.law.nagoya-u.ac.jp/jalii/refvis/about.html |
| **デジタル庁 法令 API ハッカソン作品**（2023/2025） | **参考のみ**。「参照先条文ポップアップ」「建築法令をグラフ DB 化」等＝参照解決/グラフ化は既に実証済み（自前構築の難度が現実的である傍証）。作者/repo は未特定 | https://www.digital.go.jp/en/news/9fb5ef8e-c631-4974-96d9-0b145304c553 |
| **lwhb/lawhub** | 参考のみ（差分追跡。正当性無保証） | — |

### 4.4 自前で作る部分（縮小した）
- **委任の typing**（参照のうち「政令/省令への授権」を `delegates_to` と判定）と、**委任の限界・趣旨の評価**
  （これは DD-SUBTRANS の assertion）。＝AKN 流（ref＋activeRef/passiveRef＋オントロジー）を範に、
  **参照抽出層の出力の上に分類・評価レイヤだけを自前で乗せる**。これは MILESTONE §9 の「事務所の判断資産」と一致。

### 4.5 パース層の選択 — Python(ja-law-parser) vs Rust(japanese-law-analysis スタック)【決定点】
`analysis_*` 群を辿って分かったこと: japanese-law-analysis（puripuri2100/金子尚樹, 2023, MIT）は
`japanese_law_xml_schema`(crate v4.0.2＝標準 XML v3 型付パーサ) を土台に **jplaw_text / listup_law /
analysis_yomikae(読替)** が揃った**一貫した Rust スタック**。各部品の実体（src 精読済）:

| 部品 | 実体（確認済） | codex への価値 |
|---|---|---|
| **jplaw_text**（MIT, 474行, 依存=quick-xml のみ・軽量） | `xml_to_law_text(xml)->Vec<LawText>`。`Article{article, paragraph, item, sub_item}` で**条・項・号粒度**の locator＋本文を返す | **高**。lawdelta が食う `(article_path, text)` 単位そのもの。**精度 L5（項・号粒度）に直結** |
| **listup_law**（MIT, binary） | 法令 XML フォルダ→`japanese_law_xml_schema` で 法令番号・題名・公布日 を抽出し JSON 索引化 | 中。法令カタログ。**取得層 gitlaw-jp と役割が重なる** |
| **japanese_law_xml_schema**（crate v4.0.2） | 標準 XML v3 の型付パーサ | 高。Rust 版の基盤パーサ（Python の ja-law-parser に相当） |

**決定点（owner 判断・本ノートでは保留）**: codex producer は Python(stdlib)。パース層を
(A) **Python の takuyaa/ja-law-parser** で単一言語に揃える（連携摩擦ゼロ）か、
(B) **Rust スタック**（jplaw_text の項号粒度＋同エコシステムの **読替(yomikae)** を低コストで取り込める）を
JSON 受け渡しで採るか。
**暫定推奨**: パース層は (A) Python ja-law-parser で開始（パイプライン単一言語の利を優先）。
ただし **読替(yomikae) を `reads_as` edge に使う段で (B) の jplaw_text+japanese_law_xml_schema を
部品採用**（読替解析が Rust 側にしか無いため、その一画だけ Rust→JSON で受ける）。＝言語は用途で割る。

---

## §5. 精度（PLAN_lawobject_precision）との接続

接続軸は精度プランの **L4（同定の地盤：article_path 正規化＋lawtime 接続）を一段強くする**:
- 委任/参照を張るには**条項単位の正準 URI（article-level identity）が前提**。L4 の crosswalk と同じ土台を共有。
- 参照解決（Lawtext 由来）の正否は L1 評価ハーネスで pattern 単位 P/R を測れる（新 task: `lawref`）。
- 行政解釈レイヤ（告示・通達）は DD-SUBTRANS の `source_type`（`ministry_commentary` 等）と tier 体系に乗る。

---

## §6. 次アクション（このノートの宿題）
1. ~~`analysis_law_reference` の src/ 精読~~ **✅ 完了（2026-06-23）**: 略称辞書ビルダーと判明（§4.2 訂正）。
   流用は「略称名寄せ部品」＋依存の `jplaw_text`/`listup_law` に限定。
2. ~~`jplaw_text`/`listup_law` の中身確認~~ **✅ 完了（2026-06-23）**: §4.5 に整理。jplaw_text は
   条・項・号粒度の本文抽出器で価値高（L5 直結）だが Rust。パース層は Python ja-law-parser を暫定推奨、
   読替の一画だけ Rust 部品採用、と方向づけ（最終は owner 判断）。
3. **参照抽出の本体 = Lawtext の評価 PoC**（次の最重要点）。Lawtext で同一法令の条文参照抽出を回し、
   出力を `references` edge 形に写像、precision を L1 ハーネス（新 task `lawref`）で測る。
   TS 実装なので Python パイプラインとの連携形（CLI/JSON 受け渡し）も併せて検討。
4. e-Gov 法令 API v2 OAS の**全文確認**（一部 HTTP 403 で未取得）→ 条文単位取得・改正履歴の仕様確定。
5. `alo_edges` への接続軸 edge 型の DDL 案（DD-LAWTIME/SUBTRANS と同じ append-only・gate 様式）。
6. 自前部分の最小化設計: 参照抽出層の出力に **委任 typing（`delegates_to`）＋委任限界の評価 assertion**
   だけを乗せる境界を明確化（形式 edge は機械、評価は DD-SUBTRANS の出典付き assertion）。
7. 本ノートを GPT お目付け役 gate `DDLAWREF` に投函 → owner ratify で DD 昇格。

## §7. 不確実な点（推測で埋めない）
- **lawvis** はデータ/コードの GitHub 公開を確認できず（可視化結果サイトのみ）。粒度は法令単位。
- **デジタル庁ハッカソン作品**の作者/repo 名は公式 PDF が 403 で未特定。公開 OSS かデモかも未確認。
- v2 OAS 本文・OASIS 逐語定義の一部は環境側 HTTP 403 で未取得。
- `jstatutree`（自治体例規系の候補）は実在/所在を一次確認できず。
- 各 OSS のスター数・最終更新日は閲覧時点の概数。

## §8. changelog
- v0.1 (2026-06-23 初版): 接続軸の問題提起。e-Gov は政令/省令テキストを持つが委任/参照/告示の
  「接続」が無いことを一次情報で確定。OSS 戦略を「取得/パースは既製・接続グラフは自前」と整理。
- v0.1 改訂 (2026-06-23, owner 方針反映): 「ゼロイチ自前を避け既存を踏み台に」を受け、委任/参照
  グラフの先行事例を狙い撃ち再調査。lawvis/JaLII RefVis/ハッカソンを参考事例に追加、§4 を全面改訂。
- v0.1 訂正 (2026-06-23, src 精読): `analysis_law_reference` を clone して精読 → **「参照抽出器」は
  過大評価で、実体は略称辞書ビルダー（条文参照も委任も抽出せず・法令名取得は未実装）**と判明。
  参照抽出の本体は **Lawtext** に確定し直し、analysis_law_reference は略称名寄せ部品に格下げ、依存の
  `jplaw_text`/`listup_law` をパース層部品として評価。§4.2/§4.1/§6/§7 を訂正。look-before-adopt の実地適用。
- v0.1 追補 (2026-06-23, parse 層 src 精読): `jplaw_text`/`listup_law` を clone 精読し §4.5 を追加。
  jplaw_text は条・項・号粒度の本文抽出器（軽量・L5 直結）だが Rust。japanese-law-analysis は
  `japanese_law_xml_schema` を土台にした一貫 Rust スタックと判明。**パース層は Python ja-law-parser
  暫定推奨・読替の一画のみ Rust 部品採用**という言語分割の決定点を明文化（最終は owner 判断）。
