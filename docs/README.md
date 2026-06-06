# Project Codex — 設計ドキュメント

## 正本（SoT）は Box の ALO 技術仕様書

このリポジトリは**正本ではない**。法令・判例・文献・雑誌・語彙・リンクの設計の正本は
Box `事務所内本棚DX化計画` ほかにある ALO Knowledge Database 技術仕様書群：

- 全体 / 法令 / 判例 / 文献 / 雑誌 / 語彙ハブ(v0.3.0+v0.4.0増分) / リンク 各レイヤ仕様書
- データリネージ仕様書 v1.0 / Multi-Agent Access Spec
- 語彙ハブ設計仕様書（term_dict ボトムアップ進捗含む）

本リポジトリは、それらに**準拠した実装プラン／状態スナップショット**の置き場として使う
（competing SoT を作らない）。

## 実装プラン

- [`legallib-seed-build-plan.md`](./legallib-seed-build-plan.md)
  — legallib 詳細TOC を起点とした RDB 構築プラン v0.2（対象: Supabase `asai-dot's Project`）。
  ALO 各レイヤ仕様に突合済み。DB未適用（P0=DDLレビュー後に適用）。

## 補足

- [`00-metadata-join-fabric.md`](./00-metadata-join-fabric.md)
  — 初期の概念整理。**ALO 正本設計に置換済み（superseded）**。経緯保存のため残置。
- `forks/` — 派生アイデアの探索メモ（検索/RAG・購入レコメンド・論文entity 等）。正本ではない。
