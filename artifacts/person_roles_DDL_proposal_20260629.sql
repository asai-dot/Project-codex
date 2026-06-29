-- ============================================================================
-- PROPOSAL ONLY — DO NOT APPLY WITHOUT AUDIT GATE
-- ============================================================================
-- person_roles_v1 — non-lossy multi-role representation for authority.person
--
-- Status:       DRAFT / proposal artifact (2026-06-29)
-- Gate:         DDL is HOLD per governance (no DDL/backfill/promote without
--               separate audit gate). This file is a reviewable design, NOT a
--               migration to run. apply_migration was deliberately NOT called.
-- Motivation:   authority.person.person_type is a single-value column. For
--               dual-title people (弁護士兼大学教授, 元裁判官→教授, 弁理士兼弁護士,
--               etc.) collapsing to one enum discards the other attested roles.
--               The pilot over 223 adjudication authors found 42/98 distinct
--               persons hold ≥2 roles; one (六車 明) holds 5. See
--               artifacts/person_multirole_profiles_20260629.{tsv,json}.
-- Principle:    candidate ≠ confirmed. Each role carries its own evidence and
--               decision_method; nothing here promotes candidates to confirmed.
-- ============================================================================

-- Current state (for reviewer reference; from live schema 2026-06-29):
--   authority.person(
--     person_id text PK,
--     person_type text NOT NULL
--       CHECK (person_type IN ('scholar','judge','lawyer_practitioner','unknown')),
--     canonical_name text NOT NULL,
--     canonical_name_normalized text,
--     display_name text,
--     status text NOT NULL DEFAULT 'active'
--       CHECK (status IN ('active','inactive','merged')),
--     created_at timestamptz NOT NULL DEFAULT timezone('utc', now()),
--     updated_at timestamptz NOT NULL DEFAULT timezone('utc', now())
--   )
--   Row counts: scholar 73,155 | lawyer_practitioner 48,690 | judge 6,236
--
-- person_type is KEPT (backward compatible) and treated as the cached
-- "primary role". The new table is the authoritative full record.

BEGIN;

-- ── 1. New table: one row per (person, role) ────────────────────────────────
CREATE TABLE IF NOT EXISTS authority.person_role (
    person_role_id  text        PRIMARY KEY,           -- e.g. 'prole:<uuid>' or '<person_id>:<role>'
    person_id       text        NOT NULL
                                REFERENCES authority.person(person_id)
                                ON DELETE CASCADE,
    role            text        NOT NULL
                                CHECK (role IN (
                                    'scholar',
                                    'lawyer_practitioner',
                                    'judge',
                                    'prosecutor',
                                    'patent_attorney',
                                    'bureaucrat',
                                    'other',
                                    'unknown'
                                )),
    role_status     text        NOT NULL DEFAULT 'unknown'
                                CHECK (role_status IN (
                                    'current', 'former', 'concurrent', 'unknown'
                                )),
    is_primary      boolean     NOT NULL DEFAULT false, -- mirrors person.person_type
    detail          text,                               -- 所属・専門・時期 (free text)
    confidence      text        CHECK (confidence IN ('high','medium','low')),
    -- provenance / governance (candidate ≠ confirmed)
    claim_status    text        NOT NULL DEFAULT 'candidate'
                                CHECK (claim_status IN (
                                    'candidate', 'needs_review', 'accepted', 'rejected'
                                )),
    decision_method text,                               -- e.g. 'worker_blind_profile_v1'
    evidence_source text,                               -- e.g. 'multirole_profile_20260629'
    created_at      timestamptz NOT NULL DEFAULT timezone('utc', now()),
    updated_at      timestamptz NOT NULL DEFAULT timezone('utc', now()),

    -- a person cannot list the same role twice
    CONSTRAINT person_role_unique_role UNIQUE (person_id, role)
);

-- ── 2. At most one primary role per person ──────────────────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS person_role_one_primary
    ON authority.person_role (person_id)
    WHERE is_primary;

