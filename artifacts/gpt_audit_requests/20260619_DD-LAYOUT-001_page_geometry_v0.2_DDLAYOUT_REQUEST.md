---
request_id: DD-LAYOUT-001-v0.2-20260619
supersedes_request_id: DD-LAYOUT-001-20260619
topic: page 幾何・text-region 面 candidate v0.2（先行研究3クラスタ接地版）の独立意味監査
gate: DDLAYOUT
status: queued
result_expected_filename: 20260619_DD-LAYOUT-001_page_geometry_v0.2_DDLAYOUT_RESULT.md
target_mode: inline_embedded
source_hash: sha256:7c79e46fd179cb08864a598518c16d183af19de0f39166622127019b34163c1d
review_scope:
  include:
    - 「巨人の肩」クロスウォーク（§1）の対応付けが正確か（Docling ProvenanceItem / DocLayNet11 / STAM / W3C selectors / NIF-RFC5147 / METS structMap / ALTO-PAGE-hOCR / IIIF / FRBR-LRM）
    - page_block の多重セレクタ robust anchoring（text_pos + text_quote + content_hash）の妥当性
    - 自己修復＝STAM 整列(Needleman-Wunsch)＋transposition の設計健全性（1:1非前提）
    - 両生成経路（bbox_ocr / retrofit）併存・append-only/current-view
    - claim_support_eligible=false ゲートの一貫性
    - 最小性（net-new = page_block + toc_locator、標準は内面化のみ）
  exclude:
    - 三軸 v0.3（源泉×分野×法域）の中身（既決）
    - DD-LITRIGHTS 不作成（既決）
    - toc_nodes 本番投入の事実（552,544・既決）
    - FORMOBJ 4層分離・form_uid opaque（owner ratify 済）
regression_anchors:
  - DD-FORMOBJ-002 v0.2（Box 2286527242803）
  - 01_TOC DD v0.1（Box 2279844275881）claim_support_eligible=false / TOCDRIFT
  - DDTOCNODES production apply（Box 2285740892425）biblio.toc_nodes 552,544
  - 02_LIT_DESIGN_RECORD_CLEANED（Box 2286222789037）source_text_revision/chunk/link
  - bookshelf_supabase_schema_draft（Box 2205460643463）正本H/Box release/Supabase catalog
  - DD-BOOKQ-001 v0.2（Box 2257663257570）digital.pdf_quality
  - prior_art: Docling arxiv:2501.17887 / DocLayNet arxiv:2206.01062 / STAM annotation.github.io/stam / W3C annotation-model / NIF RFC5147 / METS loc.gov/standards/mets / ALTO loc.gov/standards/alto / IIIF iiif.io / FRBR-LRM ifla.org
self_doubt:
  - 幾何面を独立 first-class にすべきか LITASSET/TOC 下位かの線引き
  - retrofit(B) の char_span 整列の現実精度（既存OCR座標なし）
  - reading_order 挿入耐性キー（実数/LexoRank）未確定（O4）
  - catalog 投影先（toc_index に page 無し）未定（O5）
  - H側ローカルに DD-LAYOUT 相当が既存でないか Box から確認不能（O1）
questions_for_gpt:
  - 設計 closure 候補として前進可か
  - 幾何面 first-class 化の是非（FORMOBJ「親なし」原則整合）
  - ページ番号を同一性にせず char-offset＋content_hash＋多重セレクタを真とする設計は再OCR・軽量版再生成に壊れないか
  - 標準の「内面化のみ（フルMETS/TEI/CIDOC不採用）」の線引きは妥当か
  - ratify 前ゲート（O1 H側突合・O7 canonical配置）の十分性
decision_requested:
  - PASS可否 / closure候補前進可否 / 幾何面 first-class 採否 / 最小性の妥当性 / 追加 must_fix
expected_label: DDLAYOUT_PASS_WITH_NOTES または DDLAYOUT_MODIFY_REQUIRED（approach reject でなく must_fix/should_fix で前進できる形を希望）
---

# DDLAYOUT 監査依頼: DD-LAYOUT-001 v0.2（page 幾何・text-region 面・標準接地版）

- target_mode: inline_embedded（全文を下記に逐語埋め込み）。authoritative bytes = GitHub `asai-dot/Project-codex` ブランチ `claude/daiichi-houki-fact-system-qcn7ph` `docs/dd_candidates/DD-LAYOUT-001_page_geometry_text_region_plane_candidate_v0.2_20260619.md`（PR #32, sha256:7c79e46f…）。
- gate: 設計のみ candidate。DDL/DB/Box mutation/mint/OCR/embedding は HOLD。
- v0.1 からの差分: 「幾何・テキスト・構造を分離し疎結合で持つ」発想の先行研究3クラスタを反映し、白地でない部分を全て既存標準に接地（§1 クロスウォーク）。

