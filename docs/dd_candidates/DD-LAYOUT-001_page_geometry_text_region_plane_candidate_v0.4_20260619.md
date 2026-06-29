# DD-LAYOUT-001 v0.4 — page 幾何・text-region 面 ＋ block_ref / reading projection（型別・合成読み）candidate

> **id**: DD-LAYOUT-001 / **version**: candidate v0.4 / **supersedes**: v0.3
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-19 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/OCR/embedding/canonical 発番は HOLD。
> **改訂理由（v0.3→v0.4）**: owner 着想「位置情報を持つと、脚注だけ/図表だけ/チャートだけ/本文と別紙を繋げて読む、がリッチになる」を正式化。**型フィルタ読みは v0.3 で既に無料**（block_type＋reading_order_scope）、**別紙との stitching だけが net-new** ＝ `block_ref` エッジ1枚＋「読みの射影」概念を追加。
> **承継**: v0.3 §0〜§7（中核命題・巨人の肩クロスウォーク・page_block 確定スキーマ＝座標明示/hash bundle/text_pos.state/text_quote 制限/reading_order_key+scope/ALO subtype・自己修復 STAM・ゲート6本）は**不変**。本ファイルは差分を追加。

---

## 0. 監査履歴
v0.3 = `DDLAYOUT_PASS_WITH_NOTES` blocking 反映済（RESULT Box 2295464622640）。v0.4 はその上に owner 着想の機能を追加（座標/セレクタ/hash/reading_order の v0.3 締めは維持）。

## 1. 読みの2クラス
| クラス | 例 | 必要なもの | v0.3 で足りる？ |
|---|---|---|---|
| **(a) 型フィルタ読み** | 脚注だけ／図表だけ／チャートだけ／本文だけ（脚注捨て速読） | `block_type` ＋ `reading_order_scope` への射影クエリ | **✅ 追加ゼロ** |
| **(b) stitching 読み** | 本文＋脚注＋図＋**別紙**を繋げて読む | ブロック間参照の解決 | ❌ `block_ref`（§3 net-new） |

## 2. (a) 読みの射影（reading projection）＝ v0.3 既存機能の言語化
「読みの射影」＝ `(block_type[.subtype], reading_order_scope, asset_variant)` への**クエリ**で、`reading_order_key` 昇順に並べたブロック列を返すビュー。
- 図表だけ＝`block_type ∈ {Table,Picture,Caption,Formula}`／チャートだけ＝`Picture.subtype=chart`／判例引用だけ＝`subtype=判例引用ブロック`。
- 脚注だけ＝`reading_order_scope=footnote`／本文だけ＝`scope=body`（脚注・柱・傍注を除外して速読）。
- **先行研究＝IIIF Range**（canvas/region を選んで並べる合成シーケンス＝型別ビュー）。再発明しない。射影は**派生・claim_support_eligible=false**。

## 3. (b) `block_ref`（net-new・薄いエッジ1枚）
本文と脚注/図/表/**別紙**を繋いで読むには、フィルタでなく**参照解決（stitching）**が要る。
```text
block_ref                         # 派生・release scoped・claim_support_eligible=false
  ref_id
  src_block / src_span            # 参照元（「図3参照」「*1」「別紙1のとおり」「前掲注5」）
  dst_block / dst_asset / dst_page_no   # 参照先（別page・別asset＝別紙/附録でも可）
  reference_type                  # footnote_marker | figure_ref | table_ref | formula_ref
                                  #  | appendix_ref(別紙) | exhibit_ref | cross_page | cross_doc | prior_note(前掲)
  resolver / resolver_version / confidence
  status            raw|candidate|current
  provenance        {generation_method∈{marker_match|nlp_ref|manual}, ...}
```
- これで「本文を読みながら参照先（脚注・図・別紙）を inline 差し込み／側注で並走」を合成可能。**別紙が別ファイルでも `dst_asset` で跨げる**。
- **先行研究**：TEI `@corresp`/`<note>`/`<ptr>`/`<ref>`、METS `structLink`、DocAI の reference resolution（図表・脚注参照の解決）。乗るだけ。
- **棲み分け**：DD-LITLINK＝他オブジェクト（法令/判例/語彙）への外部リンク。`block_ref`＝**同一/別紙文書内のブロック間リンク**（層が違う・衝突しない）。

## 4. 合成読みの出力（reading composition）
クエリ例：「本文を流し読み、脚注と図は参照地点で inline 展開、別紙は末尾に連結」
= body scope のブロック列（reading_order_key 順）＋ 各 src の `block_ref` closure を `reference_type` 別ポリシ（inline / 側注 / 末尾連結）で差し込む。**全て派生ビュー・非canonical・claim_support 不可**。AI エージェントは型別射影や stitching を**安価に要求**できる（ブロックが型付き・アドレス可能だから）。

## 5. ゲート（v0.3 ＋ 追加）
v0.3 既存（COORD_EXPLICIT/SELECTOR_STATE_REQUIRED/HASH_SPLIT/QUOTE_LENGTH_LIMIT/CURRENT_BY_RESOLVER_ONLY/NO_LEGAL_CLAIM_SUPPORT ＋ v0.2 基底）に加え：
- **G_LAYOUT_REF_DERIVED**：block_ref / reading projection は派生・非canonical・claim_support_eligible=false（参照解決の誤りを根拠化しない）。
- **G_LAYOUT_REF_RESOLVER_VERSIONED**：block_ref は resolver_version を持ち、誤解決は撤回可能（append-only）。
- **G_LAYOUT_PROJECTION_NO_TRUTH**：射影ビューは閲覧/供給用であり、欠落（未付与ブロック）を「存在しない」と断定しない。

## 6. 最小性（維持）
net-new は **`block_ref` エッジ1枚**のみ（型フィルタ読みは v0.3 の既存フィールドで提供）。`page_block` 本体は無改変。IIIF Range/TEI 参照/METS structLink は**概念のみ内面化**（フル XML 化しない）。

## 7. open items / loop_state
O1 reference_type の最小語彙確定／O2 resolver（marker_match/nlp_ref）の実装・confidence／O3 別紙(cross_doc)の dst_asset 解決（asset 同定＝FRBR/DD-LITID 接続）／（v0.3 由来 O は承継）。
loop_state = **v0.4（追加）→ 再監査候補**。HOLD：DDL/DB/Box mutation/mint/昇格。
