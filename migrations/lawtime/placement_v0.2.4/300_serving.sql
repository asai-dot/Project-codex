-- DD-LAWTIME-001 v0.2.4 (placement / C-option) — serving schema (出口 gate)
-- ============================================================================
-- serving = the exit layer that LLM/MCP read (blocking note #7). It exposes the
-- current/accepted/claim_support-judged views, in the SAME house style as the
-- existing d1law_taikei serving layer. These views REPLACE the v0.2.3a R-1 views
-- (lawtime.v_lawtime_formal_status / v_lawtime_resolved_ref) and are the explicit-
-- qualified connection point for DD-LAWSUBTRANS (no search_path).
--
-- DD-LAWSUBTRANS connection contract (replaces unqualified refs):
--   v_lawtime_formal_status  ->  serving.lawtime_formal_status_current
--   v_lawtime_resolved_ref   ->  serving.lawtime_resolved_ref_current
--   (column shapes are kept compatible; cited endpoints are now URIs.)
-- Re-pointing the lawsubtrans gates is a downstream DD-LAWSUBTRANS change, gated
--   on lawtime placement ratify — NOT done in this lawtime-scoped patch.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS serving;

BEGIN;

-- ── formal status single window (column-compatible with v_lawtime_formal_status)─
CREATE OR REPLACE VIEW serving.lawtime_formal_status_current AS
  SELECT r.law_id,
         CASE
           WHEN bool_or(r.revision_status = 'CurrentEnforced') THEN 'in_force'
           WHEN bool_or(r.revision_status = 'Repeal')          THEN 'repealed'
           WHEN bool_or(r.revision_status = 'PreviousEnforced')THEN 'superseded'
           WHEN bool_or(r.revision_status = 'UnEnforced')      THEN 'not_yet_in_force'
           ELSE 'unknown'
         END AS formal_status,
         max(r.valid_from) FILTER (WHERE r.revision_status='CurrentEnforced') AS current_from
  FROM lawtime.law_revision r
  GROUP BY r.law_id;

-- ── resolved citation reference (母屋 edge ⨝ lawtime side-table) ───────────────
--    column-compatible with v_lawtime_resolved_ref; endpoints are URIs now.
CREATE OR REPLACE VIEW serving.lawtime_resolved_ref_current AS
  SELECT e.edge_id,
         e.src_uri  AS citing_uri,
         e.dst_uri  AS cited_law_work_uri,
         ct.as_of_basis,
         ct.as_of_date,
         ct.target_law_revision_uri,
         ct.temporal_status,
         ct.temporal_caveat,
         (ct.target_law_revision_uri IS NOT NULL
          AND ct.temporal_status IS NOT NULL
          AND ct.temporal_status <> 'unchecked') AS lawtime_resolved
  FROM d1law_taikei.alo_edges e
  JOIN lawtime.citation_temporal ct ON ct.edge_id = e.edge_id
  WHERE e.edge_type IN (SELECT edge_type FROM lawtime.citation_edge_type_v20260624);

-- ── integrated claim_support decision — TRUTH TABLE (blocking note #7) ─────────
--    lawtime's CONTRIBUTION to the claim_support decision, exposed as the boolean
--    factors AND their conjunction, so the decision is auditable/diff-able rather
--    than a hidden scalar. Final claim_support is the AND of THIS with:
--      (i)  d1law_taikei pending exclusion
--           (v_gate_d1taxo_pending_l3_excluded_from_claim_support_v20260619 = empty), and
--      (ii) DD-LAWSUBTRANS accepted ∧ ¬disputed ∧ evidence_pointer present.
--    Those two are owned by their layers; this view does not duplicate them.
--
--    lawtime truth table (lawtime_serve = AND of the four factors):
--      resolved | status_ok | caveat_ok | eval_present | lawtime_serve
--      ---------+-----------+-----------+--------------+--------------
--         F     |     *     |     *     |      *        |      F
--         T     |     F     |     *     |      *        |      F
--         T     |     T     |     F     |      *        |      F
--         T     |     T     |     T     |      F        |      F
--         T     |     T     |     T     |      T        |      T
CREATE OR REPLACE VIEW serving.lawtime_claim_support_decision AS
  SELECT ct.edge_id,
         (ct.target_law_revision_uri IS NOT NULL)                 AS resolved,
         (ct.temporal_status IN ('current','superseded'))         AS status_ok,
         (ct.temporal_caveat = 'none')                            AS caveat_ok,
         EXISTS (SELECT 1 FROM lawtime.temporal_eval_event v
                 WHERE v.edge_id = ct.edge_id)                    AS eval_present,
         ( ct.target_law_revision_uri IS NOT NULL
           AND ct.temporal_status IN ('current','superseded')
           AND ct.temporal_caveat = 'none'
           AND EXISTS (SELECT 1 FROM lawtime.temporal_eval_event v
                       WHERE v.edge_id = ct.edge_id) )            AS lawtime_serve
  FROM lawtime.citation_temporal ct;

COMMIT;
