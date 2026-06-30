# RATIFY — DD-ORCH-CONTINUITY-001 v0.3（Head↔Owner 決定ログ / 航海日誌）

- decision_id: DD-ORCH-CONTINUITY-001
- ratified_design: `docs/alo/DD-ORCH-CONTINUITY-001_head_owner_log_v0.3_20260630.md`
- source_hash: sha256:6849fd20c374e481181e8fc6e62157e339c9cb551b830ffd71ecebcfc68b3b5f
- gpt_result: `20260630_DD-ORCH-CONTINUITY-001_head_owner_log_v0.3_RESULT.md`（file_id 2318022243805）
- verdict: **DESIGN_PASS_WITH_NOTES**
- ratified_by: owner(asai) 2026-06-30
- audit lineage: v0.1 MODIFY_REQUIRED → v0.2 MODIFY_REQUIRED(祖先バグ) → **v0.3 PASS_WITH_NOTES**

## Binding notes（実装時に必ず遵守・GPT/owner 指定）

1. `REJECT_REQUIRED_STANDING_OMITTED` は **`required_log_commit` 時点**の active な `global_required` set で評価する。
2. worker がより新しい `read_log_commit` を読んでも、`read_digest_id` は dispatch が要求した `required_digest_id` と一致させる。
3. 旧 field 名 alias（`context_log_digest_id` 等）は許さない。正本語彙6つのみ。
4. `REJECT_INLINE_HISTORY` は初期実装では文字数上限・禁止 marker 検出などの保守的 heuristic でよい。
5. `HEAD_OWNER_LOG.md` は**設計判断正本ではなく**、継続性・意図・HOLD・owner pending の蒸留ログに限定する。

## 実装上の訂正（owner 承認 2026-06-30）

- canonical ブランチを DD 記載の `origin/main` → **`origin/claude/magazine-object-analysis-seg9cr`** に訂正。
  理由: head インフラ（CLAUDE.md / wake_worker.sh / HEAD-ORDER-PROTOCOL / AGENT_ORG）が main に無く magazine に集約・main は stale。
  設計ロジック（祖先照合・正本語彙6・enforcement）は不変。将来 infra が main 集約時に canonical を main へ移す。

## GO（owner 2026-06-30）

- v0.3 を design reference として
- `docs/alo/HEAD_OWNER_LOG.md` 最小 seed 作成
- `CLAUDE.md` 着手前チェック追記
- `wake_worker.sh` 生成プロンプト追記
- `HEAD-ORDER-PROTOCOL.md` / worker RESULT schema へ6 field 追加
- ORCH 検収への7 reject code 最小チェック追加
- 初回 backfill は直近7日 または 主要10決定に限定

## HOLD（owner GO なしに進めない）

- production 扱い / 外部公開 / DB・DDL・canonical・MCP
- 既存 HEAD-HAND-HANDOFF の dispatch schema 再設計
- transcript 全量保存 / 常駐デーモン増設
- owner GO なしの canonical 昇格・本番反映
