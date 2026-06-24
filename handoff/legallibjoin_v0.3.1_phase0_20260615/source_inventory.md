# Phase 0 source inventory (legallibjoin v0.3.1, report-only)

> canonical/legallib とも未書込。final_toc 未生成。

## A. legallib 詳細TOC (接合の new 側ソース)

- ファイル総数: **4052**
- content_type 内訳:

| content_type | files | with_toc | total_nodes | empty_title率 | isbn欄あり |
|---|---:|---:|---:|---:|---:|
| <unset> | 1 | 0 | 0 | None | 0 |
| book | 2760 | 2759 | 623891 | 0.0001 | 0 |
| journal | 422 | 422 | 12657 | 0.0 | 0 |
| material | 214 | 214 | 16494 | 0.0 | 0 |
| pubcom | 655 | 399 | 9675 | 0.1593 | 0 |

> **所見: legallib はネイティブに ISBN を持たない** (isbn欄あり=0)。ISBN は resolver_decisions.jsonl による title/publisher/year 突合で後付け。→ 接合キーの素性は resolver 品質に従属する。

## B. canonical 書誌 (接合の existing 側 / 書込先候補)

- レコード総数: **7728** / ISBN付与: 5535 (ユニーク 5535) / hasToc: 6157
- mediaType 内訳: {'book': 4049, '<unset>': 2663, 'periodical': 966, 'web': 50}
> canonical 書誌に **頁数欄なし** → edition identity の page_count 照合は legallib 側のみ。

## C. resolver 突合 (legallib_book_id → canonical ISBN)

- 判定総数: **2760**
- bucket 内訳: {'auto_accept': 1839, 'human_review': 305, 'defer_new': 616}
  - auto_accept/human_review = canonical 一致 (= edition identity 対象 1988 ISBN)
  - defer_new = canonical 不在 → 接合では create 候補
- ed_conflict フラグ: 32 / ambiguous: 155
- write_candidates (v0.2 既出): 943 件 (TOC 差分既知)

## D. edition identity 診断 (classify_edition_identity, 実 2ソース対)

- 評価対象 (canonical ISBN 一致): **2082**
- resolved_same_manifestation: 1738
- suspected_different_manifestation (生): 344 = title divergence 319 + year divergence 25 (うち年差±1のノイズ 14 / 年差≧2 11)

### title divergence の層別 (生の文字列差は別版を意味しない)

| 層 | 件数 | 意味 |
|---|---:|---|
| cosmetic | 123 | 全半角・〔〕〈〉括弧・読点差のみ → 同一 |
| subtitle_difference | 87 | 片方が副題を含む/欠く → 同一本 |
| edition_marker_asymmetry | 53 | 片方のみ版表記 → 要レビュー |
| edition_number_conflict | 26 | **版番号が相違 (例 第7版 vs 第4版) → 真の別版** |
| genuine_title_diff | 30 | 核タイトルが相違 → 要レビュー |

- **偽陽性 (装飾/副題/年差±1) = 226 件** (別版ではない)。
- **真に要レビュー (版衝突/版非対称/核相違/年差≧2) = 118 件** (全評価の 5.7%)。
  - うち確実な別版 (版番号衝突) = **26 件**。

> **所見1 (閾値調整に直結)**: 生 344 件 (16.5%) の別版疑いは過検知。内訳は title装飾/副題差 210 + 年差±1ノイズ 14 = 偽陽性 226、実質 118。信頼できる別版信号は**抽出した版番号の相違**であり、現行 `classify_edition_identity` の『title 文字列一致 / 年が1つでも違えば別版』判定では過検知する。→ apply ゲートは『版番号抽出 + 核タイトル包含 + 年差トレランス(±1許容)』へ強化すべき (本 PR はスコープ外、別 DD で実装)。

> **所見2 (normalize_title の穴)**: 共有 `normalize_title` は NFKC するが `〔〕` `〈〉` `、`(読点) を strip しない。これだけで cosmetic 123 件が別版誤判定。`_STRIP_RE` へ 3 文字追加で解消 (共有モジュール変更=別 DD)。

> **所見2b (年差ノイズ)**: year divergence 25 件のうち 14 件は年差±1 (例: 同一『第36版』が 2022 vs 2023、判例集の巻号が前後年)。出版年は print 年/刊年/カタログ年で表記が揺れるため ±1 は同一物とみなすべき。

> **所見3 (resolver 偽陽性)**: resolver auto_accept 1839 件中 108 件が別版疑い → うち装飾/副題を除く **実質要レビュー 12 件**。これらは apply_guard の edition gate が物理拒否 (HOLD 維持の根拠)。

> **所見4 (resolver recall)**: bucket=defer_new (canonical 不在として create 予定) のうち **58 件は canonical に同一 ISBN が存在**。resolver の取りこぼし候補 → human_review へ差し戻すべき。

