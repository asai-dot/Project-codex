DDSELFHEAL_PASS_WITH_NOTES

request_id: DDSELFHEAL
reviewed_at_jst: 2026-06-15
gate: design_direction
scope: self-healing literature data platform / 3-layer chain / scan-repair-rescan loop
production_apply: HOLD
rdb_write: HOLD
repair_write: HOLD_until_owner_ratify_and_gate

(from_gpt/DDSELFHEAL_result.md Box 2286209883693 の控え。反映状況は
20260615_DDSELFHEAL_PASS_WITH_NOTES.md を参照。)

## verdict
DDSELFHEAL_PASS_WITH_NOTES. 設計方針は正しい (単発の接合を恒常 corpus health ループへ)。
ただし self-healing 書込はまだ許可しない。SCAN/分類/dashboard は report-only で可。repair 実行は
gated・可逆・owner ratify 必須。決定的 repair / ratchet / quarantine KPI / whitelist の境界を明確化せよ。

## answers (要旨)
1. repair 決定性境界: 決定的・可逆・局所・before/after 完全トレース・意味判断なしのみ auto。
   auto 可=body_sha 再計算/page_basis 再profiling/信頼1.0+検証済 本単位 offset/決定的 fingerprint
   再生成/unaccounted→quarantine。auto 不可=orphan 再parent(曖昧)/edition 同定/意味マージ/NDC補完/
   canonical・accepted TOC・source snapshot 変更。
2. ratchet: score 下降は decision_log 理由必須で許容可。真の不変条件=silent degradation なし/
   unlogged regression なし/clean set 理由なき縮小なし/repair は冪等可逆/quarantine は明示。
   30/40/30 と係数0.85 は dashboard 既定としては可だが policy parameter に。edition 未解決は
   health に関わらず apply 適格を 0 に cap せよ。
3. quarantine: clean 改善の手段だが corpus を綺麗にしたのとは別。clean_set_growth/quarantine
   count・rate・age/escape_rate/recurrence を track。quarantine は成功でなく管理対象の負債。
4. apply_guard+whitelist: auto repair も whitelist+apply_guard 必須は適切 (法務データでは過剰でない)。
   将来、ごく狭い決定的 repair に低摩擦レーンを足す余地。C0=全書込 whitelist+gate / C1=pre-approved
   決定的 class / C2=identity・canonical は owner approve。

## must_fix
1 repair class 5分類 / 2 raw source mutate 禁止 / 3 identity・canonical は owner packet 必須 /
4 health_score と apply_eligibility 分離 (高 health≠apply 許可) / 5 quarantine KPI /
6 regression taxonomy / 7 repair manifest schema / 8 LLM・semantic は決定的ループ外 (v0.4)。

## should_fix
層別重み thresholds 可変 / health と独立の P0 apply cap / golden を10冊から拡張してから repair 書込 /
health・eligibility・quarantine・regression を別 dashboard track / repair_noop_idempotent gate /
clean_set_membership_reason。

## release boundary
今 許可: 設計採用 / report-only SCAN・分類・dashboard / data_health・thresholds・golden 可視化 /
manifest・gate 設計準備。
HOLD: production apply / RDB write / repair 書込 / canonical projection 変更 / raw source 変更 /
semantic・LLM repair / owner whitelist 緩和。

## final
DDSELFHEAL_PASS_WITH_NOTES. self-healing ループは正しい長期方向。まず health・quarantine の
ガバナンス層として扱い、自律書込エンジンにしない。repair 実行は owner ratify + class 境界 +
quarantine KPI + health/apply 分離 + manifest schema + rollback + apply_guard 強制を待つ。
