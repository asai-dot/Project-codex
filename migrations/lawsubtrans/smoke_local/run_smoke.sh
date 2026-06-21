#!/usr/bin/env bash
# DD-LAWSUBTRANS-001 — LOCAL STRUCTURAL smoke test (NOT the data dry-run).
#
# What this DOES verify (cheap, no live law layer needed):
#   - 001..005 + stub R-1 views apply cleanly, in order, with no SQL errors
#   - all 16 gate views are queryable (verify_dry_run.sql => ALL GATES EMPTY on no data)
#   - each gate has detection power (planted violations are caught)
#   - append-only triggers RAISE on UPDATE/DELETE; ck_subchg_claim rejects claim_support w/o evidence
#
# What this does NOT verify (false-positive zone — see ../README.md):
#   - backfill / formal_status consistency / lawtime_resolved joins over REAL rows.
#     Those require the materialized law layer (alo_law_work/alo_statutes/alo_edges) +
#     DD-LAWTIME v0.2.2/v0.2.3. Run the real dry-run on a Supabase branch per ../README.md.
#
# Usage: bash run_smoke.sh   (spins up a throwaway local Postgres, tears it down)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MIG="$(cd "$HERE/.." && pwd)"
PGBIN="${PGBIN:-/usr/lib/postgresql/16/bin}"
PORT="${PGPORT:-55432}"
DATA="$(mktemp -d /tmp/pgsmoke.XXXXXX)"
RUN="$(mktemp -d /tmp/pgrun.XXXXXX)"
# Postgres refuses to run as root; drop to the postgres system user if we are root.
AS=""; [ "$(id -u)" = "0" ] && AS="su postgres -c"
own(){ [ -n "$AS" ] && chown -R postgres:postgres "$@"; }
run(){ if [ -n "$AS" ]; then $AS "$*"; else bash -c "$*"; fi; }
own "$DATA" "$RUN"
trap 'run "$PGBIN/pg_ctl -D $DATA stop -m fast" >/dev/null 2>&1 || true; rm -rf "$DATA" "$RUN"' EXIT

run "$PGBIN/initdb -D $DATA -U postgres --auth=trust" >/dev/null
run "$PGBIN/pg_ctl -D $DATA -o '-p $PORT -k $RUN -c listen_addresses=\"\"' -w start" >/dev/null
PSQL="$PGBIN/psql -h $RUN -p $PORT -U postgres -v ON_ERROR_STOP=1"
chmod 644 "$HERE"/*.sql "$MIG"/*.sql

echo "== apply stub law layer + R-1 views =="
run "$PSQL -q -f $HERE/stub_lawlayer.sql"
for f in 001_tables 002_append_only_triggers 003_current_views 004_gates 005_lawtime_connection_gates; do
  echo "== apply $f =="; run "$PSQL -q -f $MIG/$f.sql"
done
echo "== verify_dry_run (no data => ALL GATES EMPTY) =="
run "$PSQL -f $MIG/verify_dry_run.sql"
echo "== planted-violation detection =="
run "$PSQL -f $HERE/violations.sql"
echo "== append-only + CHECK guards (each MUST raise an ERROR) =="
# psql exits non-zero on the intentional errors; capture output and assert it contains ERROR.
guard(){ # $1=label  $2=sql
  local out; out="$(run "$PGBIN/psql -h $RUN -p $PORT -U postgres -c \"$2\"" 2>&1 || true)"
  if echo "$out" | grep -qi 'ERROR'; then
    echo "  OK blocked: $1 -> $(echo "$out" | grep -i ERROR | head -1)"
  else
    echo "  FAIL not blocked: $1"; FAILED=1
  fi
}
FAILED=0
guard "UPDATE append-only" "UPDATE alo_law_substantive_change_assertion SET change_type='unknown' WHERE assertion_id=1;"
guard "DELETE append-only" "DELETE FROM alo_law_assertion_review_event WHERE review_id=1;"
guard "claim_support CHECK" "INSERT INTO alo_law_substantive_change_assertion(law_work_id,article_path,change_type,asserted_by_source_type,source_tier,claim_support_eligible) VALUES ('LW_minpo','art:1','unknown','court',3,true);"
[ "$FAILED" = "0" ] && echo "== STRUCTURAL SMOKE OK ==" || { echo "== STRUCTURAL SMOKE FAILED =="; exit 1; }