## 特に見てほしい点
1. §1 クロスウォークの対応が正確か（誤った権威付け・誤接続がないか）。
2. 多重セレクタ＋STAM 転置で「再OCR・軽量版再生成に壊れない」が本当に成り立つか。
3. 標準の「内面化のみ」線引き（フルMETS/TEI/CIDOC不採用）が過小/過大でないか。
4. 最小性（net-new = page_block + toc_locator）の主張。

===== 監査対象本文（逐語・inline_embedded）=====

# DD-LAYOUT-001 v0.2 — page 幾何・text-region 面（PDFに添える構造）candidate

> **id**: DD-LAYOUT-001 / **version**: candidate v0.2 / **supersedes**: v0.1 candidate（2026-06-19、同日先行研究3クラスタ反映で改訂）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-19 JST
> **gate**: **設計のみ（candidate）**。DDL・DB書込み・Box mutation・mint・OCR/embedding 実行・canonical 発番は **含まない／HOLD**。
> **canonical 配置**: 未決（CANONICAL_MAP 従属）。`docs/dd_candidates/` に candidate 配置、`docs/tmplstruct/` 昇格は owner ratify 後。
> **改訂理由（v0.1→v0.2）**: 「幾何・テキスト・構造を分離し疎結合で持つ」設計の**先行研究を3クラスタ調査**し、確立済み標準に乗せ替え（再発明の排除）。**白地でない部分は全て出典に接地**した。

---

## 0. 中核命題（不変）

PDF は線形テキストでない（段組・脚注・表・図・ヘッダ・ノンブル）。AI が PDF を縦横無尽に読むには、**ページ画像（pixels）・論理テキスト（OCR本文）・構造（章節）を一つの座標系で相互参照**できる必要がある。既存スパイン（`source_text_revision` char-offset／`toc_nodes` path）に対し**紙面幾何の面が空いている**。本 DD は幾何面 `page_block`（＋ `toc_locator`）を、**派生・非 canonical・claim_support_eligible=false** のレイヤとして定義する。

**v0.2 の姿勢**: この分離＝疎結合（stand-off）の発想は図書館・NLP・Document AI で確立済み。**自前で建てず巨人の肩に乗る**。novelty として主張するのは、この面の上に載る AI 連続応用（→ DD-XMODAL-001）であって、幾何面の表現そのものではない。

---

## 1. ★巨人の肩クロスウォーク（我々の要素 → 乗る既存標準・出典）

| 我々の要素 | 乗る既存標準/研究 | 出典 |
|---|---|---|
| `page_block{page, bbox, char_span}` の形 | **Docling `ProvenanceItem{page_no, bbox, charspan}`** | arxiv 2501.17887 / docling-project.github.io |
| `block_type` 語彙 | **DocLayNet 11ラベル**（Caption/Footnote/Formula/List-item/Page-footer/Page-header/Picture/Section-header/Table/Text/Title） | arxiv 2206.01062 |
| `reading_order` | **PAGE `ReadingOrder/OrderedGroup/RegionRefIndexed`**（最明示）／LayoutReader-ReadingBank | PRImA PAGE-XML / arxiv 2108.11591 |
| 幾何＋OCR の入力取り込み | **ALTO**（HPOS/VPOS/WIDTH/HEIGHT, String@CONTENT/WC）, **hOCR**(`bbox`,`x_wconf`), **PAGE**(polygon) | loc.gov/standards/alto, kba.github.io/hocr-spec |
| テキストへの参照（bbox側は文字を持たない） | **stand-off**：NIF `beginIndex/endIndex`(RFC5147 gap・0始) / UIMA `begin/end` / ISO24612 LAF anchor | nif-core, uima.apache.org, iso 24612 |
| 自己修復（再OCR→整列→転置） | **STAM**：TextResource/Offset + Needleman-Wunsch/Smith-Waterman alignment & **transposition** | annotation.github.io/stam |
| robust anchoring（多重セレクタ） | **W3C Web Annotation**：TextPositionSelector + TextQuoteSelector{exact,prefix,suffix} / Hypothes.is fuzzy / CDC-Rabin / Memento(RFC7089) | w3.org/TR/annotation-model |
| 構造スパイン `toc_nodes`(path/depth/type/order/page) | **METS logical structMap**(div/ORDER/TYPE/LABEL) ＋ physical structMap ＋ structLink / TEI `<div>` / IIIF `Range`(structures) | loc.gov/standards/mets, iiif.io presentation 3.0 |
| テキスト⇄座標の繋ぎ | **METS `<area FILEID SHAPE COORDS>`** / **TEI `@facs`**（任意要素→zone） | mets / tei-c.org PH |
| 画像領域配信 | **IIIF Image API** `{id}/{region}/{size}/{rotation}/{quality}.{fmt}`（`pct:x,y,w,h`）＋ Canvas `#xywh`(Media Fragments) | iiif.io/api/image/3.0, w3.org/TR/media-frags |
| 書誌同一性 work/expression/asset | **FRBR/IFLA LRM WEMI** / **BIBFRAME** Work/Instance/Item / LRMoo | ifla.org LRM, loc.gov/bibframe |
| 版/drift・as_of | **Memento RFC7089**（reference rot = link rot + content drift） | rfc-editor.org/rfc/rfc7089 |

