# scholar_enrich — parse harvested CiNii data into columns

## Problem this fixes
`authority.person` scholar rows (`alo:person:scholar:kaken:<NRID>`, 73,155) were
loaded from the CiNii **identifier-trace** layer only. `person_affiliation` holds
the placeholder `"CiNii scholar identifier anchor"` for every scholar — real
institution and research field were never parsed into columns, even though the
rich article data was already harvested.

## The rich data IS already harvested (no external fetch needed)
Box: `浅井/claude/cinii_batch/` (~3.14 GB)
- `detail/` — one CiNii Research JSON-LD per article. Each carries
  `creator[].personIdentifier(NRID)`, `creator[].jpcoar:affiliationName`
  (real institution), `dcterms:subject`/`foaf:topic` (NDC research field),
  `publication` (name / publisher / date).
- `opensearch/` — search-result pages (researcher/ISSN → crid lists).

## Join key (verified 2026-06-29)
```
article.creator[].personIdentifier(@type=NRID).@value
  == authority.person_history.scholar_nrid
  == tail of authority.person.person_id   (alo:person:scholar:kaken:<NRID>)
```

## What the parser produces (column-ready, candidate-level)
`parse_cinii_detail.py <input> --out-dir artifacts/`
- `person_affiliation_enriched.tsv` → maps to `authority.person_affiliation`:
  person_id, organization_name/normalized, organization_type (大学→university…),
  role_title (教授/博士課程…), start_year/end_year (from pub dates),
  evidence_count, evidence_strength, source_system=`cinii_article_affiliation_v1`
- `person_research_field.tsv` → NDC code + top-3 + count + share per person
- `parse_stats.json`

`<input>` = a directory of detail JSONs, a `.jsonl`, or a single `.json`.

Validated on a real detail record (NRID 9000293532889, 松田和憲):
→ 京都大学大学院アジア・アフリカ地域研究研究科博士課程 / university / 博士課程 /
  2015 / NDC 302.27. Correct.

## Where to run the bulk pass
The detail corpus (~3 GB, hundreds of thousands of files) is in Box, locally
synced on the harvest machine. Run the parser there (or stream detail/ down)
— per-file fetch through the MCP layer is not practical at that scale.

## Why this is the first move (初手)
1. Restores the degraded scholar columns (institution, field).
2. Supplies the disambiguation signal (NRID + institution + NDC field) that lets
   the same-name scholar clusters be deduped safely — including the 5,126
   researchmap-less rows — without 同姓同名 over-merge.

## Governance
Local artifacts only. candidate ≠ confirmed. No DB write, no DDL, no egress
(Box-internal data already harvested). Promotion gated.
