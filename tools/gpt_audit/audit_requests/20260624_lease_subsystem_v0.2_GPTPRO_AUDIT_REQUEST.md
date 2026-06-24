---
request_id: 20260624_lease_subsystem_v0.2
topic: lease subsystem v0.2 — mutating レーン解禁（v0.1 MODIFY_REQUIRED への patch）
gate: design
status: queued
result_expected_filename: 20260624_lease_subsystem_v0.2_GPTPRO_AUDIT_RESULT.md
review_scope: LEASE_SUBSYSTEM_DESIGN_v0.2_20260624.md の設計妥当性 (v0.1 must_fix 6件の閉塞確認)
regression_anchors: LEASE_SUBSYSTEM_DESIGN_v0.1 (result 2304096222240) / HANDOFF_SCHEMA_APPENDIX_v0.5 §4.4 / HANDOFF_OPERATIONAL_IMPL_DESIGN_v0.1 / handoff_proto/validator.py
decision_requested: v0.1 must_fix 6件が閉じたか / §3 の G0-G10 は fail-closed として十分か / §7 の残論点4件への判断
prior_result: 2304096222240 (LEASE_SUBSYSTEM_DESIGN_v0.1, MODIFY_REQUIRED)
target_mode: design_review
source_branch: claude/gpt-codex-mcp-plugin-r4cleb (repo: asai-dot/Project-codex, PR #29)
---

# REQUEST 20260624_lease_subsystem_v0.2

## 監査依頼

`LEASE_SUBSYSTEM_DESIGN_v0.2` は、v0.1（result 2304096222240, **MODIFY_REQUIRED**）で
指摘された must_fix 6件への patch です。mutating レーンを lease 付きで **dispatch 可判定
まで**解禁する方針は不変。実 mutate 実行・external は範囲外（別 gate）。

## v0.1 must_fix → v0.2 対応（観てほしい中心）

1. **ledger 書込み安全境界**（#1）: §1.1 で単一固定 path・append-only・create-new
   (no-overwrite)・hash chain を必須化し、チェーン不整合は `lease_ledger_tampered` で
   全 block。これで grant/release を「承認不要事務」に収める根拠が立つか。
2. **canonical_target_key**（#2）: §1.2 で Box file_id/folder_id 等 stable id を最優先、
   path のみは realpath/NFC/case/trailing-slash 正規化必須、正規化不能は block。抜け道は。
3. **holder 合成**（#3）: §1.3 で assignee+machine_id+runner_id/session_id の合成、欠落は
   `holder_underspecified`。単一書き手同定として十分か。
4. **TTL**（#4）: §1.4 で既定 30 分・上限 2h・無期限禁止・延長は新発行（in-place 更新は
   §1.1 で構造的に不可）。
5. **scope 正規化**（#5）: §1.5 で enum set・完全一致のみ・prefix 一致禁止。
6. **二重 active 検出**（#6）: §3 G10 で同一 (canonical_target_key, scope) に active 複数
   → `lease_double_active`。運用側 grant でも二重防御。

## 観てほしい点（横断）

- §3 の G0–G10 gate 列が fail-closed として網羅的か（不明・欠落・改ざんを全て block 側へ）。
  漏れる mutate 経路は残っていないか。
- 単一実装維持（validator.py に集約・運用ツールは import のみ）が壊れていないか。
- §5 のスコープ境界が HOLD（paid/egress/外部/本番DB/canonical/SF/自動実行/実 mutate）を
  一つも崩していないか。
- feature flag 既定 off の継続（operational must_fix #4）。

## 判断を仰ぐ事項（§7 残論点）

1. canonical_target_key の stable id 優先順位（Box は file_id/folder_id 固定で可か / ローカルは
   realpath で十分か）。
2. holder の runner_id と session_id のどちらを正とするか。
3. 既定 TTL 30 分・上限 2h の確定可否。
4. v0.2 も「dispatch 可判定まで」で切り実 mutate は次 gate、の再確認。

## 添付（normative; repo branch claude/gpt-codex-mcp-plugin-r4cleb）

- `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.2_20260624.md`（全文を下記に同梱）
- `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.1_20260623.md`（前段）
- `tools/gpt_audit/handoff_proto/validator.py`（現 §4.4 実装）
- `tools/gpt_audit/HANDOFF_SCHEMA_APPENDIX_v0.5_20260619.md`

---

# 添付全文: LEASE_SUBSYSTEM_DESIGN v0.2

（本文は repo の `tools/gpt_audit/LEASE_SUBSYSTEM_DESIGN_v0.2_20260624.md` と同一。Box 単体監査用に同梱）
