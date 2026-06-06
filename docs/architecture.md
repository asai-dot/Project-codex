# アーキテクチャ & 引き継ぎ — Fork 2（検索 / RAG・横断ビューワー）

## 0. 背景

事務所の蔵書6,384冊について、複数ソースから収集した詳細目次（TOC）が揃った。これにより人間のリサーチが
大きく前進する。鍵は **「目次から該当ページへヌルヌル飛べる」** こと、そして **目次の体系を機械（AI）に
渡せる** こと。本リポジトリ（`project-codex`）はその第一弾として、検索基盤＋横断ビューワーを構築する。

既存資産（Box『事務所内本棚DX化計画』）:
- 稼働ビューワー `app/server.js`（:3000）＋ `app/public/app.js` … **自炊PDFのみ** `/pdf_orig/{folder}/{file}` に着地
- `app/data/toc/isbn_*.json`（目次ノード, 5,206冊）, `app/data/books.json`（33MB）, `toc_search_index.json`
- 既存インデックスは `{t, d}` のみ＝ページに着地できなかった ← 本リポジトリで解消

## 1. 4図書館モデル

「デジタル図書館（有償2＋自炊1）＋物理図書館（無料1）」を**並列**に並べ、1ビューワーから横断する。

```
┌── 検索（目次横断, 書名・章節・ページに着地）
│
├─ 自炊PDF      (owned, free)  /pdf_orig/{folder}/{file}#page={viewer_page}
├─ ベンコム      (paid)         https://www.businesslawyers.jp/lib/book/{book_key}?page={viewer_page}   ※暫定
├─ リーガル      (paid)         https://legal-library.jp/book/{book_key}/page/{viewer_page}             ※暫定
└─ 物理本棚      (owned, free)  棚位置＋印刷ページ（URLなし）
```

## 2. ジャンプ解決エンジン（`src/deeplink.js`）

唯一の真実。サーバとブラウザが共有。純関数 `resolveLink(source, link, printPage)`。

| 入力条件 | status | 着地 |
|---|---|---|
| offsetあり & printPageあり & テンプレ解決可 | `page` | `url_template` に `viewer_page=print_page+offset` |
| 上記以外（offset未校正 / printPage不明 / テンプレ不完全） | `book_top` | `book_url_template`（本トップ） |
| 物理本 | `physical` | location + print_page |
| その本が無い | `unavailable` | — |

`viewer_page = print_page + offset`。offset は **本×図書館ごと**。
`computeOffset(printPage, viewerPage) = viewerPage - printPage`（1点合わせ）。

## 3. インデックス（`scripts/build_toc_search_index.py`）

各ノードに `t / d / p(印刷ページ) / path(章節パス) / path_id / src(出典) / id` を持たせる。
`parent_toc_node_id` をたどって `path`（例「第3章 消滅時効 > 第2節 時効の起算点」）を生成。
既存 `server.js` の品質防衛（JS/HTML断片・ナビ語彙・文字化け）をビルド時に移植・除去。

出力 `data/toc_search_index.json`:
```json
{ "built_at": "...", "books": { "isbn_9784641138001": { "title": "...", "isbn": "...", "nodes": [ {"t","d","p","path","path_id","src","id"} ] } } }
```

本番で回す場合は環境変数で Box のパスを指す:
```bash
TOC_DIR=~/Box/.../app/data/toc BOOKS_JSON=~/Box/.../app/data/books.json \
OUT=~/Box/.../app/data/toc_search_index_v2.json python3 scripts/build_toc_search_index.py
```

## 4. 検収（acceptance）

代表クエリ「時効の起算点」で、正解の章節×ページに上位3件以内で到達すること。
本リポジトリのサンプルでは上位3件すべてが正解章節に着地（`npm start` 後 `/api/search?q=時効の起算点`）。

## 5. 次にやること

1. **有償DLの実テンプレ確定**:
   - リーガルライブラリー: **確定済** `https://legal-library.jp/r/{book_key}?page={viewer_page}&ctg=view`（実例 `/r/326510?page=39`）。
     `link_parse` で実URLから book_key/viewer_page を自動抽出 → `calibrate --url ... --print P` で offset 確定。
   - ベンコム（弁護士ドットコム・ライブラリー）: **book-top確定** `https://library.bengo4.com/reader/?cid={book_key}`
     （`cid`=64桁hexの content hash。`/books/{hash}` ランディング形式も link_parse で捕捉）。
     ページ送り時のURL（reader はSPAで page param 未確認）は**本文の特定ページを開いた実URLが1本**あれば確定。
     それまで bencom は cid を貼付け校正で取得し **トップ着地**（offset=null）。
2. **本番データ接続**: Box『app/data』の 5,206冊 TOC と books.json でインデックス再構築。
   所有側2図書館（自炊PDF・物理本）の `book_links.json` は **`scripts/generate_book_links.py`** で
   books.json から自動生成できる（校正ゼロ・有償DLの校正値はマージ保持）:
   ```bash
   BOOKS_JSON=~/Box/.../app/data/books.json OUT=data/book_links.json python3 scripts/generate_book_links.py --dry-run
   ```
   フィールド揺れ（canonical v1 / legacy）は候補パス総当りで吸収。実データに合わせ `CANDIDATES` を調整。
3. **③ 埋め込み + RAG**: `schema/supabase_schema.sql` を alo-connect か asai-dot's Project に適用し、
   `toc_nodes` を投入 → `embedding`（pgvector）→「事務所ライブラリに聞く」アシスタント。回答は必ず
   引用ハンドル（書名・章節・ページ・各図書館deeplink）付きで返す。
4. **既存ビューワー統合**: 本エンジン（deeplink.js）と4図書館リンクを `app/public/app.js` の書誌詳細に組み込み、
   現行の自炊PDF専用ジャンプを4図書館横断に拡張。

## 6. 設計判断ログ

- **offset方式**（base+print_page+offset）を採用。理由: 有償DLは内部ページ番号が非公開だが、1点合わせだけで
  全ページに着地でき、運用コストが最小。LEGAL LIBRARY の「現在ページURL発行」とも整合（調査で確認）。
- **当面JSON、Supabase互換スキーマ**。124k+ノードは JSON でも即時検索可能。RAG段階で無改修でpgvectorへ。
- **deeplink.js を単一実装**にしてサーバ/ブラウザ共有 → 着地挙動のズレを構造的に排除。
- **本文コピー = 引用ハンドル**。実本文テキストはPDF/有償DL側の権利物のため複製せず、「書名・章節・ページ・
  各図書館deeplink・node_id」という機械可読ハンドルをコピーする。AIに渡せば出典付きで参照できる。
