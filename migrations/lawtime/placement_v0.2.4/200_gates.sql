-- DD-LAWTIME-001 v0.2.4 (placement / C-option) — quality gates (house style)
-- ============================================================================
-- Gate naming follows the existing d1law_taikei house style (blocking note #5):
--   v_gate_<domain>_<predicate>_vYYYYMMDD   (cf. d1law_taikei
--   v_gate_d1taxo_pending_l3_excluded_from_claim_support_v20260619).
-- domain = lawtime ; date pin = 20260624 (this placement revision).
-- Each gate is a VIEW that returns OFFENDING ROWS; CI/dry-run asserts 0 rows.
-- All references are EXPLICITLY schema-qualified (no search_path).
-- ----------------------------------------------------------------------------
-- Citation-edge predicate (the lawtime-relevant subset of d1law_taikei.alo_edges).
-- ⚠️ edge_type vocabulary is owned by DDLAWREF, NOT by lawtime. lawtime does NOT
--    invent or expand edge_type. The set below is the v0.2.3 statute-citation
--    predicate, carried forward verbatim; it MUST be reconciled with the DDLAWREF
--    taxonomy before production (blocking note #5 / decision_requested edge_type).
--      => ('cites_statute','statute_ref','applies_statute')
-- ============================================================================

BEGIN;

-- ── INTEGRATION (C-option): every statute-citation edge has exactly one temporal
--    side-table row, and no side-table row is orphaned / points at a non-citation
--    edge. These replace the "own alo_edges" invariants with cross-table ones. ──

-- G-INT-1: citation edge in the 母屋 with NO lawtime temporal side-table row.
CREATE OR REPLACE VIEW lawtime.v_gate_lawtime_citation_edge_missing_side_table_v20260624 AS
  SELECT e.edge_id
  FROM d1law_taikei.alo_edges e
  WHERE e.edge_type IN ('cites_statute','statute_ref','applies_statute')
    AND NOT EXISTS (SELECT 1 FROM lawtime.citation_temporal ct WHERE ct.edge_id = e.edge_id);

-- G-INT-2: side-table row whose edge is missing OR not a statute-citation edge.
CREATE OR REPLACE VIEW lawtime.v_gate_lawtime_side_table_orphan_or_noncitation_v20260624 AS
  SELECT ct.edge_id
  FROM lawtime.citation_temporal ct
  LEFT JOIN d1law_taikei.alo_edges e ON e.edge_id = ct.edge_id
  WHERE e.edge_id IS NULL
     OR e.edge_type NOT IN ('cites_statute','statute_ref','applies_statute');

-- ── P0-2. resolved 版の as_of カバレッジ両端検査（side-table 版）────────────────
CREATE OR REPLACE VIEW lawtime.v_gate_lawtime_resolved_revision_covers_asof_v20260624 AS
  SELECT ct.edge_id
  FROM lawtime.citation_temporal ct
  JOIN lawtime.law_revision r ON r.revision_uri = ct.target_law_revision_uri
  WHERE ct.as_of_basis <> 'unknown' AND ct.as_of_date IS NOT NULL
    AND (
         (r.valid_from IS NOT NULL AND ct.as_of_date <  r.valid_from)   -- 施行前に当てた
      OR (r.valid_to   IS NOT NULL AND ct.as_of_date >= r.valid_to)     -- 失効後に当てた
    );

-- ── P0-3. claim_support 許容を current/superseded + caveat none + eval 在 に絞る ──
CREATE OR REPLACE VIEW lawtime.v_gate_lawtime_claim_support_requires_resolved_v20260624 AS
  SELECT ct.edge_id
  FROM lawtime.citation_temporal ct
  WHERE ct.claim_support_eligible = true
    AND ( ct.target_law_revision_uri IS NULL
       OR ct.temporal_status IS NULL
       OR ct.temporal_status NOT IN ('current','superseded')
       OR ct.temporal_caveat <> 'none'
       OR NOT EXISTS (SELECT 1 FROM lawtime.temporal_eval_event v WHERE v.edge_id = ct.edge_id) );

-- ── P0-4. succession 多重マッチ（曖昧な期間重なり）検出 ──────────────────────────
CREATE OR REPLACE VIEW lawtime.v_gate_lawtime_succession_no_ambiguous_overlap_v20260624 AS
  SELECT a.succession_id AS succession_id_a, b.succession_id AS succession_id_b
  FROM lawtime.law_succession_edge a
  JOIN lawtime.law_succession_edge b
    ON a.work_uri = b.work_uri
   AND a.succession_id < b.succession_id
   AND a.relation_type <> 'unknown' AND b.relation_type <> 'unknown'
   AND a.confidence IN ('reviewed','confirmed')
   AND b.confidence IN ('reviewed','confirmed')
   AND (a.valid_from IS NULL OR b.valid_to IS NULL OR a.valid_from < b.valid_to)
   AND (b.valid_from IS NULL OR a.valid_to IS NULL OR b.valid_from < a.valid_to)
  WHERE a.law_id <> b.law_id
    AND (a.lineage_event_id IS DISTINCT FROM b.lineage_event_id
         OR a.lineage_event_id IS NULL);

-- ── N-1. resolver fallback の非決定性（succession 不在で複数 law_id）─────────────
CREATE OR REPLACE VIEW lawtime.v_gate_lawtime_work_single_fallback_law_id_v20260624 AS
  SELECT r.work_uri
  FROM lawtime.law_revision r
  WHERE NOT EXISTS (
          SELECT 1 FROM lawtime.law_succession_edge se
          WHERE se.work_uri = r.work_uri
            AND se.relation_type <> 'unknown' )
  GROUP BY r.work_uri
  HAVING count(DISTINCT r.law_id) > 1;

-- ── N-2. 同一 law_id の版区間 [valid_from, valid_to) 重なり検出 ───────────────────
CREATE OR REPLACE VIEW lawtime.v_gate_lawtime_statute_revision_no_ambiguous_overlap_v20260624 AS
  SELECT a.revision_uri AS revision_uri_a, b.revision_uri AS revision_uri_b
  FROM lawtime.law_revision a
  JOIN lawtime.law_revision b
    ON a.law_id = b.law_id
   AND a.revision_uri < b.revision_uri
   AND (a.valid_from IS NULL OR b.valid_to IS NULL OR a.valid_from < b.valid_to)
   AND (b.valid_from IS NULL OR a.valid_to IS NULL OR b.valid_from < a.valid_to);

-- ── N-3/N-4. formal status 状態整合（CurrentEnforced 重複 / Repeal 同居）─────────
CREATE OR REPLACE VIEW lawtime.v_gate_lawtime_formal_status_inconsistent_v20260624 AS
  SELECT r.law_id
  FROM lawtime.law_revision r
  GROUP BY r.law_id
  HAVING count(*) FILTER (WHERE r.revision_status = 'CurrentEnforced') > 1
      OR ( bool_or(r.revision_status = 'CurrentEnforced')
       AND bool_or(r.revision_status = 'Repeal') );

COMMIT;
