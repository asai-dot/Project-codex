#!/usr/bin/env bash
# wake_codex.sh — ハンド「コーデックス」に仕事を振るランチャー
# 使い方: ./tools/wake_codex.sh artifacts/periodical/ORCH-XXXX_order.md
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$REPO" || exit 1
BRANCH="claude/magazine-object-analysis-seg9cr"
ORDER="${1:?発注書パスを指定 (artifacts/periodical/ORCH-*.md)}"

# ===== CONFIG（owner が一度設定） =====
# Codex の実行コマンド。例: codex exec / openai codex 等。未設定ならエラーで停止。
CODEX_CMD="${CODEX_CMD:-}"
# =====================================

case "$ORDER" in artifacts/periodical/ORCH-*.md) ;; *) echo "拒否: ORCH-*.md のみ" >&2; exit 2;; esac
[ -z "$CODEX_CMD" ] && { echo "未設定: 環境変数 CODEX_CMD にCodex起動コマンドを入れて下さい(例: export CODEX_CMD='codex exec'). docs/alo/AGENT_ORG_AND_ROUTING.md §4参照" >&2; exit 3; }

git pull origin "$BRANCH" --rebase 2>/dev/null || git pull origin "$BRANCH" || true
PROMPT="git pull origin ${BRANCH} してから発注書 ${ORDER} を読んで指示どおり実行し、成果物を commit して push。受入基準/出力スキーマ/read-only指定を厳守。"
echo "[wake_codex] $CODEX_CMD で起動: $ORDER"
exec $CODEX_CMD "$PROMPT"
