-- Plant deliberate violations and confirm each target gate DETECTS them (>0 rows).
-- Structural detection-power check for the gate algebra.

-- base refs
INSERT INTO alo_law_work(law_work_id) VALUES ('LW_minpo') ON CONFLICT DO NOTHING;
INSERT INTO alo_statutes(law_revision_id, law_id, valid_from, valid_to, revision_status)
  VALUES ('REV_repealed','L_old','2000-01-01','2020-04-01','Repeal') ON CONFLICT DO NOTHING;

-- V1: substantive assertion, no evidence, promoted to 'reviewed' via T6 event.
--     -> gate_substantive_requires_evidence should fire.
INSERT INTO alo_law_substantive_change_assertion
  (law_work_id, article_path, related_delta_id, change_type, asserted_by_source_type, source_tier)
  VALUES ('LW_minpo','art:415', NULL, 'scope_expansion', 'court', 3)
  RETURNING assertion_id \gset v1_
INSERT INTO alo_law_assertion_review_event
  (assertion_kind, assertion_id, new_status, review_basis, decided_by)
  VALUES ('substantive_change', :v1_assertion_id, 'reviewed', 'planted-violation', 'smoke');

-- V2: old_law_survival with empty applicability_scope -> three_axis gate fires.
INSERT INTO alo_old_law_survival_assertion
  (law_work_id, article_path, superseding_revision_id, formal_status, substantive_status,
   applicability_scope, asserted_by_source_type, source_tier)
  VALUES ('LW_minpo','art:415','REV_repealed','in_force','continues',
          '{}', 'scholar', 4)
  RETURNING survival_id \gset v2_
-- V2 also: formal_status='in_force' but lawtime says 'repealed' (REV_repealed)
--   -> gate_formal_status_consistent_with_lawtime + gate_formal_status_mirror_consistent fire.

\echo '--- gate detection (expect >0 for the planted ones) ---'
SELECT 'gate_substantive_requires_evidence' g, count(*) FROM gate_substantive_requires_evidence
UNION ALL SELECT 'gate_old_law_survival_three_axis', count(*) FROM gate_old_law_survival_three_axis
UNION ALL SELECT 'gate_formal_status_consistent_with_lawtime', count(*) FROM gate_formal_status_consistent_with_lawtime
UNION ALL SELECT 'gate_formal_status_mirror_consistent', count(*) FROM gate_formal_status_mirror_consistent
UNION ALL SELECT 'gate_assertion_append_only_enforced(meta,expect 0)', count(*) FROM gate_assertion_append_only_enforced;
