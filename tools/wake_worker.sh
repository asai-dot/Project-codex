#!/usr/bin/env bash
# wake_worker.sh — ワーカー Claude Code を1コマンドで起こすランチャー
#
# 使い方:
#   ./tools/wake_worker.sh                       # 既定: 記事接合(ORCH-ARTICLE-JOIN)を起動
#   ./tools/wake_worker.sh artifacts/periodical/ORCH-HIGHHOLD-INGEST_order_20260624.md
#
# 何をするか:
#   1. リポジトリへ移動し最新を pull
#   2. 指定の発注書(ORCH-*.md)を読んで実行するよう、ワーカーを --bg(バックグラウンド)で起動
#   3. セッションIDを表示
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || { echo "repo not found: $REPO" >&2; exit 1; }
BRANCH="claude/magazine-object-analysis-seg9cr"
# 引数なしなら「今ワーカーに振る発注書」= ORCH-CURRENT.txt の先頭行
ORDER="${1:-}"
[ -z "$ORDER" ] && ORDER="$(grep -vE '^\s*#|^\s*$' artifacts/periodical/ORCH-CURRENT.txt 2>/dev/null | head -1)"
[ -z "$ORDER" ] && { echo "発注書未指定 かつ ORCH-CURRENT.txt が無い/空" >&2; exit 4; }

# 安全: 発注書は artifacts/periodical/ORCH-*.md のみ許可（暴発防止）
case "$ORDER" in
  artifacts/periodical/ORCH-*.md) ;;
  *) echo "拒否: 発注書は artifacts/periodical/ORCH-*.md のみ ($ORDER)" >&2; exit 2;;
esac

echo "[wake_worker] sync $BRANCH (競合安全) ..."
git merge --abort 2>/dev/null; git rebase --abort 2>/dev/null
git fetch origin "$BRANCH" -q 2>/dev/null && git reset -q --hard "origin/$BRANCH" 2>/dev/null || \
  { git pull origin "$BRANCH" --rebase 2>/dev/null || true; }

if [ ! -f "$ORDER" ]; then
  echo "発注書が見つからない: $ORDER" >&2; exit 3
fi

PROMPT="git pull origin ${BRANCH} してから、発注書 ${ORDER} を読んで指示どおり実行し、成果物を commit して push して。発注書に read-only / dry-run / 受入基準 / 出力スキーマ の指定があれば厳守。出力ファイル名は発注書の指定に従い、P##系の番号は使わない。"

echo "[wake_worker] order = $ORDER"

# ★ storm サーキットブレーカー: 起動前に blocked ゾンビを回収し、同時起動数を縛る。
#   生存ワーカーが上限(MAX_LIVE 既定1)に達していたら起動を拒否する。
#   どうしても重ねたい時は MAX_LIVE=2 ./tools/wake_worker.sh ... のように上書き。
if [ -x ./tools/worker_guard.sh ]; then
  if ! ./tools/worker_guard.sh check; then
    echo "[wake_worker] 起動中止(guardが拒否)。既存ワーカーが居ます。" >&2
    exit 5
  fi
fi

echo "[wake_worker] launching worker (--bg, bypassPermissions) ..."
claude --bg --permission-mode bypassPermissions "$PROMPT"
echo "[wake_worker] 起動完了。'claude agents' で確認 / 'claude logs <id>' でログ。"
