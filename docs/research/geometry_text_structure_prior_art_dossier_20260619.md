# 先行研究ドシエ：幾何・テキスト・構造の「分離＋疎結合」— 出典付き調査記録

> **date**: 2026-06-19 JST / **author**: 番頭(リモートClaude)＋背景調査エージェント3本 / **status**: research record（保存用・非DD）
> **目的**: DD-LAYOUT-001（幾何面）/ DD-XMODAL-001（3面合意）が乗っている既存標準・研究を、出典とともに独立保存する。「再発明していない」証跡。DDに溶け込んだ知見の原典控え。
> **feeds**: DD-LAYOUT-001 v0.5（accepted）/ DD-XMODAL-001 v0.4（accepted）/ DD-XDOC-001（文献間比較）。
> **一次情報優先**：loc.gov / iiif.io / tei-c.org / ifla.org / w3.org / arxiv / 各実装公式。一部サイトは自動取得に 403 を返したため正規ミラー（GitHub スキーマ等）から要素名を抽出、URLは正典。

---

## 0. 結論（巨人の肩クロスウォーク）
| 我々の要素 | 乗る既存標準/研究 | 出典 |
|---|---|---|
| `page_block{page_no,bbox,char_span}` の形 | Docling **ProvenanceItem**{page_no,bbox,charspan} | arxiv:2501.17887 / docling-project.github.io |
| `block_type` 語彙 | **DocLayNet 11ラベル** | arxiv:2206.01062 |
| `reading_order` | **PAGE ReadingOrder** / LayoutReader-ReadingBank | PRImA / arxiv:2108.11591 |
| 幾何＋OCR 入力取り込み | **ALTO** / **hOCR** / **PAGE** | loc.gov/standards/alto / kba.github.io/hocr-spec / primaresearch.org |
| 本文への stand-off 参照 | **NIF**(RFC5147) / **UIMA CAS** / **ISO24612 LAF** | nlp2rdf / uima.apache.org / iso 37326 |
| 自己修復（再OCR→整列→転置） | **STAM** + Needleman-Wunsch/Smith-Waterman | annotation.github.io/stam |
| robust anchoring（多重セレクタ） | **W3C Web Annotation** selectors / Hypothes.is fuzzy / **CDC-Rabin** / **Memento(RFC7089)** | w3.org/TR/annotation-model |
| 構造スパイン `toc_nodes` | **METS structMap**(logical/physical) / TEI div / **IIIF Range** | loc.gov/standards/mets / iiif.io |
| テキスト⇄座標 | METS `<area>` / **TEI @facs/zone** | mets / tei-c.org |
| 画像領域配信 | **IIIF Image API** region(pct:) / Canvas #xywh | iiif.io/api/image/3.0 / w3.org/TR/media-frags |
| 書誌同一性 work/expression/asset | **FRBR/IFLA LRM WEMI** / BIBFRAME / LRMoo | ifla.org / loc.gov/bibframe |
| 2-of-3 合意（誤謬/構造発見） | **Fellegi-Sunter** / **Snorkel** / co-training / consensus clustering / multi-view outlier / FRBRization / RoadRunner | §3 |

---

## CLUSTER 1 — Document AI / レイアウト・アンカリング

### 1.1 レイアウトデータセット & block_type 語彙
- **DocLayNet**（IBM, 80,863ページ手動注釈, COCO）11ラベル（**verbatim**）: `Caption / Footnote / Formula / List-item / Page-footer / Page-header / Picture / Section-header / Table / Text / Title`。→ block_type 正準。 arxiv.org/abs/2206.01062 ; github.com/DS4SD/DocLayNet
- **PubLayNet**（~330K）5カテゴリ: text/title/list/table/figure。 arxiv.org/abs/1908.07836
- **DocBank**（500K, トークン単位・弱教師）12ラベル（Abstract/Author/Caption/Date/Equation/Figure/Footer/List/Paragraph/Reference/Section/Table/Title）。 arxiv.org/abs/2006.01038

### 1.2 Docling DoclingDocument（bbox＋provenance＋reading order を1構造で保持）
- content collections: `texts/tables/pictures/key_value_items/form/groups`、構造ツリー: `body/furniture/groups`、`pages`。
- 各 item に `self_ref`(`#/texts/3`)・`parent`・`children`(RefItem `{"$ref":...}`)。**reading order = body/groups の children 順走査**（別配列を持たない）。
- 各 item の `prov` = **ProvenanceItem**{`page_no`, `bbox`(l,t,r,b + coord_origin TOPLEFT/BOTTOMLEFT), `charspan`[start,end]}。← `page_block` の直接先例。
- arxiv.org/abs/2501.17887 ; docling-project.github.io/docling/concepts/docling_document/ ; schema: github.com/docling-project/docling-core/blob/main/docs/DoclingDocument.json

### 1.3 reading order
- **LayoutReader**（LayoutLM 上, seq2seq, ReadingBank 500K）。 arxiv.org/abs/2108.11591 ; github.com/doc-analysis/ReadingBank
- Detect-Order-Construct（階層＋順序のツリー構築）arxiv.org/abs/2401.11874

