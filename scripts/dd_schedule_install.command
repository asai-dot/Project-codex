#!/usr/bin/env bash
# DD snapshot を「毎朝 09:00」に自動更新する macOS スケジュール (launchd) の導入/解除。
#   bash scripts/dd_schedule_install.command             # 09:00 毎日 採取→描画→コミット→push を登録
#   bash scripts/dd_schedule_install.command --no-push   # push せずコミットまで
#   bash scripts/dd_schedule_install.command --uninstall # 解除
#   ALO_BOOKDX_ROOT=/path bash scripts/dd_schedule_install.command  # Box パスを焼き込む
#
# macOS 専用 (launchd)。Box/~/alo-ai を走査するので **Mac で一度だけ**実行する。
# 登録後は Mac が起きていれば毎朝 9 時に走る (寝ていた場合は起床直後に取りこぼし実行)。
set -euo pipefail

LABEL="com.alo.dd-collect"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG="$HOME/Library/Logs/dd_collect.log"

PUSH=1
ACTION=install
for a in "$@"; do
  case "$a" in
    --no-push)            PUSH=0 ;;
    --uninstall|--remove) ACTION=uninstall ;;
    -h|--help)            sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown arg: $a (--no-push / --uninstall / --help)"; exit 2 ;;
  esac
done

[ "$(uname)" = "Darwin" ] || { echo "❌ これは macOS (launchd) 専用です。Mac で実行してください。"; exit 1; }

if [ "$ACTION" = "uninstall" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null \
    || launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "✓ 解除しました: $LABEL"
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
REPO_ROOT="$(git rev-parse --show-toplevel)"
COLLECT="$REPO_ROOT/scripts/dd_collect.command"
chmod +x "$COLLECT" 2>/dev/null || true

mkdir -p "$HOME/Library/LaunchAgents" "$(dirname "$LOG")"

# --push を渡すかどうか。
PUSH_ARG=""
[ "$PUSH" -eq 1 ] && PUSH_ARG=$'\n    <string>--push</string>'

# 導入シェルに root が env で設定されていれば plist に焼き込む (定時ジョブは
# 対話シェルの env を継承しないため)。未設定なら dd_collect 側の自動探索に任せる。
ENV_EXTRA=""
[ -n "${ALO_BOOKDX_ROOT:-}" ] && ENV_EXTRA+=$'\n    <key>ALO_BOOKDX_ROOT</key><string>'"$ALO_BOOKDX_ROOT"'</string>'
[ -n "${ALO_ALO_ROOT:-}" ]    && ENV_EXTRA+=$'\n    <key>ALO_ALO_ROOT</key><string>'"$ALO_ALO_ROOT"'</string>'
[ -n "${ALO_GAKUYO_ROOT:-}" ] && ENV_EXTRA+=$'\n    <key>ALO_GAKUYO_ROOT</key><string>'"$ALO_GAKUYO_ROOT"'</string>'

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$COLLECT</string>$PUSH_ARG
  </array>
  <key>WorkingDirectory</key><string>$REPO_ROOT</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>9</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>$ENV_EXTRA
  </dict>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
PLISTEOF

# 再登録 (既存を外してから load)。
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null \
  || launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"

echo "✓ 登録しました: 毎日 09:00 に DD snapshot を更新 (push=$PUSH)"
echo "  対象     : $COLLECT"
echo "  plist    : $PLIST"
echo "  ログ     : $LOG"
echo "  確認     : launchctl list | grep $LABEL"
echo "  今すぐ試す: launchctl start $LABEL   (→ $LOG を確認)"
echo "  解除     : bash scripts/dd_schedule_install.command --uninstall"
