#!/usr/bin/env python3
"""
parse_cinii_detail.py — parse CiNii Research detail JSON (already harvested in Box
under 浅井/claude/cinii_batch/detail/) into column-ready scholar enrichment rows.

WHY: the scholar authority records (alo:person:scholar:kaken:<NRID>) were loaded
from the CiNii *identifier-trace* layer only — person_affiliation holds the
placeholder "CiNii scholar identifier anchor". The RICH content (real institution,
NDC research field, publications) is present in the harvested article JSONs but was
never parsed into columns. This script does that parse.

JOIN KEY (verified 2026-06-29):
  article.creator[].personIdentifier(@type=NRID).@value
    == authority.person_history.scholar_nrid
    == tail of authority.person.person_id  ('alo:person:scholar:kaken:<NRID>')

INPUT: a directory (or list) of CiNii Research detail JSON files (one article each),
       OR a JSONL with one article object per line.
OUTPUT (column-ready, candidate-level, no DB write):
  - person_affiliation_enriched.tsv   (person_id, organization_name, ...)
  - person_research_field.tsv         (person_id, ndc_code, ndc_label, count, ...)
  - parse_stats.json

Governance: produces local artifacts only. candidate ≠ confirmed. No DB write,
no DDL. Promotion is gated.
"""
import json, sys, os, re, argparse, glob, unicodedata
from collections import defaultdict, Counter

SOURCE_SYSTEM = "cinii_article_affiliation_v1"


# ── extraction ──────────────────────────────────────────────────────────────
def _vals(node, lang_pref=("ja", None, "en")):
    """Pull values from a JSON-LD list-of-{@language,@value} (or plain), lang-ordered."""
    if node is None:
        return []
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        node = [node]
    out = []
    for want in lang_pref:
        for x in node:
            if isinstance(x, dict) and x.get("@language") == want and x.get("@value"):
                out.append(x["@value"])
    # any remaining without language
    for x in node:
        if isinstance(x, dict) and x.get("@value") and x["@value"] not in out:
            out.append(x["@value"])
    return out


def _first(node, **kw):
    v = _vals(node, **kw)
    return v[0] if v else None


def _year(date_str):
    if not date_str:
        return None
    m = re.search(r"(\d{4})", str(date_str))
    return int(m.group(1)) if m else None


def extract_article(art):
    """Yield one record per (creator-with-NRID) in this article."""
    pub = art.get("publication") or {}
    pub_name = _first(pub.get("prism:publicationName"))
    publisher = _first(pub.get("dc:publisher"))
    pub_year = _year(pub.get("prism:publicationDate") or art.get("availableAt"))
    crid = art.get("@id")

    # NDC research field(s)
    ndc = []
    for s in (art.get("dcterms:subject") or []):
        if isinstance(s, dict) and (s.get("subjectScheme") == "NDC"):
            for n in s.get("notation", []):
                if isinstance(n, dict) and n.get("@value"):
                    ndc.append(n["@value"])
    for t in (art.get("foaf:topic") or []):
        if isinstance(t, dict) and t.get("dc:title") and re.match(r"^\d", str(t["dc:title"])):
            ndc.append(str(t["dc:title"]))
    ndc = sorted(set(ndc))

    for cr in (art.get("creator") or []):
        if not isinstance(cr, dict):
            continue
        nrid = None
        for pid in (cr.get("personIdentifier") or []):
            if isinstance(pid, dict) and pid.get("@type") == "NRID" and pid.get("@value"):
                nrid = str(pid["@value"])
                break
        if not nrid:
            continue
        name_ja = _first(cr.get("foaf:name"), lang_pref=("ja", None))
        name_en = _first(cr.get("foaf:name"), lang_pref=("en",))
        affil = _first(cr.get("jpcoar:affiliationName"), lang_pref=("ja", None, "en"))
        yield {
            "nrid": nrid,
            "name_ja": name_ja,
            "name_en": name_en,
            "affiliation": affil,
            "ndc": ndc,
            "pub_name": pub_name,
            "publisher": publisher,
            "pub_year": pub_year,
            "crid": crid,
        }


# ── normalization ───────────────────────────────────────────────────────────
_ORG_TYPE_HINTS = [
    (re.compile(r"大学|大学院|学院"), "university"),
    (re.compile(r"研究所|研究機構|センター|機関"), "research_institute"),
    (re.compile(r"省|庁|裁判所|地方公共団体"), "government"),
    (re.compile(r"株式会社|有限会社|法律事務所|特許事務所"), "private"),
]
_ROLE_HINTS = re.compile(r"(教授|准教授|助教|講師|博士課程|修士課程|研究員|名誉教授)")


