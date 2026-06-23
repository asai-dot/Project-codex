---
request_id: 20260623_lease_subsystem_v0.1
topic: lease subsystem v0.1 — mutating レーン解禁の最小設計
gate: design
status: queued
result_expected_filename: 20260623_lease_subsystem_v0.1_GPTPRO_AUDIT_RESULT.md
submitted_to_box: 2026-06-23 to_gpt/ file_id=2303989218514
review_scope: LEASE_SUBSYSTEM_DESIGN_v0.1_20260623.md の設計妥当性 (mutating 解禁の安全性)
regression_anchors: HANDOFF_SCHEMA_APPENDIX_v0.5 §4.4 / HANDOFF_OPERATIONAL_IMPL_DESIGN_v0.1 / handoff_proto/validator.py
decision_requested: この設計で mutating レーンを解禁してよいか / §3 の block 集合は fail-closed として十分か / §7 の 4 問への判断
target_mode: design_review
source_hash: blob:366c1da0ff357854f417c1e9e6c18697f0800592 commit:b03d7a2
---

# REQUEST 20260623_lease_subsystem_v0.1

## 監査依頼

`LEASE_SUBSYSTEM_DESIGN_v0.1` は、現在 fail-closed で全 block している **mutating
レーン**を、time-bound・single-writer の **lease（占有権）** 付きで初めて解禁する
最小設計です。external 解禁・実 mutate 実行は範囲外。

## 観てほしい点

1. **fail-closed の網羅性**: §3 の mutating gate block 集合
   （`lease_ref_missing` / `lease_not_found` / `lease_inactive` / `lease_expired` /
   `lease_target_mismatch` / `lease_scope_mismatch` / `lease_holder_mismatch`）で、
   二重書き込み・期限切れ占有・他人のリースでの mutate を防げているか。漏れる経路は。
2. **単一実装の維持**: 検証を `handoff_proto/validator.py` に追加し運用ツールは import
   のみ、という方針（operational v0.1 must_fix #3）が壊れていないか。
3. **スコープ境界**: §5 の「解禁する / しない」が、これまでの HOLD（paid/egress/外部/
   本番DB/canonical/SF/自動実行）を一つも崩していないか。実 mutate を次 gate に分けた
   切り方は妥当か。
4. **feature flag 既定 off の継続**（must_fix #4）。

## 判断を仰ぐ事項（§7）

- target_key 正規化 / lease TTL 既定・上限 / holder 同定 / v0.1 を「dispatch 可判定
  まで」で切ることの是非。

## 添付（normative）

- `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.1_20260623.md`
- `tools/gpt_audit/handoff_proto/validator.py`（現 §4.4 実装）
- `tools/gpt_audit/HANDOFF_SCHEMA_APPENDIX_v0.5_20260619.md`
