-- DD-LAWSUBTRANS-001 v0.1.3 §4 — lawtime connection gates (P1, lawtime-dependent)
-- 由来: DD-LAWTIME v0.2.3 RESULT §6（P1 接続点で入れるべき gate）。
-- 依存: DD-LAWTIME v0.2.3 R-1 view（v_lawtime_formal_status / v_lawtime_resolved_ref）。
-- ★ lawtime v0.2.3 が branch apply されるまで本ファイルは HOLD（他 gate は先行可）。
-- 家風: 各 gate は「違反行を返す view」。CI / dry-run で 0件 を assert する。

BEGIN;

-- A) formal_status_mirror_consistent:
--    LAWSUBTRANS 側に formal_status 保存列（T4）を持つ以上、lawtime の単一窓口と一致すること。
--    superseding_revision_id → alo_statutes.law_id → v_lawtime_formal_status で突き合わせる。
--    （004_gates.sql の formal_status_consistent_with_lawtime と同趣旨。R-1 view 経由に統一）
CREATE OR REPLACE VIEW gate_formal_status_mirror_consistent AS
  SELECT s.survival_id
  FROM alo_old_law_survival_assertion s
  JOIN alo_statutes st ON st.law_revision_id = s.superseding_revision_id
  JOIN v_lawtime_formal_status f ON f.law_id = st.law_id
  WHERE s.formal_status <> f.formal_status;

-- B) lawtime_resolved_not_sufficient_for_claim_support:
--    claim_support_eligible=true は lawtime_resolved=true「だけ」では不可。
--    accepted ∧ disputed=false（counter 無し）∧ evidence あり を併せて要求する。
--    （lawtime_resolved を充分条件と誤読した行を検出。T2/T3/T4 横断）
CREATE OR REPLACE VIEW gate_lawtime_resolved_not_sufficient AS
  SELECT v.assertion_id AS id, 'substantive_change'::text AS kind
  FROM v_subchg_current v
  WHERE v.claim_support_eligible = true
    AND ( v.current_status <> 'accepted'
       OR v.counter_assertion_id IS NOT NULL
       OR v.evidence_pointer_id IS NULL )
  UNION ALL
  SELECT v.transition_id, 'interpretation_transition'
  FROM v_inttr_current v
  WHERE v.claim_support_eligible = true
    AND ( v.current_status <> 'accepted'
       OR v.counter_transition_id IS NOT NULL
       OR v.evidence_pointer_id IS NULL )
  UNION ALL
  SELECT v.survival_id, 'old_law_survival'
  FROM v_survival_current v
  WHERE v.claim_support_eligible = true
    AND ( v.current_status <> 'accepted'
       OR v.counter_survival_id IS NOT NULL
       OR v.evidence_pointer_id IS NULL );

-- C) unknown_or_unchecked_blocked:
--    lawtime_resolved=false または temporal_status='unchecked' の参照に紐づく
--    claim_support_eligible=true を禁止（MCP evidence 出口に出さない）。
--    結合キーは ingest 確定（P2）まで law_work_id 近似。確定後に edge 単位へ精緻化。
CREATE OR REPLACE VIEW gate_unknown_or_unchecked_blocked AS
  SELECT v.assertion_id
  FROM v_subchg_current v
  WHERE v.claim_support_eligible = true
    AND NOT EXISTS (
      SELECT 1 FROM v_lawtime_resolved_ref lr
      WHERE lr.cited_law_work_id = v.law_work_id
        AND lr.lawtime_resolved = true
        AND lr.temporal_status <> 'unchecked' );

COMMIT;
