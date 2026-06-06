# Fork 4 — 論文 entity ＆ 法令リンク（アイデア B・F）

> 上位: [`../00-metadata-join-fabric.md`](../00-metadata-join-fabric.md)
> 依存: Fork 1（所蔵紐付け部分）

## 目的

雑誌「タイトル　著者」を `{title, authors}` に分解 → 著者検索 / 引用組み立て。
TOC ↔ e-gov 法令の相互リンク（引用グラフの芽）。

## 前提資産

- 指示書: Box `cc_instruction_legallib_journal_article_parser_20260605.md`(2266423916572)
  （parse_rate 80% hard / 90% soft、出力 schema 確定済）
- 雑誌 422号 / 124,529 toc nodes
- git 履歴の `data/egov` 痕跡（法令データ）

## 最初の一歩

1. article parser を全422号スイープ → `articles_extracted.jsonl`
2. 著者正規化（同名著者の disambiguation は背骨の resolver パターンで）
3. TOC見出し / 論文中の条文・判例参照を抽出して e-gov 法令へリンク

## 検収

- parse_rate ≥ 80%（hard）
- 著者横断検索が成立
- 法令リンクのサンプル目検
