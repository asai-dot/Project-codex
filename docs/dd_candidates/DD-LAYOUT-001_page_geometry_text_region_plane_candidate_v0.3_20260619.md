# DD-LAYOUT-001 v0.3 — page 幾何・text-region 面（PDFに添える構造）candidate

> **id**: DD-LAYOUT-001 / **version**: candidate v0.3 / **supersedes**: v0.2
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-19 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/OCR/embedding/canonical 発番は HOLD。
> **改訂理由（v0.2→v0.3）**: GPT Pro 監査 `DDLAYOUT_PASS_WITH_NOTES`（RESULT Box 2295464622640）の blocking must-fix 5点を反映。approach は是認・前進可。**本 v0.3 は blocking 反映版＝owner ratify 候補**。
> **承継**: v0.2 §0〜§14 の本体（中核命題・巨人の肩クロスウォーク・接地・最小性）は不変。本ファイルは差分を上書き定義する。

---

## 0. 監査反映サマリ（v0.2 からの blocking must-fix）
| # | GPT must-fix | v0.3 反映 |
|---|---|---|
| 1 | content_hash を用途別に分割 | §3 hash bundle（5種） |
| 2 | bbox に座標系/原点/回転/ページ寸法/transform を必須化 | §3 bbox 拡張＋G_LAYOUT_COORD_EXPLICIT |
| 3 | text_pos は source_text_revision の State を併用（W3C 推奨・リソース変更に脆い） | §3 text_pos.state＋G_LAYOUT_SELECTOR_STATE_REQUIRED |
| 4 | text_quote の保存量制限（著作権・権利制約／W3C 注意） | §3 text_quote 制限＋G_LAYOUT_QUOTE_LENGTH_LIMIT |
| 5 | reading_order は単純 int 不可（挿入耐性キー＋scope） | §3 reading_order 拡張＋O4 解決 |

## 1. 幾何面 `page_block`（v0.3 確定スキーマ）
```text
page_block                         # 派生・release scoped・非canonical
  block_id
  asset_ref / asset_variant        # heavy | light（FRBR Manifestation/Item 相当）
  page_no
  # --- 座標（G_LAYOUT_COORD_EXPLICIT：暗黙にしない）---
  bbox             [x0,y0,x1,y1]    # 正規化 0..1
  coordinate_system                 # 例 "iiif_pct" | "pixel"
  coord_origin                      # TOPLEFT（既定・IIIF/ALTO 準拠）
  page_width / page_height          # 元寸法（pixel/mm10/inch1200）
  rotation_applied                  # 度。レンダ前回転を記録
  transform         optional        # 正規化への affine（傾斜補正等）
  bbox_polygon      optional        # 湾曲/傾斜/表のみ（PAGE/TEI @points）
  block_type                        # DocLayNet 11 ＋ ALO subtype（§2）
  reading_order_key                 # 挿入耐性キー（LexoRank or decimal path 文字列）
  reading_order_scope               # body | footnote | marginal | column:N（名前空間別）
  # --- テキストへの多重セレクタ stand-off（robust anchoring）---
  text_pos          {begin, end, state}   # TextPositionSelector ＋ state
  #   state = { source_text_revision_id, revision_hash, ocr_engine_ver }  ← W3C State 併用
  text_quote        {exact, prefix, suffix}  # 長さ上限あり（§3.2）
  # --- hash bundle（G_LAYOUT_HASH_SPLIT：用途別）---
  asset_content_hash                # PDF/asset 版
  page_image_hash                   # 当該ページ画像
  block_image_hash                  # bbox 切出し画像
  text_range_hash                   # char_span のテキスト
  selector_bundle_hash              # セレクタ束全体（再アンカー検証用）
  toc_node_id     -> biblio.toc_nodes
  confidence
  status            raw|observation|alignment|candidate|current
  provenance        {generation_method, engine, engine_version, source_text_revision_ref, provenance_family}
```

### 3.2 text_quote 保存量制限（G_LAYOUT_QUOTE_LENGTH_LIMIT）
W3C は TextQuoteSelector が引用コピー方式ゆえ著作権・権利制約下で危険になりうると注意。よって `exact ≤ N1`、`prefix/suffix ≤ N2`（既定 N1=64, N2=32 字、release ポリシで調整）。長文同定は text_pos＋hash に寄せ、quote は曖昧再付着の最小素片に限定。

## 2. block_type：DocLayNet 11 ＋ ALO subtype（監査指摘＝法律書特有を吸収）
DocLayNet 11 を基層に、法律書特有を ALO subtype として後付け：`注(脚注/傍注)`／`柱(running head/ノンブル)`／`条文囲み`／`判例引用ブロック`／`要旨`。subtype は基層ラベルに `block_type.subtype` として従属（基層との互換維持）。

## 3. State 併用の意味（G_LAYOUT_SELECTOR_STATE_REQUIRED）
W3C TextPositionSelector は start/end の0始まり位置だがリソース変更に脆い。よって text_pos は**必ず** `state`（どの `source_text_revision` 版に対するオフセットか＋revision_hash）を持つ。版が変われば §自己修復（STAM 整列・転置）で新版 state の observation を別途生成、旧 state は保持。

## 4. ゲート（v0.2 ＋ 監査追加）
v0.2 既存（DERIVED / NO_CLAIM_SUPPORT / APPEND_ONLY / ASSET_HASH_VERIFIED / MULTISOURCE / RELEASE_SCOPED）に加え：
- **G_LAYOUT_COORD_EXPLICIT**：bbox は座標系/原点/寸法/回転を明示。暗黙の pixel/正規化禁止。
- **G_LAYOUT_SELECTOR_STATE_REQUIRED**：text_pos は source_text_revision state 必須。
- **G_LAYOUT_HASH_SPLIT**：単一 content_hash 禁止。用途別 hash bundle。
- **G_LAYOUT_QUOTE_LENGTH_LIMIT**：text_quote 長さ上限（著作権配慮）。
- **G_LAYOUT_CURRENT_BY_RESOLVER_ONLY**：current は resolver のみが決定（手書き昇格禁止）。
- **G_LAYOUT_NO_LEGAL_CLAIM_SUPPORT**：bbox/locator/quote/reading_order は法的 claim_support に使わない（既存 NO_CLAIM_SUPPORT の法務明示）。

## 5. 不変（v0.2 承継）
自己修復＝STAM 整列＋transposition（1:1非前提）／両生成経路 bbox_ocr・retrofit 併存（append-only・current-view）／本文(LIT)・書式(FORMOBJ) 共有基盤（FORMOBJ bbox 補完）／METS 二重 structMap 思想（論理 toc_nodes・物理 page_no）／検証ルートは DD-XMODAL に分離／標準は内面化のみ（フル METS/TEI/CIDOC 不採用）。

## 6. open items（更新）
O1 H側 DD-LAYOUT 突合／O4 **解決**＝reading_order_key（LexoRank/decimal path）＋reading_order_scope／O5 catalog 投影スキーマ／O6 retrofit 抽出器・confidence／O7 canonical 配置（CANONICAL_MAP）。O2/O3 は v0.3 で解決済（座標明示・DocLayNet11＋subtype）。

## 7. loop_state
DDLAYOUT_PASS_WITH_NOTES の blocking_before_ratify＝§0 の5点を本 v0.3 で反映済 → **blocking 解消＝owner ratify 候補**。HOLD：DDL/DB/Box mutation/mint/昇格。