→ 幾何面の表現は**ほぼ全部既存**。借りた各行が本 DD の prior_art アンカー。

## 2. 接地する既存（ALO内）オブジェクト
- テキストスパイン = DD-LITTEXT-001 `source_text_revision`（char-offset・hash lineage）。
- 構造スパイン = `biblio.toc_nodes`（DDTOCNODES 本番投入済 552,544 行。列 book/title/page/depth/path/parent/source/status）。
- 意味 = DD-LITCHUNK-001（chunk / embedding 境界。境界決定に **CDC/Rabin** を採用）。
- 関係 = DD-LITLINK-001。資産 = books.json `digital.*`（DD-BOOK-002/BOOKQ、heavy/light variant）。
- 位置決め先例 = FORMOBJ `form_witness.{page_span,toc_node,content_hash,...}`（bbox 欠落を本 DD が補完）。
- 観測ライフサイクル = 01_TOC DD `raw/observation/alignment/candidate/current`、単一観測非canonical、TOCDRIFT。

## 3. 幾何面 `page_block`（Docling ProvenanceItem 形に整合）
```text
page_block                         # 派生・release scoped・canonical にしない
  block_id
  asset_ref / asset_variant        # heavy | light（pixels の出所＝FRBR Manifestation/Item 相当）
  page_no                          # 物理ページ（Docling 命名に整合）
  bbox            [x0,y0,x1,y1]     # ページ正規化 0..1（IIIF pct: と同思想・DPI非依存）
  bbox_polygon    optional          # 湾曲/傾斜/表のみ（PAGE/TEI @points 式）
  block_type      DocLayNet 11ラベル
  reading_order   int               # PAGE ReadingOrder 準拠
  # --- テキストへの stand-off 参照（多重セレクタ＝robust anchoring）---
  text_pos        {begin,end}       # TextPositionSelector ＝ source_text_revision の char-offset（NIF/RFC5147 gap・0始）
  text_quote      {exact,prefix,suffix}  # TextQuoteSelector（内容で再付着・自己修復の片割れ）
  content_hash                      # CDC/Rabin 安定識別（asset版・内容検証）
  toc_node_id     -> biblio.toc_nodes    # 論理構造への逆リンク（METS area↔div, TEI @facs）
  confidence
  status          raw|observation|alignment|candidate|current
  provenance      {generation_method, engine, engine_version, source_text_revision_ref, asset_content_hash, provenance_family}
```
- **オフセット規約を固定**：NIF/RFC5147（gap基準・0始まり・`char=B,E`）。`source_text_revision` 側もこの規約。
- **多重セレクタ必須**：`text_pos`（高速）＋`text_quote`（内容再付着）＋`content_hash`（検証）。フォールバック順で再アンカー（§6）。

### 3.1 `toc_locator`（目次タップ→該当ページ。①内包）
```text
toc_locator{ toc_node_id, asset_ref, asset_variant, printed_page, page_no, page_offset, content_hash, status }
```
IIIF Image API では `bbox(正規化)→pct:x,y,w,h`、Canvas は `#xywh` で領域配信。

