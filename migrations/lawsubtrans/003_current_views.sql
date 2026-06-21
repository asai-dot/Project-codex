-- DD-LAWSUBTRANS-001 v0.1.3 §3.7 — current-status views (P1)
-- 各 assertion の current_status / current_rank は、物理 status（T3/T4）を起点に
-- 最新 review-event(T6) を畳んだ値を正本とする。食い違いは review-event 優先。
-- T2 は物理 status を持たないため 'candidate' 起点。

BEGIN;

CREATE OR REPLACE VIEW v_subchg_current AS
SELECT a.*,
       COALESCE(r.new_status, 'candidate') AS current_status,
       COALESCE(r.new_rank,  a.rank)       AS current_rank
FROM alo_law_substantive_change_assertion a
LEFT JOIN LATERAL (
  SELECT e.new_status, e.new_rank FROM alo_law_assertion_review_event e
  WHERE e.assertion_kind = 'substantive_change' AND e.assertion_id = a.assertion_id
  ORDER BY e.decided_at DESC LIMIT 1
) r ON true;

CREATE OR REPLACE VIEW v_inttr_current AS
SELECT a.*,
       COALESCE(r.new_status, a.assertion_status) AS current_status,
       COALESCE(r.new_rank, 'normal')             AS current_rank
FROM alo_law_interpretation_transition a
LEFT JOIN LATERAL (
  SELECT e.new_status, e.new_rank FROM alo_law_assertion_review_event e
  WHERE e.assertion_kind = 'interpretation_transition' AND e.assertion_id = a.transition_id
  ORDER BY e.decided_at DESC LIMIT 1
) r ON true;

CREATE OR REPLACE VIEW v_survival_current AS
SELECT a.*,
       COALESCE(r.new_status, a.assertion_status) AS current_status,
       COALESCE(r.new_rank, 'normal')             AS current_rank
FROM alo_old_law_survival_assertion a
LEFT JOIN LATERAL (
  SELECT e.new_status, e.new_rank FROM alo_law_assertion_review_event e
  WHERE e.assertion_kind = 'old_law_survival' AND e.assertion_id = a.survival_id
  ORDER BY e.decided_at DESC LIMIT 1
) r ON true;

COMMIT;
