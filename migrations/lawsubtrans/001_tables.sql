-- DD-LAWSUBTRANS-001 v0.1.3 — T1–T6 tables (production DDL, P1)
-- status: design accepted (owner ratified 2026-06-10). Validation = Supabase
--   branch dry-run against the real alo_* tables + lawtime R-1 views.
--   DO NOT validate on an empty local DB (false positive: base tables/rows absent).
-- depends_on: alo_law_work(law_work_id), alo_statutes, alo_edges  [existing law layer]
--             v_lawtime_formal_status / v_lawtime_resolved_ref     [DD-LAWTIME v0.2.3 R-1]
-- principle: 形式(DD-LAWTIME) と 実質(本層) を分離。実質は出典付き assertion、
--            真として自動確定しない。claim_support 既定 false（原則 view 導出）。

BEGIN;

-- ── T1. 観測・形式の基盤（Phase2）。実質変化を主張しない ──────────────
CREATE TABLE alo_law_textual_delta (
  delta_id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  law_work_id          text NOT NULL REFERENCES alo_law_work(law_work_id),
  law_id               text NOT NULL,
  article_path         text NOT NULL,                 -- egov URI tail (art:709[:para:n[:item:n]])
  from_law_revision_id text NOT NULL,
  to_law_revision_id   text NOT NULL,
  delta_kind           text NOT NULL,                 -- AKN textualMod 準拠
  text_changed         boolean NOT NULL,
  similarity           numeric,
  diff_pointer         text,
  detector_version     text NOT NULL,
  source_snapshot_id   text NOT NULL,
  known_from           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_delta_kind CHECK (delta_kind IN
    ('substitution','insertion','repeal','renumber','relocate','split','join','no_change','unknown'))
);
CREATE INDEX alo_delta_work_art_idx ON alo_law_textual_delta(law_work_id, article_path);

-- ── T5. 証拠ポインタ（先に定義: T2–T4 が FK 参照する） ────────────────
-- Note A: locator 系列は nullable のまま。完全性は gate `evidence_locator_complete`
--         で reviewed/accepted/claim_support 対象に限定して検査（一律 NOT NULL にしない）。
CREATE TABLE alo_law_interpretive_evidence (
  evidence_pointer_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_type          text NOT NULL,
  source_tier          smallint NOT NULL,
  source_uri           text,
  source_record_key    text,
  locator              text,
  source_span_hash     text,
  quoted_text          text,
  parser_version       text,
  retrieved_at         timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_ev_tier CHECK (source_tier BETWEEN 1 AND 5),
  CONSTRAINT ck_ev_src CHECK (source_type IN
    ('official_legal_data','legislative_drafter','ministry_commentary','legislative_record',
     'court','scholar','treatise','practitioner','alo_internal'))
);

