-- DD-LAWTIME-001 v0.2.4 (placement / C-option) — lawtime schema (作業棟)
-- ============================================================================
-- C-option physical placement (per RESULT DDLAWTIME_PLACEMENT_PASS_WITH_NOTES,
-- file_id 2305621550301, 2026-06-24):
--   * lawtime  = TIME-AXIS WORK SHED: work/revision/provision time axis,
--                succession, revision mapping, temporal resolution run/result,
--                unresolved queue, and the edge_id-keyed citation TEMPORAL SIDE-TABLE.
--   * d1law_taikei.alo_edges = CANONICAL citation-edge body (the 母屋). lawtime does
--                NOT own an alo_edges of its own. The v0.2.3a `lawtime.alo_edges`
--                stand-in is WITHDRAWN (blocking note #1).
--   * serving  = exit gate (see 300_serving.sql).
-- Identity = URI (blocking note #3). search_path append is WITHDRAWN (blocking
--   note #2): every reference here is EXPLICITLY schema-qualified.
-- status: candidate (design_audit). production apply / Supabase materialize HOLD.
-- ============================================================================
-- URI scheme (auditor §2.4):
--   law work     : alo:law:jp:{law_id}
--   law revision : alo:lawrev:jp:{law_id}:{enforcement_key}
--   provision    : alo:lawprov:jp:{law_id}:art:{article_path}:rev:{revision_key}
-- Local text ids (e.g. 'LW_minpo') are STAGING/FIXTURE only, never canonical.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS lawtime;

BEGIN;

-- ── Work-level identity (stable anchor across succession) ────────────────────
CREATE TABLE IF NOT EXISTS lawtime.law_work (
  work_uri text PRIMARY KEY,                      -- alo:law:jp:{law_id}
  title    text,
  CONSTRAINT ck_law_work_uri CHECK (work_uri LIKE 'alo:law:jp:%')
);

-- ── Statute revisions (formal time axis: 公布/施行/改正/廃止/版) ─────────────
CREATE TABLE IF NOT EXISTS lawtime.law_revision (
  revision_uri    text PRIMARY KEY,               -- alo:lawrev:jp:{law_id}:{key}
  work_uri        text NOT NULL REFERENCES lawtime.law_work(work_uri),
  law_id          text NOT NULL,                  -- law_id this revision embodies
  valid_from      date,                           -- 施行（半開区間 [from, to)）
  valid_to        date,                           -- 失効/次版施行
  revision_status text NOT NULL,
  CONSTRAINT ck_revision_uri CHECK (revision_uri LIKE 'alo:lawrev:jp:%'),
  CONSTRAINT ck_revision_status CHECK (revision_status IN          -- (recon: R)
    ('CurrentEnforced','PreviousEnforced','Repeal','UnEnforced'))
);
CREATE INDEX IF NOT EXISTS law_revision_lawid_idx
  ON lawtime.law_revision(law_id, valid_from);
CREATE INDEX IF NOT EXISTS law_revision_work_idx
  ON lawtime.law_revision(work_uri);

-- ── Provision-level identity (optional granularity; minimal here) ────────────
CREATE TABLE IF NOT EXISTS lawtime.law_provision (
  provision_uri text PRIMARY KEY,                 -- alo:lawprov:jp:{law_id}:art:{..}:rev:{..}
  revision_uri  text NOT NULL REFERENCES lawtime.law_revision(revision_uri),
  article_path  text NOT NULL,
  CONSTRAINT ck_provision_uri CHECK (provision_uri LIKE 'alo:lawprov:jp:%')
);

-- ── Succession (襲名/統廃合の系譜。二段 resolver の tier1) ─────────────────────
CREATE TABLE IF NOT EXISTS lawtime.law_succession_edge (
  succession_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  work_uri         text NOT NULL REFERENCES lawtime.law_work(work_uri),
  law_id           text NOT NULL,                 -- law_id embodying the work in this span
  relation_type    text NOT NULL DEFAULT 'unknown',
  valid_from       date,
  valid_to         date,
  confidence       text NOT NULL DEFAULT 'candidate',
  lineage_event_id text,                          -- merge/split bundle key
  CONSTRAINT ck_succ_rel CHECK (relation_type IN                  -- (recon: R)
    ('renamed','merged','split','absorbed','reorganized','continues','unknown')),
  CONSTRAINT ck_succ_conf CHECK (confidence IN                    -- (recon: R, P0-4 由来)
    ('candidate','reviewed','confirmed','unknown'))
);
CREATE INDEX IF NOT EXISTS law_succ_work_idx
  ON lawtime.law_succession_edge(work_uri, valid_from);

-- ── Revision mapping / amendment delta (改正 → 版マッピング。最小) ───────────
CREATE TABLE IF NOT EXISTS lawtime.revision_mapping (
  mapping_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  from_revision_uri text REFERENCES lawtime.law_revision(revision_uri),
  to_revision_uri   text NOT NULL REFERENCES lawtime.law_revision(revision_uri),
  amendment_law_id  text,
  effective_date    date
);

-- ── Citation TEMPORAL side-table (C-option core; edge_id-keyed 1:1 with the
--    母屋's citation edges). Replaces the temporal/as_of/resolved/claim_support
--    columns that the v0.2.3a stand-in carried on its own alo_edges.
--    INVARIANT: a row exists here ONLY for statute-citation edges in
--    d1law_taikei.alo_edges. Because every row is by construction a citation edge,
--    the v0.2.3 two-tier rule is enforced INLINE (no NOT VALID dance needed —
--    the side-table is greenfield). Cross-table completeness/orphan checks live in
--    200_gates.sql. FK is ON DELETE CASCADE: the edge is the canonical fact, the
--    temporal row is its evaluation and must not outlive it. ────────────────────
CREATE TABLE IF NOT EXISTS lawtime.citation_temporal (
  edge_id                  bigint PRIMARY KEY
                             REFERENCES d1law_taikei.alo_edges(edge_id) ON DELETE CASCADE,
  as_of_basis              text NOT NULL DEFAULT 'unknown',
  as_of_date               date,
  source_law_revision_uri  text REFERENCES lawtime.law_revision(revision_uri),
  target_law_revision_uri  text REFERENCES lawtime.law_revision(revision_uri),  -- resolved target
  resolved_revision_confidence text NOT NULL DEFAULT 'candidate',
  temporal_status          text,
  temporal_caveat          text NOT NULL DEFAULT 'none',
  claim_support_eligible   boolean NOT NULL DEFAULT false,
  resolution_method        text,
  evidence_pointer         text,
  parser_version           text,
  created_at               timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_ct_asof_basis CHECK (as_of_basis IN              -- (recon: R)
    ('explicit','document_date','event_date','unknown')),
  CONSTRAINT ck_ct_tstatus CHECK (temporal_status IS NULL OR temporal_status IN  -- (recon: R)
    ('unchecked','current','superseded','pre_enactment','unenforced','repealed','not_yet_in_force')),
  CONSTRAINT ck_ct_tcaveat CHECK (temporal_caveat IN            -- (recon: R)
    ('none','approximate','ambiguous','unknown')),
  CONSTRAINT ck_ct_rconf CHECK (resolved_revision_confidence IN  -- (recon: R)
    ('candidate','reviewed','confirmed','unknown')),
  -- two-tier invariant (INLINE; every side-table row is a citation edge):
  CONSTRAINT ck_ct_two_tier CHECK (
       (as_of_basis <> 'unknown' AND as_of_date IS NOT NULL)
    OR (as_of_basis = 'unknown' AND as_of_date IS NULL
          AND target_law_revision_uri IS NULL
          AND temporal_status = 'unchecked'
          AND claim_support_eligible = false)
  )
);
CREATE INDEX IF NOT EXISTS citation_temporal_target_idx
  ON lawtime.citation_temporal(target_law_revision_uri);

-- ── Temporal resolution run/result event log (append-only) ───────────────────
CREATE TABLE IF NOT EXISTS lawtime.temporal_eval_event (
  eval_id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  edge_id                 bigint NOT NULL
                            REFERENCES d1law_taikei.alo_edges(edge_id),
  target_law_revision_uri text,
  temporal_status         text,
  method                  text,
  parser_version          text,
  evaluated_by            text NOT NULL,
  evaluated_at            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS temporal_eval_edge_idx
  ON lawtime.temporal_eval_event(edge_id, evaluated_at DESC);

CREATE OR REPLACE FUNCTION lawtime.trg_eval_append_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'lawtime.temporal_eval_event is append-only';
END; $$;
DROP TRIGGER IF EXISTS eval_append_only ON lawtime.temporal_eval_event;
CREATE TRIGGER eval_append_only BEFORE UPDATE OR DELETE ON lawtime.temporal_eval_event
  FOR EACH ROW EXECUTE FUNCTION lawtime.trg_eval_append_only();

-- ── Unresolved queue (citation edges awaiting temporal resolution) ───────────
CREATE TABLE IF NOT EXISTS lawtime.unresolved_queue (
  edge_id     bigint PRIMARY KEY
                REFERENCES d1law_taikei.alo_edges(edge_id) ON DELETE CASCADE,
  reason      text NOT NULL DEFAULT 'unresolved',
  enqueued_at timestamptz NOT NULL DEFAULT now()
);

-- ── two-tier resolver (URI-keyed). tier1: succession で law_id 解決、
--    tier2: as_of の版選択。v0.2.2 互換で LIMIT 1 維持（曖昧は gate で事前に空）。
--    全参照は明示修飾。返り値は revision_uri（NULL 可）。──────────────────────
CREATE OR REPLACE FUNCTION lawtime.fn_resolve_law_reference_at(
  p_work_uri text, p_as_of date
) RETURNS text
LANGUAGE sql STABLE AS $$
  WITH resolved_law AS (    -- tier1: as_of 時点で work を体現する law_id
    SELECT s.law_id
    FROM lawtime.law_succession_edge s
    WHERE s.work_uri = p_work_uri
      AND s.relation_type <> 'unknown'
      AND (s.valid_from IS NULL OR s.valid_from <= p_as_of)
      AND (s.valid_to   IS NULL OR p_as_of < s.valid_to)
    ORDER BY s.valid_from DESC NULLS LAST
    LIMIT 1
  )
  SELECT r.revision_uri                -- tier2: as_of の版
  FROM lawtime.law_revision r
  WHERE r.law_id = COALESCE(
          (SELECT law_id FROM resolved_law),
          (SELECT law_id FROM lawtime.law_revision WHERE work_uri = p_work_uri LIMIT 1))
    AND (r.valid_from IS NULL OR r.valid_from <= p_as_of)
    AND (r.valid_to   IS NULL OR p_as_of < r.valid_to)
  ORDER BY r.valid_from DESC NULLS LAST
  LIMIT 1;                             -- ★ LIMIT 1 維持（曖昧は N-1/N-2 gate）
$$;

COMMIT;

-- NOTE: NO `ALTER DATABASE ... SET search_path` here. search_path append is
--   WITHDRAWN (blocking note #2). Consumers must reference serving.* / lawtime.*
--   with explicit schema qualification.
