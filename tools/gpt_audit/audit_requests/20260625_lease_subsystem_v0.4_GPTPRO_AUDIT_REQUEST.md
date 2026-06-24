---
request_id: 20260625_lease_subsystem_v0.4
topic: lease subsystem v0.4 — mutating レーン解禁（v0.3 LEASE_MODIFY_REQUIRED への patch）
gate: design
status: queued
result_expected_filename: 20260625_lease_subsystem_v0.4_GPTPRO_AUDIT_RESULT.md
review_scope: LEASE_SUBSYSTEM_DESIGN_v0.4_20260625.md の設計妥当性 (v0.3 blocking B9-B16 の閉塞確認・実装一意性)
regression_anchors: LEASE_SUBSYSTEM_DESIGN_v0.3 (result 2306525973159) / HANDOFF_SCHEMA_APPENDIX_v0.5 DISPATCH schema / HANDOFF_OPERATIONAL_IMPL_DESIGN_v0.1 / handoff_proto/validator.py
decision_requested: v0.3 blocking B9-B16 が閉じたか / §4 の G0-L gate 列で本文だけから一意な fail-closed validator が実装可能か / §8 の残論点4件
prior_result: 2306525973159 (LEASE_SUBSYSTEM_DESIGN_v0.3, LEASE_MODIFY_REQUIRED)
target_mode: design_review
source_branch: claude/gpt-codex-mcp-plugin-r4cleb (repo: asai-dot/Project-codex, PR #29)
---

# REQUEST 20260625_lease_subsystem_v0.4

## 監査依頼

`LEASE_SUBSYSTEM_DESIGN_v0.4` は、v0.3（result 2306525973159, **LEASE_MODIFY_REQUIRED**）の
blocking B9–B16 への patch です。方針不変（dispatch 可判定まで・Box stable ID 限定・実 mutate /
external は別 gate）。狙いは「本文だけで一意な fail-closed validator が実装可能」になること。

## v0.3 blocking → v0.4 対応（観てほしい中心）

- **B9（回帰）feature-flag gate 脱落**: §4 **G0** として最初に明記。flag off は authorize/ledger
  read/write/card を一切行わず block。fx#0 で negative 固定。
- **B10 mutation_op を上位 schema/packet hash に接続**: §2.1 で HANDOFF DISPATCH schema に条件付き
  必須 field として正規追加（registry id/version/content_hash + required_lock_domains_digest +
  required_scopes_digest + lease_set_digest）、全て packet hash 対象。canonical patch は別 ratify。
- **B11 typed mutation_args**: §2.2 で op 別 typed args 固定、`required_lock_domains(op,args)` 純関数
  （§1.3）、Box read で current 照合（§4 G_args）。
- **B12 exact lease set binding**: §2.3 で canonical-sorted `lease_refs[]`（grant_event_hash 含む）
  必須、`lease_set_digest` を hash 対象、active view と exact match（§4 L）、実 mutation gate 再検証。
- **B13 authorization registry 正本 + principal 分離**: §3 で上位 HANDOFF versioned policy registry
  を正本（validator 参照のみ）、holder と authorization principal を別 field、既定 deny。
- **B14 event 遷移/ sequence**: §1.5 で有効遷移固定、global sequence と per-lease ordinal 分離、
  invalid transition は view invalid で block。
- **B15 HMAC key lifecycle**: §1.6 で key id/version/algorithm・rotation・旧 key read-only verify・
  取得失敗 block・署名対象 bytes 固定。
- **B16 multi-lease partial failure**: §2.4 で acquisition_attempt_id・逆順 release・recovery queue・
  全 exact lease ref 成立時のみ dispatch。

## 観てほしい点（横断）

- §4 の G0→G1→G2→G_args→G3→G4→G_chain→GA→L 列で、本文のみから fail-closed validator が**実装
  一意**になっているか。残る曖昧点・迂回経路は。
- §2.1 の HANDOFF schema 追加（mutation_op/args/lease_refs/digest 群）が上位 schema と整合し、
  packet hash・thin index・staleness と矛盾しないか。canonical 化を別 ratify に切る判断の是非。
- 単一実装維持（validator.py 集約）・flag 既定 off 継続。
- §6 のスコープ境界が HOLD を一つも崩していないか。

## 判断を仰ぐ事項（§8 残論点）

1. HANDOFF schema への追加を v0.4 は提案に留め canonical patch は別 ratify gate で良いか。
2. authorization policy registry の version 管理主体。
3. HMAC 鍵 rotation 周期・保管（Env secret + key id で当面確定可か）。
4. recovery queue（孤児 lease）の掃除主体（v0.4 は運用ツール手動 release で十分か）。

## 添付（normative; repo branch claude/gpt-codex-mcp-plugin-r4cleb）

- `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.4_20260625.md`（全文を下記に同梱）
- `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.3_20260625.md`（前段）
- `tools/gpt_audit/HANDOFF_SCHEMA_APPENDIX_v0.5_20260619.md`（DISPATCH schema の規範）
- `tools/gpt_audit/handoff_proto/validator.py`（現 §4.4 実装）

---

# 添付全文: LEASE_SUBSYSTEM_DESIGN v0.4

（本文は repo の `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.4_20260625.md` と同一。Box 単体監査用に同梱）
