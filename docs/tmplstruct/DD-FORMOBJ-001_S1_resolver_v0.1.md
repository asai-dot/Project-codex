# DD-FORMOBJ-001 S1: 式→toc_nodeアドレスリゾルバ 仕様 v0.1

> gate: 設計＋参照実装のみ。DB非書込み。実装: `tools/form_address_resolver.py`（自己テスト7/7 PASS）。
> 役割: S2 snapshotの anchor の null（`toc_node_id / page_span_print / span_kind`）を機械で埋める。

## 1. 入出力
- 入力: `form_title`（式名）, 当該書籍の `toc_nodes`配列, 任意 `form_page_hint`, 任意 `parent_scope_id`
- 出力: `Resolution{ toc_node_id, match_kind, match_score, decision_status, page_span_print, span_kind, norm_version, note, candidates }`
- 前段 S1a（書籍解決）: source_book → `canonical_book_id`（DD-LITID identity, isbn13_exact等）。本リゾルバは S1b（ノード解決）。

## 2. norm_title_v1（誤謬クラス吸収つき）
`NFKC → PUA(U+E000-F8FF)除去 → 確定誤謬クラス語単位置換 → lower → 記号統一 → 空白/約物除去`
- **確定誤謬クラス**: LB系統OCR「廷→延」を**語単位**で吸収（公判延→公判廷 等）。
  - 語単位なので「順延/延期」の正当な「延」は不変（過剰マージ無し）＝テスト実証。
- `norm_version` をResolutionに記録（誤謬クラス追加時は version up、DD-TOCATTACH §1.2準拠）。

## 3. マッチ ladder（親パス修飾＋ordinalタイブレーク）
1. **normalized_title 一致** → 一意なら `auto`(0.95)
2. **包含一致**（式名⊆ノード見出し or 逆、最短6字以上）→ 書式集の「巻末資料1〔型〕<式名>」型を拾う → `auto`
3. 複数候補 → `form_page_hint` で**ページ近接タイブレーク**(`review`0.8)／ヒント無しは `title_only`(`review`0.6, 候補列挙)
4. **一致無し（解説埋込型）** → `form_page_hint` から**内包セクションへフォールバック**。同頁は最深(ordinal大)を選択
   → `span_kind=embedded` / `embedded_parent` / `review`（vision再分割対象）
5. ヒントも無ければ `unmatched`

- **親パス修飾スコープ** `parent_scope_id`: 逐条の「Ⅰ 趣旨」反復のような書内衝突を部分木で一意化（DD-TOCATTACH §1.3、E0で衝突率6.5-9.7%→0.19-1.58%）。
- **ノード発明しない**: 一致が無くても親へ係留するだけ（`gate_no_node_invention`）。

## 4. page_span 導出
ノードに `end_page` があれば採用、無ければ**次の同階層以上(level≤)ノードの page-1** を終端に。
※ `page_span_print`（印刷/headline頁）。PDF物理頁は本ごとの `page_offset_pdf_minus_print` で換算（S2側 anchorで保持）。

## 5. decision_status の扱い
| status | 意味 | 後段 |
|---|---|---|
| auto | 正規化/包含一致が一意 | そのまま anchor確定 |
| review | 複数候補/埋込/title_only | 人手 or vision再分割（埋込型）で確定 |
| unmatched | 手当なし | 式インベントリ側の見直し |

## 6. tmplstruct含意（§13-3への回答）
- **書式集型**（独立ノード）: ladder1-2で `auto`、page_spanそのまま → S2量産が機械化。
- **解説埋込型**（契約解消の解除通知例等）: 独立ノード無し→内包セクションへ係留＋`embedded`フラグ＋頁範囲。
  この頁範囲を **vision で再分割**して式を切り出す（S2のpage_span内サブセグメント）＝§13-3の運用。

## 7. 次段
- toc_nodes投入後、出典本175×式インベントリに対しバルク適用 → anchor一括充填。
- `auto` はそのまま、`review`/`embedded` はvision再分割キューへ。
- 誤謬クラスは誤謬チェックレーン確定分を `ERROR_CLASSES` へ追記（norm_version up）。
