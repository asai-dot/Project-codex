---
request_id: 20260625_lease_subsystem_v0.3
topic: lease subsystem v0.3 — mutating レーン解禁（v0.2 LEASE_MODIFY_REQUIRED への patch）
gate: design
status: queued
result_expected_filename: 20260625_lease_subsystem_v0.3_GPTPRO_AUDIT_RESULT.md
review_scope: LEASE_SUBSYSTEM_DESIGN_v0.3_20260625.md の設計妥当性 (v0.2 blocking B1-B8 の閉塞確認)
regression_anchors: LEASE_SUBSYSTEM_DESIGN_v0.2 (result 2306477639392) / HANDOFF_SCHEMA_APPENDIX_v0.5 §4.4 next_action_type enum / HANDOFF_OPERATIONAL_IMPL_DESIGN_v0.1 / handoff_proto/validator.py
decision_requested: v0.2 blocking B1-B8 が閉じたか / §4 の A-gate(認可) ∧ L-gate(排他) は fail-closed として十分か / §8 の残論点4件への判断
prior_result: 2306477639392 (LEASE_SUBSYSTEM_DESIGN_v0.2, LEASE_MODIFY_REQUIRED)
target_mode: design_review
source_branch: claude/gpt-codex-mcp-plugin-r4cleb (repo: asai-dot/Project-codex, PR #29)
---

# REQUEST 20260625_lease_subsystem_v0.3

## 監査依頼

`LEASE_SUBSYSTEM_DESIGN_v0.3` は、v0.2（result 2306477639392, **LEASE_MODIFY_REQUIRED**）の
blocking findings B1–B8 への patch です。方針（lease 付きで dispatch 可判定まで解禁・実
mutate / external は別 gate）は不変。今回 **初期解禁対象を Box stable ID object に限定**
（B7）し、**認可と排他 lease を分離して AND**（B1）しました。

## v0.2 blocking → v0.3 対応（観てほしい中心）

- **B1 認可 ≠ lease**: §2 で `authorized(principal, op, domains) ∧ ∀domain valid_exclusive_lease`
  を AND。lease 単独で認可不可。issuer と principal を分離（§2.1, §4 GA1-2）。
- **B2 scope/operation 結合 + schema 違反**: §1.2 で `next_action_type` enum は触らず別 field
  `mutation_op` の registry を新設、`required_scopes = derive(op, side_effect_flags)` を local
  deterministic 導出、packet による縮小を block（§3 G2）。
- **B3 multi-target**: §1.3 `required_lock_domains` を registry 導出、全 domain に lease 要求、
  canonical order で deadlock 回避（§4 L-loop）。
- **B4 trusted holder**: §1.4 で holder を Env から注入（primary=runner_instance_id）、packet
  holder は echo・不一致は `holder_spoofed`（§4 L8）。
- **B5 event sourcing**: §1.5 で grant/release/revoke + sequence_no + prior_event_hash、state は
  fold 導出、expired は時刻導出。
- **B6 原子性/並行/改ざん**: §1.6 single-writer/OS lock・O_APPEND・fsync・partial-tail
  quarantine・UUIDv7 unique・HMAC（tamper-evident と tamper-proof を区別）。
- **B7 identity**: §1.1 初期 Box stable ID 限定、local は stat identity+parent で dispatch 直前
  再照合（将来）。
- **B8 trusted input**: §1.6/§4 G_chain で genesis→tail 全 chain 検証、lookup は検証済み view
  単一実装から。

## 観てほしい点（横断）

- §4 の G1→G_chain→A-gate→L-gate 列が fail-closed として網羅的か。認可と排他を AND した形で
  迂回経路が残っていないか。
- `mutation_op` registry と `next_action_type` enum の分離が上位 HANDOFF schema と整合するか。
- 単一実装維持（validator.py 集約・運用ツールは import のみ）。
- §6 のスコープ境界が HOLD を一つも崩していないか。flag 既定 off 継続。

## 判断を仰ぐ事項（§8 残論点）

1. 認可 policy registry の置き場（validator 同梱 / 別 file / 上位 schema 追加）。
2. `mutation_op` を上位 HANDOFF schema に正規追加するか、lease ローカル registry に留めるか。
3. HMAC 鍵管理（Env 注入で可か / 外部 append-only log 移行余地）。
4. local object 解禁は次々 gate で良いか（v0.3 は Box stable ID 限定で確定）。

## 添付（normative; repo branch claude/gpt-codex-mcp-plugin-r4cleb）

- `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.3_20260625.md`（全文を下記に同梱）
- `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.2_20260624.md`（前段）
- `tools/gpt_audit/handoff_proto/validator.py`（現 §4.4 実装）
- `tools/gpt_audit/HANDOFF_SCHEMA_APPENDIX_v0.5_20260619.md`（next_action_type enum の規範）

---

# 添付全文: LEASE_SUBSYSTEM_DESIGN v0.3

（本文は repo の `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.3_20260625.md` と同一。Box 単体監査用に同梱）