-- ── 3. Lookup index ─────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS person_role_person_idx
    ON authority.person_role (person_id);
CREATE INDEX IF NOT EXISTS person_role_role_idx
    ON authority.person_role (role);

-- ── 4. Backward-compatibility view (legacy single-value consumers) ──────────
-- Exposes the primary role as person_type, identical column name/shape so
-- existing readers need no change.
CREATE OR REPLACE VIEW authority.person_primary_role AS
SELECT p.person_id,
       p.canonical_name,
       COALESCE(pr.role, p.person_type) AS person_type,  -- prefer explicit primary
       pr.role_status,
       pr.confidence
FROM authority.person p
LEFT JOIN authority.person_role pr
       ON pr.person_id = p.person_id AND pr.is_primary;

COMMIT;

-- ============================================================================
-- BACKFILL PLAN (separate gated step — NOT executed here)
-- ============================================================================
-- Phase B1 (lossless seed): for every existing authority.person, insert one
-- person_role row mirroring the current person_type as is_primary=true,
-- role_status='unknown', claim_status='accepted' (it is the current canonical),
-- decision_method='legacy_person_type_backfill'. This loses nothing.
--
--   INSERT INTO authority.person_role
--     (person_role_id, person_id, role, role_status, is_primary,
--      claim_status, decision_method, evidence_source)
--   SELECT p.person_id || ':' || p.person_type, p.person_id,
--          CASE WHEN p.person_type IN
--               ('scholar','lawyer_practitioner','judge','unknown')
--               THEN p.person_type ELSE 'unknown' END,
--          'unknown', true, 'accepted', 'legacy_person_type_backfill',
--          'authority.person.person_type'
--   FROM authority.person p
--   ON CONFLICT (person_id, role) DO NOTHING;
--
-- Phase B2 (enrich, candidate-level): load the 98 profiled persons from
-- artifacts/person_multirole_profiles_20260629.json. For each role NOT already
-- present, insert claim_status='candidate' (or 'needs_review'), is_primary set
-- only where it matches the profile's primary_role AND a reviewer accepts.
-- Matching person_id requires resolving the multirole 'name' to person_id via
-- canonical_name_normalized — note person entity duplication: the same name maps
-- to multiple person_id rows, so B2 MUST run AFTER person dedup, or attach the
-- role to all duplicate person_ids and let dedup merge them. DO NOT auto-accept.
--
-- Phase B3 (sync, optional): keep person.person_type == the is_primary role via
-- trigger or scheduled job, OR deprecate person.person_type in favour of the
-- view. Decide at gate.
--
-- ============================================================================
-- OPEN QUESTIONS FOR THE AUDIT GATE
-- ============================================================================
-- Q1. ID scheme for person_role_id: surrogate ('prole:<uuid>') vs natural
--     ('<person_id>:<role>'). Natural is human-debuggable and makes the UNIQUE
--     (person_id, role) redundant; surrogate is stabler if role values ever change.
-- Q2. Should person.person_type CHECK be widened to include the 4 new roles
--     (prosecutor/patent_attorney/bureaucrat/other) so primary can be any role,
--     or should primary be constrained to the legacy 4 for compatibility?
--     Pilot found primary=patent_attorney (時井真), bureaucrat (高橋健),
--     other (河合潤) — so widening is required to represent them faithfully.
-- Q3. Multiplicity of 'scholar' (e.g. former + current at different universities):
--     UNIQUE(person_id, role) forbids two 'scholar' rows. If institution-level
--     history matters, add affiliation/period columns and relax the unique key.
--     Pilot collapsed these into one scholar row + detail text — acceptable for v1.
-- Q4. claim_status default 'candidate' keeps the candidate≠confirmed invariant;
--     promotion to 'accepted' needs ≥2 independent origin_family + adjudication,
--     same as publication_author_claim. Confirm this is the intended bar.
-- ============================================================================
