# IMPL_STATUS 進捗共有レビュー結果 (記録) + closeout note 反映

- RESULT: `from_gpt/20260611_legallibjoin_v0.3.1_IMPL_STATUS_REVIEW_RESULT.md` (file 2283375021595, 2026-06-13)
- verdict: **IMPL_STATUS_PASS_WITH_NOTES** / production_apply=HOLD / rdb_write=HOLD
- 重大ドリフトなし。P0 7点カバー確認。Phase0/A report-only 継続可。

## 反映した closeout note (本コミット)
- normalizer/page_basis/concordance の **version stamp** を report 出力(report.md/summary.json)に追加
  (PIPELINE_VERSIONS; 各モジュールに *_VERSION="0.3.1")。
- **consensus 除外 source 数**(provenance_origin 未宣言)を book_summary と report に出力。
- report 文言に「`pdf_primary` は qualified PDF observation であり絶対真理ではない」を明記。
- decision_log chain hash 検証は verify_chain で Phase0 サンプル検証する旨を evidence 要件に明記(下記)。

## Phase0 後の最小 dry-run evidence (GPT 指定5点・Mac inventory 後にこれで足りる)
1. source inventory table
2. parser success histogram
3. 既知 conflict 10冊 seed
4. all_nodes_accounted_for count reconciliation
5. apply_guard が 未whitelist / 未解決conflict を物理拒否するログ
+ decision_log chain hash のサンプル検証 (verify_chain)。

## HOLD 維持
production apply / final_toc / RDB write は未承認。実データ inventory(Mac Phase0)待ち。
