-- DD-LAWSUBTRANS-001 v0.1.3 §4 — quality gates as violation-views (P1)
-- 家風: 各 gate は「違反行を返す view」。CI / branch dry-run で「空である」を assert する。
-- lawtime 依存 gate は DD-LAWTIME v0.2.3 R-1 view（v_lawtime_formal_status /
-- v_lawtime_resolved_ref）を参照する。lawtime ratify 前は当該 gate のみ HOLD。

BEGIN;

-- 1) amendment_not_auto_substantive:
--    textual_delta のみを根拠（delta 検出器）に substantive_change が candidate 超に上がらない。
--    実装: T2 が related_delta_id を持ちつつ asserted_by_source_type が実在の解釈源でなく、
--    かつ current_status が candidate を超える行を違反とする。検出器は source 値域に無いので、
--    「delta 由来のみ＝evidence_pointer_id 無し かつ status>candidate」を違反として捕捉する。
CREATE OR REPLACE VIEW gate_amendment_not_auto_substantive AS
  SELECT v.assertion_id
  FROM v_subchg_current v
  WHERE v.related_delta_id IS NOT NULL
    AND v.evidence_pointer_id IS NULL
    AND v.current_status IN ('reviewed','accepted');

-- 2) substantive_requires_evidence:
CREATE OR REPLACE VIEW gate_substantive_requires_evidence AS
  SELECT assertion_id FROM v_subchg_current
  WHERE current_status IN ('reviewed','accepted') AND evidence_pointer_id IS NULL;

-- 3) disputed_blocks_claim: counter があれば claim_support 不可 かつ status=disputed
CREATE OR REPLACE VIEW gate_disputed_blocks_claim AS
  SELECT assertion_id FROM v_subchg_current
  WHERE counter_assertion_id IS NOT NULL
    AND (claim_support_eligible = true OR current_status <> 'disputed')
  UNION ALL
  SELECT transition_id FROM v_inttr_current
  WHERE counter_transition_id IS NOT NULL
    AND (claim_support_eligible = true OR current_status <> 'disputed')
  UNION ALL
  SELECT survival_id FROM v_survival_current
  WHERE counter_survival_id IS NOT NULL
    AND (claim_support_eligible = true OR current_status <> 'disputed');

-- 4) claim_support_requires_accepted:
--    claim_support=true ⇒ accepted ∧ disputed=false ∧ evidence>=1 ∧ counter 無し ∧ lawtime_resolved
--    （evidence_count: 当面 evidence_pointer_id IS NOT NULL を 1 とみなす — Note B）
CREATE OR REPLACE VIEW gate_claim_support_requires_accepted AS
  SELECT v.assertion_id
  FROM v_subchg_current v
  LEFT JOIN v_lawtime_resolved_ref lr
    ON lr.cited_law_work_id = v.law_work_id          -- work 単位の解決確認（近似）
  WHERE v.claim_support_eligible = true
    AND ( v.current_status <> 'accepted'
       OR v.counter_assertion_id IS NOT NULL
       OR v.evidence_pointer_id IS NULL
       OR COALESCE(lr.lawtime_resolved, false) = false );

-- 5) accepted_requires_review_event: accepted は review_basis 非空の T6 event を要する
CREATE OR REPLACE VIEW gate_accepted_requires_review_event AS
  SELECT v.assertion_id AS id, 'substantive_change'::text AS kind
  FROM v_subchg_current v
  WHERE v.current_status = 'accepted'
    AND NOT EXISTS (SELECT 1 FROM alo_law_assertion_review_event e
                    WHERE e.assertion_kind='substantive_change' AND e.assertion_id=v.assertion_id
                      AND e.new_status='accepted' AND e.review_basis <> '')
  UNION ALL
  SELECT v.transition_id, 'interpretation_transition'
  FROM v_inttr_current v
  WHERE v.current_status = 'accepted'
    AND NOT EXISTS (SELECT 1 FROM alo_law_assertion_review_event e
                    WHERE e.assertion_kind='interpretation_transition' AND e.assertion_id=v.transition_id
                      AND e.new_status='accepted' AND e.review_basis <> '')
  UNION ALL
  SELECT v.survival_id, 'old_law_survival'
  FROM v_survival_current v
  WHERE v.current_status = 'accepted'
    AND NOT EXISTS (SELECT 1 FROM alo_law_assertion_review_event e
                    WHERE e.assertion_kind='old_law_survival' AND e.assertion_id=v.survival_id
                      AND e.new_status='accepted' AND e.review_basis <> '');