-- ── T2. 実質的変更 assertion（中核） ──────────────────────────────────
-- claim_support_eligible は原則 §3.7 view 導出。物理列保持のため drift gate
-- (claim_support_consistent_with_view) を 004_gates.sql に置く。
-- T2 は物理 assertion_status を持たない（現在 status は T6 を畳んだ view 解決, 'candidate' 起点）。
CREATE TABLE alo_law_substantive_change_assertion (
  assertion_id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  law_work_id          text NOT NULL REFERENCES alo_law_work(law_work_id),
  article_path         text NOT NULL,
  from_law_revision_id text,
  to_law_revision_id   text,
  related_delta_id     bigint REFERENCES alo_law_textual_delta(delta_id),
  change_type          text NOT NULL,
  temporal_reach       text NOT NULL DEFAULT 'unknown',
  asserted_by_source_type text NOT NULL,
  source_tier          smallint NOT NULL,
  evidence_pointer_id  bigint REFERENCES alo_law_interpretive_evidence(evidence_pointer_id),
  confidence           text NOT NULL DEFAULT 'low',
  rank                 text NOT NULL DEFAULT 'normal',
  rank_reason          text,
  counter_assertion_id bigint REFERENCES alo_law_substantive_change_assertion(assertion_id),
  valid_for_case_type  text,
  applies_from         date,
  applies_until        date,
  claim_support_eligible boolean NOT NULL DEFAULT false,
  asserted_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_subchg_type CHECK (change_type IN
    ('no_substantive_change','wording_clarification','scope_expansion','scope_reduction',
     'requirement_added','requirement_removed','requirement_changed','effect_changed',
     'subject_changed','procedure_changed','efficacy_change','substantive_change_unspecified',
     'disputed','unknown')),
  CONSTRAINT ck_subchg_reach CHECK (temporal_reach IN ('ex_nunc','ex_tunc','unknown')),
  CONSTRAINT ck_subchg_src CHECK (asserted_by_source_type IN
    ('official_legal_data','legislative_drafter','ministry_commentary','legislative_record',
     'court','scholar','treatise','practitioner','alo_internal')),
  CONSTRAINT ck_subchg_tier CHECK (source_tier BETWEEN 1 AND 5),
  CONSTRAINT ck_subchg_conf CHECK (confidence IN ('low','medium','high')),
  CONSTRAINT ck_subchg_rank CHECK (rank IN ('preferred','normal','deprecated')),
  CONSTRAINT ck_subchg_rankrsn CHECK (rank = 'normal' OR rank_reason IS NOT NULL),
  CONSTRAINT ck_subchg_claim CHECK (
    claim_support_eligible = false
    OR (evidence_pointer_id IS NOT NULL AND counter_assertion_id IS NULL))
);
CREATE INDEX alo_subchg_work_art_idx ON alo_law_substantive_change_assertion(law_work_id, article_path);

-- ── T3. 解釈変遷 assertion ────────────────────────────────────────────
CREATE TABLE alo_law_interpretation_transition (
  transition_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  law_work_id          text NOT NULL REFERENCES alo_law_work(law_work_id),
  article_path         text,
  doctrine_label       text,
  transition_type      text NOT NULL,
  before_revision_id   text,
  after_revision_id    text,
  interpretive_basis   text,
  treatment_relation   text,
  asserted_by_source_type text NOT NULL,
  source_tier          smallint NOT NULL,
  evidence_pointer_id  bigint REFERENCES alo_law_interpretive_evidence(evidence_pointer_id),
  assertion_status     text NOT NULL DEFAULT 'candidate',
  confidence           text NOT NULL DEFAULT 'low',
  counter_transition_id bigint REFERENCES alo_law_interpretation_transition(transition_id),
  claim_support_eligible boolean NOT NULL DEFAULT false,
  asserted_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_inttr_type CHECK (transition_type IN
    ('interpretation_continues','interpretation_discontinued','interpretation_modified',
     'interpretation_newly_established','interpretation_disputed','unknown')),
  CONSTRAINT ck_inttr_treatment CHECK (treatment_relation IS NULL OR treatment_relation IN
    ('followed','applied','approved','relied_upon','cited','considered','explained',
     'distinguished','limited','questioned','criticized','called_into_doubt','declined_to_extend',
     'followed_with_reservations','not_applied','overruled','abrogated','disapproved','superseded_by_statute')),
  CONSTRAINT ck_inttr_src CHECK (asserted_by_source_type IN
    ('official_legal_data','legislative_drafter','ministry_commentary','legislative_record',
     'court','scholar','treatise','practitioner','alo_internal')),
  CONSTRAINT ck_inttr_tier CHECK (source_tier BETWEEN 1 AND 5),
  CONSTRAINT ck_inttr_status CHECK (assertion_status IN
    ('observed','candidate','reviewed','accepted','disputed','deprecated')),
  CONSTRAINT ck_inttr_conf CHECK (confidence IN ('low','medium','high')),
  CONSTRAINT ck_inttr_claim CHECK (
    claim_support_eligible = false
    OR (evidence_pointer_id IS NOT NULL AND counter_transition_id IS NULL))
);
CREATE INDEX alo_inttr_work_art_idx ON alo_law_interpretation_transition(law_work_id, article_path);

