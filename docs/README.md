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
  — legallib → biblio 取込プラン v0.4（ライブスキーマ準拠）。**legallib は既存 Supabase `biblio`
  スキーマ（弁コム・所蔵が稼働中）への source 追加**。`asai-biblio-ingest` の load_bencom.py に倣う。
  v0.1〜v0.3（alo.works/メダリオン）は撤回・superseded。

## 補足

- [`00-metadata-join-fabric.md`](./00-metadata-join-fabric.md)
  — 初期の概念整理。**ALO 正本設計に置換済み（superseded）**。経緯保存のため残置。
- `forks/` — 派生アイデアの探索メモ（検索/RAG・購入レコメンド・論文entity 等）。正本ではない。
