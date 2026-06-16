# DD-TOCADOPT-001-IMPL — GPT 監査結果 (MODIFY_REQUIRED) と是正計画

- 日付: 2026-06-16
- 投函: `to_gpt/20260616_DD-TOCADOPT-001_IMPL_REVIEW_REQUEST.md` (Box 2288567927811)
- 結果: `from_gpt/DD-TOCADOPT-001-IMPL_result.md` (Box 2288591644740) = **MODIFY_REQUIRED**
- reviewer: GPT-5.5 Pro / 関連: H項目数 correction (count=9 ACCEPTED, Box 2288576113742)
- 不変: production apply / canonical projection / RDB write / policy 本番切替 = **HOLD 継続**

## 総合判定

「report-only / synthetic regression としては有用だが本番手前には上げられない。**自己申告どおり
雑さは妥当**。H項目9件のうち少なくとも6件が blocker」。**甘い PASS 不可**。

## must_fix before C1 (GPT 指定の順序)

| 順 | 項目 | 是正内容 | 種別 |
|---|---|---|---|
| 1 | **C1** | `sha256(title_norm)` 捏造を**廃止**。source_hash 欠落時は `source_snapshot_missing`/review/non-adoptable に倒す | blocker |
| 2 | **C4** | `partinfo_kind_filter` 実装 (contents のみ採用 / volume_structure 拒否 / mixed_small review) | blocker |
| 3 | **D1/D2** | 非合議ノードを accepted projection から分離 (pending/human_review lane)。`adoptable` = identity_ok AND consensus_ok AND authority≠human_review AND provenance_ok | blocker |
| 4 | **E1** | policy legacy `rules` ブロックを**廃止明記 or 実装**し append_missing_only との矛盾を消す | blocker |
| 5 | **B1/B2** | 粒度指標を depth/node_count/page_coverage の複合に。granularity_guard も同指標。simple_only 張替え意味論を policy/engine/gate で一致 | 是正必須 |
| 6 | **F2** | baseline export 仕様 (book_cluster_id/base_source/toc_node_id/parent_id/title_norm/page_start_end/author/provenance_origin/source_snapshot_hash/projection_sha) を作り、sha だけでなく**ノード集合・親子・ページ・base分布の同値検査** | blocker |
| 7 | **A1** | one-anchor 判定を**全ペア graph / connected component** 方式へ | 是正必須 |

## should_fix (本番手前まで)
- A2 (基準は node-bearing 源優先) / C2 (toc_node_id に lineage/locator/parent/sibling/title を含め衝突回避) /
  C3 (単一 offset は許容本に限定・confidence/exception lane) / E2 (confidence 未使用なら policy 明記) /
  F1 (gate3 も per-source override を読む) / F3 (fixture を identity 入力必須列に補強) /
  G1 (敵対的入力追加: title collision / cyclic parent / missing hash / no page / multi-offset / non-consensus /
  volume_structure / protected-base conflict / cross-edition mixed cluster)。

## GO / HOLD (GPT)
- **GO**: synthetic regression 拡張 / report-only engine refinement / baseline export 仕様作成 / C1 blocker 修正 branch。
- **HOLD**: production apply / canonical projection / RDB write / policy 本番切替 /
  **accepted projection への非合議ノード混入** / **fake provenance hash での gate 通過**。

## 反映状況 (2026-06-16・同日是正済 / report-only)

owner 裁定: **E1 = 廃止明記** (legacy rules を採用しない)。全 must_fix を反映:

| 項目 | 是正内容 | 状態 |
|---|---|---|
| **C1** | source_hash 欠落は捏造せず `snapshot_missing=True` で **pending**。accepted は実 sha のみ | ✅ |
| **C4** | `partinfo_kind_filter` 実装。volume_structure を **rejected**、mixed_small を pending | ✅ |
| **D1** | `accepted`(consensus∧provenance健全) と `pending`(理由付き lane) を分離。projection=accepted のみ | ✅ |
| **D2** | `adoptable` = identity ∧ consensus ∧ authority≠HR ∧ provenance。blocker を列挙 | ✅ |
| **E1** | policy `rules._deprecated` 明記・`replace_if_higher_source=false`。append_missing_only に一本化 | ✅ |
| **B1** | 粒度を **(最大深さ, ノード数, ページ被覆) 複合**に。guard は最富源比 **かつ** 深さ非劣化 | ✅ |
| **B2** | simple_only 張替え意味論を実装 (protected 保護 / simple incumbent のみ詳細で張替え / rich は skip) | ✅ |
| **F2** | `export_baseline()` (toc_node_id/parent_id/title_norm/page/origin/snapshot_hash) + gate1 を **ノード集合・親子・ページ・base分布**同値検査へ強化 | ✅ |
| **A1** | 全ペア edge → anchor の **connected component** で合議集合。anchor は node 持ち源優先 (A2) | ✅ |
| **C2** | toc_node_id に lineage (isbn/origin/locator/title) で衝突回避 | ✅ |
| **C3** | offset は検証済本に限定・`page_converted_from_pdf`/`needs_offset` を付与 | ✅ |
| **F1** | gate3 が policy の per-source override / default を読む (engine と一致) | ✅ |
| E2 | confidence 未使用を policy `confidence_usage` に明記 | ✅ |
| F3/G1 | fixture を identity 入力列に補強 / 敵対カテゴリ (volume_structure・missing_hash) を golden に追加 | ✅ 一部 (G1 は更に拡張余地) |

実装版 = `TOC_ADOPT_VERSION 0.2.0`。golden 9 シナリオ (7→9)・`test_tocadopt.py` 161 checks。
stdlib 全体 **796 checks green**。挙動は大幅に保守化: 合成 9 冊で adoptable は **consensus3 の1冊のみ**
(3 独立 origin 一致)、他は pending/identity blocker で正しく非採用。

> production apply / canonical / RDB / policy 本番切替 = HOLD 継続。投影のみ・書込ゼロ。
> 再監査が要れば本 IMPL を v0.2.0 として再投函可。
