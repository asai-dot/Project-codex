# ACCEPTED: DDJOIN legallibjoin — owner ratify

- gate: **DDJOIN** / topic: legallibjoin / version: **v0.2**
- status: **accepted**（候補 → 受理）
- ratified_by: 浅井（owner）/ 2026-06-10 / 経路: web CC セッション
- 監査: `to_gpt/20260610_legallibjoin_v0.1_DDJOIN_REQUEST.md` (file 2277021246691)
  → GPT `DDJOIN_MODIFY_REQUIRED`（RESULT: `from_gpt/20260610_legallibjoin_v0.1_DDJOIN_RESULT.md`）
  → v0.2 で全指摘を反映 → owner ratify
- PR #5 / branch `claude/legallib-integration-design-Jgrtf`

## 受理した方針（v0.2 = MODIFY_REQUIRED 全対応）

| 論点 | 確定方針 | 実装 |
|---|---|---|
| F2 | **(A) `auto_accept ⇒ 有効ISBN必須` を契約化**。対象なしは `bucket=defer_new`。 | `validate_resolver`: auto_accept+空/不正ISBN を hard error。本体は `blocked_bad_isbn` 多層防御 |
| F3 | **(B) 構造ガード + (A) 上流ラベル是正**。`toc_status=simple` でも depth>1/parent/階層path/page あれば保護。 | `is_structurally_rich()` / `protection_reason()` → `route_human_review`。(C) bencom全保護は不採用 |
| 第3論点 | provenance 付与 + ambiguous は identity review へ | converter `CONVERTER_VERSION` + ノードへ `legallib_book_id`/`converter_version`。dryrun が `resolver_confidence`/`source_sha256`/old・new sha。`identity_review.jsonl` |

検証: 全 **175 checks 緑**、CI 緑（commit `bc52080`）。記録: `docs/dd/20260610_legallibjoin_v0.2_changes.md`。

## accepted の意味と残務（別タスク）
- 接合ポリシー（simple-only + 構造ガード + 誤マージ0 + provenance）は **production 方針として確定**。
- **残 (A) 上流ラベル是正**: 供給側（openbd/bencom 取り込み時の `toc_status` 付与）の修正は別タスク。ゲート側は (B) で安全に倒しているため接合は先行可。
- **本適用前の必須**: F1(ネスト)＋v0.2 後の converter で **全数ドライランを再実行**し `overwrites_bundle` を作り直す（旧 `4a7bea1` は F1 前生成のため nested 欠落）。その後、承認 ISBN を `--only-isbns` で `legallib_join_apply.py --commit`。

## 監査ループ総括（接合系）
- DDPROGRESS（ダッシュボード）: v0.1→v0.2→v0.2.1 → **accepted**。
- DDJOIN（接合ポリシー）: v0.1 MODIFY_REQUIRED → v0.2 → **accepted**（本書）。
