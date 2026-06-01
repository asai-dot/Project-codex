#!/usr/bin/env bash
#
# slice_unit.sh — DEFAULT, granularity-agnostic slicer.
#
# Contract: given the unit id in env GAKUYO_UNIT and the three input files as
# $1 (gemini index) $2 (paddle index) $3 (json1-derived txt), print the
# per-unit text block that will be embedded in the reconciliation prompt.
#
# >>> THE SLICER IS THE GRANULARITY KNOB. <<<
# Whether a "unit" is a page, a heading block, or a 章 is a head-level decision
# (see return-leg of DISPATCH-HEADLESS-MIGRATE-001). That decision is encoded
# HERE, not in the orchestrator. Swap this script (config: SLICER=...) once head
# fixes the granularity, without touching gakuyo_reconcile.sh.
#
# This default implementation supports two conventions out of the box:
#
#  1. MARKER convention (recommended for real runs): each input file delimits
#     units with lines of the form `### <unit-id>`. We print only the block for
#     GAKUYO_UNIT from each source. Robust, explicit, granularity-free.
#
#  2. WHOLE-FILE fallback (smoke test / tiny inputs only): if no marker for the
#     unit is found in a file, that file is passed in full with a warning. Do
#     NOT rely on this for large indexes — it defeats per-unit context scoping.
#
set -euo pipefail

unit="${GAKUYO_UNIT:?GAKUYO_UNIT must be set}"
gemini="${1:?gemini index path required}"
paddle="${2:?paddle index path required}"
json1="${3:?json1 txt path required}"

emit_block() {
  local label="$1" file="$2"
  printf -- '----- BEGIN %s (%s) -----\n' "$label" "$unit"
  if [ ! -f "$file" ]; then
    printf '(missing source file: %s)\n' "$file"
  elif grep -qE "^###[[:space:]]+${unit}([[:space:]]|$)" "$file"; then
    # MARKER convention: print lines from the unit's marker up to the next marker.
    awk -v u="$unit" '
      $0 ~ "^###[[:space:]]+" u "([[:space:]]|$)" { grab=1; next }
      grab && /^###[[:space:]]+/ { grab=0 }
      grab { print }
    ' "$file"
  else
    # WHOLE-FILE fallback.
    printf '(no marker "### %s" found; passing whole file — smoke-test only)\n' "$unit" >&2
    cat "$file"
  fi
  printf -- '----- END %s (%s) -----\n' "$label" "$unit"
}

emit_block "GEMINI INDEX" "$gemini"
emit_block "PADDLE INDEX" "$paddle"
emit_block "JSON1-DERIVED TXT" "$json1"
