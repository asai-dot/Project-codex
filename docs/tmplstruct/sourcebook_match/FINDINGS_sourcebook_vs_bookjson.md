# 調査所見 — 書式の「根拠本」× うちの蔵書(BookJSON) 突き合わせ

**作成**: 2026-06-11 ／ **作成者**: 番頭(リモートClaude) ／ **依頼**: 浅井先生
**目的**: tmplstruct を「リーガルライブラリーOCR だけ」に依存させず、**より生に近いきれいな材料**（native原本／うちの現物本・自前PDF／出版社DL／付録DVD）がうちに無いかを確認し、構造化精度を上げる。

---

## 0. 結論（先に3行）

1. **3,806書式（実体は弁コムライブラリー全体で 175冊・6,976書式）は、1件残らず「出典本・出典ページ・直DL URL」を持っている。** 根拠本は推測不要で確定済み。
2. **最大の発見**: 各書式は弁コムの doc-templates API 経由で **native の Word/PDF/Excel 原本を直接DLできる**（Word 5,282件=76%）。OCR復元より遥かにきれいで、これが「君の仕事の精度を上げる材料」の本命。
3. **うちの蔵書 books.json との突合は機構が既にある**（ISBN解決＋既存 resolver）。出典本101/175冊で ISBN を解決済み。所蔵/自前PDF/OCR の最終判定だけ、books.json がローカルにある Mac で 1 コマンド実行すれば出る（本書同梱の matcher）。

---

## 1. データの地図（どこに何があるか）

### 1-A. 書式側＝リーガルライブラリー（＝弁護士ドットコム「弁コムライブラリー」）
Box: `…/事務所内本棚DX化計画/handoffs/gpt_ometsuke/material_queue/弁コム法律書カタログ_20260610/`
- `catalog.csv` / `catalog.jsonl`（505MB）: **全4,490冊**の書誌＋TOC＋判例リンク。`thumbnail_url`/`url` に **ISBN** と **出版社サイトURL** が入る。
- `templates.csv` / `templates.jsonl`: **書式を内蔵する175冊 × 6,976書式**。1書式ごとに
  `tmpl_format`(word/pdf/excel)・`tmpl_filename`・`tmpl_link_url`(**直DL**)・`tmpl_page`(出典ページ)・`tmpl_contents_id`(出典本)。
- 各書式 `description` 例: 「出典：『…』P62（三修社）」。**根拠本は明示**。

### 1-B. 蔵書側＝うちの BookJSON（本棚DX canonical）
Box: `…/事務所内本棚DX化計画/app/data/books.json`（約33MB, file_id `2161143503087`）
スキーマ `app/bookdx_canonical_schema_v1.json`。本件で効く欄：
- `identity.isbn` / `internal_id=isbn_<13>` … **突合鍵**
- `physical.present` / `physical.shelf_label` … **現物所蔵か・棚位置**（→ 高品質再スキャン可）
- `digital.pdf_present` / `pdf_files[]` / `pdf_quality` / `ocr_status` … **自前スキャンPDF・OCR済みか**
- `bib_core.title` / `publisher` / `series` … ISBN欠落時の書名突合用

### 1-C. 既存の突合機構（再利用可能）
`material_queue/20260608_legallib_join_sample/resolver_sample.jsonl` に、
legallib本 → ISBN → books.json を `auto_accept / human_review / defer_new` と
`overwrite/create/route_human_review/blocked_*` で捌く **resolver が既に実装・検証済**。
本件はこの逆引き（出典本→所蔵判定）に同じ鍵(ISBN)を流用するだけ。

---

## 2. 実集計でわかったこと（出典本側・確定）

`loaders/build_source_book_inventory.py` を templates.csv × catalog.csv に適用（read-only・決定論）:

| 指標 | 値 |
|---|---|
| 書式を内蔵する**根拠本** | **175冊** |
| 紐づく**書式総数** | **6,976**（Word 5,282 / PDF 1,625 / Excel 69） |
| ISBN解決済（books.json突合可） | **101 / 175冊**（残74は社内ID形式URLのため書名+出版社で突合） |
| 出版社DL特典 signal（書名/抄録） | 5冊（実DLは下記§3でカバー） |
| 付録CD-ROM/DVD signal | 2冊 |

**出版社別 根拠本 冊数 top:** 三修社53・日本加除出版37・中央経済社29・新日本法規22・日本商事仲裁協会15・労働新聞社7・現代人文社5。
→ いずれも**実務書式集の定番版元**。法律事務所が現物を持っている可能性が高い顔ぶれ。

