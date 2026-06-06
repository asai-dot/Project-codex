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
| 判例ID | `L` + 8桁（例 `L02420223`, `L02010234`） | 確定 |
| 判例本文画面 | `https://www.legal-info.com/plus/detail?screen_info_id={enc}&select_id={enc}` | **確定・ただし構築不可** |

> ⚠ **判例秘書への直接deeplinkは不可**。`screen_info_id`/`select_id` は Laravel の暗号化トークン
> （`eyJpdiI6…` = `{"iv","value","mac"}` のbase64）。サーバ秘密鍵で暗号化され、判例IDが露出せず、
> 毎回ランダムIV。**任意の判例についてURLを生成できない**（捕捉済みURLが鍵未変更の間だけ生きる程度）。
> → 判例秘書は「暗号化ハンドオフ」設計。ALOから L番号で直リンクする手段は提供されていない。

- チェーン: ベンコム reader 右下「**判例**」→ **引用判例リンク画面**
  `library.bengo4.com/books/{cid}/precedents#page_{viewer_page}`（**確定**。頁別の引用判例一覧、複数可）
  → 各判例リンク → LICログイン → 判例秘書 `/plus/detail`（暗号化トークン）。
- → `case_citations` の一次データはこの `precedents` ページから取れる（book=cid, viewer_page=page_, 判例=L番号＋裁判所・年月日・事件番号）。
- **着地戦略（判例秘書が直リンク不可なので）**: ①所内に生判決文(PD)があれば内部表示 → ②裁判所サイト/他DBで
  事件番号から引ける物 → ③最後に**ベンコム precedents ページ**（`/books/{cid}/precedents#page_{N}`＝構築可・安定）を
  判例秘書への“オンランプ”として開く。判例秘書 `/plus/detail` の直接生成はしない。

---

## 4. 収集チェックリスト（ケータイでタップ→URLを貼るだけ）

優先順。各URLをこのスレッドに貼れば config / case_sources に落とし込みます。

1. [x] **cid粒度** → 別セクションでも cid 不変 = 巻/ISBN単位。`bencom` は単一 `{cid, offset}` でよい。
2. [ ] **offset厳密化**（#2'）: reader 画面に印刷された**紙面ページ**と共有URLの **adr** の1組を清書（例「紙面43表示中→adr=○」）。`adr = print + offset` を1点確定。
3. [x] **引用判例リンク画面のURL** → `library.bengo4.com/books/{cid}/precedents#page_{viewer_page}`（実例 `#page_134`）。
4. [x] **判例本文URL** → `legal-info.com/plus/detail?screen_info_id={enc}&select_id={enc}`（Laravel暗号化トークン）。**直リンク構築は不可**と判明。判例秘書への着地は「ベンコム precedents ページ」をオンランプに使う（上記着地戦略）。
5. [ ] **ベンコム検索結果URL**: 任意語で検索した `library.bengo4.com/search?...`。
6. [ ] **リーガル検索/法令リンクURL**: 検索結果ページ・法令リンク先。

---

## 5. コードへの落とし込み先

| 取得物 | 反映先 |
|---|---|
| reader/ページ・book_key の形 | `config/library_sources.json` の `url_template` / `link_parse` |
| cid粒度（巻=ISBN単位、確定） | `data/book_links.json` の `bencom` は単一 `{cid, offset}` |
| 引用判例の一覧 | `case_citations`（book_id, print_page, case_id） |
| 判例/法令の着地 | 参照着地リゾルバ（§6） + `case_sources`/`law_citations`（schema コメント） |

---

## 6. ALOが構築できる公開アンカー（商用との決定的な差）

判例秘書のように暗号化された壁庭と違い、**以下は我々がURLを構築できる**＝内製グラフの着地先にできる。

### e-Gov法令（laws.e-gov.go.jp）— 文献→法令の着地
| 用途 | URL | 例（民法709条） |
|---|---|---|
| 人間向け本文 | `https://laws.e-gov.go.jp/law/{lawId}#{anchor}` | `/law/129AC0000000089#Mp-At_709`（anchor要最終確認） |
| API | `https://laws.e-gov.go.jp/api/1/articles;lawId={lawId};article={n};paragraph={p}` | `;lawId=129AC0000000089;article=709` |

- `lawId`=15桁（民法 `129AC0000000089`）。ALO `alo-kg/resolver.py`＋`law_name_lookup` が法令名→lawId を解決済。
- 版は `temporal.py` で施行時点に整合。**改正耐性**は商用ビューワーにない強み。

### 裁判所 裁判例（courts.go.jp）— 判例の公開着地（②）
| 種別 | URL | 備考 |
|---|---|---|
| 判例詳細 | `https://www.courts.go.jp/app/hanrei_jp/detail{2\|4\|7}?id={courtId}` | detail2=最高裁 / 4=下級・高裁 / 7=知財高 |
| 検索 | `https://www.courts.go.jp/app/hanrei_jp/search{2\|4\|7}` | id は事件番号から要解決（harvest時に保存） |

→ これらを `case_sources` / `law_citations` の着地テンプレに設定する。詳細設計は
  [literature_precedent_graph.md](literature_precedent_graph.md)。

### 未確認（要確認）
- e-Gov 人間向けURLの条文アンカー形式（`#Mp-At_{n}` 系）の最終確認。
- 裁判所 `detail` の `id` を事件番号から解決するクエリ形式。
- リーガルの法令リンク機能のURL形式（採取で確定）。
