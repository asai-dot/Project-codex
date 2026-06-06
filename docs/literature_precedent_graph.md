# 文献 ↔ 判例 ↔ 法令 接続設計（いいとこ取り）

> 深掘り研究メモ。Fork2（検索/RAG・4図書館横断ビューワー）を、ALO既存の知識グラフ（alo-kg）と
> 接続し、「文献から判例・法令へバーンと飛ぶ」を**ALOが自前で握れる形**で実装するための設計。
> 関連: [architecture.md §7](architecture.md) / [link_structures.md](link_structures.md) / `schema/supabase_schema.sql`

---

## 1. 出発点 — 商用2サービスの強みと「壁庭」

| | リーガルライブラリー | ベンコム（弁護士ドットコムLIBRARY） |
|---|---|---|
| 強み | **文献→法令リンク**（本文→該当法令） | **文献→判例リンク**（本文ページ→引用判例一覧） |
| ページ着地 | `/r/{id}?page=N&ctg=view`（offset校正） | `/reader/?cid=&adr=N`（共有ボタン発行） |
| 判例連携 | 弱い | 強い（判例秘書/LICを買収し連携） |
| 法令連携 | 強い（法令リンク機能） | （本文内） |
| 壁庭 | 自社ビューワー内で完結 | 判例秘書本文は `/plus/detail?screen_info_id={暗号}` で**直リンク生成不可** |

**いずれも「自社サービス内でしか繋がらない」**。ベンコムですら判例秘書とは暗号化ハンドオフで、
シームレスではない（[link_structures.md §3](link_structures.md)）。

## 2. ALOが既に持っている内製資産（重要）

`alo-kg/`（Box『事務所内本棚DX化計画』）に、**法令側の本格的な citation pipeline が既に存在**:

- `fetch → parse → link → gate` の4ステップ（`pipeline.py`）。e-Gov法令API（`api/2`）から取得し、
  条項粒度でパース、参照リンクを生成、品質ゲート（in-scope validity ≥99% / anchor ≥95%）。
- `resolver.py`（法令名解決＋略称辞書）、`temporal.py`（法令の**版**管理）、`kanji.py`（漢数字）。
- 決定論的 `link_id = sha256(source_id + raw_text + article)`、冪等、provenance付与（原則7/8）。
- ゴールド回帰（`mismatch_corrections.jsonl` 1,137件）。
- `nodes/`（provisions, law_works）、`edges/`（citation_links）、`unresolved/`。
- **`case_spine/`**: 判例の背骨（DB-backed、alembic migrations）。判例ノードの正本。
- **D1KOS/OPAC/CiNii 法令参照レーン**: 候補23,280件を staging→review-first→accept の規律で運用。
  **「support edge（文脈支持）」と「identity主張（条文同一性）」を峻別**し、機械acceptしない厳格さ。

→ ALOは「法令を内製でグラフ化」済み。**足りないのは文献(書籍)側ノードと、文献→法令/判例の橋**。
本リポジトリ（Fork2）の TOCノード＝その文献側ノードであり、4図書館deeplinkリゾルバ＝着地解決器。

## 3. 設計の核 — 「参照着地リゾルバ」への一般化

`src/deeplink.js`（図書館の着地解決）を、**3種の参照ターゲットに一般化**する。
原理は同じ「データ駆動・所有/公開優先・商用は最後にオンランプ」:

```
参照(reference) → ターゲット種別ごとに優先順で着地URLを解決
  ├─ 文献(literature) → 4図書館リゾルバ（自炊PDF / リーガル / ベンコム / 物理本）  ← 実装済
  ├─ 法令(statute)    → e-Gov（構築可・無料・ALOが正本化済）                      ← alo-kg 流用
  └─ 判例(precedent)  → 内部PD判決文 → 裁判所サイト → ベンコムprecedentsオンランプ   ← 新規
```

### 3.1 法令の着地（構築可・無料）
e-Gov法令は **lawId + 条項で安定URLを構築できる**（判例秘書と違い、我々が作れる）:

