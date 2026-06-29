#!/usr/bin/env bash
# worker_guard.sh — storm サーキットブレーカー
#
# 目的:
#   wake_worker.sh が `claude --bg` でワーカーを起こす「直前」に呼び、
#   (1) blocked ゾンビを回収し、(2) 同時起動数の上限を物理的に縛る。
#   SHA1 lock(worker_watch.sh)がすり抜けても、同時に走るワーカーが
#   MAX_LIVE を超えないので storm が原理的に発生しない。
#
# 使い方:
#   ./tools/worker_guard.sh reap                 # blocked ゾンビを stop して回収だけ行う
#   ./tools/worker_guard.sh check                # reap した上で「起動可否」を判定 (可=0 / 不可=1)
#   ./tools/worker_guard.sh status               # 現在の生存セッション数を表示
#
# env:
#   MAX_LIVE        同時に許す「終了していない」ワーカー数 (既定 1=雑誌スレは単一ワーカー)
#   REAP_BLOCKED    1 なら blocked セッションを起動前に stop (既定 1)
set -uo pipefail

MAX_LIVE="${MAX_LIVE:-1}"
REAP_BLOCKED="${REAP_BLOCKED:-1}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# claude agents --json を取得 (TTY 不要)。失敗時は空配列。
_agents_json() {
  claude agents --json 2>/dev/null || echo '[]'
}

# このリポジトリに紐づく「終了していない(=done以外)」セッションを列挙: "<id> <state>"
# id を持ち cwd がこの REPO のものだけを対象にする。
_live_sessions() {
  _agents_json | python3 -c '
import json,sys,os
repo=os.environ.get("REPO","")
try:
    d=json.load(sys.stdin)
except Exception:
    sys.exit(0)
for x in d:
    if not isinstance(x,dict): continue
    sid=x.get("id")
    st=x.get("state")
    if not sid or not st: continue
    if st in ("done",): continue            # 正常終了は対象外
    if repo and x.get("cwd") not in (repo,None): continue
    print(sid, st)
' 2>/dev/null
}

reap() {
  [ "$REAP_BLOCKED" = "1" ] || return 0
  local n=0
  while read -r sid st; do
    [ -z "${sid:-}" ] && continue
    if [ "$st" = "blocked" ]; then
      claude stop "$sid" >/dev/null 2>&1 && n=$((n+1))
    fi
  done < <(REPO="$REPO" _live_sessions)
  [ "$n" -gt 0 ] && echo "[worker_guard] blocked ゾンビ $n 件を回収(stop)しました。" >&2
  return 0
}

count_live() {
  REPO="$REPO" _live_sessions | grep -c . || true
}

case "${1:-check}" in
  reap)
    reap
    ;;
  status)
    echo "[worker_guard] MAX_LIVE=$MAX_LIVE / live=$(count_live)"
    REPO="$REPO" _live_sessions
    ;;
  check)
    # まず blocked を回収してから生存数を数える
    reap
    live="$(count_live)"
    if [ "$live" -ge "$MAX_LIVE" ]; then
      echo "[worker_guard] 起動拒否: 生存ワーカー ${live} 件 ≥ 上限 ${MAX_LIVE}。" >&2
      echo "[worker_guard] 既存を確認 → 不要なら 'claude stop <id>'、強制起動は MAX_LIVE を上げて再実行。" >&2
      REPO="$REPO" _live_sessions >&2
      exit 1
    fi
    exit 0
    ;;
  *)
    echo "usage: worker_guard.sh {reap|check|status}" >&2; exit 2;;
esac
