---
request_id: DD-LAYOUT-001-20260619
gate: DDLAYOUT
status: queued
topic: page 幾何・text-region 面（PDFに添える構造）candidate v0.1 の独立意味監査
result_expected_filename: DD-LAYOUT-001_page_geometry_DDLAYOUT_RESULT.md
target_mode: design_only
source_hash: dcd893ff33627bf356489c3b22212ee24fc26af25bb62b5c612295d8d386c893
review_scope:
  - 幾何面 page_block（bbox/block_type/reading_order/char_span/toc_node 橋渡し）の設計妥当性
  - toc_locator（目次タップ→該当ページ）の内包設計
  - 両生成経路（bbox_ocr 主 / retrofit_from_existing_ocr 従）の first-class 併存
  - 更新・付け加え・修正パターンの append-only / current-view 設計
  - 自己修復（asset_content_hash 不一致時の幾何のみ再整列・1:1 非前提）
  - 本文(LIT)と書式(FORMOBJ)の共有基盤化（FORMOBJ の bbox 欠落補完）
  - 既存スパイン（source_text_revision / toc_nodes / LITCHUNK / LITLINK）への接地の正しさ
regression_anchors:
  - DD-FORMOBJ-002 v0.2（form_witness の locating 項目・gate_witness_edition_verified）
  - 01_TOC DD v0.1（raw/observation/alignment/candidate/current・単一TOC非canonical・claim_support_eligible=false）
  - DDTOCNODES production apply（biblio.toc_nodes 552,544 行・列 book/title/page/depth/path/parent/source/status）
  - DD-LITTEXT-001（source_text_revision・hash lineage）/ DD-LITCHUNK-001 / DD-LITLINK-001
  - DD-BOOK-002 §3 / DD-BOOKQ-001（books.json digital.pdf_quality・heavy/light variant）
  - bookshelf_supabase_schema_draft（正本H側 / Box release store / Supabase read-mostly catalog / active_release pointer）
  - 三軸インデックス設計 v0.3（源泉×分野×法域・research_unit）
decision_requested: >
  本 candidate を「設計 closure 候補」として前進させてよいか。
  幾何面を 7 オブジェクト横断の独立 first-class レイヤとして切り出す方針の是非、
  net-new を page_block ＋ toc_locator の 1 レイヤに留める最小性の妥当性、
  および ratify 前に解くべき open item（特に O1: H 側既存 DD-LAYOUT 相当の突合、
  O7: canonical 配置の CANONICAL_MAP 従属）の十分性を判定されたい。
---

# DDLAYOUT 監査依頼: DD-LAYOUT-001 v0.1（page 幾何・text-region 面）

## 1. 監査対象
- 設計本体: `docs/dd_candidates/DD-LAYOUT-001_page_geometry_text_region_plane_candidate_v0.1_20260619.md`
- source_hash（sha256）: `dcd893ff33627bf356489c3b22212ee24fc26af25bb62b5c612295d8d386c893`
- gate: **設計のみ（candidate）**。DDL/DB/Box mutation/mint/OCR/embedding は HOLD（本DD §10）。

## 2. 一行
PDF に添える「紙面座標 ⇄ 論理テキスト ⇄ 構造」の橋渡し面 `page_block`（＋ `toc_locator`）を、
派生・非 canonical・`claim_support_eligible=false` のレイヤとして定義し、最小追加で AI の縦横無尽アクセスを開く。

## 3. 特に見てほしい論点（独立意味監査）
1. **first-class 切り出しの是非**: 幾何面を文献・書式の下位産物にせず横断基盤にする判断（FORMOBJ の「親を持たせない」原則との整合）。
2. **同一性**: ページ番号を同一性にせず char-offset＋content_hash を真とする設計が、再OCR・軽量版再生成に対して本当に壊れないか。
3. **両生成経路の併存**（owner 指示「2は両方」）: bbox_ocr と retrofit を上書きでなく provenance 併存で扱う設計の健全性。
4. **更新/追加/修正パターン**（owner 指示「色々パターンありそう」）: append-only＋current-view＋lineage で破壊的更新を避ける設計の十分性・抜け。
5. **claim_support 不可ゲート**: 位置決め/ナビを証拠に昇格させない境界が、TOC由来参照禁止ゲートと一貫しているか。
6. **最小性**: net-new を page_block＋toc_locator に限る主張が過小/過大でないか。

## 4. 既知の弱点・open（本DD §9）
- O1: H 側ローカルに DD-LAYOUT 相当が既存でないかの突合（再発見回避・ratify 前ゲート）。
- O2 座標系規約 / O3 block_type 語彙 / O4 reading_order 挿入耐性キー / O5 catalog 投影スキーマ / O6 retrofit 抽出器・confidence 規約 / O7 canonical 配置（CANONICAL_MAP 従属）。

## 5. 想定 verdict
`DDLAYOUT_PASS_WITH_NOTES` または `DDLAYOUT_MODIFY_REQUIRED`（must_fix 付き）。
approach reject でなく、must_fix/should_fix 反映で前進できる形での指摘を求める。
