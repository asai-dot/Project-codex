# DD-D1TAXO-001 精度確認 — A: 内部整合チェック結果

> date: 2026-06-15
> 対象: D1-Law 民事セレクション 体系目次 ライブキャプチャ（DD-D1TAXO-001）
> 入力: `app/data/pacsigny/iteration/d1law_live_taxonomy_20260612_nodes.csv`（55,074行）
>        ＋ `..._summary.json` ／ `d1law_taikei_alo_terms_load_20260615_v3_manifest.json`
> 方法: nodes.csv を全件読み、木構造の整合と変換スコープを独立再計算して manifest 申告値と突合（read-only）

## 結論

内部整合は **全項目 PASS**。取りこぼし・重複・木の破断・規律違反はゼロ。
ただしこれは「データが壊れていない」証明であり、「D1 の実体系と一致」の証明ではない（→ B: 実画面照合が真値）。

## A1. 木構造（nodes.csv 全 55,074 件）

| 検査 | 結果 |
|---|---|
| 行数 55,074 / 列ズレ行 | OK / 0 |
| key 重複 | 0 |
| root（parent空・level0） | 21（21法編） |
| orphan（parent_key 未解決） | 0 |
| level 整合（child.level == parent.level+1） | 違反 0 |
| child_count（宣言値 == 実子数） | 不一致 0 |
| is_leaf 整合（is_leaf ⇔ child_count==0） | 不整合 0 |
| by_level == summary.json | 一致 |
| NFC 非正規化 name | 0 |
| 全ノード rooted / 循環 | 0 / 0 |
| 葉ノード | 41,311（summary 一致） |

by_level: `{0:21, 1:137, 2:5183, 3:10823, 4:11440, 5:8753, 6:6158, 7:6356, 8:3021, 9:1849, 10:1333}`（合計 55,074）

## A2. 変換（源 CSV レベル分布から独立再計算 → v3 manifest 突合）

DD の L 番号 = level+1。L1-L3（level 0-2）→ `alo_statutes` 候補、L4-L11（level 3-10）→ `alo_terms`。

| 項目 | 計算（源CSV） | 申告（v3 manifest） | 判定 |
|---|--:|--:|---|
| alo_terms (L4-11) | 49,733 | 49,733 | OK |
| statutes 候補 (L1-3) | 5,341 | 5,341 | OK |
| 合計 | 55,074 | 55,074 | OK（scope_check）|
| alo_term_relations (skos_broader = level≥4) | 38,910 | 38,910 | OK |
| alo_term_labels（1/term） | 49,733 | 49,733 | OK |
| alo_d1law_taikei_extra（1/term） | 49,733 | 49,733 | OK |

`relations 38,910 = level≥4` は、「L4 ノードの親（L3 = statutes 側）へは skos_broader を張らない」という
スキーム横断禁止規律の実装証明になっている（level3 ノード 10,823 件分が親リンクを持たない）。

## 限界（要追加検査）

- `alo_terms` 系は `.jsonl` で Box がテキスト抽出できず、**件数は CSV レベル分布からの独立再計算で全一致を確認**した。
- `term_uri` の実体ユニーク性／`skos_broader` の `dst_term_uri` 実在／`pref` ラベル重複の**バイト単位検査**は未実施。
  ワーカーちゃん側で JSONL 直接検査（or CSV 書き出し）を 1 回回すのが確実。

## 次（B）

`ACCURACY_SAMPLE_CHECK_DD-D1TAXO-001_105.md`（21法編 × 5 = 105 件）で実 D1 画面と照合。
あわせて `..._removed_box_prior.csv`（929 件）を法編別に目視し、recall 97.29% の残差を切り分ける。
