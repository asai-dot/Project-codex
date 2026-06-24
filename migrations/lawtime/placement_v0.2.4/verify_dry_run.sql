-- DD-LAWTIME-001 v0.2.4 (placement / C-option) — dry-run verifier.
-- Asserts every lawtime gate view is EMPTY. House-style names, schema-qualified.
-- Gates: 2 C-option integration + P0-2/P0-3/P0-4 + N-1/N-2/N-3/N-4 = 8.
DO $$
DECLARE
  g text; n bigint; bad text := NULL;
  gates text[] := ARRAY[
    'v_gate_lawtime_citation_edge_missing_side_table_v20260624',
    'v_gate_lawtime_side_table_orphan_or_noncitation_v20260624',
    'v_gate_lawtime_resolved_revision_covers_asof_v20260624',
    'v_gate_lawtime_claim_support_requires_resolved_v20260624',
    'v_gate_lawtime_succession_no_ambiguous_overlap_v20260624',
    'v_gate_lawtime_work_single_fallback_law_id_v20260624',
    'v_gate_lawtime_statute_revision_no_ambiguous_overlap_v20260624',
    'v_gate_lawtime_formal_status_inconsistent_v20260624'
  ];
BEGIN
  FOREACH g IN ARRAY gates LOOP
    EXECUTE format('SELECT count(*) FROM lawtime.%I', g) INTO n;
    RAISE NOTICE 'lawtime gate % => % row(s)', g, n;
    IF n <> 0 THEN bad := COALESCE(bad,'') || g || '(' || n || ') '; END IF;
  END LOOP;
  IF bad IS NOT NULL THEN
    RAISE EXCEPTION 'LAWTIME v0.2.4 DRY-RUN FAILED — non-empty gates: %', bad;
  END IF;
  RAISE NOTICE 'ALL LAWTIME v0.2.4 GATES EMPTY — dry-run PASS';
END $$;