-- 6) evidence_locator_complete: reviewed/accepted/claim_support 対象の evidence は
--    locator 系列を完備する（Note A: 一律 NOT NULL でなく対象限定）。T2/T3/T4 横断。
CREATE OR REPLACE VIEW gate_evidence_locator_complete AS
  WITH targets AS (
    SELECT evidence_pointer_id FROM v_subchg_current
      WHERE current_status IN ('reviewed','accepted') OR claim_support_eligible = true
    UNION
    SELECT evidence_pointer_id FROM v_inttr_current
      WHERE current_status IN ('reviewed','accepted') OR claim_support_eligible = true
    UNION
    SELECT evidence_pointer_id FROM v_survival_current
      WHERE current_status IN ('reviewed','accepted') OR claim_support_eligible = true
  )
  SELECT e.evidence_pointer_id
  FROM alo_law_interpretive_evidence e
  JOIN targets t ON t.evidence_pointer_id = e.evidence_pointer_id
  WHERE e.source_uri IS NULL OR e.source_type IS NULL OR e.source_tier IS NULL
     OR e.locator IS NULL OR e.source_span_hash IS NULL
     OR e.retrieved_at IS NULL OR e.parser_version IS NULL;

-- 7) drafter_intent_not_sole_truth:
--    tier2(立案担当者) 単独の継続主張(no_substantive_change)に tier3(court) の変化主張があれば
--    accepted 不可（disputed 強制）。同一 (law_work_id, article_path root) で評価。
CREATE OR REPLACE VIEW gate_drafter_intent_not_sole_truth AS
  SELECT d.assertion_id
  FROM v_subchg_current d
  WHERE d.source_tier = 2
    AND d.change_type = 'no_substantive_change'
    AND d.current_status = 'accepted'
    AND EXISTS (
      SELECT 1 FROM v_inttr_current c
      WHERE c.law_work_id = d.law_work_id
        AND split_part(COALESCE(c.article_path,''), ':para:', 1)
            = split_part(d.article_path, ':para:', 1)
        AND c.source_tier = 3
        AND c.transition_type IN ('interpretation_discontinued','interpretation_modified')
    );

-- 8) old_law_survival_three_axis: formal_status・substantive_status・非空 applicability_scope
CREATE OR REPLACE VIEW gate_old_law_survival_three_axis AS
  SELECT survival_id FROM alo_old_law_survival_assertion
  WHERE formal_status IS NULL OR substantive_status IS NULL
     OR applicability_scope IS NULL OR cardinality(applicability_scope) = 0;

-- 9) formal_status_consistent_with_lawtime: survival.formal_status は lawtime view と一致
--    (article_path から law_id を引けるのは ingest 時。ここでは superseding_revision_id 経由で
--     law_id を解決し v_lawtime_formal_status と突き合わせる近似実装。production で精緻化)
CREATE OR REPLACE VIEW gate_formal_status_consistent_with_lawtime AS
  SELECT s.survival_id
  FROM alo_old_law_survival_assertion s
  JOIN alo_statutes st ON st.law_revision_id = s.superseding_revision_id
  JOIN v_lawtime_formal_status f ON f.law_id = st.law_id
  WHERE s.formal_status <> f.formal_status;

-- 10) no_substantive_without_resolved_lawtime:
--     from/to/superseding revision が lawtime(alo_statutes) で解決可能
CREATE OR REPLACE VIEW gate_no_substantive_without_resolved_lawtime AS
  SELECT a.assertion_id
  FROM alo_law_substantive_change_assertion a
  WHERE (a.from_law_revision_id IS NOT NULL
         AND NOT EXISTS (SELECT 1 FROM alo_statutes s WHERE s.law_revision_id = a.from_law_revision_id))
     OR (a.to_law_revision_id IS NOT NULL
         AND NOT EXISTS (SELECT 1 FROM alo_statutes s WHERE s.law_revision_id = a.to_law_revision_id));

-- 11) assertion_append_only_enforced: トリガ存在を確認（メタ検査）
CREATE OR REPLACE VIEW gate_assertion_append_only_enforced AS
  SELECT t.tbl
  FROM (VALUES ('alo_law_textual_delta'),('alo_law_substantive_change_assertion'),
               ('alo_law_interpretation_transition'),('alo_old_law_survival_assertion'),
               ('alo_law_assertion_review_event')) AS t(tbl)
  WHERE NOT EXISTS (
    SELECT 1 FROM pg_trigger g JOIN pg_class c ON c.oid = g.tgrelid
    WHERE c.relname = t.tbl AND NOT g.tgisinternal);

-- 12) rank_reason_present: rank<>'normal' は rank_reason 必須（T2）
CREATE OR REPLACE VIEW gate_rank_reason_present AS
  SELECT assertion_id FROM alo_law_substantive_change_assertion
  WHERE rank <> 'normal' AND rank_reason IS NULL;

-- 13) claim_support_consistent_with_view: 物理 claim_support_eligible=true が gate4 条件を満たす
--     （保持列 drift 検出。Note C・T2/T3/T4 全系統）。実体は gate4 の和集合で表現。
CREATE OR REPLACE VIEW gate_claim_support_consistent_with_view AS
  SELECT id, kind FROM (
    SELECT assertion_id AS id, 'substantive_change'::text AS kind FROM gate_claim_support_requires_accepted
  ) s;
-- 注: T3/T4 にも claim_support 物理列があるため、production では gate4 を T3/T4 へ拡張した
--     UNION を本 view に統合する（lawtime_resolved 突き合わせの結合キー確定後）。

COMMIT;
