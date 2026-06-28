# ALO-MODEL-ROUTER v0.1 FREEZE NOTE — 2026-06-27

ALO-MODEL-ROUTER は、モデルを賢さ順に並べる表ではない。
task_type、cog_level、risk_level、mutation_power、data_zone、author_family に基づき、
どの executor が、どの範囲で、何を書いてよいかを制御する**権限ルーター**である。

高級モデルは、難所を判断するために使う。
大量処理、探索、整形、status更新、processed化には使わない。

独立監査は、能力差ではなく系統差で成立する。
作成者と同じ family のモデルによるレビューは、独立監査ではない。

worker は候補を作る。
controller/head が確定する。
canonical、accepted、production DB、processed mark は worker の権限外である。

## 5 invariants
1. **安い頭に落とす** (cog_level を下げられる仕事は下げる)
2. **重い頭は1件だけ** (L4/L5 は max_items=1)
3. **異議申立ては別系統** (same family audit禁止)
4. **書き込み権限は head/controller** (worker は draft_write まで)
5. **UNKNOWN は止める** (fail closed)

## v0.1 で実装されたもの
- model_router.yml / model_registry.yml / data_policy.yml / budget_policy.yml
- schemas: queue_item / route_decision / worker_run_packet / run_summary / audit_result_candidate / finalization_record / result_candidate
- scripts: scan_queue / classify_task / resolve_model_route / make_run_packet / validate_run_packet / collect_run_result / finalize_result / enforce_budget / verify_processed_mark
- prompts: L1 / L2 / L3 / L4 / L5
- tests: 6つの guard test (全PASS)

## 雑誌オブジェクトでの先行運用
雑誌スレ(claude/magazine-object-analysis-seg9cr)が本v0.1の最初のユーザー。
既存の HEAD-ORDER-PROTOCOL.md (発注書の中身) と直交分担:
- ALO-MODEL-ROUTER = 権限ルーター (誰が何を書けるか)
- HEAD-ORDER-PROTOCOL = 発注書の中身 (L3/L4/L5の実装ルール、EXIT条件)
- CLAUDE.md / .claude-orch/ = 起動チャネル

## 昇格判断 (EXIT-A or 形を変えての適用)
- 雑誌オブジェクトEXIT-C到達時に、本ルーターを ALO 全体に昇格させる
- それまでの間、雑誌スレで以下を監視:
  - HD1〜HD5 のうちどれかが実運用で違反しそうになる場面
  - 5 invariants のうちどれかが破られそうになる場面
  - data_zone マトリクスの不足 (新zone追加が必要な瞬間)
これらが3件以上発生したら v0.2 起こす。
