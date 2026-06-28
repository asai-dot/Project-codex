# ALO-MODEL-ROUTER v0.1 — 実行権限ルーター

> ALO-MODEL-ROUTER は、モデルを賢さ順に並べる表ではない。
> task_type、cog_level、risk_level、mutation_power、data_zone、author_family に基づき、
> どの executor が、どの範囲で、何を書いてよいかを制御する**権限ルーター**である。

## 5つの原則（実装の本丸）
1. **安い頭に落とす**（cog_level を下げられる仕事は下げる）
2. **重い頭は1件だけ**（L4/L5 は max_items=1）
3. **異議申立ては別系統**（同family の自己レビューは独立監査ではない）
4. **書き込み権限は head/controller**（worker は draft_write まで）
5. **UNKNOWN は止める**（fail closed）

## 既存資産との関係（直交分担）
- 本ルーター = **権限**（誰が何を書けるか・どのレベルで処理するか）
- `docs/periodical/HEAD-ORDER-PROTOCOL.md` = **発注書の中身**（L3/L4/L5の実装ルール、EXIT条件）
- `CLAUDE.md` = ハンド呼出のショートカット（口語→トリガ投下）
- `.claude-orch/` = トリガ/キュー基板

雑誌オブジェクトはこのv0.1の最初のユーザー。

## 7階層（固定）
L0_DETERMINISTIC / L1_CHEAP_EXTRACTION / L2_LIGHT_SUMMARY / L3_NORMAL_WORK /
L4_DEEP_REASONING / L5_INDEPENDENT_AUDIT / L6_HUMAN_FINAL

詳細は `model_router.yml` 参照。

## ファイル構成
- `model_router.yml` — 階層・rules・hard_denies
- `model_registry.yml` — role → 現行モデルID対応（モデル名はここだけ・腐ったら差替）
- `data_policy.yml` — data_zone 別のモデル許可マトリクス
- `budget_policy.yml` — daily/batch/token 制限
- `schemas/` — queue_item / route_decision / worker_run_packet / run_summary / audit_result_candidate / finalization_record
- `scripts/` — scan_queue / classify_task / resolve_model_route / make_run_packet / validate_run_packet / collect_run_result / finalize_result / enforce_budget / verify_processed_mark
- `prompts/` — L1〜L5 の worker 固定プロンプト
- `tests/` — 品質ゲート逸脱を検出するpytest群

## ステータス
v0.1 freeze candidate。雑誌オブジェクトで先行運用、本ループ完了後にALO全体へ昇格。
