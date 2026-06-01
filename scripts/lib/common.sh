# shellcheck shell=bash
# common.sh — shared helpers for the ALO gakuyo headless reconciliation job.
#
# Sourced by gakuyo_reconcile.sh and the helper scripts. Pure-bash + jq.
# Portable across macOS (Mac Studio target) and Linux (cloud headless):
#   - uses mkdir(1) as a portable mutex (macOS ships no flock(1))
#   - uses temp-file + mv(1) for atomic writes
#
# Design contract (see docs/gakuyo-headless.md):
#   - The ORCHESTRATOR owns persistence. The model only produces JSON on stdout.
#   - Source of truth for "done" = a valid results/<unit>.json on disk.
#   - state.json is a mirror for fast reporting + the last completed position.

set -o pipefail

# ---------------------------------------------------------------------------
# logging
# ---------------------------------------------------------------------------

# LOG_FILE may be empty (stdout only). Always also echoes to stderr so a `claude
# -p` stdout capture upstream is never polluted by our log lines.
log() {
  local ts msg
  ts="$(now_iso)"
  msg="[$ts] $*"
  printf '%s\n' "$msg" >&2
  if [ -n "${LOG_FILE:-}" ]; then
    printf '%s\n' "$msg" >>"$LOG_FILE"
  fi
}

die() {
  log "FATAL: $*"
  exit 1
}

now_iso() {
  # UTC ISO-8601 with seconds. `date -u` is portable across macOS/Linux.
  date -u +%Y-%m-%dT%H:%M:%SZ
}

# ---------------------------------------------------------------------------
# portable mutex (single-runner guarantee)
# ---------------------------------------------------------------------------
# Usage: acquire_lock "$LOCK_DIR"; trap 'release_lock "$LOCK_DIR"' EXIT
LOCK_ACQUIRED=""

acquire_lock() {
  local lockdir="$1"
  local waited=0 max_wait="${LOCK_TIMEOUT:-30}"
  while ! mkdir "$lockdir" 2>/dev/null; do
    if [ "$waited" -ge "$max_wait" ]; then
      die "could not acquire lock $lockdir after ${max_wait}s (another runner active?)"
    fi
    sleep 1
    waited=$((waited + 1))
  done
  LOCK_ACQUIRED="$lockdir"
  printf '%s\n' "$$" >"$lockdir/pid" 2>/dev/null || true
}

release_lock() {
  local lockdir="${1:-$LOCK_ACQUIRED}"
  [ -n "$lockdir" ] && rm -rf "$lockdir" 2>/dev/null || true
  LOCK_ACQUIRED=""
}

# ---------------------------------------------------------------------------
# atomic write: atomic_write <dest-path>   (content read from stdin)
# ---------------------------------------------------------------------------
atomic_write() {
  local dest="$1" tmp
  tmp="$(mktemp "${dest}.XXXXXX")" || die "mktemp failed for $dest"
  cat >"$tmp"
  mv -f "$tmp" "$dest"
}

# is_valid_json <file> -> 0 if file parses as JSON
is_valid_json() {
  jq -e . "$1" >/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# state.json helpers
# ---------------------------------------------------------------------------
# Schema: alo.gakuyo.state/v1
#   { schema, source, created_at, updated_at, units_total,
#     done: [..], failed: [..], last_unit }

state_init() {
  local state="$1" total="$2"
  if [ -f "$state" ] && is_valid_json "$state"; then
    return 0
  fi
  jq -n --arg now "$(now_iso)" --argjson total "$total" '{
    schema: "alo.gakuyo.state/v1",
    source: "gakuyo",
    created_at: $now,
    updated_at: $now,
    units_total: $total,
    done: [],
    failed: [],
    last_unit: null
  }' | atomic_write "$state"
}

# state_set_total <state> <total>
state_set_total() {
  local state="$1" total="$2"
  jq --arg now "$(now_iso)" --argjson total "$total" \
    '.units_total=$total | .updated_at=$now' "$state" | atomic_write "$state"
}

# state_mark_done <state> <unit>  (idempotent; also clears it from failed)
state_mark_done() {
  local state="$1" unit="$2"
  jq --arg now "$(now_iso)" --arg u "$unit" '
    .done = (.done + [$u] | unique) |
    .failed = (.failed - [$u]) |
    .last_unit = $u |
    .updated_at = $now
  ' "$state" | atomic_write "$state"
}

# state_mark_failed <state> <unit>
state_mark_failed() {
  local state="$1" unit="$2"
  jq --arg now "$(now_iso)" --arg u "$unit" '
    .failed = (.failed + [$u] | unique) |
    .updated_at = $now
  ' "$state" | atomic_write "$state"
}

# state_is_done <state> <unit> -> 0 if marked done in state.json
state_is_done() {
  local state="$1" unit="$2"
  jq -e --arg u "$unit" '.done | index($u) != null' "$state" >/dev/null 2>&1
}

# state_reconcile_from_results <state> <results_dir>
# Rebuilds .done from results/*.json actually present & valid on disk. This makes
# the on-disk results the source of truth (handles files dropped/added out of band).
state_reconcile_from_results() {
  local state="$1" results_dir="$2"
  local present=() f unit
  shopt -s nullglob
  for f in "$results_dir"/*.json; do
    if is_valid_json "$f"; then
      unit="$(basename "$f" .json)"
      present+=("$unit")
    fi
  done
  shopt -u nullglob
  local arr
  arr="$(printf '%s\n' "${present[@]:-}" | jq -R . | jq -s 'map(select(length>0))')"
  jq --arg now "$(now_iso)" --argjson present "$arr" '
    .done = ($present | unique) |
    .updated_at = $now
  ' "$state" | atomic_write "$state"
}
