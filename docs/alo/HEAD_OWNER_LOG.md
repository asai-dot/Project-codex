# HEAD_OWNER_LOG — 航海日誌（Head↔Owner 決定ログ・単一の真実）

> 本ファイルは DD-ORCH-CONTINUITY-001 v0.3（RATIFIED 2026-06-30）の成果物。
> **継続性・意図・HOLD・owner pending の蒸留ログに限定**（設計判断正本ではない）。
> head は3トリガ（方針決定 / 発注・検収 / owner判断待ち発生）でのみ digest を5行追記し push。
> 代理 head BOOTSTRAP: ①本ファイル全文 ②`claude agents --json` ③`git log -15` ④`owner_pending: yes` を最優先。
> 正本参照: `origin/claude/magazine-object-analysis-seg9cr:docs/alo/HEAD_OWNER_LOG.md`（head infra 正本ブランチ）。ORCH は `required_log_commit / required_digest_id /
> required_standing_ids` を、worker RESULT は `read_log_commit / read_digest_id / read_standing_ids` を持つ。

---

## A. STANDING（恒久の決定・好み・禁止 / active 最大20・各3行以内）

- standing_id: HOS-001
  rule: 共有ブランチへ force push / -f 禁止（rebase 後に通常 push）
  applies_to: all branches | enforcement: global_required | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

- standing_id: HOS-002
  rule: external_share_allowed=false は不変（外部公開しない）
  applies_to: all data | enforcement: global_required | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

- standing_id: HOS-003
  rule: canonical 昇格・DB投入・accepted edge化・外部公開・生payload取込は owner(asai) GO 必須
  applies_to: all threads | enforcement: global_required | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

- standing_id: HOS-004
  rule: ローカルちゃん(ローカルLLM)へは必ず処理可能サイズにチャンク分割してから発注
  applies_to: local dispatch | enforcement: task_scoped | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

- standing_id: HOS-005
  rule: 常駐デーモンを増やさない（コスト過大）。storm対策は wake_worker の起動時 cap ゲートで足りる
  applies_to: orchestration | enforcement: global_required | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

- standing_id: HOS-006
  rule: DD 監査は Box gpt_ometsuke/to_gpt 経由。PASS_WITH_NOTES 以上 → owner ratify → accepted → main commit → 実装
  applies_to: design audits | enforcement: task_scoped | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

---

## B. SESSION DIGESTS（新しい順・直近~30件 / 1件5行）

- digest_id: HOL-20260630-003
  trigger: handoff_review
  summary: ORCH検収ゲートを実行スクリプト化（tools/head_owner_log_gate.py）。7 reject code + alias lint を機械判定
  reason: protocol のチェック表を完全自動化（owner GO）。自己検証9ケース全 PASS
  related_orch: DD-ORCH-CONTINUITY-001 v0.3 | related_commit: (本コミット) | owner_pending: no

- digest_id: HOL-20260630-002
  trigger: handoff_review
  summary: head が data limit で停止 → 代理 head が git+監査レーン+claude agents から状態復元（F1 を実演）
  reason: HEAD_OWNER_LOG 未実装だったため手動フォールバックで復旧。本 seed 作成の直接動機
  related_orch: (なし) | related_commit: (本コミット) | owner_pending: no

- digest_id: HOL-20260630-001
  trigger: handoff_review
  summary: DD-ORCH-CONTINUITY-001 v0.3 が GPT Pro で DESIGN_PASS_WITH_NOTES → owner ratify → 実装GO
  reason: v0.2 の祖先方向バグ＋field統一＋enforcement scope を v0.3 で閉鎖
  related_orch: RATIFY_DD-ORCH-CONTINUITY-001_v0.3_20260630.md | related_commit: (本コミット) | owner_pending: no

- digest_id: HOL-20260629-002
  trigger: policy_decision
  summary: head 交代継続＋ワーカー意図伝播のため航海日誌(HEAD_OWNER_LOG)を起票（F1/F2 解消）
  reason: 意図・経緯が head 会話にしか宿らず limit で揮発する問題
  related_orch: DD-ORCH-CONTINUITY-001 | related_commit: - | owner_pending: no

- digest_id: HOL-20260629-001
  trigger: policy_decision
  summary: worker storm 対策は wake_worker の cap ゲートのみ採用、reap デーモンは塩漬け
  reason: 常駐はコスト過大（owner 決定）
  related_orch: - | related_commit: 08aa69e | owner_pending: no

---

## C. archive_index（30件超過時に退避した digest の薄い索引）

- （まだ archive なし）
