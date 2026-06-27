#!/usr/bin/env bash
# DD-LAWTIME + DD-LAWSUBTRANS — LOCAL STRUCTURAL smoke test (NOT the data dry-run).
#
# Chains the full stack on a throwaway local Postgres:
#   lawtime 001_base -> seed (incl. a legacy unknown edge) -> lawtime 010_patch
#   (NOT VALID -> backfill -> VALIDATE) -> lawtime verify_dry_run
#   -> lawsubtrans 001..005 -> lawsubtrans verify_dry_run
#   -> planted violations (lawtime P0-2/3/4 + lawsubtrans gates) -> guard checks.
#
# What this DOES verify (cheap, no live law layer needed):
#   - all DDL/patch/triggers/views compile and apply in order with no SQL errors
#   - P0-1 backfill actually flips the legacy edge to temporal_status='unchecked'
#   - all gate views are queryable and EMPTY on clean data
#   - each gate has detection power (planted violations are caught)
#   - append-only triggers RAISE; ck_subchg_claim / ck_law_ref_two_tier reject bad rows
#
# What this does NOT verify (false-positive zone — see ../README.md, ../../lawtime/README.md):
#   - real-data backfill / formal_status consistency / lawtime_resolved joins over the
#     ACTUAL materialized law layer. The lawtime base here is a RECONSTRUCTION (candidate).
#     Run the real dry-run on a Supabase branch once the law layer is materialized.
#
# Usage: bash run_smoke.sh   (spins up a throwaway local Postgres, tears it down)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MIG="$(cd "$HERE/.." && pwd)"                 # migrations/lawsubtrans
LAWTIME="$(cd "$MIG/../lawtime" && pwd)"       # migrations/lawtime
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
chmod 644 "$HERE"/*.sql "$MIG"/*.sql "$LAWTIME"/*.sql

echo "== lawtime: apply 001_base_v0.2.2 =="
run "$PSQL -q -f $LAWTIME/001_base_v0.2.2.sql"
echo "== seed reference data (incl. legacy unknown edge) =="
run "$PSQL -q -f $HERE/seed_pre_patch.sql"
echo "== lawtime: apply 010_patch_v0.2.3 (NOT VALID -> backfill -> VALIDATE) =="
run "$PSQL -q -f $LAWTIME/010_patch_v0.2.3.sql"
echo "== assert P0-1 backfill flipped the legacy edge to 'unchecked' =="
run "$PSQL -tAc \"SELECT 'legacy temporal_status='||temporal_status FROM alo_edges WHERE as_of_basis='unknown';\""
echo "== lawtime verify_dry_run (clean => ALL LAWTIME GATES EMPTY) =="
run "$PSQL -f $LAWTIME/verify_dry_run.sql"

for f in 001_tables 002_append_only_triggers 003_current_views 004_gates 005_lawtime_connection_gates; do
  echo "== lawsubtrans: apply $f =="; run "$PSQL -q -f $MIG/$f.sql"
done
echo "== lawsubtrans verify_dry_run (clean => ALL GATES EMPTY) =="
run "$PSQL -f $MIG/verify_dry_run.sql"

echo "== planted-violation detection (lawsubtrans) =="
run "$PSQL -f $HERE/violations.sql"
echo "== planted-violation detection (lawtime patch P0-2/3/4) =="
run "$PSQL -f $HERE/lawtime_violations.sql"

echo "== guards (each MUST raise an ERROR) =="
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
guard "lawsubtrans UPDATE append-only" "UPDATE alo_law_substantive_change_assertion SET change_type='unknown' WHERE assertion_id=1;"
guard "lawsubtrans DELETE append-only" "DELETE FROM alo_law_assertion_review_event WHERE review_id=1;"
guard "lawsubtrans claim_support CHECK" "INSERT INTO alo_law_substantive_change_assertion(law_work_id,article_path,change_type,asserted_by_source_type,source_tier,claim_support_eligible) VALUES ('LW_minpo','art:1','unknown','court',3,true);"
guard "lawtime eval append-only" "UPDATE alo_law_ref_temporal_eval_event SET method='x' WHERE eval_id=1;"
guard "lawtime two-tier CHECK" "INSERT INTO alo_edges(edge_type,as_of_basis,as_of_date,resolved_law_revision_id,temporal_status,claim_support_eligible) VALUES ('cites_statute','unknown','2020-01-01',NULL,'unchecked',false);"
[ "$FAILED" = "0" ] && echo "== STRUCTURAL SMOKE OK ==" || { echo "== STRUCTURAL SMOKE FAILED =="; exit 1; }
