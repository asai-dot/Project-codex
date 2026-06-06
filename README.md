# Project-codex — Fork 4: 論文 entity & 法令リンク（アイデア B・F）

雑誌目次の「タイトル　著者」ノードを `{title, authors}` に分解し（**著者横断検索/引用**）、
TOC 見出し・論文タイトルから **条文・判例参照を抽出して e-gov 法令へリンク**する
（引用グラフの芽）パイプライン。

上位の確定仕様は Box 指示書
`cc_instruction_legallib_journal_article_parser_20260605.md` (v1.1) に従う。

## 構成

```
data/egov/                 e-gov 法令定義 jsonl (法令名/条文の索引ソース, 154 法令)
src/codex/
  article_parser.py        ① 目次ノード → {title, authors, kind, section, ...} (指示書 §3)
  author_normalize.py      ② 著者名正規化 (横断検索キー author_key を生成)
  egov_index.py            e-gov jsonl から法令名→law_id / (law_id,条)→uri 索引
  legal_links.py           ③ 条文参照→e-gov リンク + 判例参照→引用グラフ node
  jp_numerals.py           漢数字/全角数字 → int (条番号正規化)
scripts/
  run_article_parser.py    雑誌 JSON を全数スイープ → 3 つの成果物 (指示書 §4)
  run_legal_links.py       articles → legal_links.jsonl + summary
  author_search.py         著者横断検索 (検収「著者横断検索が成立」)
fixtures/legallib_dl/      合成 + 実例由来の雑誌 JSON (E2E 検証用)
out/                       fixtures に対する生成サンプル (再生成可能)
tests/                     pytest (38 件)
reports/                   番頭への handoff report
```

## 実行

```bash
# ① 論文 parser スイープ（実データは番頭 Mac の ~/alo-ai/work/legallib_dl/）
python scripts/run_article_parser.py --src <legallib_dl-dir> --out out

# ③ 条文・判例リンク
python scripts/run_legal_links.py --articles out/articles_extracted.jsonl --out out

# ② 著者横断検索
python scripts/author_search.py --articles out/articles_extracted.jsonl --top 10
python scripts/author_search.py --articles out/articles_extracted.jsonl --query "山口 厚"

# テスト
python -m pytest tests/ -q
```

## データ可用性に関する注意

本作業環境には STEP A 成果物の **422 号分の元 JSON (`legallib_dl/*.json`) は存在しない**
（番頭 Mac ローカル資産）。そのため本リポジトリは:

- 実データが来たらそのまま全 422 号に流せる **実行可能パイプライン** を提供し、
- 指示書記載の**実例（法学セミナー No.49 / 305760）＋エッジケース合成 fixture** で
  E2E 検証（parse_rate 計算・著者横断検索・法令リンク目検）を行っている。

e-gov 法令データ（`data/egov/`）は git 履歴に存在した実資産を復元したもの。
詳細・数値は `reports/STEP_A2_JournalArticleParser_Report.md` を参照。
