-- DD-LAWTIME-001 v0.2.3 — dry-run verifier. Asserts all lawtime gates are empty.
-- backfill gate must be empty BEFORE VALIDATE (already enforced by apply order);
-- here we re-assert it plus the production gates P0-2/P0-3/P0-4.
DO $$
DECLARE
  g text; n bigint; bad text := NULL;
  gates text[] := ARRAY[
    'gate_backfill_unknown_unchecked',
    'gate_resolved_revision_covers_asof',
    'gate_claim_support_requires_resolved_lawtime',
    'gate_succession_no_ambiguous_overlap'
  ];
BEGIN
  FOREACH g IN ARRAY gates LOOP
    EXECUTE format('SELECT count(*) FROM %I', g) INTO n;
    RAISE NOTICE 'lawtime gate % => % row(s)', g, n;
    IF n <> 0 THEN bad := COALESCE(bad,'') || g || '(' || n || ') '; END IF;
  END LOOP;
  IF bad IS NOT NULL THEN
    RAISE EXCEPTION 'LAWTIME DRY-RUN FAILED — non-empty gates: %', bad;
  END IF;
  RAISE NOTICE 'ALL LAWTIME GATES EMPTY — dry-run PASS';
END $$;
