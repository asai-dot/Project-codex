-- DD-LAWTIME-001 v0.2.3 — production-DDL patch (transcribed from
--   docs/dd/DD-LAWTIME-001_v0.2.3_production_patch.md). status: candidate.
-- Closes v0.2.2 MODIFY_REQUIRED P0-1..P0-4 and adds the R-1 resolved-lawtime views
-- that DD-LAWSUBTRANS-001 connects to. Apply AFTER 001_base_v0.2.2.sql.
-- NOTE: lawtime_resolved=true is NOT by itself claim_support eligibility (R-1 note).
-- All objects live in schema `lawtime` (owner decision 2026-06-22). Consumers may
-- reference them unqualified via the appended search_path (set in 001_base).

-- ── P0-1. NOT VALID → backfill → (gate empty) → VALIDATE ────────────────────
ALTER TABLE lawtime.alo_edges ADD CONSTRAINT ck_law_ref_two_tier CHECK (
  edge_type NOT IN ('cites_statute','statute_ref','applies_statute')
  OR ( (as_of_basis <> 'unknown' AND as_of_date IS NOT NULL
          AND (cited_law_id IS NOT NULL OR cited_law_work_id IS NOT NULL))
    OR (as_of_basis = 'unknown' AND as_of_date IS NULL AND resolved_law_revision_id IS NULL
          AND temporal_status = 'unchecked' AND claim_support_eligible = false) )
) NOT VALID;

UPDATE lawtime.alo_edges
SET temporal_status = 'unchecked'
WHERE edge_type IN ('cites_statute','statute_ref','applies_statute')
  AND as_of_basis = 'unknown'
  AND temporal_status IS NULL;

-- migration-temp 検収 gate（VALIDATE 前に 0 件であること。unknown branch の全条件を検査）
CREATE OR REPLACE VIEW lawtime.gate_backfill_unknown_unchecked AS
  SELECT edge_id FROM lawtime.alo_edges
  WHERE edge_type IN ('cites_statute','statute_ref','applies_statute')
    AND as_of_basis = 'unknown'
    AND ( as_of_date IS NOT NULL
       OR resolved_law_revision_id IS NOT NULL
       OR temporal_status IS DISTINCT FROM 'unchecked'
       OR claim_support_eligible IS DISTINCT FROM false );

ALTER TABLE lawtime.alo_edges VALIDATE CONSTRAINT ck_law_ref_two_tier;

-- ── P0-2. resolved 版の as_of カバレッジ両端検査 ────────────────────────────
CREATE OR REPLACE VIEW lawtime.gate_resolved_revision_covers_asof AS
  SELECT e.edge_id
  FROM lawtime.alo_edges e
  JOIN lawtime.alo_statutes s ON s.law_revision_id = e.resolved_law_revision_id
  WHERE e.as_of_basis <> 'unknown' AND e.as_of_date IS NOT NULL
    AND (
         (s.valid_from IS NOT NULL AND e.as_of_date <  s.valid_from)   -- 施行前に当てた
      OR (s.valid_to   IS NOT NULL AND e.as_of_date >= s.valid_to)     -- 失効後に当てた
    );
-- 旧 gate_no_current_law_for_historical_citation は本 view に統合（alias 名は維持）
CREATE OR REPLACE VIEW lawtime.gate_no_current_law_for_historical_citation AS
  SELECT edge_id FROM lawtime.gate_resolved_revision_covers_asof;

-- ── P0-3. claim_support 許容 status を current/superseded に絞り込み ─────────
CREATE OR REPLACE VIEW lawtime.gate_claim_support_requires_resolved_lawtime AS
  SELECT e.edge_id FROM lawtime.alo_edges e
  WHERE e.edge_type IN ('cites_statute','statute_ref','applies_statute')
    AND e.claim_support_eligible = true
    AND ( e.resolved_law_revision_id IS NULL
       OR e.temporal_status IS NULL
       OR e.temporal_status NOT IN ('current','superseded')
       OR e.temporal_caveat <> 'none'
       OR NOT EXISTS (SELECT 1 FROM lawtime.alo_law_ref_temporal_eval_event v
                      WHERE v.edge_id = e.edge_id) );

-- ── P0-4. succession 多重マッチ（曖昧な期間重なり）検出 ──────────────────────
CREATE OR REPLACE VIEW lawtime.gate_succession_no_ambiguous_overlap AS
  SELECT a.succession_id AS succession_id_a, b.succession_id AS succession_id_b
  FROM lawtime.alo_law_succession_edge a
  JOIN lawtime.alo_law_succession_edge b
    ON a.law_work_id = b.law_work_id
   AND a.succession_id < b.succession_id
   AND a.relation_type <> 'unknown' AND b.relation_type <> 'unknown'
   AND a.confidence IN ('reviewed','confirmed')
   AND b.confidence IN ('reviewed','confirmed')
   AND (a.valid_from IS NULL OR b.valid_to IS NULL OR a.valid_from < b.valid_to)
   AND (b.valid_from IS NULL OR a.valid_to IS NULL OR b.valid_from < a.valid_to)
  WHERE a.law_id <> b.law_id
    AND (a.lineage_event_id IS DISTINCT FROM b.lineage_event_id
         OR a.lineage_event_id IS NULL);

