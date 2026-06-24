# owner 裁定: authoritative evidence ④⑤ の「第2 node 源」供給方針

- 日付: 2026-06-15
- 裁定者: owner (asai)
- 文脈: legallibjoin v0.3.1 Phase B (`handoff/legallibjoin_v0.3.1_phaseB_assembler_20260615/B_STATUS.md` §6)。
  ローカルで TOC node を持つ源は legallib 1つだけで concordance の cross-source 一致が
  成立せず、authoritative な evidence ④ (all_nodes_accounted_for 照合) / ⑤ (apply_guard
  物理拒否ログ) が出せない。第2 node 源の供給方針を owner に問うた。

## 裁定 = (b) DD-TOCADOPT-001 の統合 corpus 完成を待ってから authoritative run

- 理由: DD-TOCADOPT-001 が同じ多源統合 (lionbolt / ndl_partinfo / bencom / bib_toc,
  projection dryrun=631クラスタ/116,727ノード) を進めており、legallibjoin レーンに別経路で
  corpus を接続すると **二重管理**になる。重複構築を避ける。
- 却下: (a) 既存 corpus を `--extra-sources` で今すぐ接続 (即 baseline は出るが経路二重化)。

## これにより gate される/されない作業

**待機 (統合 corpus 到着がトリガ):**
- `assemble_books.py --extra-sources <統合corpus>` → `concordance_pipeline` で
  authoritative evidence ④⑤ を golden10 込み生成 → owner ratify → 初めて apply 検討。

**待機しない (web 側で着手可・統合と独立):**
- edition v2 配線は完了済 (既定off / `edition_classifier_version=v2` or `--edition-version v2`
  で切替)。DD-EDIDENT-001 ratify 時に config 1フリップで強化版へ。
- 実10冊 golden 安全不変条件 (`tests/test_golden_edition.py`) は固定済。
- self-healing 上位設計 (DDSELFHEAL) は GPT DD 監査へ回せる状態。

## 不変条件 (再掲)
production apply / RDB write は HOLD 継続。本記録時点まで canonical/legallib/final_toc
への書き込みは一切なし (全レーン report-only)。
