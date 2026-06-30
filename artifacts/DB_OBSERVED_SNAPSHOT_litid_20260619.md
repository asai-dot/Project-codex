# DB実測スナップショット — 書籍同定(DD-LITID)で実在するデータ

- generated_at_jst: 2026-06-19
- source: Supabase project `nixfjmwxmgugiiuqfuym`（read-only `execute_sql` 観測）
- method: read-only。本スナップショットは DB を一切変更していない（SELECT/profile のみ）。
- 目的: ISBN→NDLドライラン計画 v0.1 / DD-LITID-PLAN 4ルート版の**前提を実データで検算**する。
  「計画上の3 ISBNルート」と「実際にDBに入っているもの」の差分を固定する。

---

## サマリ（要点3つ）

1. **ISBN持ちルートで実際にDBへ入っているのは self/own（asai-bookshelf）1ルートのみ**。
   LION BOLT・legallib は `biblio.bib_records` に未投入（行ゼロ）。
2. **自所(asai-bookshelf)のISBN→NDLは既に大半解決済み**：ISBN保有5,397件のうち
   **4,976件(92%)が ndl_bib_id 解決済み**。ドライランの実体は「新規3ルート実行」ではなく
   **自所の再計測＋穴埋め**。
3. **bengo4 no-ISBN shadowレーンは既に部分実装済み**＝`bookdx.holding_bencom_link`（1,737件）。
   うち **775件が medium(noisbn+fp)＝単証拠寄り**で、DD-LITID-001「2独立証拠でconfirm」の要対象。

---

## 1. `biblio.bib_records`（10,326行）— 実在ソースは2つだけ

| source | 行数 | ISBN | ndl_bib_id | NDC | edition | pub_year |
|---|--:|--:|--:|--:|--:|--:|
| asai-bookshelf（自所） | 6,524 | 82.7% | **76.7%** | 84.4% | 6.5% | 96.1% |
| bencom-library（弁コム） | 3,802 | 0.2% | 0.0% | 0.0% | 0.0% | 100% |
| **合計** | **10,326** | 52.3% | 48.4% | 53.3% | 4.1% | 97.5% |

- **LION BOLT / legallib は bib_records に存在しない**（ドライラン計画 §1 が想定する3ルートのうち2つが未着）。
- edition列は全体で4.1%しか埋まっていない＝版同定は「これから機械で解く」対象であって既存値依存は不可。

### 自所(asai-bookshelf)の ISBN × NDL 実クロス（6,524件）

| 区分 | 件数 | 意味 |
|---|--:|---|
| ISBN有 & NDL有 | **4,976** | ISBN→NDL解決済み（ISBN保有の92%） |
| ISBN有 & NDL無 | 421 | ISBNあるのに未解決＝穴埋め1次対象 |
| ISBN無 & NDL有 | 26 | 奥付/別経路で解決済み |
| ISBN無 & NDL無 | **1,101** | 古書/奥付欠落の難所＝書誌fingerprint回し対象 |

→ ドライラン計画 §6 の「resolved_single率/no_hit率」は、自所については**既存DB値で即計測可能**。
  穴は (421) + (1,101) に局在。

## 2. `bookdx.holdings`（6,524行＝自所の媒体レイヤ）

| 指標 | 値 |
|---|--:|
| ISBN保有 | 5,397 (82.7%) |
| scanned | 611 |
| has_pdf | 611 |
| cut | 0（フラグ未投入） |
| has_toc | 0（フラグ未投入） |
| bencom_id 紐付 | 1,737 |

- `scanned == has_pdf == 611` で `bookdx.pdf_inventory`(611) と一致＝自炊PDFは611冊。
- `cut`/`has_toc` は現状0＝この2フラグはまだ運用に乗っていない（裁断/目次状態は別管理 or 未投入）。

## 3. `bookdx.holding_bencom_link`（1,737行）— 弁コム突合は既存

| match_basis | confidence | 件数 |
|---|---|--:|
| fingerprint:title_norm+publisher_norm | high(isbn_holding+fp) | 962 |
| fingerprint:title_norm+publisher_norm | medium(noisbn+fp) | 775 |

- 突合は全件 **title_norm + publisher_norm のfingerprint**（弁コム側にISBNが無いため）。
- **high 962** は holding側ISBN＋fpの2証拠。**medium 775** は no-ISBN＋fp単証拠寄り。
- → DD-LITID-001 v0.2「2独立証拠でconfirm」基準だと、**775件が要・第2独立証拠**（誤統合リスク本体）。

## 4. 参考: authority層（貼付Macパスの対応DB側）

- `authority.publication` 列: publication_id, publication_type, title, container_title, volume, issue,
  publication_year, publisher, source_system …＝**論文/記事(文献)レイヤ**。
- `authority.source_record` 内訳: bencom-library 3,802 / ndl_judge_author_match 3,500 / cinii 49。
- Macの `d1_bunken_article_meta*` / `d1law_dl/bunken` は **D1-Law 文献(記事)メタ**で、
  4ルート「書籍」同定とは別ドメイン（DD-PERIODICAL寄り）。**本スナップショットの書籍スコープ外**。

---

## 5. ドライラン計画 v0.1 への影響（前提修正）

| 計画の前提 | 実測 | 修正 |
|---|---|---|
| ISBN持ち3ルートを当てる | 実在は self/own 1ルートのみ。LION BOLT/legallib未着 | 当面**自所1ルート先行**（計画§8の懸念が現実化） |
| NDL解決をこれから測る | 自所はISBN保有の92%が解決済み | 計測は**既存DB値で即可能**。焦点は穴(421+1,101) |
| bengo4 no-ISBNは別レーンで今後 | `holding_bencom_link`に1,737件**既存** | shadowレーンは**増設でなく既存775件のconfirm精査**から |

> 本スナップショットは観測のみ。promote/DDL/backfill/本番突合は依然 HOLD。
> 次アクションの提案（自所の resolved分布レポート化 / medium775のQAサンプル）は別途承認後。
