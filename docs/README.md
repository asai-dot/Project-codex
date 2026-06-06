# Project Codex — 設計ドキュメント

法令・判例・文献・雑誌・語彙・手続・書式を、**本文を持たずメタデータ同士の接合**で
ひとつの知識グラフに繋ぐための設計メモ群。

## 地図（まず読む）

- [`00-metadata-join-fabric.md`](./00-metadata-join-fabric.md)
  — 接合ファブリック全体像 ＋ 共通 resolver 背骨（= Fork 0）。全フォークの上位概念。

## フォーク（各エッジを足していく作業）

| # | テーマ | 依存 | 概要 |
|---|---|---|---|
| 1 | [接合の実装設計](./forks/01-join-implementation.md) | 背骨そのもの | legallib 詳細TOC → 本番 canonical を安全接合 |
| 2 | [検索 / RAG](./forks/02-search-rag.md) | Fork 1 | 章節横断検索＋ページアンカー付きアシスタント |
| 3 | [購入レコメンド](./forks/03-acquisition-recommender.md) | 単体可 | 未所蔵×詳細TOC をギャップスコアで提案 |
| 4 | [論文entity＆法令リンク](./forks/04-article-entity-law-links.md) | Fork 1（所蔵紐付け部分） | 雑誌の論文分解＋TOC↔e-gov 法令リンク |

## 資産の所在（2026-06 時点）

- **実データ・スクリプト**: Box `浅井/claude/事務所内本棚DX化計画/`（本番アプリ）と `浅井/CODEX/`（接合スクリプト）
- **DB**: Supabase（`alo-connect` / `asai-dot's Project`）
- **このリポジトリ**: 設計の集約地（地図と判断の記録）。実装成果物の置き場は Fork 1 で確定する。
