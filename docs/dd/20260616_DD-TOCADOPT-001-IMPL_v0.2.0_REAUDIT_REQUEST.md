---
request_id: DD-TOCADOPT-001-IMPL-REAUDIT
topic: 統一TOC採用ルール実装 v0.2.0 再監査 (MODIFY_REQUIRED 是正の検証)
gate: implementation_review
supersedes: なし
parallel_related: [DD-TOCADOPT-001, DD-TOCADOPT-001-IMPL, DD-EDIDENT-001, DDLEGALLIBCONCORD]
current_governing_result: DD-TOCADOPT-001-IMPL = MODIFY_REQUIRED (2026-06-16)
prior_request: DD-TOCADOPT-001-IMPL (実装の批判的監査・自己申告 weak points 付き)
result_expected_filename: DD-TOCADOPT-001-IMPL-REAUDIT_result.md
status: queued
queued_date: 2026-06-16
守秘: 設計・状態語彙・件数レベルのみ。実依頼者データ本文は含めない。合成データのみでテスト。
---

# DD-TOCADOPT-001 実装 v0.2.0 再監査依頼 (MODIFY_REQUIRED 是正の検証)

## 0. 依頼の趣旨

前回監査は **MODIFY_REQUIRED**。H9件・うち blocker 6件 (C1/C4/D1/D2/E1/F2) と是正必須を頂いた。
**全件を同日是正**したので、(a) 6 blocker が解消されたか、(b) 是正により**新たな不正・退行を持ち込んでいないか**、
(c) PASS とできるか / 追加 MODIFY か、を判定いただきたい。**甘い PASS は不要。是正の副作用に赤を入れてほしい。**

production apply / canonical / RDB / policy 本番切替は **HOLD 継続**。投影のみ・書込ゼロ。合成データのみ。
owner 裁定: **E1 = 廃止明記**（legacy `rules` を採用せず append_missing_only に一本化）。

## 1. 対象 (branch claude/legallib-integration-design-Jgrtf, TOC_ADOPT_VERSION 0.2.0)

- `scripts/toc_adopt.py` — 5 ステップ採用エンジン + `export_baseline()`。
- `scripts/toc_adopt_gates.py` — 7 gate (gate1/gate3 強化)。
- `scripts/make_tocadopt_golden.py` + `tests/golden/tocadopt/synthetic_multisource.jsonl` — **9** シナリオ (7→9)。
- `tests/test_tocadopt.py` — **161** checks (回帰 + must_fix 不変条件 + 安全 + 7gate 実走)。
- `data/toc_merge_policy_unified_DRAFT.json` — `rules._deprecated` / `confidence_usage` 追記。
- stdlib 全体 **796 checks green** (前回 778)。

## 2. 前回 H 指摘 → 是正 → 反映先 (検証してほしい対応表)

| 指摘 | 重大度 | 是正内容 | 反映先 |
|---|---|---|---|
| **C1** 偽 source_hash 捏造 | H/blocker | 欠落は `source_hash=None`+`snapshot_missing=True` で **pending**。accepted は実 sha のみ | `step3_node_completion` / `adopt_book` provenance_ok |
| **C4** partinfo kind 無視 | H/blocker | `partinfo_kind_filter` 実装。volume_structure=**rejected** / mixed_small=**pending** / contents=採用候補 | `step3` make_node kind 分岐 |
| **D1** 非合議を accepted 混入 | H/blocker | `accepted`(consensus∧provenance健全∧kind≠review) と `pending`(理由付き lane) を分離。projection=accepted のみ | `step4` / `adopt_book` |
| **D2** adoptable 緩い | H/blocker | `adoptable = identity_ok ∧ consensus_ok ∧ authority≠HR ∧ provenance_ok`。blocker を列挙 | `adopt_book` |
| **E1** legacy rules 矛盾 | H/blocker | `replace_if_higher_source=false`・`_deprecated` 明記。append_missing_only 一本化 | policy JSON |
| **F2** gate1 が sha 単独 | H/blocker | `export_baseline()` 追加 + gate1 を **ノード集合・親子・ページ・base分布**の同値検査へ | gates / engine |
| **A1** anchor 1点固定 | H | 全ペア edge → anchor の **connected component** で合議集合 | `step1_identity_gate` |
| **A2** anchor が bib 源を選ぶ | M | anchor は **node 持ち源**を priority 優先で選択 | `step1` |
| **B1** 粒度=ノード数単独 | H | 粒度=**(最大深さ, ノード数, ページ被覆)** 複合。guard=最富源比 **かつ** 深さ非劣化 | `step2` `_granularity` |
| **B2** simple_only 未実装 | H | 張替え意味論を実装: protected rich は保護 / simple incumbent のみ詳細で張替え / rich incumbent は skip | `step2` |
| **C2** toc_node_id 衝突 | M | id に lineage (isbn/origin/locator/title) | `step3` |
| **C3** offset 無検証 | M | 検証済 (`validated∧confidence≥1.0`) のみ変換。`page_converted_from_pdf`/`needs_offset` 付与 | `step3` `_book_offset` |
| **E2** confidence 未使用 | L | policy `confidence_usage` に未使用を明記 | policy JSON |
| **F1** gate3 閾値二重定義 | M | gate3 が policy の per-source/default を読む | `gate3` |
| **G1** 敵対 fixture 不足 | M | volume_structure / missing_source_hash シナリオを golden 追加 (一部) | golden |