| 用途 | URL | 例（民法709条） |
|---|---|---|
| 人間向け本文 | `https://laws.e-gov.go.jp/law/{lawId}#{anchor}` | `/law/129AC0000000089#Mp-At_709`（anchor形式は要最終確認） |
| API（JSON/XML） | `https://laws.e-gov.go.jp/api/1/articles;lawId={lawId};article={n};paragraph={p}` | `;lawId=129AC0000000089;article=709` |

- `lawId` = 15桁（民法=`129AC0000000089`）。`resolver.py`＋`law_name_lookup` で法令名→lawId解決済。
- **版（temporal）**: 文献の発行時点に応じた施行版へ寄せられる（`temporal.py`）。改正耐性。

### 3.2 判例の着地（優先順）
判例秘書が直リンク不可なので、**ALOが構築できる公開アンカーを優先**:

| 優先 | ターゲット | URL/手段 | 構築可否 |
|---|---|---|---|
| ① | 所内の生判決文（PD・著作権なし） | 内部ビューワー | ◎ ALO所有 |
| ② | 裁判所サイト 裁判例 | `https://www.courts.go.jp/app/hanrei_jp/detail{2\|4\|7}?id={courtId}` | ○ idの解決が要（detail2=最高裁/4=下級/7=知財高） |
| ③ | ベンコム引用判例リンク（オンランプ） | `https://library.bengo4.com/books/{cid}/precedents#page_{viewer_page}` | ◎ 構築可・安定。ここから判例秘書へ |
| (参考) | 判例秘書本文 | `/plus/detail?screen_info_id={暗号}` | ✕ 生成不可 |

- 判例の**正本キー** = 裁判所＋判決年月日＋事件番号（例「東京高判 昭44.5.19 昭和41年(ネ)2780号」）。
  これを `case_spine` ノードに名寄せ。判例秘書ID（`L02420223`）・courtId は**参照キー**として保持。
- ②の `courtId`（事件番号→裁判所id）は **ALOに既にメタデータあり** → そのまま流用（harvest不要）。
- 着地は裁判所の **HTML判例詳細**に飛ばす（PDF判決文はDLリンクとして副）。HTMLの方が引用・接続に向く。

### 3.3 文献の着地
既存の4図書館リゾルバ（`src/deeplink.js`）。書名・章節・ページに着地。

## 4. 統一参照グラフ（alo-kg への接続）

すべて alo-kg の `nodes/` `edges/` 思想に乗せ、**1つの引用グラフ**にする。

```
literature_node (書籍/章節/ページ = 本リポジトリの toc_nodes)
   ├──cites_statute──▶ statute_node  (alo-kg provisions / e-Gov lawId+article)
   ├──cites_case────▶ case_node     (alo-kg case_spine / court+date+caseno)
   └──cites_lit─────▶ literature_node (他文献・相互参照)
```

- **エッジ生成は alo-kg の gate/provenance 規律を流用**: 決定論的 `edge_id`、品質ゲート、
  `resolver_status`（resolved / target_not_found / context_unresolved）、claim scope の峻別。
- **D1KOSの教訓を踏襲**: harvestした引用は当面 `support edge`（「この文献はこの判例/法令を引く」という
  文脈支持）であり、判例・条文の**同一性主張ではない**。accept前は `pending_review`。
  `金商法21条→商法21条` のような略称suffix誤りを弾く resolver を共用。

## 5. エッジの収集（harvest）戦略 — 「いいとこ取り」の実体

| エッジ種別 | 一次ソース（商用の強みを吸う） | 解決先（ALO公開アンカー） |
|---|---|---|
| 文献→法令 | ① リーガルの法令リンク ② 自炊PDF/OCR本文を `resolver.py`+`extract_links` で抽出 | e-Gov lawId+article |
| 文献→判例 | ベンコム `precedents#page_{N}`（頁別引用判例一覧）を採取 | case_spine → 裁判所/内部PD/オンランプ |
| 文献→文献 | 本文の「前掲」「本書○頁」等 | 4図書館リゾルバ |

