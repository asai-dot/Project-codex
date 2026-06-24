# 方針確定: legallib 接合は v0.3.1 一本化 (LEGALLIBJOIN_STRATEGY_V03_1_FIRST)

- 裁定: GPT `from_gpt/20260611_legallibjoin_strategy_clarification_RESULT.md` (file 2279046688799)
- verdict: **LEGALLIBJOIN_STRATEGY_V03_1_FIRST**（案B採用）/ owner 受領済

## 確定方針
```
primary_path: v0.3.1 concordance design -> re-audit -> dry-run -> whitelist apply
v0.2_batchA : do NOT execute as production apply
v0.2_artifacts: preserve as baseline / evidence / whitelist seed only
withdraw_notice: maintain
```

## KEEP (v0.3.1 へ継承・破棄しない)
- F1 converter children 再帰 / F2 auto_accept 有効ISBN gate / F3 構造ガード / provenance（コードはそのまま）。
- v0.2 成果物: 943 write candidates / Batch A ISBN list / write_candidates.csv hash /
  inputs_sha256 / flip_analysis / **138,970 bencom protected evidence** = baseline/evidence/whitelist seed。

## HOLD (停止)
- v0.2 Batch A production apply（`legallib_join_apply.py --commit`）← 発注は撤回 (Box WITHDRAWN 通知投函済)。
- Batch B/C 判断 / hold_overwrite_diff 根拠の追加承認 / v0.3.1 hard gate 未実装 apply。

## GO (次)
- DDLEGALLIBCONCORD (v0.3 concordance, MODIFY_REQUIRED) の P0 7点反映 → **legallibjoin v0.3.1 再投函**。
- v0.3.1: concordance source inventory / conflict status / whitelist hard gate を通過したもののみ apply 候補へ。

## 運用改善 (GPT 採択・今後の投函規約)
1. 投函直前に Mac CC / web CC で内輪同期。
2. 同一テーマの異PR投函禁止、単一 request_id へ統合。
3. 撤回判断は同テーマ from_gpt RESULT 直近24h確認後。
4. REQUEST 冒頭に supersedes / parallel_related / withdrawal_effect を必ず記載。
5. 同一テーマで複数 RESULT が出たら strategy_clarification を先に投げ、apply 系は停止。
6. from_gpt RESULT に current_governing_result: true/false を付ける。

## 他トラックの未済 (owner 整理・参考)
- lawtime v0.2.3: `DDLAWTIME_PASS_WITH_NOTES` (file 2278926323362) → 次は owner ratify / branch dry-run / gate空確認。
