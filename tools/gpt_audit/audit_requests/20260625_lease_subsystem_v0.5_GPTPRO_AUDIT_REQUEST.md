---
request_id: 20260625_lease_subsystem_v0.5
topic: lease subsystem v0.5 — mutating レーン解禁（v0.4 LEASE_MODIFY_REQUIRED への patch / clean PASS 狙い）
gate: design
status: queued
result_expected_filename: 20260625_lease_subsystem_v0.5_GPTPRO_AUDIT_RESULT.md
review_scope: LEASE_SUBSYSTEM_DESIGN_v0.5_20260625.md の設計妥当性 (v0.4 残 B11/B17 の閉塞・実装一意性)
regression_anchors: LEASE_SUBSYSTEM_DESIGN_v0.4 (result 2306561290821) / HANDOFF_SCHEMA_APPENDIX_v0.5 DISPATCH schema / HANDOFF_OPERATIONAL_IMPL_DESIGN_v0.1 / handoff_proto/validator.py
decision_requested: v0.4 残 blocking(B11 payload binding / B17 lease_echo)が閉じたか / §4 の gate 列で本文だけから一意な fail-closed validator が実装可能か / 繰延の切り方 / §9
prior_result: 2306561290821 (LEASE_SUBSYSTEM_DESIGN_v0.4, LEASE_MODIFY_REQUIRED)
target_mode: design_review
source_branch: claude/gpt-codex-mcp-plugin-r4cleb (repo: asai-dot/Project-codex, PR #29)
---

# REQUEST 20260625_lease_subsystem_v0.5

## 監査依頼

`LEASE_SUBSYSTEM_DESIGN_v0.5` は、v0.4（result 2306561290821, **LEASE_MODIFY_REQUIRED**）の
残 blocking 2 件への patch です。方針不変（dispatch 可判定まで・Box stable ID 限定・実 mutate /
external は別 gate・flag 既定 off）。clean PASS を取りに行きます。

## v0.4 残 → v0.5 対応（観てほしい中心）

- **B11 mutation payload binding**: §2.2 で `mutation_payload`/`immutable_payload_ref` +
  `mutation_payload_digest` + `conflict_policy` + `expected_item_type` + `expected_etag_or_sequence`
  を追加し packet hash 拘束。validator は executor 渡し payload と digest 一致を検査（§4 G_payload）、
  後段自由文補完を禁止。metadata values 差替え / rename actual name 不一致を block。
- **B17 lease_echo 廃止**: §1.4/§4 で packet echo を撤廃し、holder は trusted Env 由来のみで照合
  （spoof 対象が存在しない構造に）。
- 併せて CLOSED_WITH_NOTES の詰め: B10（schema patch version/hash pin・未 ratify で card 生成不可）、
  B12（lease_refs canonical sort・dup 拒否）、B13（authz policy hash 拘束・version 変更で stale）、
  B14（event 型別 schema）、B16（recovery queue runbook を operational gate 前に明示繰延）。
- **B18** は §8 に「次 gate（実 mutation）の実行直前再検証契約」として記述のみ（本版未実装）。

## 観てほしい点（横断）

- §4 の G0→G_schema→G1→G2→G_args→G_payload→G3→G4→G_chain→GA→L0→L 列で、本文のみから
  fail-closed validator が**実装一意**になっているか。残る曖昧点・迂回経路は。
- payload digest 拘束（packet hash 内 payload と executor payload の一致）で「後段すり替え」を
  塞げているか。
- 繰延事項（HANDOFF schema canonical patch / authz registry version 管理 / HMAC 鍵運用 / recovery
  queue runbook）を operational gate 前に回す切り方は妥当か。
- 単一実装維持・flag 既定 off 継続・§6 のスコープ境界が HOLD を崩していないか。

## 判断を仰ぐ事項（§9）

上記 decision_requested を参照。clean PASS 可否、又は残る must_fix の特定。

## 添付（normative; repo branch claude/gpt-codex-mcp-plugin-r4cleb）

- `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.5_20260625.md`（全文を下記に同梱）
- `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.4_20260625.md`（前段）
- `tools/gpt_audit/HANDOFF_SCHEMA_APPENDIX_v0.5_20260619.md`（DISPATCH schema の規範）
- `tools/gpt_audit/handoff_proto/validator.py`（現 §4.4 実装）

---

# 添付全文: LEASE_SUBSYSTEM_DESIGN v0.5

（本文は repo の `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.5_20260625.md` と同一。Box 単体監査用に同梱）
