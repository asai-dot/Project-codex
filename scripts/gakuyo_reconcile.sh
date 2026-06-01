#!/usr/bin/env bash
#
# gakuyo_reconcile.sh — resumable, idempotent headless reconciliation of the
# 学陽 (Gakuyo) index across 3 sources (Gemini index / Paddle index / json1-derived txt).
#
# Replaces the "tap '続けて!' from mobile to drive a long batch" workflow with a
# re-runnable headless job. See docs/gakuyo-headless.md for the full design and
# the dispatch ticket DISPATCH-HEADLESS-MIGRATE-001 it implements.
#
# Per-unit flow:
#   1. skip if results/<unit>.json already exists & is valid JSON  (idempotency)
#   2. build a self-contained prompt by SLICING the per-unit input text
#   3. call `claude -p` once for that unit (1-shot; no conversation state)
#   4. capture stdout -> strip fences -> validate JSON -> atomic move into place
#   5. update state.json + (optional) publish to Box canonical
# Kill it anytime; re-run continues from the first unprocessed unit.
#
# Usage:
#   scripts/gakuyo_reconcile.sh [--config FILE] [--units FILE] [--limit N]
#                               [--dry-run] [--only UNIT] [--force]
#
# Key env (overridable; see config/gakuyo.env.example):
#   CLAUDE_BIN   path to claude (default: claude). Override with a mock for tests.
#   SPOOL_ROOT   state/results/logs root (default: ~/.alo_spool/gakuyo)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$SCRIPT_DIR/lib/common.sh"

# ---------------------------------------------------------------------------
# defaults (a config file, if given, is sourced on top of these)
# ---------------------------------------------------------------------------
CONFIG_FILE=""
UNITS_FILE=""
LIMIT=0          # 0 = no limit
DRY_RUN=0
ONLY_UNIT=""
FORCE=0

usage() { sed -n '2,30p' "${BASH_SOURCE[0]}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --config) CONFIG_FILE="$2"; shift 2;;
    --units)  UNITS_FILE="$2"; shift 2;;
    --limit)  LIMIT="$2"; shift 2;;
    --only)   ONLY_UNIT="$2"; shift 2;;
    --dry-run) DRY_RUN=1; shift;;
    --force)  FORCE=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "unknown arg: $1" >&2; usage; exit 2;;
  esac
done

# Load config file (after CLI parse so CLI wins for the few overlapping knobs).
if [ -n "$CONFIG_FILE" ]; then
  [ -f "$CONFIG_FILE" ] || die "config file not found: $CONFIG_FILE"
  # shellcheck disable=SC1090
  . "$CONFIG_FILE"
fi

# ---------------------------------------------------------------------------
# resolved configuration
# ---------------------------------------------------------------------------
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
SPOOL_ROOT="${SPOOL_ROOT:-$HOME/.alo_spool/gakuyo}"
INPUT_DIR="${INPUT_DIR:-$SPOOL_ROOT/inputs}"
RESULTS_DIR="${RESULTS_DIR:-$SPOOL_ROOT/results}"
LOG_DIR="${LOG_DIR:-$SPOOL_ROOT/logs}"
STATE_FILE="${STATE_FILE:-$SPOOL_ROOT/state.json}"
LOCK_DIR="${LOCK_DIR:-$SPOOL_ROOT/.lock}"
UNITS_FILE="${UNITS_FILE:-${UNITS_MANIFEST:-$SPOOL_ROOT/units.txt}}"

GEMINI_INDEX="${GEMINI_INDEX:-$INPUT_DIR/gemini_index.txt}"
PADDLE_INDEX="${PADDLE_INDEX:-$INPUT_DIR/paddle_index.txt}"
JSON1_TXT="${JSON1_TXT:-$INPUT_DIR/json1.txt}"

