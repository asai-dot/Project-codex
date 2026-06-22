-- DD-LAWTIME-001 v0.2.2 — base law layer DDL (RECONSTRUCTED, candidate)
-- ============================================================================
-- ⚠️ RECONSTRUCTION NOTICE
--   The original v0.2.2 base DDL was not present in this repository. This file is
--   reconstructed from DD-LAWTIME-001_v0.2.3_production_patch.md (which references
--   v0.2.2's tables/columns/resolver/gates) + the columns consumed by
--   DD-LAWSUBTRANS-001 (migrations/lawsubtrans/*). Value domains marked "(recon)"
--   are best-effort and MUST be reconciled against the authoritative v0.2.x design
--   before any production apply. status: candidate (audit + owner ratify required).
-- ============================================================================
-- Scope of this file: the v0.2.2 objects that the v0.2.3 patch assumes already exist:
--   alo_law_work, alo_statutes, alo_edges (incl. D2 column additions),
--   alo_law_succession_edge, alo_law_ref_temporal_eval_event,
--   fn_resolve_law_reference_at (two-tier resolver, ORDER BY ... LIMIT 1),
--   append-only trigger on the eval-event log.
-- The two-tier CHECK ck_law_ref_two_tier is intentionally NOT added here — it is
--   added by 010_patch_v0.2.3.sql via NOT VALID → backfill → VALIDATE (P0-1).

BEGIN;

-- ── Work-level identity (FK target for statutes / succession / lawsubtrans) ──
CREATE TABLE IF NOT EXISTS alo_law_work (
  law_work_id text PRIMARY KEY,
  title       text
);

-- ── Statute revisions (formal time axis: 公布/施行/改正/廃止/版) ──────────
CREATE TABLE IF NOT EXISTS alo_statutes (
  law_revision_id text PRIMARY KEY,
  law_work_id     text REFERENCES alo_law_work(law_work_id),
  law_id          text NOT NULL,
  valid_from      date,                 -- 施行（半開区間 [valid_from, valid_to)）
  valid_to        date,                 -- 失効/次版施行
  revision_status text NOT NULL,
  CONSTRAINT ck_statute_status CHECK (revision_status IN          -- (recon: R-1 view 由来)
    ('CurrentEnforced','PreviousEnforced','Repeal','UnEnforced'))
);
CREATE INDEX IF NOT EXISTS alo_statutes_lawid_idx ON alo_statutes(law_id, valid_from);

-- ── Succession (法令の襲名/統廃合の系譜。二段 resolver の tier1) ──────────
CREATE TABLE IF NOT EXISTS alo_law_succession_edge (
  succession_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  law_work_id      text NOT NULL REFERENCES alo_law_work(law_work_id),
  law_id           text NOT NULL,       -- この区間で law_work を体現する law_id
  relation_type    text NOT NULL DEFAULT 'unknown',
  valid_from       date,
  valid_to         date,
  confidence       text NOT NULL DEFAULT 'candidate',
  lineage_event_id text,                -- merge/split を束ねる同一イベントキー
  CONSTRAINT ck_succ_rel CHECK (relation_type IN                  -- (recon)
    ('renamed','merged','split','absorbed','reorganized','continues','unknown')),
  CONSTRAINT ck_succ_conf CHECK (confidence IN                    -- (recon: patch P0-4 由来)
    ('candidate','reviewed','confirmed','unknown'))
);
CREATE INDEX IF NOT EXISTS alo_succ_work_idx ON alo_law_succession_edge(law_work_id, valid_from);

-- ── Generic edge table (only the statute-citation columns are modeled here) ──
-- D2 column additions (v0.2.2): as_of_*, resolved_law_revision_id, temporal_*,
--   claim_support_eligible. claim_support_eligible DEFAULT false（安全側）。
CREATE TABLE IF NOT EXISTS alo_edges (
  edge_id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  edge_type                text NOT NULL,
  src_id                   text,                 -- generic endpoints (recon, minimal)
  dst_id                   text,
  -- ── statute-citation temporal columns (D2) ──
  cited_law_work_id        text,
  cited_law_id             text,
  as_of_basis              text NOT NULL DEFAULT 'unknown',
  as_of_date               date,
  resolved_law_revision_id text REFERENCES alo_statutes(law_revision_id),
  temporal_status          text,                 -- nullable: legacy 行は NULL → patch で backfill
  temporal_caveat          text NOT NULL DEFAULT 'none',
  claim_support_eligible   boolean NOT NULL DEFAULT false,
  CONSTRAINT ck_edge_asof_basis CHECK (as_of_basis IN            -- (recon)
    ('explicit','document_date','event_date','unknown')),
  CONSTRAINT ck_edge_tstatus CHECK (temporal_status IS NULL OR temporal_status IN  -- (recon)
    ('unchecked','current','superseded','pre_enactment','unenforced','repealed','not_yet_in_force')),
  CONSTRAINT ck_edge_tcaveat CHECK (temporal_caveat IN          -- (recon)
    ('none','approximate','ambiguous','unknown'))
);
CREATE INDEX IF NOT EXISTS alo_edges_lawref_idx ON alo_edges(edge_type, cited_law_work_id);

-- ── Temporal-eval event log (resolver/監査が版解決を記録。append-only) ──────
CREATE TABLE IF NOT EXISTS alo_law_ref_temporal_eval_event (
  eval_id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  edge_id                  bigint NOT NULL REFERENCES alo_edges(edge_id),
  resolved_law_revision_id text,
  temporal_status          text,
  method                   text,
  evaluated_by             text NOT NULL,
  evaluated_at             timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS alo_eval_edge_idx ON alo_law_ref_temporal_eval_event(edge_id, evaluated_at DESC);

-- ── append-only trigger on the eval-event log (v0.2.2) ──────────────────────
CREATE OR REPLACE FUNCTION trg_lawtime_eval_append_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'alo_law_ref_temporal_eval_event is append-only';
END; $$;
DROP TRIGGER IF EXISTS eval_append_only ON alo_law_ref_temporal_eval_event;
CREATE TRIGGER eval_append_only BEFORE UPDATE OR DELETE ON alo_law_ref_temporal_eval_event
  FOR EACH ROW EXECUTE FUNCTION trg_lawtime_eval_append_only();

-- ── two-tier resolver (recon). tier1: succession で law_id 解決、tier2: as_of の版選択.
--    挙動は v0.2.2 のまま LIMIT 1（曖昧ケースは patch P0-4 gate で事前に空にする運用）──
CREATE OR REPLACE FUNCTION fn_resolve_law_reference_at(
  p_law_work_id text, p_as_of date
) RETURNS text                              -- returns law_revision_id (or NULL)
LANGUAGE sql STABLE AS $$
  WITH resolved_law AS (    -- tier1: as_of 時点で law_work を体現する law_id
    SELECT s.law_id
    FROM alo_law_succession_edge s
    WHERE s.law_work_id = p_law_work_id
      AND s.relation_type <> 'unknown'
      AND (s.valid_from IS NULL OR s.valid_from <= p_as_of)
      AND (s.valid_to   IS NULL OR p_as_of < s.valid_to)
    ORDER BY s.valid_from DESC NULLS LAST
    LIMIT 1
  )
  SELECT st.law_revision_id                -- tier2: as_of の版
  FROM alo_statutes st
  WHERE st.law_id = COALESCE((SELECT law_id FROM resolved_law),
                             (SELECT law_id FROM alo_statutes WHERE law_work_id = p_law_work_id LIMIT 1))
    AND (st.valid_from IS NULL OR st.valid_from <= p_as_of)
    AND (st.valid_to   IS NULL OR p_as_of < st.valid_to)
  ORDER BY st.valid_from DESC NULLS LAST
  LIMIT 1;                                  -- ★ v0.2.2 挙動維持（曖昧は P0-4 gate）
$$;

COMMIT;
