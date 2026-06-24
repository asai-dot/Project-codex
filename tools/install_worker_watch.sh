#!/usr/bin/env bash
# install_worker_watch.sh — worker_watch を macOS launchd の常駐エージェントとして登録。
# Mac で一度だけ実行: ./tools/install_worker_watch.sh
#   → ログアウト/再起動でも復活、落ちても自動再起動(KeepAlive)。
# 停止/解除: ./tools/install_worker_watch.sh --uninstall
set -uo pipefail

LABEL="com.alo.worker-watch"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$HOME/worker_watch.log"

if [ "${1:-}" = "--uninstall" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "[install] 解除しました: $LABEL"
  exit 0
fi

# claude / git の場所を検出して PATH に焼き込む（launchd は最小環境のため）
CLAUDE_BIN="$(command -v claude || true)"
GIT_BIN="$(command -v git || true)"
[ -z "$CLAUDE_BIN" ] && { echo "claude が PATH に無い。Claude Code をインストール/PATH 設定後に再実行。" >&2; exit 2; }
[ -z "$GIT_BIN" ] && { echo "git が PATH に無い。" >&2; exit 2; }
PATHDIRS="$(dirname "$CLAUDE_BIN"):$(dirname "$GIT_BIN"):/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin"

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${REPO}/tools/worker_watch.sh</string>
    <string>60</string>
  </array>
  <key>WorkingDirectory</key><string>${REPO}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>${PATHDIRS}</string>
    <key>CODEX_CMD</key><string>${CODEX_CMD:-}</string>
    <key>OLLAMA_MODEL</key><string>${OLLAMA_MODEL:-qwen2.5}</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>${LOG}</string>
  <key>StandardErrorPath</key><string>${LOG}</string>
</dict>
</plist>
PLISTEOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
sleep 1
echo "[install] 登録完了: $LABEL"
echo "[install] repo=$REPO  claude=$CLAUDE_BIN"
echo "[install] ログ: tail -f $LOG"
echo "[install] 稼働確認: launchctl list | grep worker-watch"
echo "[install] 解除: ./tools/install_worker_watch.sh --uninstall"