## 4. 生成経路（両方 first-class・owner「2は両方」）
`provenance.generation_method ∈ { bbox_ocr | retrofit_from_existing_ocr | manual | imported_external }` を併存（上書きしない）。
- **A bbox_ocr（主）**：将来OCRで本文と座標を同時出力（char_span と bbox 同源）。入力取り込みは **ALTO/PAGE/hOCR アダプタ**経由で内部 `page_block` に正規化。
- **B retrofit（従だが first-class）**：座標なし既存OCR＋画像から後付け推定し char_span 整列。A を待たず既存蔵書に幾何を付与。
- A/B は同一ページに併存、`current` は confidence/provenance で解決（§5、相関注意）。

## 5. 更新・追加・修正（append-only＋current-view）
新 observation 追記→resolver が current 切替、旧は status 降格で**残す**。reading_order は挿入耐性キー（実数/LexoRank、O4）。本文世代更新は revision ごとに別 observation。asset 版更新は §6。**上書き禁止・lineage 保持**。

## 6. 自己修復（崩れても追従）＝ STAM 整列＋転置
- 真は char-offset（テキストスパイン）と content_hash。ページ番号を同一性にしない。
- 軽量版再生成でページが結合/分割/回転/再圧縮 → `asset_content_hash` 不一致検知 → **その asset の幾何のみ再整列**。char_span/toc_node/chunk/embedding は無傷。
- 整列は **STAM の Needleman-Wunsch/Smith-Waterman でテキスト整列→annotation transposition**。1:1 非前提（範囲対応）。
- 再付着フォールバック順（Hypothes.is robust anchoring）：text_pos → text_pos+range → **text_quote(prefix/suffix fuzzy)** → quote fuzzy。低 confidence は candidate 止まり（人手）。

## 7. 本文(LIT)と書式(FORMOBJ)の共有基盤
`page_block` を LIT chunk も FORM witness も消費。FORMOBJ `form_witness.page_span/toc_node` を同じ `page_block` で **bbox 接地**（FORMOBJ の bbox 欠落補完）。一つの座標系で本文の論点位置と書式の条項位置を扱う。

## 8. 構造リンク（METS 二重 structMap 思想）
論理（`toc_nodes`）と物理（`page_no`）を**別軸**に保ち、リンクで繋ぐ（METS logical/physical structMap + structLink が先例）。`toc_nodes` 拡張対応：`type`←div TYPE、`order`←ORDER、`label`←LABEL。

## 9. ゲート
- G_LAYOUT_DERIVED（派生・非canonical）／G_LAYOUT_NO_CLAIM_SUPPORT（bbox/locator/reading_order/quote は claim_support_eligible=false）／G_LAYOUT_APPEND_ONLY／G_LAYOUT_ASSET_HASH_VERIFIED（content_hash 検証下でのみ current 化）／G_LAYOUT_MULTISOURCE（同一 provenance_family 多数決禁止）／G_LAYOUT_RELEASE_SCOPED（catalog 投影・active_release 経由）。

## 10. 検証ルート（cross-modal）への接続
幾何面 bbox は「原典ピクセルへの再入口」。テキスト/構造の誤謬時に bbox 領域を再レンダ→画像認識（visual_reocr）→spine へ STAM 転置→diff＝誤謬シグナル。この**多モーダル三角測量と“生きたコーパス”は別 DD `DD-XMODAL-001` に分離**（本 DD は面とアンカーの供給に限定＝最小性維持）。

## 11. 採用しない/過剰（最小性）
フル METS/TEI/CIDOC-CRM を採らない（structMap/area→file→coords とstandOff の**設計原理だけ**内面化）。ALTO/PAGE/hOCR は**入力アダプタ**で内部は `page_block` に一本化（PAGE ポリゴン/glyph は optional）。NIF は**オフセット規約のみ**（RDF 化しない）。IIIF は **Range 概念と region 文法のみ**（Manifest 必須化しない）。FRBR は **WEMI 4層のみ**（イベントオントロジ不要）。

## 12. open items（ratify 前）
O1 H側 DD-LAYOUT 相当の突合（再発見回避）／O2 **解決方針**＝座標は IIIF `pct:`／ALTO 原点左上に準拠／O3 **解決**＝block_type は DocLayNet 11／O4 reading_order 挿入耐性キー選定／O5 catalog 投影スキーマ（現 toc_index は page 無し）／O6 retrofit 抽出器・confidence 規約／O7 canonical 配置（CANONICAL_MAP 従属）。

## 13. HOLD
DDL/DB/backfill/mint/Box mutation/OCR/embedding/production mapping/single-source canonical/docs-tmplstruct 昇格。

## 14. 最小性
net-new は実質 `page_block`（幾何面）＋ `toc_locator` の1レイヤ。表現は既存標準に接地。最小追加で AI の縦横無尽アクセスが開く。