## 3. 是正後の挙動 (保守化を確認してほしい)

合成 9 冊で **adoptable は consensus3 の1冊のみ** (3 独立 origin 一致)。他は:
- `non_consensus_or_pending` (2源本は consensus 3 origin に届かず pending)、
- `identity_unresolved` (別版疑い源を connected component から除外)、
- `authority_human_review` (PDF 単独等)。

→ 前回の「ほぼ全部を雑に採用」が消え、**多源裏取りの有無が pending/accepted に正直に出る**状態。
report-only かつ HOLD 中なので、この保守側への倒し方は安全側として妥当と判断したが、**過度に厳しすぎないか**判定請う。

## 4. 今回の是正で新たに自信が持てない点 (= 新規赤入れ対象・正直開示)

- **N1 (H?)** `consensus_ok = (pending が空 ∧ accepted≥1)` と定義した。つまり **全ノードが3独立origin裏取り**でないと
  本は adoptable にならない。2源本は構造的に常に非 adoptable。これは安全側だが、**閾値3 が厳しすぎ / 本単位でなく
  ノード単位 adopt にすべきでは**、という設計論点が残る (現状は本単位 gate)。
- **N2 (M)** B2 の "incumbent(既存base)" を **clustered 内 priority 最上位の node 持ち源**で代理した。実運用の
  「既に attach 済みの base」を厳密にモデル化していない (本 repo に attach 状態が無いため)。張替え判定の入力が
  priority 依存になっている。
- **N3 (M)** `_is_simple = max_depth<=1`。flat な章リストは全部 simple 扱い。protected_base シナリオでは
  incumbent==candidate で結果は不変だが、**simple の閾値定義が恣意的**。
- **N4 (M)** parent_id を **accepted 列の深さスタック近似**で後付けした (flat→tree)。append 由来ノードが
  base の親子構造に正しくぶら下がる保証はない。export_baseline の parent_id はこの近似値。
- **N5 (L)** consensus を**全 origin 横断の title_norm 一致数**で測る。base に無く pending 行きのノードも
  votes は数える (lane 分離後)。多重 origin の独立性 (再配布が真に独立か) は source_meta 申告依存のまま。
- **N6 (L)** G1 敵対 fixture は volume_structure / missing_hash の2種のみ追加。title 衝突・循環親子・
  multi-offset・同一 origin 重複申告 等は未カバー。

## 5. 判定してほしいこと

1. blocker 6件 (C1/C4/D1/D2/E1/F2) は解消したか。
2. §4 N1〜N6 のうち **再 MODIFY 級**はどれか (特に N1 の本単位 vs ノード単位 adopt)。
3. PASS_WITH_NOTES に上げられるか、追加是正必須か。
4. 次サイクルで G1 をどこまで厚くすべきか (敵対カテゴリの優先順位)。

HOLD 不変 / report-only / 合成データのみ。赤入れ歓迎。