PROMPT_TEMPLATE="${PROMPT_TEMPLATE:-$SCRIPT_DIR/../config/prompt.gakuyo.tmpl}"
# Slicer: given a UNIT id (env GAKUYO_UNIT) + the 3 input paths as $1 $2 $3,
# prints the per-unit text block. Default slicer = scripts/slice_unit.sh.
SLICER="${SLICER:-$SCRIPT_DIR/slice_unit.sh}"
# Tools the per-unit claude call is allowed to use. Default empty: slices are
# embedded in the prompt so the model needs NO tools (tightest privilege).
ALLOWED_TOOLS="${ALLOWED_TOOLS:-}"
CLAUDE_OUTPUT_FORMAT="${CLAUDE_OUTPUT_FORMAT:-text}"
CLAUDE_EXTRA_ARGS="${CLAUDE_EXTRA_ARGS:-}"

# Box canonical publish: handled by scripts/publish_box.sh (drive | mcp-bridge | none)
PUBLISH="${PUBLISH:-1}"
PUBLISH_SCRIPT="${PUBLISH_SCRIPT:-$SCRIPT_DIR/publish_box.sh}"

mkdir -p "$INPUT_DIR" "$RESULTS_DIR" "$LOG_DIR"
LOG_FILE="$LOG_DIR/run-$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
export LOG_FILE

# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------
command -v jq >/dev/null 2>&1 || die "jq is required but not found on PATH"
[ -f "$UNITS_FILE" ] || die "units manifest not found: $UNITS_FILE (one unit id per line)"
[ -x "$SLICER" ] || die "slicer not found/executable: $SLICER"
[ -f "$PROMPT_TEMPLATE" ] || die "prompt template not found: $PROMPT_TEMPLATE"

# Read manifest: strip comments (#...) and blank lines.
mapfile -t ALL_UNITS < <(grep -vE '^\s*(#|$)' "$UNITS_FILE" | sed -E 's/[[:space:]]+$//')
[ "${#ALL_UNITS[@]}" -gt 0 ] || die "units manifest is empty: $UNITS_FILE"

log "=== gakuyo_reconcile start ==="
log "spool=$SPOOL_ROOT  units=${#ALL_UNITS[@]}  claude=$CLAUDE_BIN  dry_run=$DRY_RUN  limit=$LIMIT"
log "inputs: gemini=$GEMINI_INDEX paddle=$PADDLE_INDEX json1=$JSON1_TXT"

acquire_lock "$LOCK_DIR"
trap 'release_lock "$LOCK_DIR"' EXIT INT TERM

state_init "$STATE_FILE" "${#ALL_UNITS[@]}"
state_set_total "$STATE_FILE" "${#ALL_UNITS[@]}"
# Make on-disk results the source of truth for "done" before we start.
state_reconcile_from_results "$STATE_FILE" "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# process one unit
# ---------------------------------------------------------------------------
process_unit() {
  local unit="$1"
  local out="$RESULTS_DIR/$unit.json"

  if [ "$FORCE" -ne 1 ] && [ -f "$out" ] && is_valid_json "$out"; then
    log "SKIP  $unit (results exists & valid)"
    state_mark_done "$STATE_FILE" "$unit"
    return 0
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    log "DRY   $unit (would process)"
    return 0
  fi

  # 1. slice per-unit input text (the slicer encodes granularity — head's call)
  local slice
  if ! slice="$(GAKUYO_UNIT="$unit" "$SLICER" "$GEMINI_INDEX" "$PADDLE_INDEX" "$JSON1_TXT" 2>>"$LOG_FILE")"; then
    log "FAIL  $unit (slicer error)"
    state_mark_failed "$STATE_FILE" "$unit"
    return 1
  fi

  # 2. build prompt from template
  local prompt
  prompt="$(build_prompt "$unit" "$slice")"

  # 3. run claude (1-shot). Capture stdout; our log goes to stderr/LOG_FILE so
  #    stdout stays clean for JSON capture.
  local raw rc
  set +e
  # shellcheck disable=SC2086
  raw="$(GAKUYO_UNIT="$unit" "$CLAUDE_BIN" -p "$prompt" \
            --output-format "$CLAUDE_OUTPUT_FORMAT" \
            ${ALLOWED_TOOLS:+--allowedTools "$ALLOWED_TOOLS"} \
            $CLAUDE_EXTRA_ARGS 2>>"$LOG_FILE")"
  rc=$?
  set -e
  if [ $rc -ne 0 ]; then
    log "FAIL  $unit (claude exit $rc)"
    state_mark_failed "$STATE_FILE" "$unit"
    return 1
  fi

  # 4. extract JSON (strip ```json fences if the model added them) + validate
  local json
  json="$(extract_json <<<"$raw")"
  if ! jq -e . >/dev/null 2>&1 <<<"$json"; then
    log "FAIL  $unit (output not valid JSON; saved raw -> $out.reject)"
    printf '%s' "$raw" >"$out.reject"
    state_mark_failed "$STATE_FILE" "$unit"
    return 1
  fi

  # Stamp orchestrator-owned metadata, then atomic move into place.
  jq --arg u "$unit" --arg now "$(now_iso)" \
     '. + {unit: $u, generated_at: $now, source: "gakuyo"}' <<<"$json" \
     | atomic_write "$out"

  state_mark_done "$STATE_FILE" "$unit"
  log "DONE  $unit -> $out"

  # 5. publish to Box canonical (best-effort; never fails the unit)
  if [ "$PUBLISH" -eq 1 ] && [ -x "$PUBLISH_SCRIPT" ]; then
    if "$PUBLISH_SCRIPT" "$out" >>"$LOG_FILE" 2>&1; then
      log "PUB   $unit -> Box canonical"
    else
      log "WARN  $unit publish skipped/failed (see log; canonical may be unconfigured)"
    fi
  fi
  return 0
}