### 1.4 drift 耐性 / robust anchoring
- **STAM (Stand-off Text Annotation Model)**: `TextResource`(不変テキスト)/`TextSelection`/`Offset{begin,end}`/`Annotation`。**自動整列（Smith-Waterman / Needleman-Wunsch）→ annotation transposition**（旧→新テキストへ転置）。← 自己修復の正体。 annotation.github.io/stam ; github.com/annotation/stam
- **W3C Web Annotation Data Model**: `TextPositionSelector{start,end}`（0始・State 併用推奨, リソース変更に脆い）/ `TextQuoteSelector{exact,prefix,suffix}`（引用コピー＝著作権注意）/ `RangeSelector`/`FragmentSelector`/`refinedBy`。 w3.org/TR/annotation-model
- **Hypothes.is fuzzy anchoring / W3C Robust Anchoring**: 複数セレクタ冗長保持＋フォールバック（DOM range → 位置 → quote prefix/suffix fuzzy → quote fuzzy）。 web.hypothes.is/blog/fuzzy-anchoring/ ; w3.org/2014/04/annotation/slides/RobustAnchoring.pdf
- **CDC / Rabin（content-defined chunking）**: rolling hash 境界・編集局所性（1挿入は周辺chunkのみ影響）。 arxiv.org/abs/2409.06066
- **Memento RFC7089**（reference rot = link rot + content drift; TimeGate/TimeMap）。 rfc-editor.org/rfc/rfc7089.html ; Hiberlink: doi.org/10.1371/journal.pone.0115253

---

## CLUSTER 2 — 図書館・文化遺産デジタル化標準 / stand-off 標準

### 2.1 METS（構造＋パッケージング）
- 7セクション（metsHdr/dmdSec/amdSec/fileSec/structMap/structLink/behaviorSec）。
- `structMap TYPE="logical"`（章節）vs `"physical"`（ページ列）を**別ツリー**で両立。`div`(TYPE/ORDER/ORDERLABEL/LABEL/DMDID)。
- 繋ぎ：`div → fptr → area`(SHAPE=RECT/CIRCLE/POLY, COORDS, BEGIN/END/BETYPE) → `fileSec/file → FLocat xlink:href` → 外部ALTO/画像。
- → 論理structMap ↔ `toc_nodes`、area→file→coords ↔ `page_block`。 loc.gov/standards/mets ; METSPrimerRevised.pdf

### 2.2 ALTO（ページ幾何＋OCRテキスト）
- 階層 Page>PrintSpace>TextBlock>TextLine>String。座標 `HPOS/VPOS/WIDTH/HEIGHT`（原点左上）、`String@CONTENT`＋`WC`。単位 `MeasurementUnit`=pixel/mm10/inch1200。`PHYSICAL_IMG_NR`(綴り注意)。
- → ALTO ↔ `page_block`(bbox＋文字)。METS=構造, ALTO=幾何+テキスト の役割分担。 loc.gov/standards/alto/techcenter/layout.html

### 2.3 PAGE / hOCR
- **PAGE**: Region>TextLine>Word>Glyph。幾何=**ポリゴン** `Coords@points`+`Baseline`。**ReadingOrder>OrderedGroup>RegionRefIndexed**（最明示）。`TextEquiv/Unicode`（@conf）。 primaresearch.org/schema/PAGE
- **hOCR**: HTML マイクロフォーマット。class=`ocr_page/ocr_carea/ocr_par/ocr_line/ocrx_word`、`title` に `bbox x0 y0 x1 y1`/`x_wconf`/`baseline`。 kba.github.io/hocr-spec/1.2
- 交換選択：軽量bbox=hOCR / ポリゴン・明示読み順=PAGE / 図書館連携=ALTO。

### 2.4 IIIF
- Presentation 3.0: Collection/Manifest/Canvas/Range/Annotation（全 `items`）。Canvas=抽象座標空間（height/width）。**論理TOC = Manifest.structures の Range（入れ子）**。
- 領域：Canvas URI + Media Fragments `#xywh=x,y,w,h`（サーバ不要）。Image API URL: `{id}/{region}/{size}/{rotation}/{quality}.{format}`、region=`pct:x,y,w,h`。
- IIIF Annotation = **W3C Web Annotation そのもの**。Content Search 2.0 は TextQuoteSelector。 iiif.io/api/presentation/3.0 ; iiif.io/api/image/3.0

### 2.5 TEI
- 3層：画像幾何=`<facsimile><surface><zone>`(@ulx,@uly,@lrx,@lry / @points)+`<graphic @url>`／論理=`<text><div>`+`<pb>/<lb>`／リンク=`@facs`(任意要素→zone)/`@corresp`/`<standOff>`(P5 3.4.0)。 tei-c.org/release/doc/tei-p5-doc/en/html/PH.html ; ref-standOff.html