-- ── N-1 (audit 2026-06-23). resolver fallback の非決定性を gate で潰す ───────
-- fn_resolve_law_reference_at は succession 不在のとき
--   `alo_statutes WHERE law_work_id = p_law_work_id LIMIT 1` で law_id を fallback する。
-- ORDER BY/一意制約が無いため、同一 law_work_id が複数 law_id を持つと非決定。
-- 監査推奨（option A: gate で潰す。LIMIT 1 互換は維持）に従い、succession で
-- 解決されない law_work が複数 law_id を持たないことを検査する。0 件が VALIDATE/apply 前提。
CREATE OR REPLACE VIEW lawtime.gate_law_work_single_fallback_law_id AS
  SELECT s.law_work_id
  FROM lawtime.alo_statutes s
  WHERE NOT EXISTS (
          SELECT 1 FROM lawtime.alo_law_succession_edge se
          WHERE se.law_work_id = s.law_work_id
            AND se.relation_type <> 'unknown' )
  GROUP BY s.law_work_id
  HAVING count(DISTINCT s.law_id) > 1;

-- ── N-2 (audit 2026-06-23). statute revision の as_of 区間重なり検出 ──────────
-- resolver tier2 は `ORDER BY valid_from DESC NULLS LAST LIMIT 1`。同一 law_id の
-- 版区間 [valid_from, valid_to) が重なると tier2 も非決定になる。半開区間の重なり判定
-- （af < bt AND bf < at、NULL は開区間）で同一 law_id の重複版を検出する。
CREATE OR REPLACE VIEW lawtime.gate_statute_revision_no_ambiguous_overlap AS
  SELECT a.law_revision_id AS revision_id_a, b.law_revision_id AS revision_id_b
  FROM lawtime.alo_statutes a
  JOIN lawtime.alo_statutes b
    ON a.law_id = b.law_id
   AND a.law_revision_id < b.law_revision_id
   AND (a.valid_from IS NULL OR b.valid_to IS NULL OR a.valid_from < b.valid_to)
   AND (b.valid_from IS NULL OR a.valid_to IS NULL OR b.valid_from < a.valid_to);

-- ── N-3/N-4 (audit 2026-06-23). formal status の状態整合検出 ──────────────────
-- v_lawtime_formal_status は CurrentEnforced 優先で集約するため、データ異常
-- （同一 law_id に CurrentEnforced 複数 / CurrentEnforced と Repeal 同居）を隠す。
-- 異常検知 gate を view とセットで持つ（監査 N-3/N-4）。0 件が production 前提。
CREATE OR REPLACE VIEW lawtime.gate_formal_status_inconsistent_revision_status AS
  SELECT s.law_id
  FROM lawtime.alo_statutes s
  GROUP BY s.law_id
  HAVING count(*) FILTER (WHERE s.revision_status = 'CurrentEnforced') > 1
      OR ( bool_or(s.revision_status = 'CurrentEnforced')
       AND bool_or(s.revision_status = 'Repeal') );

-- ── R-1. resolved lawtime views (DD-LAWSUBTRANS connection point) ───────────
CREATE OR REPLACE VIEW lawtime.v_lawtime_formal_status AS
  SELECT s.law_id,
         CASE
           WHEN bool_or(s.revision_status = 'CurrentEnforced') THEN 'in_force'
           WHEN bool_or(s.revision_status = 'Repeal')          THEN 'repealed'
           WHEN bool_or(s.revision_status = 'PreviousEnforced')THEN 'superseded'
           WHEN bool_or(s.revision_status = 'UnEnforced')      THEN 'not_yet_in_force'
           ELSE 'unknown'
         END AS formal_status,
         max(s.valid_from) FILTER (WHERE s.revision_status='CurrentEnforced') AS current_from
  FROM lawtime.alo_statutes s
  GROUP BY s.law_id;

CREATE OR REPLACE VIEW lawtime.v_lawtime_resolved_ref AS
  SELECT e.edge_id, e.cited_law_work_id, e.cited_law_id, e.as_of_basis, e.as_of_date,
         e.resolved_law_revision_id, e.temporal_status, e.temporal_caveat,
         (e.resolved_law_revision_id IS NOT NULL
          AND e.temporal_status IS NOT NULL
          AND e.temporal_status <> 'unchecked') AS lawtime_resolved
  FROM lawtime.alo_edges e
  WHERE e.edge_type IN ('cites_statute','statute_ref','applies_statute');
