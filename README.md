# Project Codex — 事務所ライブラリ 横断検索 / RAG（Fork 2）

124k+ の TOC（目次）ノードを章節横断で検索し、結果を必ず **「書名・章節・ページ」** に着地させる。
さらに **4つのデータ保存（図書館）を1つのビューワーから横断** し、人間がデータ間をシームレスに行き来できるようにする。

| # | 図書館 | 種別 | 費用 | ページ着地 |
|---|--------|------|------|-----------|
| 1 | 事務所PDF（自炊） | デジタル | 無料・所有 | PDF.js `#page=`（offset済） |
| 2 | ベンコム（BUSINESS LAWYERS LIBRARY） | デジタル | 有償 | offset校正でページ／未校正はトップ |
| 3 | リーガルライブラリー（LEGAL LIBRARY） | デジタル | 有償 | offset校正でページ／未校正はトップ |
| 4 | 物理本棚（所内） | 物理 | 無料・所有 | 棚位置＋印刷ページを提示 |

人間の3つのニーズ — **目次をコピー（機械可読）／本文（引用ハンドル）をコピー／該当PDFを読む** — に合わせ、
該当箇所へ「ヌルヌル」飛べるように設計してある。

---

## クイックスタート

```bash
npm run build-index     # data/toc/*.json から検索インデックスを構築（Python3）
npm start               # http://localhost:3100 でビューワー起動（Node、npm依存なし）
npm test                # ジャンプ解決エンジンの単体テスト
```

ブラウザで `http://localhost:3100` を開き、「時効の起算点」で検索 → 上位3件が正しい章節×ページに着地し、
各結果から4図書館へワンクリックで飛べることを確認できる（検収シナリオ）。

> 自炊PDFの実配信は環境変数 `PDF_BASE`（Box『し＿自炊書籍データ』の原本ベース）を指定したときのみ有効。

---

## 着地の仕組み（ジャンプ解決エンジン）

中核は [`src/deeplink.js`](src/deeplink.js)。`(図書館, 本のリンク, 印刷ページ)` を1つの関数で解決し、
サーバ([`server/server.js`](server/server.js))とブラウザ([`public/viewer.js`](public/viewer.js))が**同じロジック**を共有する。

```
viewer_page = print_page + offset           # offsetは本×図書館ごとに「1点合わせ」
deeplink    = url_template{viewer_page}      # config/library_sources.json のテンプレ
```

- `offset` があり印刷ページが分かる → **ページ着地**（`status: "page"`）
- `offset` 未校正 or 印刷ページ不明 → **トップ着地**（`status: "book_top"`）
- 物理本 → **棚位置＋印刷ページ**（`status: "physical"`）
- その本が無い図書館 → `unavailable`

### offset の1点合わせ（calibrate）

有償DLは実ビューワーの「現在ページのURL発行（リーガル）」やページ送り表示から、
**任意の1ページについて (印刷ページ, ビューワーページ) を1点取れば** offset が確定する。

```bash
# 実ビューワーURL（ケータイ可）を貼るだけ。book_key と viewer_page を自動抽出し、印刷ページから offset 確定
node scripts/calibrate.js --book isbn_9784641138001 \
  --url "https://legal-library.jp/r/326510?page=39&ctg=view" --print 33
# → source=legal_library book_key=326510 viewer_page=39 / offset = 39 - 33 = 6

# 手入力でも可
node scripts/calibrate.js --book isbn_9784641138001 --source legal_library --print 135 --viewer 151

# ビューワー上のフォーム / API（url を渡せば book_key/viewer_page は自動）
POST /api/calibrate  {"book_id":"...","url":"https://legal-library.jp/r/326510?page=39&ctg=view","print_page":33}
```

**リーガルライブラリーの実URL形式は確定済**: `https://legal-library.jp/r/{book_key}?page={viewer_page}&ctg=view`
（`book_key` は `/r/` の数値ID、ISBNではない）。ベンコムの `url_template` は実URL取得後に確定する。

---

## データモデル

| ファイル | 役割 |
|----------|------|
| `config/library_sources.json` | 4図書館の正規設定（テンプレ・page戦略・tier） |
| `data/toc/{book_id}.json` | 各書籍の目次ノード配列（= 検索/RAGのチャンク） |
| `data/book_links.json` | 本×図書館の在庫・book_key・offset |
| `data/books.json` | 蔵書マスタ（最小） |
| `data/toc_search_index.json` | `build_toc_search_index.py` の出力（ページ・章節パス・出典入り） |
| `schema/*.json`, `schema/supabase_schema.sql` | JSON Schema と pgvector対応DDL |

保存先は**当面JSON**だが、列構成は `schema/supabase_schema.sql`（Supabase/pgvector）と1:1。
③埋め込み+RAG段階で `toc_nodes.embedding` に載せ替えられる。

---

## API

| メソッド | パス | 用途 |
|---|---|---|
| GET | `/api/libraries` | 4図書館の設定 |
| GET | `/api/search?q=` | 目次横断検索（着地＋各図書館リンク） |
| GET | `/api/toc/:bookId` | 1冊の目次ツリー |
| GET | `/api/book/:bookId` | 書誌＋目次＋全図書館リンク |
| GET | `/api/resolve?book=&source=&page=` | 単発ジャンプ解決 |
| POST | `/api/calibrate` | offsetの1点合わせ |

---

## ロードマップ（Fork 2）

- [x] ① TOCノード＝チャンクとして、book_id/isbn + page_start + path をメタにインデックス化
- [x] ② キーワード検索PoC（「書名・章節・ページ」着地、4図書館横断ジャンプ、目次/引用コピー）
- [ ] ③ 埋め込み + RAG（`toc_nodes.embedding` / pgvector、「事務所ライブラリに聞く」アシスタント）

本番データ（Box『事務所内本棚DX化計画/app/data』6,384冊）への接続と、有償DLの実テンプレ確定が次段。
