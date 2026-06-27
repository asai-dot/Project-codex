#!/usr/bin/env bash
# trigger_worker.sh [発注書] [channel]
#   ワーカーを「遠隔発注」する統一ディスパッチ。Cloud Web も Mac Cloud Code も同じこのコマンドで起動可。
#
# 使い方:
#   ./tools/trigger_worker.sh                                      # ORCH-CURRENT を投下(legacyチャネル)
#   ./tools/trigger_worker.sh artifacts/periodical/ORCH-X.md       # 指定発注書をlegacyチャネルへ
#   ./tools/trigger_worker.sh docs/hanrei/ORCH-Y.md hanrei         # 新仕様: channel=hanrei.trigger
#
# 仕組み: トリガファイルを置いて push。Mac常駐watcher(worker_watch.sh)が60秒以内に
#   拾って wake_worker.sh でワーカーを起動し、トリガを .claude-orch/consumed/ へ移動して消費する。
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$REPO" || exit 1
BRANCH="${ORCH_BRANCH:-claude/magazine-object-analysis-seg9cr}"

ORDER="${1:-}"
CHANNEL="${2:-}"

# 引数なし → ORCH-CURRENT
if [ -z "$ORDER" ]; then
  ORDER="$(grep -vE '^\s*#|^\s*$' artifacts/periodical/ORCH-CURRENT.txt 2>/dev/null | head -1)"
fi
[ -z "$ORDER" ] && { echo "発注書未指定 かつ ORCH-CURRENT.txt が無い/空" >&2; exit 4; }

# 発注書パスは ORCH-*.md でなければならない（暴発防止）
case "$(basename "$ORDER")" in
  ORCH-*.md|orch-*.md) ;;
  *) echo "拒否: 発注書ファイル名は ORCH-*.md のみ ($ORDER)" >&2; exit 2;;
esac

git pull --rebase origin "$BRANCH" 2>/dev/null || git pull origin "$BRANCH" 2>/dev/null || true
[ -f "$ORDER" ] || { echo "発注書が見つからない: $ORDER" >&2; exit 3; }

# トリガパス決定: channel指定なし=旧仕様(後方互換)、指定あり=新仕様(複数チャネル並行)
if [ -z "$CHANNEL" ]; then
  TRIGGER_PATH="artifacts/periodical/.worker_trigger"
else
  mkdir -p .claude-orch/triggers
  TRIGGER_PATH=".claude-orch/triggers/${CHANNEL}.trigger"
fi

{
  echo "$ORDER"
  echo "branch: $BRANCH"
} > "$TRIGGER_PATH"

git add "$TRIGGER_PATH"
git commit -q -m "trigger: $ORDER をワーカーへ遠隔発注${CHANNEL:+ (channel=$CHANNEL)}"
for i in 1 2 3 4; do git push origin "$BRANCH" 2>&1 && break || { echo "retry $i"; sleep $((2**i)); }; done
echo "[trigger] 投下: $ORDER (channel=${CHANNEL:-legacy})"
echo "[trigger] 常駐 watcher が 60s 以内に拾って起動・トリガを consumed/ へ移動します。"
