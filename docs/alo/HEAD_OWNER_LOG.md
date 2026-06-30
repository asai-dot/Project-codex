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

- standing_id: HOS-007
  rule: ループは EXIT-A(成功)/B(収穫逓減)/C(完了)/D(緊急停止)で必ず止める。各発注書冒頭にどの EXIT か明示
  applies_to: orchestration loops | enforcement: task_scoped | status: active | last_confirmed: 2026-06-30 | owner_ratified: yes

---

## B. SESSION DIGESTS（新しい順・直近~30件 / 1件5行）

- digest_id: HOL-20260630-003
  trigger: handoff_review
  summary: ORCH検収ゲートを実行スクリプト化（tools/head_owner_log_gate.py）。7 reject code + alias lint を機械判定
  reason: protocol のチェック表を完全自動化（owner GO）。自己検証9ケース全 PASS
  related_orch: DD-ORCH-CONTINUITY-001 v0.3 | related_commit: be6eb2c | owner_pending: no

- digest_id: HOL-20260630-002
  trigger: handoff_review
  summary: head が data limit で停止 → 代理 head が git+監査レーン+claude agents から状態復元（F1 を実演）
  reason: HEAD_OWNER_LOG 未実装だったため手動フォールバックで復旧。本 seed 作成の直接動機
  related_orch: (なし) | related_commit: 80fdc47 | owner_pending: no

- digest_id: HOL-20260630-001
  trigger: handoff_review
  summary: DD-ORCH-CONTINUITY-001 v0.3 が GPT Pro で DESIGN_PASS_WITH_NOTES → owner ratify → 実装GO
  reason: v0.2 の祖先方向バグ＋field統一＋enforcement scope を v0.3 で閉鎖
  related_orch: RATIFY_DD-ORCH-CONTINUITY-001_v0.3_20260630.md | related_commit: 80fdc47 | owner_pending: no

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

- digest_id: HOL-20260628-001
  trigger: policy_decision
  summary: ALO-MODEL-ROUTER v0.1 — 実行権限ルーターを ALO 基底に固定（雑誌スレで先行運用）
  reason: 実行権限を一元化（正本 alo_ai_router/）
  related_orch: ALO-MODEL-ROUTER | related_commit: dde3708 | owner_pending: no

- digest_id: HOL-20260627-003
  trigger: policy_decision
  summary: storm 3度目事故（login即死＋消費push失敗ループ）→ worker_watch にトリガ内容 SHA1 lock 導入
  reason: 同一内容トリガは二度起動しない＝push 失敗でも storm にならない
  related_orch: - | related_commit: 5630fca | owner_pending: no

- digest_id: HOL-20260627-002
  trigger: policy_decision
  summary: 止め時を明文化（EXIT-A 成功 / B 収穫逓減 / C 完了 / D 緊急停止）でループ無限化防止
  reason: 再発注ループが永遠に回る事故の防止（HOS-007 の根拠）
  related_orch: - | related_commit: 8398f5b | owner_pending: no

- digest_id: HOL-20260627-001
  trigger: handoff_review
  summary: ORCH-L4-COVERAGE-LIFT 完了 — orphan 誌接合救済 +1,496 / tsuukan_unavailable 0化
  reason: L4 接合被覆 99.28% → 99.6%+ 引き上げ（受入検査 PASS）
  related_orch: ORCH-L4-COVERAGE-LIFT | related_commit: 7f50299 | owner_pending: no

---

## C. archive_index（30件超過時に退避した digest の薄い索引）

- （まだ archive なし）
