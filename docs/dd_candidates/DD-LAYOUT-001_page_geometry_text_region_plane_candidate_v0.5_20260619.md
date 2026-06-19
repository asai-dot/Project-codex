# DD-LAYOUT-001 v0.5 — page 幾何・text-region 面（自己完結 ratify 版）candidate

> **id**: DD-LAYOUT-001 / **version**: candidate v0.5 / **supersedes**: v0.4（および v0.3 を内包・自己完結化）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-19 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/OCR/embedding/canonical 発番は HOLD。
> **改訂理由（v0.4→v0.5）**: GPT Pro 再監査 `DDLAYOUT_PASS_WITH_NOTES`（RESULT Box 2295584135873）反映。**v0.4 追加（block_ref/projection）は PASS**。形式note＝「v0.4 REQUEST が v0.3 閉鎖本文を inline しきっていない」を解消するため、本 v0.5 は **v0.3 確定スキーマ＋blocking閉鎖チェックリストを内包した自己完結 ratify 文書**。＋notes gate 4本を追加。

---

## 0. 監査履歴
v0.2 `PASS_WITH_NOTES`(blocking) → v0.3 で blocking 5点反映 → v0.4 で block_ref/projection 追加（`PASS_WITH_NOTES`）→ 本 v0.5 で notes 反映＋自己完結化＝**owner ratify 候補**。

## 1. ★v0.3 blocking 閉鎖チェックリスト（ratify 前確認・self-contained）
| # | v0.2 blocking must-fix | v0.5 での状態 | 該当 |
|---|---|---|---|
| 1 | content_hash を用途別分割 | ✅ hash bundle 5種 | §2 |
| 2 | bbox に座標系/原点/寸法/回転/transform 必須 | ✅ coordinate_system/coord_origin/page_w,h/rotation_applied/transform | §2・G_LAYOUT_COORD_EXPLICIT |
| 3 | text_pos に source_text_revision State 併用 | ✅ text_pos.state | §2・G_LAYOUT_SELECTOR_STATE_REQUIRED |
| 4 | text_quote 長さ上限（著作権） | ✅ exact≤N1/prefix,suffix≤N2 | §2・G_LAYOUT_QUOTE_LENGTH_LIMIT |
| 5 | reading_order を挿入耐性キー＋scope | ✅ reading_order_key(LexoRank/decimal)+reading_order_scope | §2 |

## 2. 幾何面 `page_block`（v0.3 確定スキーマ・内包）
```text
page_block                         # 派生・release scoped・非canonical
  block_id ; asset_ref / asset_variant ; page_no
  bbox [x0,y0,x1,y1] (正規化0..1) ; coordinate_system ; coord_origin(TOPLEFT)
  page_width / page_height ; rotation_applied ; transform? ; bbox_polygon?
  block_type   # DocLayNet 11 ＋ ALO subtype(注/柱/条文囲み/判例引用ブロック/要旨)
  reading_order_key   # LexoRank or decimal path（挿入耐性）
  reading_order_scope # body|footnote|marginal|column:N（名前空間別）
  text_pos {begin,end, state:{source_text_revision_id, revision_hash, ocr_engine_ver}}  # W3C State 併用
  text_quote {exact(≤N1), prefix(≤N2), suffix(≤N2)}
  asset_content_hash / page_image_hash / block_image_hash / text_range_hash / selector_bundle_hash  # hash bundle
  toc_node_id -> biblio.toc_nodes
  confidence ; status(raw|observation|alignment|candidate|current)
  provenance {generation_method, engine, engine_version, source_text_revision_ref, provenance_family}
```
オフセット規約＝NIF/RFC5147（gap・0始）。自己修復＝STAM 整列(Needleman-Wunsch)＋transposition（1:1非前提）。

## 3. reading projection（型フィルタ読み・追加ゼロ）＋ coverage（notes 反映）
`(block_type[.subtype], reading_order_scope, asset_variant)` クエリ＝脚注だけ/図表だけ/本文だけ（先行研究 IIIF Range）。
**notes 反映**：射影結果は **coverage metadata** を必ず伴い、**未付与（未型付け）ブロックを「存在しない」と断定しない**。
```text
projection_result{ items[...], coverage{ blocks_total, blocks_typed, blocks_untyped, scope_coverage } }
```

## 4. `block_ref`（stitching・薄いエッジ1枚）＋ notes 反映
```text
block_ref                         # 派生・claim_support_eligible=false
  src_block / src_span
  dst_block / dst_asset / dst_page_no
  reference_type   # 統制語彙（§5 G_LAYOUT_REF_CONTROLLED_VOCAB）
  resolver / resolver_version / confidence ; status(raw|candidate|current)
```
- **reference_type は統制語彙**：footnote_marker|figure_ref|table_ref|formula_ref|appendix_ref|exhibit_ref|cross_page|cross_doc|prior_note。
- **stitching policy を明示**（inline/側注/末尾連結）— G_LAYOUT_REF_POLICY_EXPLICIT。
- **cross_doc の dst_asset 同定**は DD-LITID/FRBR 側で解決（asset identity）— G_LAYOUT_DST_ASSET_IDENTITY_REQUIRED_FOR_CROSS_DOC。
- 棲み分け：DD-LITLINK＝外部/法的オブジェクトへのリンク／`block_ref`＝文書内・別紙間ブロックリンク。

## 5. ゲート（全体・self-contained）
v0.2 基底（DERIVED/NO_CLAIM_SUPPORT/APPEND_ONLY/ASSET_HASH_VERIFIED/MULTISOURCE/RELEASE_SCOPED）
＋ v0.3（COORD_EXPLICIT/SELECTOR_STATE_REQUIRED/HASH_SPLIT/QUOTE_LENGTH_LIMIT/CURRENT_BY_RESOLVER_ONLY/NO_LEGAL_CLAIM_SUPPORT）
＋ v0.4（REF_DERIVED/REF_RESOLVER_VERSIONED/PROJECTION_NO_TRUTH）
＋ **v0.5 notes 追加**：
- **G_LAYOUT_REF_CONTROLLED_VOCAB**：reference_type は統制語彙のみ。
- **G_LAYOUT_REF_POLICY_EXPLICIT**：stitching の差込ポリシを明示保持。
- **G_LAYOUT_PROJECTION_COVERAGE_VISIBLE**：射影は coverage を可視化、欠落を断定しない。
- **G_LAYOUT_DST_ASSET_IDENTITY_REQUIRED_FOR_CROSS_DOC**：cross_doc は dst_asset を DD-LITID/FRBR で同定。

## 6. 不変・最小性
巨人の肩クロスウォーク（Docling/DocLayNet/STAM/W3C selectors/NIF/METS/ALTO・PAGE・hOCR/IIIF/FRBR-LRM）承継。net-new は page_block＋toc_locator＋block_ref のみ、標準は内面化のみ。検証ルート（cross-modal）は DD-XMODAL に分離。

## 7. open items / loop_state
O1 H側 DD-LAYOUT 突合／O2 reference_type 最小語彙の確定／O3 block_ref resolver 実装・confidence／O5 catalog 投影スキーマ／O6 retrofit 抽出器／O7 canonical 配置（CANONICAL_MAP）。
loop_state = `PASS_WITH_NOTES`（非blocking）→ notes 反映＋自己完結化済 → **owner ratify 候補**。HOLD：DDL/DB/Box mutation/mint/昇格。
