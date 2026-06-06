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
| 検索 | `https://library.bengo4.com/search?q=...` | 未確認（要URL） |
| その他 | `/signin` `/help` `/seminar` | 確定（公開） |

- offset: `adr = print_page + offset`。例: 引用判例リンク画面「83ページ＝紙面43ページ」→ offset 40。
- アドレスバーはSPAで更新されない。**ページ取得は必ず共有/リンクボタン経由**。

### ⚠ 最重要の未解決: `cid` の粒度
スクショの見出し「**コンメンタール民事訴訟法III ／ 第2編／第1章〜第3章／第133条〜第178条**」より、
`cid` は**書籍全体ではなく「分冊／条文範囲」単位**の可能性が高い（= 1 ISBN ↔ 複数 cid）。

これが正なら book_links の `bencom` を**配列化**する必要がある:
```jsonc
"bencom": [
  { "cid": "ebaaf6...", "section": "第133条〜第178条", "print_range": [1, 220], "offset": 40 },
  { "cid": "9c1f...",    "section": "第179条〜...",     "print_range": [221, 440], "offset": 40 }
]
```
着地時は「紙面ページが入る print_range の cid」を選んで `&adr=print_page+offset`。
→ **確認方法**: 同じ本の別の条文範囲/巻を開き、reader の cid が変わるかを見る（チェックリスト#1）。

---

## 3. 判例秘書 / LIC（legal-info.com, hanreihisho.com）— 文献→判例の着地先

| 種別 | パターン | 状態 |
|---|---|---|
| 会員ログイン | `https://www.legal-info.com/`（LIC会員） | 確定（公開） |
| 判例ID | `L` + 8桁（例 `L02420223`） | 確定（スクショ） |
| 判例本文 deeplink | `legal-info.com/...?hanreiId=L...`（仮説） | **未確認（要実URL）** |

- ベンコム reader 右下「**判例**」→ 引用判例リンク画面（その紙面ページの引用判例一覧。複数可）→ 各判例 → LICログイン → 判例秘書 判例本文。
- legal-info.com も SPA で URL 不変の可能性あり。その場合は判例側も「共有/印刷ボタンが出すURL」を探す。

---

## 4. 収集チェックリスト（ケータイでタップ→URLを貼るだけ）

優先順。各URLをこのスレッドに貼れば config / case_sources に落とし込みます。

1. [ ] **cid粒度の確定**: 同じ本（例 コンメンタール民訴III）の**別の条文範囲/巻**を開いた reader 共有URL。cid が変わるか？
2. [ ] **offsetの安定性**: 目次で離れた章にジャンプ→共有→ `&adr`。紙面ページとの差が章内・巻内で一定か（同一 offset か）。
3. [ ] **引用判例リンク画面のURL**（「判例」ボタン後の画面）。共有 or アドレスバー。
4. [ ] **判例本文URL**: 引用判例リンクから1判例を開いた **legal-info.com の実URL**（ログイン後）。判例deeplink形式の確定 → `case_sources.url_template`。
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
