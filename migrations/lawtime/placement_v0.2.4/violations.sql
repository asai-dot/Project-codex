-- DD-LAWTIME-001 v0.2.4 — planted violations to confirm gate detection power.
-- Run AFTER verify_dry_run (clean => all empty). Each block trips exactly one gate.
BEGIN;

-- work + revisions used by several planted cases
INSERT INTO lawtime.law_work(work_uri,title) VALUES
 ('alo:law:jp:planted','planted work')
ON CONFLICT DO NOTHING;

-- G-INT-2 / P0-2 / P0-3 need a real citation edge to attach a bad side-table row.
-- Insert one citation edge and one NON-citation edge in the 母屋.
WITH e_cit AS (
  INSERT INTO d1law_taikei.alo_edges(src_uri,edge_type,dst_uri,source_system)
  VALUES ('alo:doc:jp:bad#p1','cites_statute','alo:law:jp:planted','smoke')
  RETURNING edge_id
), e_non AS (
  INSERT INTO d1law_taikei.alo_edges(src_uri,edge_type,dst_uri,source_system)
  VALUES ('alo:doc:jp:bad#p2','classified_under','alo:term:jp:foo','smoke')
  RETURNING edge_id
)
-- G-INT-1 fires because e_cit (a citation edge) gets NO side-table row below.
-- G-INT-2 fires because we attach a side-table row to e_non (a NON-citation edge).
INSERT INTO lawtime.citation_temporal(edge_id,as_of_basis,as_of_date,target_law_revision_uri,
                                      temporal_status,temporal_caveat,claim_support_eligible,resolution_method)
SELECT edge_id,'explicit','2021-01-01',NULL,'current','none',false,'planted' FROM e_non;

-- P0-2: as_of BEFORE the resolved revision's valid_from.
INSERT INTO lawtime.law_revision(revision_uri,work_uri,law_id,valid_from,valid_to,revision_status) VALUES
 ('alo:lawrev:jp:planted:2010','alo:law:jp:planted','planted','2010-01-01',NULL,'CurrentEnforced')
ON CONFLICT DO NOTHING;
WITH e AS (
  INSERT INTO d1law_taikei.alo_edges(src_uri,edge_type,dst_uri,source_system)
  VALUES ('alo:doc:jp:bad#p3','cites_statute','alo:law:jp:planted','smoke')
  RETURNING edge_id
)
INSERT INTO lawtime.citation_temporal(edge_id,as_of_basis,as_of_date,target_law_revision_uri,
                                      temporal_status,temporal_caveat,claim_support_eligible,resolution_method)
SELECT edge_id,'explicit','2000-01-01','alo:lawrev:jp:planted:2010','current','none',false,'planted' FROM e;

-- P0-3: claim_support_eligible=true but temporal_status NOT IN (current,superseded).
WITH e AS (
  INSERT INTO d1law_taikei.alo_edges(src_uri,edge_type,dst_uri,source_system)
  VALUES ('alo:doc:jp:bad#p4','cites_statute','alo:law:jp:planted','smoke')
  RETURNING edge_id
)
INSERT INTO lawtime.citation_temporal(edge_id,as_of_basis,as_of_date,target_law_revision_uri,
                                      temporal_status,temporal_caveat,claim_support_eligible,resolution_method)
SELECT edge_id,'explicit','2021-01-01','alo:lawrev:jp:planted:2010','repealed','none',true,'planted' FROM e;

-- P0-4: two reviewed/confirmed succession rows, same work, different law_id, overlap, no lineage bundle.
INSERT INTO lawtime.law_succession_edge(work_uri,law_id,relation_type,valid_from,valid_to,confidence,lineage_event_id) VALUES
 ('alo:law:jp:planted','planted_a','renamed','2011-01-01','2016-01-01','confirmed',NULL),
 ('alo:law:jp:planted','planted_b','merged','2013-01-01','2019-01-01','confirmed',NULL);

-- N-1: work with NO succession but TWO distinct law_id in law_revision.
INSERT INTO lawtime.law_work(work_uri,title) VALUES ('alo:law:jp:fallback','fallback') ON CONFLICT DO NOTHING;
INSERT INTO lawtime.law_revision(revision_uri,work_uri,law_id,valid_from,valid_to,revision_status) VALUES
 ('alo:lawrev:jp:fallback:a','alo:law:jp:fallback','fb_old','1990-01-01','2000-01-01','PreviousEnforced'),
 ('alo:lawrev:jp:fallback:b','alo:law:jp:fallback','fb_new','2000-01-01',NULL,'CurrentEnforced');

-- N-2: two revisions of the SAME law_id with OVERLAPPING [valid_from, valid_to).
INSERT INTO lawtime.law_work(work_uri,title) VALUES ('alo:law:jp:overlap','overlap') ON CONFLICT DO NOTHING;
INSERT INTO lawtime.law_revision(revision_uri,work_uri,law_id,valid_from,valid_to,revision_status) VALUES
 ('alo:lawrev:jp:overlap:a','alo:law:jp:overlap','ov','2010-01-01','2016-01-01','PreviousEnforced'),
 ('alo:lawrev:jp:overlap:b','alo:law:jp:overlap','ov','2014-01-01','2020-01-01','CurrentEnforced'); -- 2014<2016

-- N-3/N-4: same law_id with CurrentEnforced AND Repeal coexisting.
INSERT INTO lawtime.law_work(work_uri,title) VALUES ('alo:law:jp:badstatus','badstatus') ON CONFLICT DO NOTHING;
INSERT INTO lawtime.law_revision(revision_uri,work_uri,law_id,valid_from,valid_to,revision_status) VALUES
 ('alo:lawrev:jp:badstatus:a','alo:law:jp:badstatus','bs','2000-01-01',NULL,'CurrentEnforced'),
 ('alo:lawrev:jp:badstatus:b','alo:law:jp:badstatus','bs','1990-01-01','2000-01-01','Repeal');

COMMIT;

\echo '--- lawtime v0.2.4 gate detection (expect >0 for each planted) ---'
SELECT 'citation_edge_missing_side_table' g, count(*) FROM lawtime.v_gate_lawtime_citation_edge_missing_side_table_v20260624
UNION ALL SELECT 'side_table_orphan_or_noncitation', count(*) FROM lawtime.v_gate_lawtime_side_table_orphan_or_noncitation_v20260624
UNION ALL SELECT 'resolved_revision_covers_asof', count(*) FROM lawtime.v_gate_lawtime_resolved_revision_covers_asof_v20260624
UNION ALL SELECT 'claim_support_requires_resolved', count(*) FROM lawtime.v_gate_lawtime_claim_support_requires_resolved_v20260624
UNION ALL SELECT 'succession_no_ambiguous_overlap', count(*) FROM lawtime.v_gate_lawtime_succession_no_ambiguous_overlap_v20260624
UNION ALL SELECT 'work_single_fallback_law_id', count(*) FROM lawtime.v_gate_lawtime_work_single_fallback_law_id_v20260624
UNION ALL SELECT 'statute_revision_no_ambiguous_overlap', count(*) FROM lawtime.v_gate_lawtime_statute_revision_no_ambiguous_overlap_v20260624
UNION ALL SELECT 'formal_status_inconsistent', count(*) FROM lawtime.v_gate_lawtime_formal_status_inconsistent_v20260624
ORDER BY g;
