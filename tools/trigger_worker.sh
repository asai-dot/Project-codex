#!/usr/bin/env bash
# trigger_worker.sh <発注書 artifacts/periodical/ORCH-*.md>
#   ワーカーを「遠隔発注」する統一ディスパッチ。
#   トリガファイルを置いて push するだけ。常駐 watcher(worker_watch.sh) が 60s 以内に拾って
#   wake_worker.sh でワーカーを起動し、トリガを消費する。
#
#   Cloud Web も Mac Cloud Code も**同じこのコマンド**でワーカーを起こせる:
#     ./tools/trigger_worker.sh artifacts/periodical/ORCH-HIGHHOLD-INGEST_order_20260624.md
#
#   （Mac で直接・即時に起こしたいだけなら ./tools/wake_worker.sh <発注書> でもよい。
#    trigger 経由は「watcher が動いている環境にいる別ワーカーへ投げる」統一手段。）
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$REPO" || exit 1
BRANCH="claude/magazine-object-analysis-seg9cr"
ORDER="${1:?発注書パスを指定 (artifacts/periodical/ORCH-*.md)}"

case "$ORDER" in artifacts/periodical/ORCH-*.md) ;; *) echo "拒否: ORCH-*.md のみ ($ORDER)" >&2; exit 2;; esac

git pull --rebase origin "$BRANCH" 2>/dev/null || git pull origin "$BRANCH" 2>/dev/null || true
[ -f "$ORDER" ] || { echo "発注書が見つからない: $ORDER" >&2; exit 3; }

echo "$ORDER" > artifacts/periodical/.worker_trigger
git add artifacts/periodical/.worker_trigger
git commit -q -m "trigger: $ORDER をワーカーへ遠隔発注"
for i in 1 2 3 4; do git push origin "$BRANCH" 2>&1 && break || { echo "retry $i"; sleep $((2**i)); }; done
echo "[trigger] 投下: $ORDER"
echo "[trigger] 常駐 watcher が 60s 以内に拾って起動し、トリガを消費(コミット)します。"
