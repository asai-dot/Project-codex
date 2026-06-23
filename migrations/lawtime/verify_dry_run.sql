-- DD-LAWTIME-001 v0.2.3a — dry-run verifier. Asserts all lawtime gates are empty.
-- backfill gate must be empty BEFORE VALIDATE (already enforced by apply order);
-- here we re-assert it plus the production gates P0-2/P0-3/P0-4 AND the audit
-- 2026-06-23 ambiguity/consistency gates (N-1/N-2/N-3/N-4). The latter three are
-- the explicit precondition for keeping fn_resolve_law_reference_at's LIMIT 1.
DO $$
DECLARE
  g text; n bigint; bad text := NULL;
  gates text[] := ARRAY[
    'gate_backfill_unknown_unchecked',
    'gate_resolved_revision_covers_asof',
    'gate_claim_support_requires_resolved_lawtime',
    'gate_succession_no_ambiguous_overlap',
    -- audit 2026-06-23 (N-1/N-2/N-3/N-4): resolver fallback / statute-version /
    -- formal-status の非決定性・状態不整合が 0 件であることを LIMIT 1 維持の
    -- 前提として明示 assert する。
    'gate_law_work_single_fallback_law_id',
    'gate_statute_revision_no_ambiguous_overlap',
    'gate_formal_status_inconsistent_revision_status'
  ];
BEGIN
  FOREACH g IN ARRAY gates LOOP
    EXECUTE format('SELECT count(*) FROM lawtime.%I', g) INTO n;
    RAISE NOTICE 'lawtime gate % => % row(s)', g, n;
    IF n <> 0 THEN bad := COALESCE(bad,'') || g || '(' || n || ') '; END IF;
  END LOOP;
  IF bad IS NOT NULL THEN
    RAISE EXCEPTION 'LAWTIME DRY-RUN FAILED — non-empty gates: %', bad;
  END IF;
  RAISE NOTICE 'ALL LAWTIME GATES EMPTY — dry-run PASS';
END $$;
