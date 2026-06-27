-- DD-LAWTIME-001 v0.2.4 — FIXED sample resolver results (audit should_fix #3).
-- Deterministic golden output over seed_clean.sql, so a materialize dry-run can
-- DIFF resolver behavior (not just gate counts). Sorted for stable ordering.
\echo '--- sample resolver: fn_resolve_law_reference_at(work_uri, as_of) ---'
SELECT q.work_uri, q.as_of::text AS as_of,
       COALESCE(lawtime.fn_resolve_law_reference_at(q.work_uri, q.as_of), '<null>') AS resolved_revision_uri
FROM (VALUES
   ('alo:law:jp:minpo'::text,   '1900-01-01'::date),  -- expect ...minpo:1898
   ('alo:law:jp:minpo',         '2019-12-31'),         -- expect ...minpo:1898
   ('alo:law:jp:minpo',         '2020-04-01'),         -- expect ...minpo:2020 (half-open)
   ('alo:law:jp:minpo',         '2025-01-01'),         -- expect ...minpo:2020
   ('alo:law:jp:shotaku',       '2000-01-01'),         -- expect ...shotaku:1991
   ('alo:law:jp:shotaku',       '1990-01-01')          -- expect <null> (before enforcement)
) AS q(work_uri, as_of)
ORDER BY q.work_uri, q.as_of;
