# DD-XDOC-001 v0.9 addendum (a) — 独立性 lineage 正本 pin（DD-INDEP-LINEAGE-001 consume）

> **id**: DD-XDOC-001 / **base version**: accepted v0.9（RESULT Box 2303550755480）/ **addendum**: a (v0.9a)
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-25 JST
> **gate**: 設計のみ addendum。DDL/DB/Box mutation/mint/OCR/embedding/production/clustering/promotion/claim-support は **HOLD**。
> **性質**: **base v0.9 を狭めも広げもしない一行統治 addendum**（再 ratify 不要）。DD-TRILOGY-RECONCILE-001 v0.3 が cross-DD を governs する枠組みで、XDOC の独立性参照先を新 leaf DD に明示固定するだけ。
> **depends_on（pin）**: **DD-INDEP-LINEAGE-001 v0.1**（独立性 lineage 正本・DDINDEP_PASS_WITH_NOTES・RESULT 2306834650821）/ DD-TRILOGY-RECONCILE-001 v0.3。

---

## 1. 何を固定するか
XDOC v0.9 の eligibility（§7 priority・coverage/support 判定）が用いる **content_independence / observation_independence** は、本 addendum により **DD-INDEP-LINEAGE-001 v0.1 §5 を唯一の正本として consume** する。XDOC は独立カウントを独自に再定義しない。
```text
content_independence     ≡ leaf §5 content_independent(content_lineage_binding)
                            = DISTINCT content_independence_group_id (active) ≥ 2
observation_independence ≡ leaf §5 observation_independent(observation_run)
                            = DISTINCT observation_lineage_root_id ≥ 2   # raw_input_hash 由来
unknown lineage           : leaf note5 — 不明系譜を既定で independent に格上げしない（保守化）
```

## 2. XDOC artifact が保持する pin（B 系の append-only/参照整合と整合）
eligibility/coverage/support の独立性判断を記録する artifact は、判断の再現性のため次を保持する：
```text
independence_assessment_ref:
  lineage_binding_ref            # leaf §2 content_lineage_binding（binding_id）
  independence_policy_version    # leaf §4 independence_policy の version
  effective_independence_group   # leaf が算定した content_independence_group_id（生 object_id でない）
  observation_lineage_root_ref   # leaf §3 observation_lineage_root_id
  input_fingerprint              # 判断入力の指紋（再評価検知用）
  indep_source_pin:              # ★leaf DD の exact pin
    id: DD-INDEP-LINEAGE-001 ; version: v0.1
    content_hash: <joint release manifest で確定>
    acceptance_ref: RESULT 2306834650821 (DDINDEP_PASS_WITH_NOTES)
```
- **binding stale → XDOC 側 assessment も stale/re-eval**（leaf §2 B2 と整合・silent に独立性を変えない）。

## 3. ゲート（addendum 差分のみ）
- **G_XDOC_INDEP_SOURCE_LEAF**：XDOC の独立性は leaf DD `DD-INDEP-LINEAGE-001` を pin して consume。XDOC 内で独立カウントを再定義しない。
- **G_XDOC_INDEP_PIN_REQUIRED**：independence_assessment は leaf を id+version+content_hash+acceptance_ref で pin。pin 欠落・content_hash 未確定は eligibility gate fail。
- **G_XDOC_INDEP_UNKNOWN_CONSERVATIVE**：upstream/collapse 不明の binding は独立票に数えない（leaf note5 / GROUP_UNKNOWN）。

## 4. 受入試験（addendum 差分）
1. XDOC eligibility が独立性を leaf §5 経由で判定（独自定義を持たない）。
2. independence_assessment_ref が leaf を exact pin（欠落・content_hash 未確定で gate fail）。
3. leaf binding が stale 化 → XDOC 側 assessment も stale → re-eval（append-only で証跡）。
4. 不明系譜 binding 2件のみ → content_independence=false（note5）。

## 5. loop_state
- **GO**：addendum 統治（base v0.9 不変・再 ratify 不要）／leaf pin 整合（RECONCILE v0.3・XMODAL v0.6 と相互 pin）／content_hash は joint release manifest で確定。
- **HOLD**：base v0.9 と同一（DDL/DB/mint/Box mutation/OCR/embedding/production/clustering/promotion/claim-support）。
- loop_state = **addendum 起票（v0.9a・独立性を leaf へ pin）→ joint release manifest に同梱**。
