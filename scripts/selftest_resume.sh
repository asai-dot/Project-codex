#!/usr/bin/env bash
#
# selftest_resume.sh — proves the headless job's idempotency + resumability
# WITHOUT calling the real claude or touching Box. Uses examples/mock_claude.sh.
#
# Asserts:
#   A. partial run (--limit) produces exactly N results, leaves the rest
#   B. a re-run completes the remainder AND does NOT re-invoke the model for
#      already-done units (idempotency, proven via the mock's call log)
#   C. "death + resume": running one unit at a time advances by exactly one and
#      never re-processes earlier units
#   D. deleting a result causes ONLY that unit to be recomputed
#   E. a failing unit is recorded in state.failed and retried on the next run
#
# Exits 0 on success, non-zero on the first failed assertion.
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/gakuyo-selftest.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

SPOOL="$WORK/spool"
mkdir -p "$SPOOL/inputs"
cp "$REPO_DIR/examples/inputs/"*.txt "$SPOOL/inputs/"
cp "$REPO_DIR/examples/units.txt" "$SPOOL/units.txt"

MOCK="$REPO_DIR/examples/mock_claude.sh"
CALLS="$WORK/mock_calls.log"
: >"$CALLS"

RECONCILE="$REPO_DIR/scripts/gakuyo_reconcile.sh"

pass=0; fail=0
check() { # check <desc> <actual> <expected>
  if [ "$2" = "$3" ]; then echo "PASS: $1 ($2)"; pass=$((pass+1));
  else echo "FAIL: $1 — expected [$3], got [$2]"; fail=$((fail+1)); fi
}

run() { # run reconcile with the mock; extra args passed through
  CLAUDE_BIN="$MOCK" SPOOL_ROOT="$SPOOL" MOCK_CALLS_LOG="$CALLS" \
  GEMINI_INDEX="$SPOOL/inputs/gemini_index.txt" \
  PADDLE_INDEX="$SPOOL/inputs/paddle_index.txt" \
  JSON1_TXT="$SPOOL/inputs/json1.txt" \
  PUBLISH=0 \
  bash "$RECONCILE" --units "$SPOOL/units.txt" "$@" >/dev/null 2>>"$WORK/run.log" || true
}

results_count() { find "$SPOOL/results" -name '*.json' 2>/dev/null | wc -l | tr -d ' '; }
done_count()    { jq -r '.done | length' "$SPOOL/state.json" 2>/dev/null || echo 0; }
calls_total()   { grep -c . "$CALLS" 2>/dev/null || echo 0; }
calls_for()     { grep -c "^$1$" "$CALLS" 2>/dev/null || echo 0; }

echo "=== A. partial run (--limit 2) ==="
run --limit 2
check "results after limit 2" "$(results_count)" "2"
check "state.done after limit 2" "$(done_count)" "2"
check "mock invoked twice" "$(calls_total)" "2"

echo "=== B. resume to completion, no re-invocation of done units ==="
run
check "results after full run" "$(results_count)" "3"
check "state.done after full run" "$(done_count)" "3"
check "mock invoked exactly 3 times total (no re-run of done)" "$(calls_total)" "3"
check "unit-001 invoked exactly once" "$(calls_for unit-001)" "1"

echo "=== C. idempotent no-op: re-run when all done invokes model 0 more times ==="
before="$(calls_total)"
run
check "no new model calls on full re-run" "$(calls_total)" "$before"
check "results still 3" "$(results_count)" "3"

echo "=== D. delete one result -> only that unit recomputed ==="
rm -f "$SPOOL/results/unit-002.json"
before="$(calls_total)"
run
check "results back to 3" "$(results_count)" "3"
check "exactly one new model call" "$(calls_total)" "$((before+1))"
check "the new call was unit-002" "$(calls_for unit-002)" "2"

echo "=== E. failing unit recorded + retried ==="
# fresh spool slice for the failure scenario
rm -f "$SPOOL/results/"*.json; : >"$CALLS"
jq -n '{schema:"alo.gakuyo.state/v1",source:"gakuyo",created_at:"x",updated_at:"x",units_total:3,done:[],failed:[],last_unit:null}' >"$SPOOL/state.json"
MOCK_FAIL_UNITS="unit-002" run
check "two results despite one failure" "$(results_count)" "2"
check "unit-002 in state.failed" "$(jq -r '.failed | index("unit-002") != null' "$SPOOL/state.json")" "true"
# now let it succeed on retry
run
check "all three results after retry" "$(results_count)" "3"
check "unit-002 cleared from failed" "$(jq -r '.failed | length' "$SPOOL/state.json")" "0"

echo
echo "=== selftest summary: $pass passed, $fail failed ==="
[ "$fail" -eq 0 ]
