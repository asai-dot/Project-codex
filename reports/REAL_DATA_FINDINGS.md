# 実データ検証メモ — Supabase / Box 探索と本番データでの結果

- 日付: 2026-06-06
- 関連: Fork 4（論文 entity ＆ 法令リンク）、PR #8
- 目的: 当初「422号の元JSONは当環境に無い」と結論したが、利用可能な MCP
  （Supabase / Box / Drive）を精査し、**到達可能な実データで何ができるか**を検証した。

---

## 1. 発見したデータ資産

### 1.1 Supabase `asai-dot's Project` (`nixfjmwxmgugiiuqfuym`) — 本番DB
LegalLibrary/bencom の本番ナレッジDB。主要テーブル:

| schema.table | rows | 内容 |
|---|---|---|
| `biblio.bib_records` | 10,326 | 書誌（書籍・雑誌・記事）。`form_type`, `issn`, `title` |
| `biblio.bib_toc` | **552,544** | 目次ノード `{bib_id, ordinal(0始), level, page, text}` |
| `biblio.authors` / `bib_authors` | 2,200 / 3,310 | 構造化著者（記事横断） |
| `biblio.bib_toc_cleanup_bak_20260605` | 6,153 | 目次クリーニングのバックアップ（**前日付**） |
| `authority.person` / `person_alias` | 128,081 / 30,810 | 著者名寄せオーソリティ（5,647人が複数別名） |
| `authority.publication*` | ~7,300 | 著者-論文クレーム＋エビデンス |

### 1.2 Box
- `app/data/toc/title_*.json`, `isbn_*.json` … 1冊1ファイルの目次（`{l,p,t,depth,...}`）
- `弁コムライブラリTOCJSON.txt` (72MB), `bencom_skeleton_with_toc.json` (72MB) … 結合TOC
- `cinii_batch/detail/*.json` … CiNii 書誌（著者・引用の素材、idea B 拡張）

---

## 2. 重要な発見：article parser の入力（U+3000）はクリーニング済DBには無い

指示書の parser は「タイトル**　**著者」の**全角空白 U+3000** を著者境界に使う。
しかし **本番 `bib_toc` 552,544 ノード中、U+3000 を含むノードは 0 件**。
`bib_toc_cleanup_bak_20260605`（reason: `mokuji_alone` 3,014 / `html_entity` 2,810 /
`empty_or_1char` 329）が示す通り、目次は既にクリーニングされ U+3000 区切りは失われている。
Box の `title_*.json` サンプル（実務書 manual）も U+3000 を持たない book 型TOCだった。

→ **結論**: 「title　author」構造を保持する原本は STEP A の生 `legallib_dl/*.json`
（番頭Mac）にのみ存在。**article parser の本番スイープは番頭環境が必要**という
当初判断は妥当だった。parser 自体は指示書の実例 fixture で検証済（PR #8、parse_rate 0.9167）。

ただし `bib_toc.text` には書名・章見出し・条文・判例が**実データとして**含まれており、
**③ 法令リンク（idea F）は本番データ上で実行可能**だった（以下 §3）。

---

## 3. ③ 法令リンク（引用グラフの芽）— 本番データでの実測

### 3.1 全DBスケール（SQL集計, 552,544 ノード）
- 条文参照（`第○条`）を含むノード: **10,211**
- 判例参照（`最判平成…` 等）を含むノード: **2,042**
- 中核法令名を含むノード: **10,089**

法令別 node mention 上位（実数, full DB）→ `out_real/egov_law_mentions_full_db.csv`:
民法 3,139 / 会社法 1,293 / 刑法 952 / 商法 615 / 独占禁止法 524 / 著作権法 389 /
労働基準法 345 / 特許法 307 / 金融商品取引法 249 / 民事訴訟法 248 …

### 3.2 サンプル実行（実ノード 600件を `legal_links.py` で処理）
成果物: `out_real/legal_links_real.jsonl`（sha1 `fab1058b9d41a17cb10e1bd4832dedd0a8712214`）、
`out_real/legal_links_real_sample.csv`

- 600 実ノード → 74 links: **statute 49（high-conf 43、e-gov 定義突合 38）**、case 25
- 解決例（実データ・目検OK）:
  - 民法第255条 → `egov:129AC0000000089:art:255`
  - 出入国管理及び難民認定法第二十条の二 → `egov:326CO0000000319:art:20_2`（**枝番**正規化）
  - 農地法第３条/第４条/第５条 → `egov:327AC0000000229:art:3..5`（**全角数字**）✓egov
  - 医師法17条 → `egov:323AC0000000201:art:17`
- 判例（引用グラフ node, 実データ）:
  札幌高判平成22年6月1日 / 東京高判平成21年12月2日 / 広島高判平成19年5月29日 …
  （court/era 正規化、ひらがな巻き込みなし）

→ **法令リンクは本番データで成立。サンプル目検クリア。** kanji/全角/枝番の正規化が
実データでも機能することを確認。

---

## 4. ② 著者横断検索（idea B）— 本番データの裏付け
- `biblio.authors`×`bib_authors` で著者の書誌横断が実在（例: 升田純=14冊、松岡慶子=20冊）。
- DB 既存 `normalized_key` は**内部空白を除去していない**（"森 公任、森元 みのり" 等）。
  本PRの `author_normalize`（NFKC＋内部空白除去＋役割語分離）は既存キーより精緻で、
  名寄せ前処理として価値がある。
- `authority.person`（128,081）＋ `person_alias`（5,647人が複数別名）が名寄せの ground truth。
  外部ID（CiNii/NDL/VIAF）突合は次段タスク候補。

---

## 5. 番頭への提案（更新）
1. **article parser 本番スイープ**: 生 `legallib_dl/*.json`（U+3000保持）を番頭環境で
   `scripts/run_article_parser.py` に投入。当環境のクリーニング済DBでは不可。
2. **法令リンク本番化**: `legal_links.py` を `biblio.bib_toc` 全 10K+ 法令ノードへ適用し、
   `bib_toc` ↔ e-gov の引用グラフ辺テーブル（例 `biblio.bib_toc_legal_ref`）として投入する
   設計を提案。**書込みは未実施**（本セッションは read-only に限定）。要承認。
3. **著者正規化の DB 反映**: `author_normalize` を `authors.normalized_key` 再計算に適用する案。要承認。