def norm_org(s):
    if not s:
        return None
    return unicodedata.normalize("NFKC", s).strip()


def org_type(s):
    if not s:
        return "unknown"
    for pat, t in _ORG_TYPE_HINTS:
        if pat.search(s):
            return t
    return "other"


def role_from_affil(s):
    if not s:
        return None
    m = _ROLE_HINTS.search(s)
    return m.group(1) if m else None


# ── aggregation per NRID ─────────────────────────────────────────────────────
def aggregate(records):
    by_nrid = defaultdict(list)
    for r in records:
        by_nrid[r["nrid"]].append(r)

    affil_rows, field_rows = [], []
    for nrid, recs in by_nrid.items():
        person_id = f"alo:person:scholar:kaken:{nrid}"
        # affiliations: count + year range
        aff_stats = defaultdict(lambda: {"count": 0, "years": []})
        for r in recs:
            a = norm_org(r["affiliation"])
            if not a:
                continue
            aff_stats[a]["count"] += 1
            if r["pub_year"]:
                aff_stats[a]["years"].append(r["pub_year"])
        total_aff = sum(v["count"] for v in aff_stats.values()) or 1
        for org, st in sorted(aff_stats.items(), key=lambda kv: -kv[1]["count"]):
            yrs = st["years"]
            affil_rows.append({
                "person_id": person_id,
                "nrid": nrid,
                "organization_name": org,
                "organization_normalized": org,
                "organization_type": org_type(org),
                "role_title": role_from_affil(org),
                "start_year": min(yrs) if yrs else "",
                "end_year": max(yrs) if yrs else "",
                "evidence_count": st["count"],
                "evidence_strength": round(min(0.95, 0.4 + st["count"] / total_aff * 0.5), 3),
                "source_system": SOURCE_SYSTEM,
            })
        # research fields: NDC top-level (first 3 chars) frequency
        ndc_cnt = Counter()
        for r in recs:
            for code in r["ndc"]:
                ndc_cnt[code] += 1
        total_pub = len(recs) or 1
        for code, c in ndc_cnt.most_common():
            field_rows.append({
                "person_id": person_id,
                "nrid": nrid,
                "ndc_code": code,
                "ndc_top": str(code)[:3],
                "count": c,
                "share": round(c / total_pub, 3),
                "source_system": SOURCE_SYSTEM,
            })
    return affil_rows, field_rows


# ── io ───────────────────────────────────────────────────────────────────────
def iter_articles(path):
    if os.path.isdir(path):
        for fp in glob.glob(os.path.join(path, "**", "*.json"), recursive=True):
            try:
                yield json.load(open(fp, encoding="utf-8"))
            except Exception as e:
                print(f"skip {fp}: {e}", file=sys.stderr)
    elif path.endswith(".jsonl"):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except Exception as e:
                    print(f"skip line: {e}", file=sys.stderr)
    else:
        yield json.load(open(path, encoding="utf-8"))


def write_tsv(rows, path, fields):
    import csv
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="dir of detail JSONs, a .jsonl, or a single .json")
    ap.add_argument("--out-dir", default="artifacts")
    args = ap.parse_args()

    records, n_art = [], 0
    for art in iter_articles(args.input):
        n_art += 1
        records.extend(extract_article(art))

    affil_rows, field_rows = aggregate(records)
    n_nrid = len({r["nrid"] for r in records})

    write_tsv(affil_rows, os.path.join(args.out_dir, "person_affiliation_enriched.tsv"),
              ["person_id", "nrid", "organization_name", "organization_normalized",
               "organization_type", "role_title", "start_year", "end_year",
               "evidence_count", "evidence_strength", "source_system"])
    write_tsv(field_rows, os.path.join(args.out_dir, "person_research_field.tsv"),
              ["person_id", "nrid", "ndc_code", "ndc_top", "count", "share", "source_system"])

    stats = {"articles": n_art, "creator_records": len(records), "distinct_nrid": n_nrid,
             "affiliation_rows": len(affil_rows), "field_rows": len(field_rows)}
    json.dump(stats, open(os.path.join(args.out_dir, "parse_stats.json"), "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
