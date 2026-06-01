#!/usr/bin/env bash
#
# mock_claude.sh — a stand-in for `claude` used by selftest_resume.sh.
#
# It mimics the surface the orchestrator depends on: `claude -p "<prompt>" ...`,
# reads the unit from env GAKUYO_UNIT, records that it was invoked (so the test
# can prove already-done units are NOT re-invoked = idempotency), and prints a
# deterministic JSON result on stdout (the contract the orchestrator captures).
#
# Set MOCK_CALLS_LOG to a file path to record one line per real invocation.
# Set MOCK_FAIL_UNITS (space-separated) to make those units exit non-zero.
#
set -euo pipefail

unit="${GAKUYO_UNIT:-unknown}"
[ -n "${MOCK_CALLS_LOG:-}" ] && printf '%s\n' "$unit" >>"$MOCK_CALLS_LOG"

for f in ${MOCK_FAIL_UNITS:-}; do
  if [ "$f" = "$unit" ]; then
    echo "mock_claude: simulated failure for $unit" >&2
    exit 1
  fi
done

# Deterministic, schema-shaped result. Wrapped in a code fence on purpose to
# exercise the orchestrator's fence-stripping path.
cat <<EOF
Here is the reconciliation result:
\`\`\`json
{
  "schema": "alo.gakuyo.result/v1",
  "canonical_headings": [
    { "heading": "mock heading for ${unit}", "level": 1, "page": null, "confidence": "low" }
  ],
  "sources_compared": ["gemini_index", "paddle_index", "json1"],
  "discrepancies": [],
  "reasoning": "deterministic mock output for ${unit}"
}
\`\`\`
EOF
