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
  — legallib → biblio 取込プラン **v0.5**（ライブスキーマ準拠 ＋ legaldb v0.5 監査整合）。**legallib は既存
  Supabase `biblio` スキーマ（弁コム・所蔵が稼働中）への source 追加**。`asai-biblio-ingest` の load_bencom.py に倣う。
  v0.5 で GPT お目付け役 `legaldb v0.5 DESIGN`（MODIFY_REQUIRED）の横断指摘 F1/F2/F5/F6 を biblio 層へ落とし込み
  （識別子責務表・anchor⊥locator・candidate規律・over-reachラベル）。v0.1〜v0.3 は撤回・superseded。
- [`../loaders/load_legallib.py`](../loaders/load_legallib.py) / [`sanity_checks.sql`](../loaders/sanity_checks.sql)
  — ローダのドラフトと取込後検証クエリ。フィールド名未確定箇所は TODO 明示。

## 補足

- [`00-metadata-join-fabric.md`](./00-metadata-join-fabric.md)
  — 初期の概念整理。**ALO 正本設計に置換済み（superseded）**。経緯保存のため残置。
- `forks/` — 派生アイデアの探索メモ（検索/RAG・購入レコメンド・論文entity 等）。正本ではない。
