# Fork 1 — 接合の実装設計

> 上位: [`../00-metadata-join-fabric.md`](../00-metadata-join-fabric.md)（背骨）
> 位置づけ: **背骨そのもの。他フォークの土台。**

## 目的

legallib 詳細TOC を本番ブックJSON（canonical）に安全接合し、resolver の3層を本番に
どう落とすか確定する。

## 前提資産

- resolver 出力: `auto_accept 1,839（うち既merge 344 → 新規≈1,495）/ human_review 305 / defer_new 616`、誤マージ0ガード
- canonical 定義: Box `app/bookdx_canonical_schema_v1.json`(2217714412089) / `.md`(2217711724108)
- 既存同期: `CODEX/scripts/sync_safe_codex_toc_into_app.py`(2180809847675)、`build_toc_canonical_registry.py`(2180783889402)
- 現行TOC: `app/data/toc/isbn_*.json`（ISBN採番。`toc_source` / `toc_status` あり。`simple` はフラット）
- 詳細TOC: `legallib_dl/*.json`（book_id 採番。`{l, p, t, level}`、depth L1/L2/L3、`print_page`/`pdf_page`）

## 接合のキー問題

- 本番 = **ISBN13** 採番（`toc_node_id = alo:book:isbn:9784502310218:toc:001`）
- legallib = **内部 book_id** 採番（`305760` 等）
- 単純 join 不可 → resolver（所蔵一致＋pdf_page強化）で橋渡し。

## 最初の一歩

1. **スキーマ変換器**: legallib `{l, p, t, level}` → canonical
   （`parent_toc_node_id` を level の入れ子から再構築、`page_start` に pdf/print_page）
2. **`source` 優先順位ポリシー**（最重要）: 人手 / NDL canonical > legallib。
   `toc_status: "simple"` のみ昇格上書き可。非simple は劣化させない。
3. **auto_accept 新規分のドライラン diff** を出してから本番反映。

## 検収

- 既存の人手/NDL TOC を1件も劣化させない（非simple の上書き前後 diff = 0 件）
- book_id↔ISBN 突合の誤マージ0 を維持

## メモ

- `source` 設計は全フォーク共通の前提。最初に握ること。
