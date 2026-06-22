# PARKED（別スレ送り）: ワーカー自走化 — dispatcher daemon

- 記録: 2026-06-19 / status: **PARKED（別スレで扱う）**
- 出自: 本スレ（library-data-reanalysis）末尾の議論。501 dry-run が「WOを置いても Mac CC が読みに来ない」で止まった＝**実行系が非自走**という運用課題。

## 課題（1行）
`_claude_dispatch/to_worker/` は push-only キューで、それを能動 pull する常駐プロセスが無い。head/worker とも人起動セッション＝WOは手動起動まで座る。

## 解の方向（別スレで設計する）
- **launchd/cron ポーラ**（or `fswatch`/WatchPaths イベント駆動）が `to_worker/` を監視 → 新規WOを headless `claude -p`(Agent SDK) で実行 → `from_worker/` へ結果 → `done/` へ移動。
- **ガバナンス両立が肝**: WOに `auto_runnable: true|false`。**read-only/dry-run のみ自走**、DDL/backfill/canonical promotion は owner ratify ゲートで自動実行禁止。
- 既存 `DD-CLAUDEHEAD-001` / `_claude_dispatch` 規約への追補として設計。
- 位置づけ: 本スレの「人がボトルネック」論（`docs/2026-06-14_ai_ready_legal_research_methodology.md`）の**実行系への着地**。

## 当面の回避策
Mac CC に WO を**名指しで実行指示**（例: `WO_attrlayer501_dryrun_20260615_1740` / file_id 2286268562080）。

## 関連
- 待機中の実行: 501 attr-layer dry-run（`docs/2026-06-15_attr_layer_501_dryrun_runbook.md` / 戻り後 `docs/2026-06-19_post_501_dryrun_handling_plan_v0.1.md`）。
