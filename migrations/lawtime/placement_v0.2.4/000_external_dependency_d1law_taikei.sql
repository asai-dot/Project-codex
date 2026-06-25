-- DD-LAWTIME-001 v0.2.4 (placement / C-option) — EXTERNAL DEPENDENCY DECLARATION
-- ============================================================================
-- ⚠️ SMOKE FIXTURE ONLY — DO NOT APPLY TO SUPABASE.
--   In asai-dot's Project the schema `d1law_taikei` and its canonical URI typed-edge
--   table `alo_edges` ALREADY EXIST (verified read-only 2026-06-24). The v0.2.4
--   placement patch TREATS d1law_taikei.alo_edges as the canonical citation-edge
--   layer (the "母屋"); it does NOT create or alter it in production.
--   This file exists so the LOCAL structural smoke has the 母屋 to reference. The
--   real table is owned by the d1law_taikei migrations, NOT by lawtime.
-- ----------------------------------------------------------------------------
-- Real shape captured from the live project (placement consultation REQUEST §1.1):
--   alo_edges(edge_id bigint, src_uri text NOT NULL, edge_type text NOT NULL,
--             dst_uri text NOT NULL, source_system text, source_version text,
--             valid_from date)
--   => URI->URI generic typed-edge graph. It does NOT carry temporal/as_of/
--      resolved-revision/claim_support columns. Those live in lawtime (side-table).
-- edge_type vocabulary is owned by DDLAWREF (NOT by lawtime). lawtime only READS a
--   citation subset; see migrations/lawtime/placement_v0.2.4/200_gates.sql header.
-- ----------------------------------------------------------------------------
-- ⚠️ B′ read-only re-confirmation (2026-06-25, zero-charge introspection):
--   The live alo_edges PK is `edge_id bigint` (FK type-match ✅) and the column list
--   above is faithful. BUT the live table currently holds ONLY edge_type
--   'classified_under' (10,823 rows) — ZERO statute-citation edges. The citation
--   edge_type set used by 200_gates ('cites_statute'/'statute_ref'/'applies_statute')
--   is a PLACEHOLDER not yet present in the real 母屋; reconciling it is a DDLAWREF
--   decision (blocking note #5). See docs/dd/DD-LAWTIME-001_v0.2.4_B-prime_dryrun_evidence.md.
--   NOTE: live identity is a nextval default; this fixture uses GENERATED ALWAYS — the
--   smoke never inserts an explicit edge_id, so the difference is immaterial.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS d1law_taikei;

-- Minimal stand-in of the EXISTING canonical edge table (smoke only).
CREATE TABLE IF NOT EXISTS d1law_taikei.alo_edges (
  edge_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  src_uri        text NOT NULL,
  edge_type      text NOT NULL,
  dst_uri        text NOT NULL,
  source_system  text,
  source_version text,
  valid_from     date
);
CREATE INDEX IF NOT EXISTS alo_edges_type_dst_idx
  ON d1law_taikei.alo_edges(edge_type, dst_uri);
