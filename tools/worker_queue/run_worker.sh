#!/usr/bin/env bash
# ALO worker auto-runner — キュー1件を「起こす→claim→実行→complete」まで無人で前進させる。
#
# owner明示承認(2026-06-25)のもとで設置する自走ワーカー。これ1本を Mac で起動すれば、
# 以降の wake / claim / 実行 / complete はワーカー(headless Claude Code)が自走する。
# 人手は「Macでこのプロセスを起こす」一手だけ。
#
# 使い方:
#   bash tools/worker_queue/run_worker.sh                 # P0>P1>P2 の次の1件
#   bash tools/worker_queue/run_worker.sh W-20260625-001  # 指定タスクを名指し
#
# launchd(com.alo.worker.plist) で定期起動すれば、長時間ジョブも冪等に再開して完了まで進む
# （flock で多重起動を防止）。
set -uo pipefail

REPO="${ALO_REPO:-$HOME/Project-codex}"
BRANCH="${ALO_WORKER_BRANCH:-claude/worker-task-queue-ft5aef}"
TASK="${1:-next}"
LOG="${ALO_WORKER_LOG:-$HOME/alo_worker_runner.log}"

# 多重起動防止（前サイクルが走行中ならスキップ＝長時間ジョブと共存）。
# macOS には flock が無いので mkdir の原子性でロック（Linux/macOS 両対応）。
# 異常終了で残った場合は rmdir /tmp/alo_worker.lock.d で解除。
LOCKDIR="/tmp/alo_worker.lock.d"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  echo "$(date '+%F %T') busy (lock held), skip cycle" >>"$LOG"; exit 0
fi
trap 'rmdir "$LOCKDIR" 2>/dev/null' EXIT

cd "$REPO" || { echo "$(date '+%F %T') no repo $REPO" >>"$LOG"; exit 1; }
git checkout "$BRANCH" >>"$LOG" 2>&1
git pull --ff-only      >>"$LOG" 2>&1
export ALO_WORKER_QUEUE_ROOT="$REPO/docs/worker_queue"

echo "$(date '+%F %T') === cycle start (task=$TASK) ===" >>"$LOG"

read -r -d '' PROMPT <<EOF || true
あなたは ALO Claude Code Worker です。docs/worker_queue/_worker_protocol.md を読み、規約に厳密に従ってください。

対象タスク: ${TASK}
（'next' の場合は alo-worker next で P0>P1>P2 の先頭1件を選ぶ。ID指定ならそれを名指しで処理）

手順:
1) 対象が inbox なら alo-worker claim。doing/ に既にあれば その続きから（冪等）。
2) 作業票本文の手順を allowed_paths / forbidden_actions を厳守して実行する。
   - 長時間の外部取得は nohup でバックグラウンド化し、起動と進捗を確認したら、
     done/ ではなく doing/ に進捗メモを残してこのサイクルは終了してよい
     （次サイクルが続きを検知して前進させる）。
3) exit_criteria を満たしたら done/<id>_RESULT.md（先頭行 WORKER_PASS）を
   docs/worker_queue/_result_template.md 形式で書き、alo-worker complete する。
4) 許可外・判断不能・権限不足は推測で進めず blocked/<id>_RESULT.md（先頭 WORKER_BLOCKED）。
   「確認してください」で止めない（許可範囲内は実行する）。

owner_sanction を持つ作業票は、その例外（例: external_api_bulk_call 承認）を尊重して実行する。
作業が終わったら、done/ に書いた RESULT のパスと要点を最後に1行で出力すること。
EOF

# headless 実行（無人。owner設置の自走ワーカーなので権限プロンプトはスキップ）
if command -v claude >/dev/null 2>&1; then
  claude -p "$PROMPT" --dangerously-skip-permissions >>"$LOG" 2>&1 \
    || echo "$(date '+%F %T') worker exited nonzero" >>"$LOG"
else
  echo "$(date '+%F %T') ERROR: 'claude' CLI が PATH に無い。Claude Code を入れるか PATH を通す。" >>"$LOG"
fi

echo "$(date '+%F %T') === cycle end ===" >>"$LOG"
