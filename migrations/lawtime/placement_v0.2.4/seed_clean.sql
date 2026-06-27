-- DD-LAWTIME-001 v0.2.4 — clean deterministic seed for the structural smoke.
-- URI identity throughout. All gates must be EMPTY on this dataset.
BEGIN;

-- works ----------------------------------------------------------------------
INSERT INTO lawtime.law_work(work_uri,title) VALUES
 ('alo:law:jp:minpo','民法'),
 ('alo:law:jp:shotaku','借地借家法')
ON CONFLICT DO NOTHING;

-- revisions (non-overlapping per law_id; one CurrentEnforced per law_id) ------
INSERT INTO lawtime.law_revision(revision_uri,work_uri,law_id,valid_from,valid_to,revision_status) VALUES
 ('alo:lawrev:jp:minpo:1898','alo:law:jp:minpo','minpo','1898-07-16','2020-04-01','PreviousEnforced'),
 ('alo:lawrev:jp:minpo:2020','alo:law:jp:minpo','minpo','2020-04-01',NULL,'CurrentEnforced'),
 ('alo:lawrev:jp:shotaku:1991','alo:law:jp:shotaku','shotaku','1992-08-01',NULL,'CurrentEnforced')
ON CONFLICT DO NOTHING;

-- succession (unambiguous; shotaku continues, reviewed) -----------------------
INSERT INTO lawtime.law_succession_edge(work_uri,law_id,relation_type,valid_from,valid_to,confidence,lineage_event_id) VALUES
 ('alo:law:jp:shotaku','shotaku','continues','1992-08-01',NULL,'reviewed','lin_shotaku_1')
ON CONFLICT DO NOTHING;

-- canonical citation edges in the 母屋 (d1law_taikei.alo_edges) ---------------
--   edge_id is IDENTITY; capture them to attach side-table rows deterministically.
WITH ins AS (
  INSERT INTO d1law_taikei.alo_edges(src_uri,edge_type,dst_uri,source_system,source_version,valid_from)
  VALUES
   ('alo:doc:jp:caseX#p1','cites_statute','alo:law:jp:minpo','smoke','v0','2021-05-01'),
   ('alo:doc:jp:caseY#p1','cites_statute','alo:law:jp:shotaku','smoke','v0','2000-01-01'),
   ('alo:doc:jp:caseZ#p1','cites_statute','alo:law:jp:minpo','smoke','v0',NULL)  -- unknown-basis citation
  RETURNING edge_id, dst_uri, valid_from
)
INSERT INTO lawtime.citation_temporal(
  edge_id, as_of_basis, as_of_date, target_law_revision_uri,
  resolved_revision_confidence, temporal_status, temporal_caveat,
  claim_support_eligible, resolution_method, evidence_pointer, parser_version)
SELECT i.edge_id,
       CASE WHEN i.valid_from IS NULL THEN 'unknown' ELSE 'explicit' END,
       i.valid_from,
       CASE
         WHEN i.valid_from IS NULL THEN NULL
         WHEN i.dst_uri='alo:law:jp:minpo'   THEN lawtime.fn_resolve_law_reference_at('alo:law:jp:minpo', i.valid_from)
         WHEN i.dst_uri='alo:law:jp:shotaku' THEN lawtime.fn_resolve_law_reference_at('alo:law:jp:shotaku', i.valid_from)
       END,
       CASE WHEN i.valid_from IS NULL THEN 'candidate' ELSE 'reviewed' END,
       CASE WHEN i.valid_from IS NULL THEN 'unchecked' ELSE 'current' END,
       'none',
       false,                                  -- claim_support stays false (safe side)
       CASE WHEN i.valid_from IS NULL THEN NULL ELSE 'resolver:v0.2.4' END,
       CASE WHEN i.valid_from IS NULL THEN NULL ELSE 'ev:smoke' END,
       'smoke-0.2.4'
FROM ins i;

-- eval events for the resolved (non-unknown) edges ---------------------------
INSERT INTO lawtime.temporal_eval_event(edge_id,target_law_revision_uri,temporal_status,method,parser_version,evaluated_by)
SELECT ct.edge_id, ct.target_law_revision_uri, ct.temporal_status, ct.resolution_method, ct.parser_version, 'smoke'
FROM lawtime.citation_temporal ct
WHERE ct.target_law_revision_uri IS NOT NULL;

COMMIT;
