# Fork 2 — 検索 / RAG（アイデア A・G）

> 上位: [`../00-metadata-join-fabric.md`](../00-metadata-join-fabric.md)
> 依存: Fork 1（接合）

## 目的

124k+ TOCノードの章節横断検索 ＋ ページアンカー付き「事務所ライブラリに聞く」アシスタント。

## 前提資産

- 既存: `app/scripts/build_toc_search_index.py`(2180728948279)
- 全TOCノード（書籍2,751 ＋ 雑誌422、`pdf_page`/`print_page` 付き）
- Supabase（`alo-connect` / `asai-dot's Project`、pgvector 候補）

## 最初の一歩

1. TOCノード = チャンク（`book_id`/`isbn` + `page_start` + path をメタに）でインデックス
2. キーワード検索 PoC
3. 埋め込み + RAG。検索結果は必ず「書名・章節・ページ」で着地。

## 検収

- 代表クエリ（例「時効の起算点」）で正解の章節×ページに上位3件以内で到達。
