---
worker_task_id: W-20260627-510
status: hold
priority: P0
owner: claude-code-worker
created_at: 2026-06-27
release_when: §9 STOP gate のいずれか(SUCCESS_STOP / DIMINISHING / HOLD_BOUNDARY / BLOCKED / EMERGENCY)が発火し head が release した時点
depends_on:
  - W-20260626-501
  - W-20260626-502
  - W-20260627-503
  - W-20260627-504
  - W-20260627-505
request: docs/HEAD_OPS_CASELINK_SILVER_LOOP_20260627.md (§10)
goal: シルバー精度向上ループ閉幕後の「ループ自体」を GPT Pro メタ監査に投函するための self-contained packet を作成し to_gpt/ へ。head/worker 交互作用の質と次ループの改善方向を引き出す
mode: implementation
allowed_paths:
  - artifacts/caselink/
  - to_gpt/
  - _claude_dispatch/from_worker/
  - docs/_loop_retrospectives/
allowed_actions:
  - read_files(全 W-NNN RESULT / _loop_health.json / done|blocked|inbox)
  - spawn_subagent (タスク台帳の chunked 集計)
  - write(LOOP_RETROSPECTIVE.md + meta_audit_packet)
forbidden_actions:
  - production_db_write
  - salesforce_write
  - box_write_move_rename_delete
  - raw_source_mutation
  - alo_edges_write
  - canonical_promotion
  - claim_support_eligibility
  - reviewed_true_backfill
  - pii_in_general_artifact
  - human_gate_bypass
  - fill_unknown_with_generalities
  - stall_whole_run_waiting_for_input
exit_criteria:
  - artifacts/caselink/_LOOP_RETROSPECTIVE_<stop_kind>_<date>.md(§10.1 の7項目を網羅)
  - to_gpt/20260NNN_loopmeta_caselink_silver_REQUEST.md(self-contained・本文同梱・5論点)
  - docs/_loop_retrospectives/<date>_RETROSPECTIVE.md(蓄積版)
  - RESULT を done/ に書く
deliverables:
  - artifacts/caselink/_LOOP_RETROSPECTIVE_<stop_kind>_<date>.md
  - to_gpt/20260NNN_loopmeta_caselink_silver_REQUEST.md
  - docs/_loop_retrospectives/<date>_RETROSPECTIVE.md
  - _claude_dispatch/from_worker/20260NNN_loop_meta_audit_packet_RESULT.md
max_attempts: 2
result_expected_filename: W-20260627-510_RESULT.md
---

# Task — ループ閉幕後のメタ監査 packet 作成(GPT へ「ループの回し方」を見てもらう)

§9 のどれで止まっても、最後の作業として **ループ自体** を GPT Pro に監査依頼する。これにより head/worker 交互作用の質と次ループ(別ドメイン or 同ドメイン再開)の改善方向が確定する。

## 手順
1. **STOP 判定確認**: head が release したことを確認(release_when 条件)。`_loop_health.json` の最終値・STOP 種別を取得。
2. **タスク台帳集計**(subagent 並列可): W-501〜510 を全件読み:
   - RESULT label(PASS/NOTES/MODIFY/BLOCKED/FAIL)
   - 所要 cycle / 検収判定 / subagent 使用回数 / 主要メトリクス
   - hold→queue 遷移時刻と理由(head の判断ログ)
3. **詰まり履歴**: BLOCKED の cause→recover→結末 を時系列に。
4. **規律違反候補**: forbidden_actions の境界踏み込みがあったか(false alarm 含む)を集計。
5. **健全性メトリクス全推移**: `_loop_health.json` を cycle ごと縦並びに。
6. **head 自己評価セクション**: 検収の厳しさ・hold 解放の早さ・設計改変頻度の自己採点(私が後で追記する欄を空けて出す)。
7. **RETROSPECTIVE.md** をまとめ、自走runner が読める形式で commit。さらに `docs/_loop_retrospectives/` にも複製(蓄積)。
8. **GPT 監査 REQUEST packet**(`to_gpt/`)を §10.2 の 5 論点で起票:
   - 入力同梱(本文 inline・前回 NEED_MORE の教訓)
   - 求めるラベル `LOOPMETA_<PASS|PASS_WITH_NOTES|MODIFY_REQUIRED|REJECT|NEED_MORE>`
   - 結果は `from_gpt/` に戻る → 次ループの HEAD_OPS v0.2 で反映

## RETROSPECTIVE.md の必須節(§10.1 準拠)
1. STOP 種別と判定根拠
2. タスク台帳(全 W-NNN)
3. hold→queue 遷移ログ
4. 詰まり履歴(BLOCKED 系列)
5. 規律違反候補
6. 健全性メトリクス全推移
7. head 自己評価(空欄でOK・head が後追記)

## GPT REQUEST packet の必須節(§10.2 準拠)
- (a) 検収基準の適否
- (b) hold→queue 遷移
- (c) サブエージェント許可範囲
- (d) STOP gate 閾値
- (e) head/worker 役割分担
- + free response 欄

## HEAD OPS 準拠
本タスクは `docs/HEAD_OPS_CASELINK_SILVER_LOOP_20260627.md` の規律に従う(サブエージェント許可・self-check・STOP gate・RESULT 構造・MERTRICS_JSON)。

## 完了後
1. head が GPT 戻りを受領 → notes を HEAD_OPS v0.2 に反映。
2. 3回ループ後に共通改善パターンを抽出 → HEAD_OPS v1.0(汎化版) を起こす(雑誌オブジェクトでも使える形)。
3. これが「ループの回し方」自体の学習ループ(メタループ)。