build_prompt() {
  local unit="$1" slice="$2"
  # Literal {{UNIT}}/{{SLICE}} substitution; slice content is inserted verbatim
  # (special chars safe) because it travels via the environment, not the args.
  UNIT="$unit" SLICE="$slice" python3 - "$PROMPT_TEMPLATE" <<'PY'
import os, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    tmpl = fh.read()
tmpl = tmpl.replace("{{SLICE}}", os.environ.get("SLICE", ""))
tmpl = tmpl.replace("{{UNIT}}", os.environ.get("UNIT", ""))
sys.stdout.write(tmpl)
PY
}

# extract_json: pull the first {...} or [...] JSON block from stdin, stripping
# markdown code fences if present. Tolerant of leading/trailing prose.
# NOTE: uses `python3 -c` (not a heredoc) so stdin stays free for the piped data.
extract_json() {
  python3 -c '
import sys, re
s = sys.stdin.read()
m = re.search(r"```(?:json)?\s*(.*?)```", s, re.S)
if m:
    s = m.group(1)
s = s.strip()
start = min([i for i in (s.find("{"), s.find("[")) if i != -1], default=-1)
if start > 0:
    s = s[start:]
sys.stdout.write(s)
'
}

# ---------------------------------------------------------------------------
# main loop
# ---------------------------------------------------------------------------
processed=0
fail=0
for unit in "${ALL_UNITS[@]}"; do
  [ -n "$unit" ] || continue
  if [ -n "$ONLY_UNIT" ] && [ "$unit" != "$ONLY_UNIT" ]; then
    continue
  fi
  if [ "$LIMIT" -gt 0 ] && [ "$processed" -ge "$LIMIT" ]; then
    log "LIMIT reached ($LIMIT); stopping."
    break
  fi
  if process_unit "$unit"; then :; else fail=$((fail+1)); fi
  processed=$((processed+1))
done

# Final summary
done_count="$(jq -r '.done | length' "$STATE_FILE")"
failed_count="$(jq -r '.failed | length' "$STATE_FILE")"
log "=== summary: total=${#ALL_UNITS[@]} done=$done_count failed=$failed_count (this run: processed=$processed fail=$fail) ==="
log "state: $STATE_FILE"
log "log:   $LOG_FILE"

# Exit non-zero if anything failed this run, so launchd/cron can alert.
[ "$fail" -eq 0 ]
