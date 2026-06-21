-- Minimal STUB of the existing law layer + DD-LAWTIME v0.2.3 R-1 views.
-- Purpose: STRUCTURAL smoke test only (does the lawsubtrans DDL/triggers/views/gates
-- compile and are the 16 gate views queryable). This is NOT the data dry-run:
-- per migrations/lawsubtrans/README.md, an empty/stub local DB pass is a false positive
-- for the data-dependent checks (backfill, formal_status consistency, lawtime_resolved joins).
BEGIN;
CREATE TABLE alo_law_work (
  law_work_id text PRIMARY KEY
);
CREATE TABLE alo_statutes (
  law_revision_id text PRIMARY KEY,
  law_id          text NOT NULL,
  valid_from      date,
  valid_to        date,
  revision_status text   -- CurrentEnforced / PreviousEnforced / Repeal / UnEnforced / ...
);
CREATE TABLE alo_edges (
  edge_id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  edge_type               text,
  cited_law_work_id       text,
  cited_law_id            text,
  as_of_basis             text,
  as_of_date              date,
  resolved_law_revision_id text,
  temporal_status         text,
  temporal_caveat         text
);
-- DD-LAWTIME v0.2.3 R-1 views (the connection point gate 4/9/13 + 005 depend on)
CREATE VIEW v_lawtime_formal_status AS
  SELECT s.law_id,
         CASE
           WHEN bool_or(s.revision_status = 'CurrentEnforced') THEN 'in_force'
           WHEN bool_or(s.revision_status = 'Repeal')          THEN 'repealed'
           WHEN bool_or(s.revision_status = 'PreviousEnforced')THEN 'superseded'
           WHEN bool_or(s.revision_status = 'UnEnforced')      THEN 'not_yet_in_force'
           ELSE 'unknown'
         END AS formal_status,
         max(s.valid_from) FILTER (WHERE s.revision_status='CurrentEnforced') AS current_from
  FROM alo_statutes s
  GROUP BY s.law_id;
CREATE VIEW v_lawtime_resolved_ref AS
  SELECT e.edge_id, e.cited_law_work_id, e.cited_law_id, e.as_of_basis, e.as_of_date,
         e.resolved_law_revision_id, e.temporal_status, e.temporal_caveat,
         (e.resolved_law_revision_id IS NOT NULL
          AND e.temporal_status IS NOT NULL
          AND e.temporal_status <> 'unchecked') AS lawtime_resolved
  FROM alo_edges e
  WHERE e.edge_type IN ('cites_statute','statute_ref','applies_statute');
COMMIT;
