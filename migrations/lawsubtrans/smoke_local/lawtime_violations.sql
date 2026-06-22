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

\echo '--- lawtime gate detection (expect >0 for planted) ---'
SELECT 'gate_resolved_revision_covers_asof' g, count(*) FROM gate_resolved_revision_covers_asof
UNION ALL SELECT 'gate_claim_support_requires_resolved_lawtime', count(*) FROM gate_claim_support_requires_resolved_lawtime
UNION ALL SELECT 'gate_succession_no_ambiguous_overlap', count(*) FROM gate_succession_no_ambiguous_overlap;
