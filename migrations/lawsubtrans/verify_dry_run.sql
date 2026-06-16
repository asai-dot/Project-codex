-- DD-LAWSUBTRANS-001 — branch dry-run verifier (P1)
-- 使い方: 法令レイヤ実体化済みの Supabase branch で 001→005 を apply し、合成/実データ投入後、
--         本スクリプトを実行する。いずれかの gate に違反行があれば EXCEPTION で停止する。
-- ★ 空のローカル DB で「通った」は偽陽性（base テーブル・既存行が無い）。検証は branch で行う。
-- 出力: 全 gate 0件なら NOTICE 'ALL GATES EMPTY'。違反があれば最初の違反 gate で停止。

DO $$
DECLARE
  g   text;
  n   bigint;
  bad text := NULL;
  -- 004 + 005 の全 gate view（lawtime 依存は lawtime apply 後のみ通る）
  gates text[] := ARRAY[
    -- 004_gates.sql
    'gate_amendment_not_auto_substantive',
    'gate_substantive_requires_evidence',
    'gate_disputed_blocks_claim',
    'gate_claim_support_requires_accepted',
    'gate_accepted_requires_review_event',
    'gate_evidence_locator_complete',
    'gate_drafter_intent_not_sole_truth',
    'gate_old_law_survival_three_axis',
    'gate_formal_status_consistent_with_lawtime',
    'gate_no_substantive_without_resolved_lawtime',
    'gate_assertion_append_only_enforced',
    'gate_rank_reason_present',
    'gate_claim_support_consistent_with_view',
    -- 005_lawtime_connection_gates.sql
    'gate_formal_status_mirror_consistent',
    'gate_lawtime_resolved_not_sufficient',
    'gate_unknown_or_unchecked_blocked'
  ];
BEGIN
  FOREACH g IN ARRAY gates LOOP
    EXECUTE format('SELECT count(*) FROM %I', g) INTO n;
    RAISE NOTICE 'gate % => % row(s)', g, n;
    IF n <> 0 THEN
      bad := COALESCE(bad, '') || g || '(' || n || ') ';
    END IF;
  END LOOP;

  IF bad IS NOT NULL THEN
    RAISE EXCEPTION 'DRY-RUN FAILED — non-empty gates: %', bad;
  END IF;
  RAISE NOTICE 'ALL GATES EMPTY — dry-run PASS (record this in the audit REQUEST)';
END $$;
