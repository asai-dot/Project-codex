# 外部デジタル図書館 リンク構造アトラス

有償DL（リーガル/ベンコム）と判例DB（判例秘書/LIC）の**リンク構造の地図**。
deeplink.js / config.link_parse / 将来の case_citations を確定するための一次資料。
`確定` は実URLで裏取り済み、`未確認` は実物URLが要る（収集チェックリスト参照）。

---

## 1. リーガルライブラリー（legal-library.jp）

| 種別 | パターン | 状態 |
|---|---|---|
| ページ着地 | `https://legal-library.jp/r/{book_key}?page={viewer_page}&ctg=view` | **確定**（実例 `/r/326510?page=39`） |
| 本トップ | `https://legal-library.jp/r/{book_key}?ctg=view` | 確定 |
| book_key | `/r/` の数値ID（ISBN非依存） | 確定 |
| 検索 | `legal-library.jp/search?...`（要確認） | 未確認 |
| 法令リンク機能 | 書籍本文→該当法令への内部リンク（2024 新機能） | 未確認 |

- offset: `viewer_page = print_page + offset`、共有URL貼付け校正で1点確定。

---

## 2. ベンコム / 弁護士ドットコムライブラリー（library.bengo4.com）

| 種別 | パターン | 状態 |
|---|---|---|
| 書籍ランディング | `https://library.bengo4.com/books/{cid}` | **確定**（cid=64桁hex） |
| reader 本トップ | `https://library.bengo4.com/reader/?cid={cid}` | 確定 |
| reader ページ着地 | `https://library.bengo4.com/reader/?cid={cid}&adr={viewer_page}` | **確定**（共有/リンクボタンが発行。adr=ビューワーページ） |
| 引用判例リンク（頁別の引用判例一覧） | `https://library.bengo4.com/books/{cid}/precedents#page_{viewer_page}` | **確定**（実例 `#page_134`）。**文献→判例の入口** |
| 検索 | `https://library.bengo4.com/search?q=...` | 未確認（要URL） |
| その他 | `/signin` `/help` `/seminar` | 確定（公開） |

- offset: `adr = print_page + offset`。例: 引用判例リンク画面「83ページ＝紙面43ページ」→ offset 40。
- アドレスバーはSPAで更新されない。**ページ取得は必ず共有/リンクボタン経由**。
- 観測: 同地点で reader `adr=133` と precedents `#page_134` が**1ずれ**（adr=0始まり / `page_`=1始まりの疑い）。
  reader 画面に印刷された紙面ページと adr の1組を清書すれば offset を厳密確定できる（チェックリスト#2'）。
- `precedents#page_{N}` の `N` は viewer ページ（≒ adr+1）。判例一覧は**紙面ページではなく viewer ページで引ける**。

### ✓ `cid` の粒度 — 巻/ISBN単位（暫定確定）
検証: 同一書籍内で**別セクションへ移動しても reader の cid は不変**（同じ `ebaaf6907d0c…465b5`）。
→ `cid` は **1 ebook（≒ 1 巻 = 1 ISBN）単位**。引用判例リンク見出しの「第133条〜第178条」は
そのページの所在ラベルであって cid の範囲ではない。

**帰結**: `data/book_links.json` の `bencom` は **単一 `{cid, offset}` でよい**（現状の設計のまま。配列化不要）。
- 多巻物は各巻が別ISBN＝別cidなので、book_id(ISBN)キーで自然に分かれる。
- 将来 1 cid が複数巻を内包する例が出たら、その本だけ `print_range` で cid を選ぶ配列化に拡張する。

---

## 3. 判例秘書 / LIC（legal-info.com, hanreihisho.com）— 文献→判例の着地先

| 種別 | パターン | 状態 |
|---|---|---|
| 会員ログイン | `https://www.legal-info.com/`（LIC会員） | 確定（公開） |
| 判例ID | `L` + 8桁（例 `L02420223`） | 確定（スクショ） |
| 判例本文 deeplink | `legal-info.com/...?hanreiId=L...`（仮説） | **未確認（要実URL）** |

- チェーン: ベンコム reader 右下「**判例**」→ **引用判例リンク画面**
  `library.bengo4.com/books/{cid}/precedents#page_{viewer_page}`（**確定**。頁別の引用判例一覧、複数可）
  → 各判例 → LICログイン → 判例秘書 判例本文。
- → `case_citations` の一次データはこの `precedents` ページから取れる（book=cid, viewer_page=page_, 判例=L番号）。
- 残: 各判例 → **legal-info.com の判例本文URL**（判例deeplink形式）。legal-info.com も SPA で URL 不変の可能性あり。
  その場合は判例側も「共有/印刷ボタンが出すURL」を探す。

---

## 4. 収集チェックリスト（ケータイでタップ→URLを貼るだけ）

優先順。各URLをこのスレッドに貼れば config / case_sources に落とし込みます。

1. [x] **cid粒度** → 別セクションでも cid 不変 = 巻/ISBN単位。`bencom` は単一 `{cid, offset}` でよい。
2. [ ] **offset厳密化**（#2'）: reader 画面に印刷された**紙面ページ**と共有URLの **adr** の1組を清書（例「紙面43表示中→adr=○」）。`adr = print + offset` を1点確定。
3. [x] **引用判例リンク画面のURL** → `library.bengo4.com/books/{cid}/precedents#page_{viewer_page}`（実例 `#page_134`）。
4. [ ] **判例本文URL** ←次の最重要：引用判例リンクから1判例を開いた **legal-info.com の実URL**（ログイン後）。判例deeplink形式の確定 → `case_sources.url_template`。
5. [ ] **ベンコム検索結果URL**: 任意語で検索した `library.bengo4.com/search?...`。
6. [ ] **リーガル検索/法令リンクURL**: 検索結果ページ・法令リンク先。

---

## 5. コードへの落とし込み先

| 取得物 | 反映先 |
|---|---|
| reader/ページ・book_key の形 | `config/library_sources.json` の `url_template` / `link_parse` |
| cid粒度（分冊） | `data/book_links.json` の `bencom` を配列化 + deeplink.js に range選択を追加 |
| 判例deeplink形式 | `schema/supabase_schema.sql` の `case_sources.url_template`（現在コメント） |
| 引用判例の一覧 | `case_citations`（book_id, print_page, case_id） |
