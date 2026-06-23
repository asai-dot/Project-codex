-- Planted violations for the lawtime v0.2.3 patch gates (P0-2/P0-3/P0-4).
-- Run AFTER lawtime verify_dry_run (clean) to confirm detection power.
INSERT INTO alo_law_work(law_work_id,title) VALUES ('LW_x','test work') ON CONFLICT DO NOTHING;

-- P0-2: as_of_date BEFORE the resolved revision's valid_from -> covers_asof fires
INSERT INTO alo_edges(edge_type,cited_law_work_id,cited_law_id,as_of_basis,as_of_date,
                      resolved_law_revision_id,temporal_status,temporal_caveat,claim_support_eligible)
 VALUES ('cites_statute','LW_minpo','L_minpo','explicit','2000-01-01','REV_cur','current','none',false);

-- P0-3: claim_support_eligible=true but temporal_status NOT IN (current,superseded)
INSERT INTO alo_edges(edge_type,cited_law_work_id,cited_law_id,as_of_basis,as_of_date,
                      resolved_law_revision_id,temporal_status,temporal_caveat,claim_support_eligible)
 VALUES ('cites_statute','LW_minpo','L_minpo','explicit','2021-01-01','REV_cur','repealed','none',true);

-- P0-4: two reviewed/confirmed succession rows, same work, different law_id, overlapping, no lineage bundle
INSERT INTO alo_law_succession_edge(law_work_id,law_id,relation_type,valid_from,valid_to,confidence,lineage_event_id)
 VALUES ('LW_x','L_a','renamed','2010-01-01','2015-01-01','confirmed',NULL),
        ('LW_x','L_b','merged','2012-01-01','2018-01-01','confirmed',NULL);

-- N-1 (audit 2026-06-23): a law_work with NO succession edge but TWO distinct law_id
--   in alo_statutes -> fn_resolve_law_reference_at fallback would be non-deterministic.
INSERT INTO alo_law_work(law_work_id,title) VALUES ('LW_fallback','no-succession work') ON CONFLICT DO NOTHING;
INSERT INTO alo_statutes(law_revision_id,law_work_id,law_id,valid_from,valid_to,revision_status) VALUES
 ('REV_fb_a','LW_fallback','L_fb_old','1990-01-01','2000-01-01','PreviousEnforced'),
 ('REV_fb_b','LW_fallback','L_fb_new','2000-01-01',NULL,'CurrentEnforced');

-- N-2 (audit 2026-06-23): two revisions of the SAME law_id with OVERLAPPING
--   [valid_from, valid_to) -> tier2 ORDER BY ... LIMIT 1 would be non-deterministic.
INSERT INTO alo_law_work(law_work_id,title) VALUES ('LW_overlap','overlapping versions') ON CONFLICT DO NOTHING;
INSERT INTO alo_statutes(law_revision_id,law_work_id,law_id,valid_from,valid_to,revision_status) VALUES
 ('REV_ov_a','LW_overlap','L_ov','2010-01-01','2016-01-01','PreviousEnforced'),
 ('REV_ov_b','LW_overlap','L_ov','2014-01-01','2020-01-01','CurrentEnforced');  -- 2014<2016 => overlap

-- N-3/N-4 (audit 2026-06-23): same law_id with CurrentEnforced AND Repeal coexisting
--   -> v_lawtime_formal_status would hide the anomaly behind 'in_force'.
INSERT INTO alo_law_work(law_work_id,title) VALUES ('LW_badstatus','status anomaly') ON CONFLICT DO NOTHING;
INSERT INTO alo_statutes(law_revision_id,law_work_id,law_id,valid_from,valid_to,revision_status) VALUES
 ('REV_bs_a','LW_badstatus','L_bs','2000-01-01',NULL,'CurrentEnforced'),
 ('REV_bs_b','LW_badstatus','L_bs','1990-01-01','2000-01-01','Repeal');

\echo '--- lawtime gate detection (expect >0 for planted) ---'
SELECT 'gate_resolved_revision_covers_asof' g, count(*) FROM gate_resolved_revision_covers_asof
UNION ALL SELECT 'gate_claim_support_requires_resolved_lawtime', count(*) FROM gate_claim_support_requires_resolved_lawtime
UNION ALL SELECT 'gate_succession_no_ambiguous_overlap', count(*) FROM gate_succession_no_ambiguous_overlap
UNION ALL SELECT 'gate_law_work_single_fallback_law_id', count(*) FROM gate_law_work_single_fallback_law_id
UNION ALL SELECT 'gate_statute_revision_no_ambiguous_overlap', count(*) FROM gate_statute_revision_no_ambiguous_overlap
UNION ALL SELECT 'gate_formal_status_inconsistent_revision_status', count(*) FROM gate_formal_status_inconsistent_revision_status;
