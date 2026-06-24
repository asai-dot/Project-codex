#!/usr/bin/env bash
# dispatch_local.sh — ハンド「ローカルちゃん」(QEN / Ollama) に1チャンクを渡す
#
# 重要: ローカルちゃんは能力/コンテキストが小さい。タスクはヘッドが**事前に小さく切り分け**、
#       1チャンク=このスクリプト1回呼び出し、で渡す（このスクリプトは分割しない）。
#
# 使い方:
#   ./tools/dispatch_local.sh "プロンプト" [入力ファイル]
#   ./tools/dispatch_local.sh "この100件を分類して" chunk_001.jsonl
set -uo pipefail
PROMPT="${1:?プロンプトを指定}"
INPUT="${2:-}"

# ===== CONFIG（owner が一度設定） =====
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5}"     # QEN の実モデル名に合わせる
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
# =====================================

command -v ollama >/dev/null 2>&1 || { echo "ollama 未検出。Ollama を起動 or PATH 確認。docs/alo/AGENT_ORG_AND_ROUTING.md §4参照" >&2; exit 3; }

if [ -n "$INPUT" ]; then
  [ -f "$INPUT" ] || { echo "入力ファイル無し: $INPUT" >&2; exit 4; }
  echo "[dispatch_local] model=$OLLAMA_MODEL input=$INPUT"
  { printf '%s\n\n----\n' "$PROMPT"; cat "$INPUT"; } | OLLAMA_HOST="$OLLAMA_HOST" ollama run "$OLLAMA_MODEL"
else
  echo "[dispatch_local] model=$OLLAMA_MODEL"
  OLLAMA_HOST="$OLLAMA_HOST" ollama run "$OLLAMA_MODEL" "$PROMPT"
fi
