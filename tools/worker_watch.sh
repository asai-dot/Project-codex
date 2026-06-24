#!/usr/bin/env bash
# worker_watch.sh — Mac側で常駐し、リポジトリのトリガを拾ってワーカーを自動起動する監視役。
#
# これにより Cloud Web(私)も「トリガを commit/push する」だけでワーカーを起こせる。
# （私は Mac のプロセスを直接起動できないため、トリガ経由で間接起動する）
#
# 一回だけ Mac で常駐させる:
#   nohup ./tools/worker_watch.sh > ~/worker_watch.log 2>&1 &
#   （または下記 launchd 登録。停止は kill か launchctl unload）
#
# トリガの形式:
#   ファイル artifacts/periodical/.worker_trigger の1行目に発注書パスを書いて push する。
#   例:  artifacts/periodical/ORCH-ARTICLE-JOIN_order_20260624.md
#   watcher が検出 → wake_worker.sh で起動 → トリガを消費(削除commit)して多重起動を防ぐ。
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || { echo "repo not found: $REPO" >&2; exit 1; }
BRANCH="claude/magazine-object-analysis-seg9cr"
TRIGGER="artifacts/periodical/.worker_trigger"
INTERVAL="${1:-60}"   # 秒

echo "[worker_watch] $TRIGGER を $BRANCH 上で ${INTERVAL}s ごとに監視開始 ($(date))"
while true; do
  git fetch origin "$BRANCH" -q 2>/dev/null || true
  if git cat-file -e "origin/$BRANCH:$TRIGGER" 2>/dev/null; then
    ORDER="$(git show "origin/$BRANCH:$TRIGGER" 2>/dev/null | head -1 | tr -d '[:space:]')"
    echo "[worker_watch] トリガ検出: order=$ORDER ($(date))"
    case "$ORDER" in
      artifacts/periodical/ORCH-*.md)
        git pull origin "$BRANCH" -q --rebase 2>/dev/null || git pull origin "$BRANCH" -q || true
        bash ./tools/wake_worker.sh "$ORDER" || echo "[worker_watch] 起動失敗"
        # トリガ消費（削除して push）— 同じトリガでの多重起動を防ぐ
        git rm -q "$TRIGGER" 2>/dev/null \
          && git commit -q -m "worker_watch: $ORDER 起動につきトリガ消費" \
          && (git push -q origin "$BRANCH" || true)
        ;;
      *)
        echo "[worker_watch] 不正なorder($ORDER) — 無視。トリガは ORCH-*.md のみ許可。"
        ;;
    esac
  fi
  sleep "$INTERVAL"
done