### 2.6 書誌同一性
- **FRBR Group1 WEMI**: Work →(realized through)→ Expression →(embodied in)→ Manifestation →(exemplified by)→ Item。
- **IFLA LRM**(2017, 11実体, WEMI=E2..E5)。**LRMoo/CIDOC-CRM**(F1/F2/F3/F5)。**BIBFRAME 2.0**: Work/Instance/Item。
- → work_id=Work、expression=Expression、asset=Manifestation+Item。 ifla.org LRM PDF ; loc.gov/bibframe

### 2.7 stand-off 言語標準
- **ISO 24612:2012 LAF/GrAF**: character offset anchor → region → node/edge + feature structure。 iso.org/standard/37326.html
- **NIF 2.0**: RDF/URI offset、`nif:Context`(isString)、`beginIndex/endIndex`（**RFC5147 gap・0始**）、URI `#char=B,E`。 nlp2rdf core
- **UIMA CAS/Sofa**: Sofa(解析対象)に begin/end の stand-off。1 CAS 複数 View。 uima.apache.org
- inline vs stand-off: stand-off は一次データ不変・重複/並行階層可・非XML可、欠点=offset drift。 Thompson&McKelvie 1997

### 2.8 採らない（最小性）
フル METS/TEI/CIDOC-CRM/NIF-RDF/IIIF-Manifest 必須化は過剰。**設計原理（structMap分離・area→coords・standOff・offset規約・Range・region文法・WEMI）だけ内面化**、ALTO/PAGE/hOCR は入力アダプタ。

---

## CLUSTER 3 — 多観測の一致・不一致（誤謬検出 & 潜在構造発見）

| ニーズ | 既存枠組み | 出典 |
|---|---|---|
| 2面一致→自己教師ラベル化 | **Co-training**(条件付独立2視点)/co-regularization | COLT1998(Blum&Mitchell) / ICML-W2005(Sindhwani) |
| 3ノイズ源を相関込み確率ラベル化 | **Data programming / Snorkel label model** | arxiv:1605.07723 / VLDB2017 |
| match/**possible-match**/non-match の3決定 | **Fellegi-Sunter**(log(m/u), Neyman-Pearson) | JASA1969 |
| 複数ビュー→コア/境界 | **consensus clustering(EAC, co-association)** | TPAMI2005(Fred&Jain) |
| 1面だけ外れ検出 | **multi-view outlier detection**(class outlier) | IJCAI2015 / TIP2018(Zhao&Fu) |
| 版違いを work へ束ねる | **FRBRization / work-set** | OCLC Research(Hickey&Toves) |
| 反復テンプレ/section 帰納 | **wrapper/template induction(RoadRunner)** | VLDB2001(Crescenzi) |
| 視覚-意味の緩い一致（限定） | **CLIP** | arxiv:2103.00020 |

**設計上の核心（DD-XMODAL に反映済）**：
- 「2-of-3」= Fellegi-Sunter possible-match＋Snorkel label model（生多数決でなく相関補正）。
- **独立性の破れ**：3面は条件付き独立でない（同スキャン/OCR由来）。素朴多数決は相関2票が正しい1票を潰す→**相関補正必須**。
- ∴ 第3軸は**外部の法律体系**＝D0(prior)/D1(mapper, T結合=非独立)/D2(外部証拠)に分割し、**confirmed には D2＋独立2 family**（external_source_family registry）。「外部語彙で飾った自己一致」を遮断。

---

## 参考文献（一次URL・抜粋）
DocLayNet arxiv.org/abs/2206.01062 ／ Docling arxiv.org/abs/2501.17887, docling-project.github.io ／ LayoutReader arxiv.org/abs/2108.11591 ／ STAM annotation.github.io/stam ／ W3C Web Annotation w3.org/TR/annotation-model ／ Hypothes.is web.hypothes.is/blog/fuzzy-anchoring/ ／ CDC arxiv.org/abs/2409.06066 ／ Memento rfc-editor.org/rfc/rfc7089.html ／ METS loc.gov/standards/mets ／ ALTO loc.gov/standards/alto ／ PAGE primaresearch.org/schema/PAGE ／ hOCR kba.github.io/hocr-spec/1.2 ／ IIIF iiif.io/api/presentation/3.0, iiif.io/api/image/3.0 ／ Media Fragments w3.org/TR/media-frags ／ TEI tei-c.org/release/doc/tei-p5-doc ／ FRBR/LRM ifla.org ／ BIBFRAME loc.gov/bibframe ／ LRMoo/CIDOC-CRM cidoc-crm.org ／ ISO24612 iso.org/standard/37326.html ／ NIF nlp2rdf ／ UIMA uima.apache.org ／ Fellegi-Sunter JASA1969 ／ Snorkel arxiv:1605.07723, VLDB2017 ／ Co-training COLT1998 ／ EAC TPAMI2005 ／ multi-view outlier IJCAI2015 ／ FRBRization OCLC ／ RoadRunner VLDB2001 ／ CLIP arxiv:2103.00020
