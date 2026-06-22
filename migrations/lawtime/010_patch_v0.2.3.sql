-- DD-LAWTIME-001 v0.2.3 — production-DDL patch (transcribed from
--   docs/dd/DD-LAWTIME-001_v0.2.3_production_patch.md). status: candidate.
-- Closes v0.2.2 MODIFY_REQUIRED P0-1..P0-4 and adds the R-1 resolved-lawtime views
-- that DD-LAWSUBTRANS-001 connects to. Apply AFTER 001_base_v0.2.2.sql.
-- NOTE: lawtime_resolved=true is NOT by itself claim_support eligibility (R-1 note).

-- ── P0-1. NOT VALID → backfill → (gate empty) → VALIDATE ────────────────────
ALTER TABLE alo_edges ADD CONSTRAINT ck_law_ref_two_tier CHECK (
  edge_type NOT IN ('cites_statute','statute_ref','applies_statute')
  OR ( (as_of_basis <> 'unknown' AND as_of_date IS NOT NULL
          AND (cited_law_id IS NOT NULL OR cited_law_work_id IS NOT NULL))
    OR (as_of_basis = 'unknown' AND as_of_date IS NULL AND resolved_law_revision_id IS NULL
          AND temporal_status = 'unchecked' AND claim_support_eligible = false) )
) NOT VALID;

UPDATE alo_edges
SET temporal_status = 'unchecked'
WHERE edge_type IN ('cites_statute','statute_ref','applies_statute')
  AND as_of_basis = 'unknown'
  AND temporal_status IS NULL;

-- migration-temp 検収 gate（VALIDATE 前に 0 件であること。unknown branch の全条件を検査）
CREATE OR REPLACE VIEW gate_backfill_unknown_unchecked AS
  SELECT edge_id FROM alo_edges
  WHERE edge_type IN ('cites_statute','statute_ref','applies_statute')
    AND as_of_basis = 'unknown'
    AND ( as_of_date IS NOT NULL
       OR resolved_law_revision_id IS NOT NULL
       OR temporal_status IS DISTINCT FROM 'unchecked'
       OR claim_support_eligible IS DISTINCT FROM false );

ALTER TABLE alo_edges VALIDATE CONSTRAINT ck_law_ref_two_tier;

-- ── P0-2. resolved 版の as_of カバレッジ両端検査 ────────────────────────────
CREATE OR REPLACE VIEW gate_resolved_revision_covers_asof AS
  SELECT e.edge_id
  FROM alo_edges e
  JOIN alo_statutes s ON s.law_revision_id = e.resolved_law_revision_id
  WHERE e.as_of_basis <> 'unknown' AND e.as_of_date IS NOT NULL
    AND (
         (s.valid_from IS NOT NULL AND e.as_of_date <  s.valid_from)   -- 施行前に当てた
      OR (s.valid_to   IS NOT NULL AND e.as_of_date >= s.valid_to)     -- 失効後に当てた
    );
-- 旧 gate_no_current_law_for_historical_citation は本 view に統合（alias 名は維持）
CREATE OR REPLACE VIEW gate_no_current_law_for_historical_citation AS
  SELECT edge_id FROM gate_resolved_revision_covers_asof;

-- ── P0-3. claim_support 許容 status を current/superseded に絞り込み ─────────
CREATE OR REPLACE VIEW gate_claim_support_requires_resolved_lawtime AS
  SELECT e.edge_id FROM alo_edges e
  WHERE e.edge_type IN ('cites_statute','statute_ref','applies_statute')
    AND e.claim_support_eligible = true
    AND ( e.resolved_law_revision_id IS NULL
       OR e.temporal_status IS NULL
       OR e.temporal_status NOT IN ('current','superseded')
       OR e.temporal_caveat <> 'none'
       OR NOT EXISTS (SELECT 1 FROM alo_law_ref_temporal_eval_event v
                      WHERE v.edge_id = e.edge_id) );

-- ── P0-4. succession 多重マッチ（曖昧な期間重なり）検出 ──────────────────────
CREATE OR REPLACE VIEW gate_succession_no_ambiguous_overlap AS
  SELECT a.succession_id AS succession_id_a, b.succession_id AS succession_id_b
  FROM alo_law_succession_edge a
  JOIN alo_law_succession_edge b
    ON a.law_work_id = b.law_work_id
   AND a.succession_id < b.succession_id
   AND a.relation_type <> 'unknown' AND b.relation_type <> 'unknown'
   AND a.confidence IN ('reviewed','confirmed')
   AND b.confidence IN ('reviewed','confirmed')
   AND (a.valid_from IS NULL OR b.valid_to IS NULL OR a.valid_from < b.valid_to)
   AND (b.valid_from IS NULL OR a.valid_to IS NULL OR b.valid_from < a.valid_to)
  WHERE a.law_id <> b.law_id
    AND (a.lineage_event_id IS DISTINCT FROM b.lineage_event_id
         OR a.lineage_event_id IS NULL);

-- ── R-1. resolved lawtime views (DD-LAWSUBTRANS connection point) ───────────
CREATE OR REPLACE VIEW v_lawtime_formal_status AS
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

CREATE OR REPLACE VIEW v_lawtime_resolved_ref AS
  SELECT e.edge_id, e.cited_law_work_id, e.cited_law_id, e.as_of_basis, e.as_of_date,
         e.resolved_law_revision_id, e.temporal_status, e.temporal_caveat,
         (e.resolved_law_revision_id IS NOT NULL
          AND e.temporal_status IS NOT NULL
          AND e.temporal_status <> 'unchecked') AS lawtime_resolved
  FROM alo_edges e
  WHERE e.edge_type IN ('cites_statute','statute_ref','applies_statute');
