#!/usr/bin/env bash
# worker_watch.sh — Mac側で常駐し、トリガを拾ってワーカーを自動起動する監視役。
#
# 監視対象:
#   - .claude-orch/triggers/*.trigger (新仕様・複数チャネル並行)
#   - artifacts/periodical/.worker_trigger (旧仕様・後方互換)
#
# トリガファイル形式:
#   1行目: 発注書パス (ORCH-*.md で始まる相対パス)
#   2行目以降(任意): `branch: <branch-name>` を書けば指定ブランチに切替えて起動
#                   (デフォルトは現在のブランチ。雑誌は claude/magazine-object-analysis-seg9cr 固定が安全)
#
# 起動成功時: トリガを .claude-orch/consumed/<timestamp>_<元名> に移動して消費。
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || { echo "repo not found: $REPO" >&2; exit 1; }
DEFAULT_BRANCH="${WATCHER_BRANCH:-claude/magazine-object-analysis-seg9cr}"
LEGACY_TRIGGER="artifacts/periodical/.worker_trigger"
TRIGGERS_DIR=".claude-orch/triggers"
CONSUMED_DIR=".claude-orch/consumed"
INTERVAL="${1:-60}"

mkdir -p "$TRIGGERS_DIR" "$CONSUMED_DIR"
echo "[worker_watch] $TRIGGERS_DIR/*.trigger と $LEGACY_TRIGGER を監視 (${INTERVAL}s 周期, $(date))"

LOCKS_DIR="$HOME/.claude-orch-watcher-locks"
mkdir -p "$LOCKS_DIR"

consume_and_run() {
  local trigger_path="$1"   # 作業ツリー上のパス
  local origin_form="$2"    # git管理上のパス
  local content="$(git show "origin/$DEFAULT_BRANCH:$origin_form" 2>/dev/null || cat "$trigger_path" 2>/dev/null)"
  local order="$(echo "$content" | head -1 | tr -d '[:space:]')"
  local branch="$(echo "$content" | grep -i '^branch:' | head -1 | awk -F: '{print $2}' | tr -d '[:space:]')"
  [ -z "$branch" ] && branch="$DEFAULT_BRANCH"

  case "$order" in
    *ORCH-*.md|*orch-*.md) ;;
    *) echo "[worker_watch] 不正なorder($order) — 無視。ORCH-*.md のみ許可。"; return 1;;
  esac

  # ★★ storm再発防止の本丸 ★★
  # トリガ内容のハッシュをローカルlockに記録。同じハッシュは絶対に二度起動しない。
  # 消費push失敗でトリガがoriginに残り続けても、stormにはならない。
  local sig; sig="$(printf '%s' "$content" | shasum -a 1 | awk '{print $1}')"
  local lock_key; lock_key="$(printf '%s' "$origin_form" | tr '/' '_')"
  local lockfile="$LOCKS_DIR/${lock_key}.${sig}"
  if [ -f "$lockfile" ]; then
    return 0   # このトリガ内容では既に起動済み。静かに無視。
  fi

  echo "[worker_watch] トリガ検出: order=$order branch=$branch ($(date))"

  # 競合/未マージ状態を必ず解除し origin に揃えてから処理
  git merge --abort 2>/dev/null; git rebase --abort 2>/dev/null
  git fetch origin "$branch" -q 2>/dev/null || true
  git checkout "$branch" -q 2>/dev/null || true
  git reset -q --hard "origin/$branch" 2>/dev/null || true

  # wake前にlockを取る(wake成功/失敗・push成功/失敗いずれでも二度目を防ぐ)
  date -u +%Y-%m-%dT%H:%M:%SZ > "$lockfile"

  bash ./tools/wake_worker.sh "$order" || { echo "[worker_watch] wake失敗"; return 1; }

  # トリガ消費push。失敗しても lock があるので storm にならない
  local ts; ts="$(date +%Y%m%d-%H%M%S)"
  local fname; fname="$(basename "$origin_form")"
  if git cat-file -e "HEAD:$origin_form" 2>/dev/null; then
    git mv -k "$origin_form" "$CONSUMED_DIR/${ts}_${fname}" 2>/dev/null || git rm -q "$origin_form" 2>/dev/null
    git commit -q -m "worker_watch: $order 起動につきトリガ消費" 2>/dev/null
    git fetch origin "$branch" -q 2>/dev/null
    git rebase "origin/$branch" -q 2>/dev/null || git rebase --abort 2>/dev/null
    git push -q origin "$branch" 2>/dev/null || echo "[worker_watch] 消費push失敗(lockで二度起動防止済)"
  fi
}

while true; do
  # storm 防止: トリガ有無に関わらず毎周期 blocked ゾンビを回収する
  [ -x ./tools/worker_guard.sh ] && ./tools/worker_guard.sh reap 2>/dev/null || true

  git fetch origin "$DEFAULT_BRANCH" -q 2>/dev/null || true

  # 旧仕様トリガ (1ファイルのみ)
  if git cat-file -e "origin/$DEFAULT_BRANCH:$LEGACY_TRIGGER" 2>/dev/null; then
    consume_and_run "$LEGACY_TRIGGER" "$LEGACY_TRIGGER" || true
  fi

  # 新仕様: .claude-orch/triggers/*.trigger を全部拾う
  for t in $(git ls-tree -r --name-only "origin/$DEFAULT_BRANCH" 2>/dev/null | grep -E "^${TRIGGERS_DIR}/[^/]+\.trigger$" || true); do
    consume_and_run "$t" "$t" || true
  done

  sleep "$INTERVAL"
done
