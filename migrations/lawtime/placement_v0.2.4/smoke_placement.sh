#!/usr/bin/env bash
# DD-LAWTIME-001 v0.2.4 (placement / C-option) — LOCAL STRUCTURAL smoke.
# Self-contained: stands up a throwaway Postgres, creates a FIXTURE of the EXISTING
# d1law_taikei.alo_edges (the 母屋 — NOT applied in prod), then the lawtime schema,
# gates, and serving views, and exercises them.
#
# What this verifies (cheap, no live law layer):
#   - all DDL/views compile and apply in order, fully schema-qualified (no search_path)
#   - lawtime owns NO alo_edges; citation temporal lives in the edge_id-keyed side-table
#   - all 8 gate views are queryable and EMPTY on clean seed
#   - each gate has detection power (planted violations are caught)
#   - resolver golden output is stable (audit should_fix #3)
#   - append-only trigger RAISEs; the side-table two-tier CHECK rejects bad rows;
#     the FK to the 母屋 rejects a side-table row for a non-existent edge
#
# What this does NOT verify: real-data backfill over the ACTUAL materialized
#   d1law_taikei.alo_edges. That is the materialize dry-run (HOLD, owner ratify).
#
# Usage: bash smoke_placement.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PGBIN="${PGBIN:-/usr/lib/postgresql/16/bin}"
PORT="${PGPORT:-55433}"
DATA="$(mktemp -d /tmp/pgsmoke244.XXXXXX)"
RUN="$(mktemp -d /tmp/pgrun244.XXXXXX)"
AS=""; [ "$(id -u)" = "0" ] && AS="su postgres -c"
own(){ [ -n "$AS" ] && chown -R postgres:postgres "$@"; }
run(){ if [ -n "$AS" ]; then $AS "$*"; else bash -c "$*"; fi; }
own "$DATA" "$RUN"
trap 'run "$PGBIN/pg_ctl -D $DATA stop -m fast" >/dev/null 2>&1 || true; rm -rf "$DATA" "$RUN"' EXIT

run "$PGBIN/initdb -D $DATA -U postgres --auth=trust" >/dev/null
run "$PGBIN/pg_ctl -D $DATA -o '-p $PORT -k $RUN -c listen_addresses=\"\"' -w start" >/dev/null
PSQL="$PGBIN/psql -h $RUN -p $PORT -U postgres -v ON_ERROR_STOP=1"
chmod 644 "$HERE"/*.sql

echo "== fixture: EXISTING d1law_taikei.alo_edges (母屋, smoke only) =="
run "$PSQL -q -f $HERE/000_external_dependency_d1law_taikei.sql"
echo "== lawtime schema (URI identity, side-table, resolver) =="
run "$PSQL -q -f $HERE/100_lawtime_schema.sql"
echo "== gates (house style) =="
run "$PSQL -q -f $HERE/200_gates.sql"
echo "== serving (exit views + claim_support truth table) =="
run "$PSQL -q -f $HERE/300_serving.sql"
echo "== seed clean deterministic data =="
run "$PSQL -q -f $HERE/seed_clean.sql"

echo "== verify_dry_run (clean => ALL LAWTIME v0.2.4 GATES EMPTY) =="
run "$PSQL -f $HERE/verify_dry_run.sql"

echo "== golden resolver sample (should_fix #3) =="
run "$PSQL -f $HERE/sample_resolver.sql"

echo "== serving sanity: resolved_ref + claim_support_decision =="
run "$PSQL -c 'SELECT edge_id, lawtime_resolved FROM serving.lawtime_resolved_ref_current ORDER BY edge_id;'"
run "$PSQL -c 'SELECT edge_id, resolved, status_ok, caveat_ok, eval_present, lawtime_serve FROM serving.lawtime_claim_support_decision ORDER BY edge_id;'"

echo "== planted-violation detection =="
run "$PSQL -f $HERE/violations.sql"

echo "== guards (each MUST raise an ERROR) =="
guard(){ local out; out="$(run "$PGBIN/psql -h $RUN -p $PORT -U postgres -c \"$2\"" 2>&1 || true)"
  if echo "$out" | grep -qi 'ERROR'; then echo "  OK blocked: $1 -> $(echo "$out" | grep -i ERROR | head -1)";
  else echo "  FAIL not blocked: $1"; FAILED=1; fi; }
FAILED=0
guard "eval append-only UPDATE" "UPDATE lawtime.temporal_eval_event SET method='x' WHERE eval_id=1;"
guard "eval append-only DELETE" "DELETE FROM lawtime.temporal_eval_event WHERE eval_id=1;"
guard "side-table two-tier CHECK (unknown branch w/ as_of_date)" \
  "INSERT INTO d1law_taikei.alo_edges(src_uri,edge_type,dst_uri) VALUES ('alo:doc:jp:g#1','cites_statute','alo:law:jp:minpo'); \
   INSERT INTO lawtime.citation_temporal(edge_id,as_of_basis,as_of_date,temporal_status,claim_support_eligible) \
   VALUES ((SELECT max(edge_id) FROM d1law_taikei.alo_edges),'unknown','2020-01-01','unchecked',false);"
guard "side-table FK to 母屋 (no such edge)" \
  "INSERT INTO lawtime.citation_temporal(edge_id,as_of_basis,as_of_date,temporal_status) VALUES (999999,'explicit','2020-01-01','current');"
guard "law_work URI CHECK" "INSERT INTO lawtime.law_work(work_uri) VALUES ('LW_minpo');"
[ "$FAILED" = "0" ] && echo "== STRUCTURAL SMOKE OK (v0.2.4 placement) ==" || { echo "== STRUCTURAL SMOKE FAILED =="; exit 1; }