**書式数トップの根拠本（＝復元の高価値が集中する本）:**
| 書式数 | 本 | 出版社 | ISBN |
|---:|---|---|---|
| 321 | 新・会社法実務問題シリーズ／7 会社議事録の作り方〈第3版〉 | 中央経済社 | 9784502430213 |
| 304 | 企業労働法実務入門【書式編】 | 日本リーダーズ協会 | 9784890170111 |
| 238 | 会社法務書式集〈第3版〉 | 中央経済社 | — |
| 200 | 問題社員をめぐるトラブル予防・対応文例集 | 新日本法規 | — |
| 176 | 株式会社・各種法人別 清算手続と書式 | 新日本法規 | — |
| 147 | 刑事弁護ビギナーズver.2.1 | 現代人文社 | 9784877987206（付録signal）|
| 144 | 民法改正対応 契約書式の実務 上 | 創耕舎 | 9784908621093 |
| 131 | 民法改正対応 契約書式の実務 下 | 創耕舎 | 9784908621109 |

> tmplstruct の `docx_priority_score` 上位（会社議事録・就業規則・定款・取引基本契約 等）は、
> この数冊の根拠本に集中する。**= 数冊を押さえれば高価値復元の大半が生材料化できる。**

成果物: `docs/tmplstruct/sourcebook_match/source_books_175.csv`（1行1根拠本）。

---

## 3. きれいな材料チャネル（精度向上の選択肢）

| # | チャネル | 何が得られるか | 状態 |
|---|---|---|---|
| **A** | **弁コム doc-templates 直DL**（`tmpl_link_url`） | **native Word 5,282 / PDF 1,625 / Excel 69** = 書式の原本そのもの | **全6,976件で利用可**。OCR不要・最優先。※ 月30 .docx枠との関係は要検証（別 endpoint の可能性）|
| B | **うちの現物所蔵本**（books.json `physical.present`） | 高解像度で再スキャンできる正本 | §4で判定（worker） |
| C | **うちの自前PDF**（books.json `digital.pdf_present`/`ocr_status`） | 既にスキャン済みの本文画像・OCR | §4で判定（worker） |
| D | **出版社サイトDL**（catalog `url` ＝ publisher_site_url） | 版元公式の書式ダウンロード（例: 三修社/中央経済社） | URL取得済。版元ごとにDL有無を要確認 |
| E | **付録CD-ROM/DVD** | 紙書籍添付の書式データ | signal 2冊＋現物確認で増える見込み |

**いちばん効くのは A**。tmplstruct はこれまで「OCR=正本／月30枠の.docxエクスポート」で苦労していたが、
templates.csv は全書式に native 原本の直リンクを持つ。**A が枠制約を受けないなら、3,806件の構造化材料が一気に生Word化できる。**（この1点は owner 確認の価値が大きい）

---

## 4. 未実行＝ワーカーで1コマンド（books.json 所蔵突合）

books.json は約33MB・**Mac ローカルが唯一の実体**（このリモート実行環境はセッション上限で33MB全量を引けない）。
同梱の決定論マッチャを Mac で走らせれば、出典本ごとに 現物所蔵/自前PDF/OCR を判定し、CSV＋サマリが出る：

```
python3 loaders/match_sourcebooks_to_bookjson.py \
  --source docs/tmplstruct/sourcebook_match/source_books_175.csv \
  --books  ~/alo-ai/.../app/data/books.json
```
出力: `sourcebook_holdings_match.csv`＋`_HOLDINGS_MATCH_SUMMARY.md`
（突合鍵: ① ISBN完全一致 ② 書名正規化＋出版社 で fuzzy。曖昧は human_review）。

詳細手順は `WORKER_TASK_PACKET_tmplstruct_sourcebook_match.md`。read-only・books.json非改変・クォータ0。

---

## 5. 番頭の推し（owner判断ポイント）

- **P1**: チャネルA（native直DL）が月30 .docx枠を消費するのか別経路かを worker に検証させる。別経路なら tmplstruct の取得設計を「OCR逆算」から「native原本主体」に切替＝精度・速度とも段違い。
- **P2**: §4マッチャを実行し、書式数トップの根拠本（会社議事録/会社法務書式集/問題社員文例集 等）を**うちが現物・PDFで持っているか**確定。持っていればB/Cで版元品質の生材料が即手に入る。
- **P3**: ISBN欠落74冊は版元URLからISBNを後追い解決（三修社/biz-book等はURLにISBN在り）し突合率を上げる。

---

## 付録: 生成物
- `loaders/build_source_book_inventory.py` — 出典本175冊の集計（本リポジトリで実行済）
- `loaders/match_sourcebooks_to_bookjson.py` — books.json 突合（worker 実行）
- `docs/tmplstruct/sourcebook_match/source_books_175.csv` — 出典本索引（確定）
- `WORKER_TASK_PACKET_tmplstruct_sourcebook_match.md` — worker 実行パケット