- ベンコム precedents は **viewer_page で引ける**ので、`book_links.bencom.offset` で紙面ページ↔viewer_page
  を相互変換し、我々のTOC（章節→紙面ページ）と接合 → 「**この章が引く判例**」が機械的に出る。
- リーガルの法令リンク／OCR本文抽出は、alo-kg の既存 resolver/gate にそのまま流し込める。
- どのソースも**ログインが要る商用画面**なので、採取は人手 or セッション付きスクレイプで、
  **エッジ（事実関係）だけを内部化**する（本文は権利物なので複製しない＝図書館deeplinkと同方針）。

## 6. RAG への接続（③段階）

「事務所ライブラリに聞く」の回答は、**1つの論点に対し3レーンの出典**を同梱:

```
Q: 賃料不払を理由とする解除が信義則上制限される場合は？
A: …（要旨）…
   📖 文献: コンメンタール民訴III 第133条解説 p.43   [自炊PDF p.83 / リーガル / ベンコム]
   ⚖ 判例: 東京高判 昭44.5.19 昭和41(ネ)2780号       [裁判所 detail4 / ベンコムprecedents]
   📜 法令: 民法1条2項(信義則), 民法541条             [e-Gov /law/129AC0000000089#Mp-At_1]
```

引用ハンドル（書名・章節・ページ・node_id・各deeplink）に、根拠法令・根拠判例のリンクを足すだけ。
着地はすべて §3 のリゾルバが解決。pgvector の検索対象は文献ノード、回答時にエッジを辿って法令/判例を付す。

## 7. なぜこれが商用2サービスに勝つか

- **統合**: リーガル(法令)とベンコム(判例)が別々に持つリンクを、**1つのグラフで横断**。
- **所有**: 着地が e-Gov / 裁判所 / 内部PD ＝ ALOが構築でき、契約終了・UI改悪・暗号化ハンドオフに**縛られない**。
- **改正耐性**: 法令は temporal で版を合わせる。商用ビューワーにはできない時点整合。
- **横断**: 文献は4図書館（有償2＋自炊＋物理）を等価に。判例は公開＋オンランプ。
- 商用の壁庭（判例秘書の暗号化URL等）には**最後にオンランプするだけ**で、本体価値は内部グラフが握る。

## 8. 段階ロードマップ

1. **接続層**: 本リポジトリ `toc_nodes` を alo-kg の literature_node として登録（id体系を `alo:book:isbn:...:toc:...` で既に整合）。
2. **法令レーン（既存流用）**: 自炊PDF/OCR本文 → alo-kg resolver → 文献→法令エッジ。e-Gov着地。
3. **判例レーン（新規）**: ベンコム precedents harvest → case_spine 名寄せ → 文献→判例エッジ。
   裁判所 detail / 内部PD / オンランプの着地リゾルバ実装（deeplink.js を参照種別で一般化）。
4. **オフセット相互変換**: TOC紙面ページ ↔ 各図書館viewer_page ↔ precedents page_ を一本化。
5. **RAG**: pgvector（文献ノード）＋エッジ同梱回答。3レーン出典で着地。

## 9. 未確定・要確認

- e-Gov 人間向けURLの**条文アンカー形式**（`#Mp-At_{n}` 系）の最終確認（APIは確定）。
- ~~裁判所 `detail` の id を事件番号から解決する手段~~ → **ALOに既にメタデータあり**（事件番号→courtId）。harvest不要、既存を流用。
- ベンコム precedents の判例行→裁判所id / 判例秘書L番号の対応取得（harvest設計）。
- リーガルの法令リンク機能のURL形式（採取で確定）。

