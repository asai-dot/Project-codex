-- Reference data inserted AFTER lawtime 001_base, BEFORE 010_patch.
-- Includes a "legacy" unknown statute edge (temporal_status NULL) so the patch's
-- P0-1 backfill (NOT VALID -> backfill -> VALIDATE) has something to act on.
INSERT INTO alo_law_work(law_work_id,title) VALUES ('LW_minpo','民法') ON CONFLICT DO NOTHING;
INSERT INTO alo_statutes(law_revision_id,law_work_id,law_id,valid_from,valid_to,revision_status) VALUES
 ('REV_old','LW_minpo','L_minpo','2005-04-01','2020-04-01','PreviousEnforced'),
 ('REV_cur','LW_minpo','L_minpo','2020-04-01',NULL,'CurrentEnforced')
 ON CONFLICT DO NOTHING;
INSERT INTO alo_law_succession_edge(law_work_id,law_id,relation_type,valid_from,valid_to,confidence)
 VALUES ('LW_minpo','L_minpo','continues','2005-04-01',NULL,'confirmed');
-- legacy unknown edge: temporal_status NULL -> backfilled to 'unchecked' by the patch
INSERT INTO alo_edges(edge_type,as_of_basis,as_of_date,resolved_law_revision_id,temporal_status,claim_support_eligible)
 VALUES ('cites_statute','unknown',NULL,NULL,NULL,false);
-- a clean resolved edge (R-1 lawtime_resolved=true), passes the two-tier CHECK
INSERT INTO alo_edges(edge_type,cited_law_work_id,cited_law_id,as_of_basis,as_of_date,
                      resolved_law_revision_id,temporal_status,temporal_caveat,claim_support_eligible)
 VALUES ('cites_statute','LW_minpo','L_minpo','explicit','2021-01-01','REV_cur','current','none',false);
-- an eval-event for that resolved edge (records the version resolution; append-only)
INSERT INTO alo_law_ref_temporal_eval_event(edge_id, resolved_law_revision_id, temporal_status, method, evaluated_by)
 SELECT edge_id, 'REV_cur', 'current', 'smoke', 'seed'
 FROM alo_edges WHERE resolved_law_revision_id='REV_cur' ORDER BY edge_id LIMIT 1;
