-- DD-LAWSUBTRANS-001 v0.1.3 — append-only enforcement (P1)
-- T1–T4,T6 の content は不変。status/rank の変更は T6 への INSERT で表現し、
-- 現在値は 003_current_views.sql の view で解決する（lawtime eval_event と同思想）。

BEGIN;

CREATE OR REPLACE FUNCTION trg_subtrans_append_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION
    '% is append-only (content immutable); record lifecycle via alo_law_assertion_review_event',
    TG_TABLE_NAME;
END; $$;

CREATE TRIGGER delta_append_only       BEFORE UPDATE OR DELETE ON alo_law_textual_delta
  FOR EACH ROW EXECUTE FUNCTION trg_subtrans_append_only();
CREATE TRIGGER subchg_append_only      BEFORE UPDATE OR DELETE ON alo_law_substantive_change_assertion
  FOR EACH ROW EXECUTE FUNCTION trg_subtrans_append_only();
CREATE TRIGGER inttr_append_only       BEFORE UPDATE OR DELETE ON alo_law_interpretation_transition
  FOR EACH ROW EXECUTE FUNCTION trg_subtrans_append_only();
CREATE TRIGGER surv_append_only        BEFORE UPDATE OR DELETE ON alo_old_law_survival_assertion
  FOR EACH ROW EXECUTE FUNCTION trg_subtrans_append_only();
CREATE TRIGGER review_append_only      BEFORE UPDATE OR DELETE ON alo_law_assertion_review_event
  FOR EACH ROW EXECUTE FUNCTION trg_subtrans_append_only();
-- 注: evidence(T5) は再現性ポインタであり、candidate 段階の補正を許すため append-only 対象外。
--     ただし production ingest は dedup_key 主導の冪等 UPSERT とする（P2 で規定）。

COMMIT;
