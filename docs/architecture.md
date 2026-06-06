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
   - ベンコム（弁護士ドットコム・ライブラリー）: **ページ着地 確定** `https://library.bengo4.com/reader/?cid={book_key}&adr={viewer_page}`
     （`cid`=64桁hexの content hash。`/books/{hash}` ランディング形式も link_parse で捕捉）。
     アドレスバーはSPAで更新されないが、reader の**共有/リンクボタンが `&adr={viewer_page}` 付きURLを発行**する。
     `adr`=ビューワーページ=紙面+offset。offsetは『引用判例リンク』画面の「○ページ 紙面△ページ」表記
     （例: 83ページ=紙面43ページ→offset 40）または共有URL貼付け校正で1点確定。
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

## 7. 文献→判例リンク（本丸の構想・将来）

ベンコム reader は本文ページ（紙面43）に対し **右下「判例」ボタン → 引用判例リンク** を持ち、
そのページで引用されている裁判例の一覧（裁判所・年月日・事件番号・事件名）を表示する。
さらに各判例は **判例秘書（LIC / legal-info.com）** の判例本文へ遷移する（ベンコムがLICを買収し連携）。
観測例（コンメンタール民訴III・紙面43p）: 東京高判昭43.8.6、東京高判昭44.5.19（判例秘書ID `L02420223`）、福岡高判昭46.3.9 等。

**ALOが目指す姿**: 別会社・別目的で作られた「文献リーダー × 判例DB」の継ぎ目を、所内の静的DBで溶かし、
`(書籍, 紙面ページ) → 引用判例 → 判例本文` を**ワンクリックでバーンと飛べる**形にする。現状ベンコム×判例秘書の
連携はUIが粗く実用に遠いので、所内側で滑らかな導線を作る価値が高い。

**判明した制約（重要）**: 判例秘書（legal-info.com）の判例本文URLは
`/plus/detail?screen_info_id={enc}&select_id={enc}` で、両トークンは **Laravel暗号化**（iv/value/mac）。
判例IDが露出せず毎回ランダムIVのため、**任意の判例についてURLを生成できない**＝判例秘書への直リンクは不可。
これがベンコム×判例秘書の連携が「シームレスでない」技術的理由（暗号化ハンドオフ）。一方、ベンコムの
引用判例リンク画面 `library.bengo4.com/books/{cid}/precedents#page_{viewer_page}` は**構築可・安定**。

設計の足がかり（本リポジトリの拡張として）:
- TOCノード/ページに対し **引用判例のエッジ**（`case_citations`）を持たせる。1ページに複数判例可。
  一次データはベンコム `precedents` ページから取得（book=cid, viewer_page, 裁判所/年月日/事件番号/L番号）。
- 判例の正規キー = 裁判所＋年月日＋事件番号（＋判例秘書L番号は参考キー）。
- **着地はデータ駆動で優先順** （deeplink.js と同じ思想の `case_sources`）:
  ① 所内に生判決文(PD・著作権なし)があれば内部表示 → ② 裁判所サイト等の安定URLがあればそこ →
  ③ **ベンコム precedents ページをオンランプ**に判例秘書へ。判例秘書 `/plus/detail` は直接生成しない。
- ③RAGの回答は、書籍パッセージの引用ハンドルに加えて**根拠判例へのリンク**（上記優先順で解決）も同梱する。

→ `schema/supabase_schema.sql` 末尾に `case_citations` / `case_sources` の将来用DDL（コメント）を用意。