### 表示方針: JSON → HTML 優先（PDFは最後）
着地・表示は **構造化JSON（nodes/edges）が HTML を駆動する**形を優先する（PDFより使いやすい）:
- 判例 → 裁判所の **HTML判例詳細**（`detail{2|4|7}?id=`）に着地。PDF判決文は副（DLリンク）。
- 法令 → e-Gov の **HTML本文**（条文アンカー）。
- 文献 → 目次/本文はHTMLビューワーで提示し、原PDFは「該当ページを開く」導線として併設。
理由: HTMLはアンカー可・コピー可・軽量で、引用ハンドルや判例/法令リンクと地続きにできる。PDFは塊で繋ぎにくい。

## 10. 時点整合（temporal alignment）— 法律家ペインの本丸

### 10.1 ペイン
2018年刊の文献が「民法167条」を引く。2020/4/1施行の債権法改正で旧167条は実質**現166条**へ移動・改変。
文献のリンクを**現行**e-Gov 167条に素直に飛ばすと、読者は**別物の条文**に着地する（しかも気づきにくい）。
「いつの版の条文か」を文献の発行時点に合わせる＝商用ビューワーが誰もやらない価値。

### 10.2 ALOが既に持っているもの（`alo-kg/temporal.py`）
**7割できている**。`resolve_batch(records, date_field="pub_date")` ＝文献の発行日×引用法令で判定:
- `temporal_judgment`: `current / superseded / repealed / pre_enactment / unenforced_only`
- `superseded_severity`: `minor / moderate / major / structural`（系譜マップで分割・統合・全面改正を検出）
- `law_succession_map.json`: **法令の系譜データ**（split / consolidation / major_revision / rename_and_restructure）＝「現行↔過去の対応データ」の器
- 法令名の**変遷チェーン**（証取法→金商法 等）、`law_revisions.jsonl`（e-Gov施行日タイムライン）
- 既知の限界: e-Gov改正データは概ね**2017年以降**。それ以前の版は「superseded だが版を特定不可」とフラグ（補完予定）。
- スコープ: **法令レベルは Phase 1（実装済）**、**条文レベルは Phase 2（未）**。

### 10.3 外部データ源の現状（2025-2026）
- **e-Gov法令API v2（2025/3）が「特定時点の検索」に対応**＝過去時点の条文取得・廃止法令取得が可能に。
  → Phase 1（版の判定）から Phase 2（**当時の条文テキストそのもの**を出す）へ進める土台ができた。
- **条文レベルの旧→新対応**（旧167条→現166条）のクリーンなオープンデータは**まだ無い**。
  新旧対照表は Word/一太郎ベースで機械可読化は途上（デジタル庁・法務省が法令標準XML/自動生成を推進中）。
  → ここは ALO が**新旧対照表・改正附則から自前で構築**する領域（大改正から着手）。

### 10.4 段階的な価値（ペイン解消の順）
1. **誤着地の警告（今すぐ可・Phase1）**: 文献pubdate×引用法令で `temporal_judgment` を出し、
   「⚠ この引用は債権法改正(2020/4/1)前。旧法の可能性」バッジを付ける。**沈黙の誤リンクを潰すだけで激痛が消える**。
2. **当時の条文へ着地（e-Gov v2時点指定）**: 現行ではなく**発行時点の版**の条文URL/本文に着地。「すごい」の核。
3. **条文ジャンプ（旧条→新条、frontier）**: 新旧対照表/附則から `旧167条→現166条` の対応を構築。
   全法令は重いので**大改正優先**（債権法・相続法・会社法・個人情報保護法統合 等）。部分被覆で始める。

### 10.5 設計への組み込み
- 文献→法令エッジ（`law_citations`）に **`as_of`（=書誌pubdate）** と **`temporal_status`** を持たせる。
- 参照着地リゾルバ（§3）は、法令ターゲットで **temporal_status を見て版を選ぶ**:
  `current`→現行URL / `superseded`→（可能なら）当時版URL＋警告バッジ / `structural`→系譜先を提示。
- RAGの法令出典は版バッジ付きで返す（例「民法166条（2020改正後）／文献は旧167条を引用」）。
- 書誌スキーマの `bib_core.pubdate` が as_of の供給源（canonicalスキーマに既存）＝**追加採取不要**。