-- ── T4. 旧法存続 assertion（三軸） ────────────────────────────────────
CREATE TABLE alo_old_law_survival_assertion (
  survival_id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  law_work_id          text NOT NULL REFERENCES alo_law_work(law_work_id),
  article_path         text,
  superseding_revision_id text,
  formal_status        text NOT NULL,                 -- lawtime ミラー（gate 必須）
  substantive_status   text NOT NULL,
  applicability_scope  text[] NOT NULL DEFAULT '{}',
  temporal_reach       text NOT NULL DEFAULT 'unknown',
  basis_kind           text,
  asserted_by_source_type text NOT NULL,
  source_tier          smallint NOT NULL,
  evidence_pointer_id  bigint REFERENCES alo_law_interpretive_evidence(evidence_pointer_id),
  assertion_status     text NOT NULL DEFAULT 'candidate',
  confidence           text NOT NULL DEFAULT 'low',
  counter_survival_id  bigint REFERENCES alo_old_law_survival_assertion(survival_id),
  claim_support_eligible boolean NOT NULL DEFAULT false,
  asserted_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_surv_formal CHECK (formal_status IN
    ('in_force','repealed','expired','superseded','not_yet_in_force','annulled')),
  CONSTRAINT ck_surv_subst CHECK (substantive_status IN
    ('continues','partially_continues','discontinued','transformed','disputed','unknown')),
  CONSTRAINT ck_surv_reach CHECK (temporal_reach IN ('ex_nunc','ex_tunc','unknown')),
  CONSTRAINT ck_surv_scope CHECK (applicability_scope <@ ARRAY[
    'pending_cases','past_events','existing_contracts','transitional_period',
    'specific_industry','specific_procedure','none','unknown']::text[]),
  CONSTRAINT ck_surv_src CHECK (asserted_by_source_type IN
    ('official_legal_data','legislative_drafter','ministry_commentary','legislative_record',
     'court','scholar','treatise','practitioner','alo_internal')),
  CONSTRAINT ck_surv_tier CHECK (source_tier BETWEEN 1 AND 5),
  CONSTRAINT ck_surv_status CHECK (assertion_status IN
    ('observed','candidate','reviewed','accepted','disputed','deprecated')),
  CONSTRAINT ck_surv_conf CHECK (confidence IN ('low','medium','high')),
  CONSTRAINT ck_surv_claim CHECK (
    claim_support_eligible = false
    OR (evidence_pointer_id IS NOT NULL AND counter_survival_id IS NULL))
);
CREATE INDEX alo_surv_work_art_idx ON alo_old_law_survival_assertion(law_work_id, article_path);

-- ── T6. append-only ライフサイクル（resolution_log の具体化） ──────────
CREATE TABLE alo_law_assertion_review_event (
  review_id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  assertion_kind       text NOT NULL,
  assertion_id         bigint NOT NULL,
  new_status           text NOT NULL,
  new_rank             text,
  review_basis         text NOT NULL,                 -- accepted 化に必須（P2241/P7452 相当）
  decided_by           text NOT NULL,
  decided_at           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_rev_kind CHECK (assertion_kind IN
    ('substantive_change','interpretation_transition','old_law_survival')),
  CONSTRAINT ck_rev_status CHECK (new_status IN
    ('observed','candidate','reviewed','accepted','disputed','deprecated')),
  CONSTRAINT ck_rev_rank CHECK (new_rank IS NULL OR new_rank IN ('preferred','normal','deprecated'))
);
CREATE INDEX alo_rev_assertion_idx ON alo_law_assertion_review_event(assertion_kind, assertion_id, decided_at DESC);

COMMIT;
