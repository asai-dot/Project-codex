# DDJOINAUDIT 監査 (MODIFY_REQUIRED) → P0-1/P1 実装で対応

- 監査: `to_gpt/20260610_legallibjoin_analysis_v0.1_DDJOINAUDIT_REQUEST.md` (2277162918122)
  → GPT `DDJOINAUDIT_MODIFY_REQUIRED` (RESULT: `from_gpt/..._DDJOINAUDIT_RESULT.md`, 2277275881483)
- owner 懸念「web の分析が危ない気がする」= **半分正解**。分析は安全側で妥当だが、
  ツールが「レビュー前提」を物理強制していない点が P0。

## 判定要旨
- web Claude の分析(7主張)は概ね妥当。`invariant 0 はトートロジー気味`の自己評価も「正しい謙抑」。
- 危険の正体: `overwrite_simple`(=既存全置換) が `create`(=非破壊) と同じ WRITE_ACTIONS に入り、
  **whitelist 無し `apply --commit` で全 overwrite を書ける**。レビューが人手運用頼みで CLI 未強制。

## 実装した対応 (PR #5)
- **P0-1 [済]**: `legallib_join_apply.py` — commit かつ overwrite_simple を含み whitelist 無し →
  **拒否 (exit 1)**。`create`(非破壊)のみ自動可、`overwrite` は `--only-isbns` 承認必須。
- **P1 rollback [済]**: `--backup-dir` で overwrite 前に旧ファイルを退避 (create は対象外)。
- テスト追加 (拒否/承認済みで書込/backup)。全 34+101+45=180 checks 緑。

## 残ゲート (本適用前・owner/Mac)
- P0-2: F3後の全数ドライラン再実行 (旧 4a7bea1 数字は使わない)。
- P0-3: 全 overwrite を render_proposed_diff で enrich/replace 仕分け、replace は原則 human_review。
- P1: apply log に old/new sha・provenance。render_proposed_diff に正規化タイトル類似度+page近接を追加(将来)。
- 全置換 vs マージ: 当面は全置換でよい(マージは偽構造リスク)。
