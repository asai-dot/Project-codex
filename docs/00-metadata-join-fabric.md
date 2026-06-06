# 接合ファブリック（初期概念整理）— SUPERSEDED

> この文書は会話初期の概念スケッチ。その後 Box の **ALO Knowledge Database 技術仕様書群**
> （正本/SoT）を精読した結果、本書の枠組みは正本設計に**置換された**。経緯保存のため残置。

## 何が置き換わったか（正しい理解）

- 当初「語彙が背骨」と書いたが、**正しくは日本法ハブ（SKOS星型, alo_hubs）が背骨**、
  NDLSH 等は attach 専用（語彙ハブ仕様書 v0.3.0）。Term=sense（v0.4.0増分）。
- 当初の「接合ファブリック」＝ 正本の **リンクレイヤ（alo_edges＋fingerprints）**。
  より厳密（時点版管理・根拠必須・assertion_mode規律・llm_inferred DB禁止）。
- 「本文なしでメタデータ接合で精度」＝ 正本の設計原則 **Links Are the Core Asset**。
- 「背骨は何本あってもええ／差し替えやなく追加」＝ Canonical/Derived分離・
  source_priority(override/append/defer)・provenance による**追加型**設計で実装済み。

## 現在の正本・実装プラン

- 正本: Box ALO 各レイヤ技術仕様書（[README](./README.md) 参照）
- 実装プラン: [`legallib-seed-build-plan.md`](./legallib-seed-build-plan.md)
