#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
transform_books_to_bib_records.py — 蔵書 books.json → biblio.bib_records 投入成果物

書誌軸の第一歩。NDL正本enrich済の蔵書(books.json 6,537冊)を、実測した biblio.bib_records スキーマへ
マッピングし、(1) staging jsonl と (2) ガバナンス付き投入SQL を生成する。これで §8 の橋 biblio.bib_terms
（書誌↔語彙：巻末索引/事項索引 → biblio.terms）を張る土台ができる。

biblio.bib_records 実列（2026-06-03 実測）:
  bib_id(PK,NOT NULL) title(NOT NULL) title_yomi subtitle responsibility edition publisher pub_place
  pub_year(int) series volume physical isbn issn ncid ndl_bib_id ndc ndlc language note
  source(NOT NULL) raw(jsonb) form_type  [imported_at/updated_at は default]

books.json のキー名は版で揺れるため**フォールバック付きゲッタ**で吸収し、未マップキーは stderr に報告
（measure-then-build）。source='asai-bookshelf'。bib_id は ISBN→NDL bib_id→slug の優先で決定（NOT NULL保証）。
生データ非改変・冪等(ON CONFLICT)・可逆(source で DELETE)。

使い方（books.json がある手元で）:
  python3 transform_books_to_bib_records.py /path/to/books.json
  → data/db_staging/bib_records_bookshelf_v1.jsonl / .sql を出力
  投入: psql "$SUPABASE_DB_URL" -f data/db_staging/bib_records_bookshelf_v1.sql
"""
import json
import os
import re
import sys
import hashlib
from collections import Counter

SOURCE = "asai-bookshelf"
KNOWN = {  # bib_records列 → books.json候補キー（先頭優先）
    "title": ["title", "ndl_title", "title_main"],
    "title_yomi": ["title_yomi", "ndl_title_yomi", "yomi"],
    "subtitle": ["subtitle", "title_sub"],
    "responsibility": ["responsibility", "creators", "authors", "author", "creator"],
    "edition": ["edition", "edition_statement"],
    "publisher": ["publisher", "ndl_publisher"],
    "pub_place": ["pub_place", "publication_place", "place"],
    "pub_year": ["pub_year", "publication_year", "year"],
    "series": ["series", "series_title"],
    "volume": ["volume", "vol"],
    "physical": ["physical", "pages", "ndl_pages", "extent"],
    "isbn": ["isbn", "isbn13", "ISBN"],
    "issn": ["issn", "ISSN"],
    "ncid": ["ncid", "NCID"],
    "ndl_bib_id": ["ndl_bib_id", "ndlBibID", "ndl_bibid"],
    "ndc": ["ndc", "ndc10", "ndc9", "NDC"],
    "ndlc": ["ndlc", "NDLC"],
    "language": ["language", "lang"],
    "note": ["note", "notes", "remarks"],
    "form_type": ["form_type", "media_type", "material_type"],
}
_PUB_DATE = ["publication_date", "date", "pub_date", "ndl_date"]


def first(rec, keys):
    for k in keys:
        if k in rec and rec[k] not in (None, "", [], {}):
            return rec[k]
    return None


def as_text(v):
    if isinstance(v, list):
        return "・".join(as_text(x) for x in v if x)
    if isinstance(v, dict):
        return v.get("name") or v.get("text") or json.dumps(v, ensure_ascii=False)
    return str(v) if v is not None else None


def year_of(rec):
    y = first(rec, ["pub_year", "publication_year", "year"])
    if isinstance(y, int):
        return y
    s = as_text(first(rec, _PUB_DATE) or y)
    m = re.search(r"(\d{4})", s or "")
    return int(m.group(1)) if m else None


def make_bib_id(rec):
    isbn = as_text(first(rec, KNOWN["isbn"]))
    if isbn:
        return "ISBN_" + re.sub(r"[^0-9Xx]", "", isbn)
    ndl = as_text(first(rec, KNOWN["ndl_bib_id"]))
    if ndl:
        return "NDLBIB_" + ndl
    title = as_text(first(rec, KNOWN["title"])) or ""
    return "BOOK_" + hashlib.sha1(title.encode("utf-8")).hexdigest()[:12]


def transform(rec):
    title = as_text(first(rec, KNOWN["title"]))
    if not title:
        return None  # NOT NULL: titleなしは投入不可（quarantine相当）
    row = {"bib_id": make_bib_id(rec), "title": title, "source": SOURCE, "raw": rec}
    for col in ("title_yomi", "subtitle", "responsibility", "edition", "publisher",
                "pub_place", "series", "volume", "physical", "isbn", "issn",
                "ncid", "ndl_bib_id", "ndc", "ndlc", "language", "note", "form_type"):
        row[col] = as_text(first(rec, KNOWN[col]))
    row["pub_year"] = year_of(rec)
    return row


def load_books(path):
    txt = open(path, encoding="utf-8").read().strip()
    if txt[:1] == "[":
        return json.loads(txt)
    if txt[:1] == "{":
        o = json.loads(txt)
        for k in ("books", "records", "items", "data"):
            if isinstance(o.get(k), list):
                return o[k]
        return list(o.values()) if all(isinstance(v, dict) for v in o.values()) else [o]
    return [json.loads(l) for l in txt.splitlines() if l.strip()[:1] == "{"]


def main(argv=None):
    args = argv or sys.argv[1:]
    if not args:
        sys.exit("usage: transform_books_to_bib_records.py /path/to/books.json")
    books = load_books(args[0])
    os.makedirs("data/db_staging", exist_ok=True)
    rows, skipped, seen_keys = [], 0, Counter()
    seen_id = set()
    for rec in books:
        if not isinstance(rec, dict):
            continue
        for k in rec:
            seen_keys[k] += 1
        r = transform(rec)
        if not r or r["bib_id"] in seen_id:
            skipped += 1
            continue
        seen_id.add(r["bib_id"])
        rows.append(r)
    with open("data/db_staging/bib_records_bookshelf_v1.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    cols = ["bib_id", "title", "title_yomi", "subtitle", "responsibility", "edition", "publisher",
            "pub_place", "pub_year", "series", "volume", "physical", "isbn", "issn", "ncid",
            "ndl_bib_id", "ndc", "ndlc", "language", "note", "source", "form_type", "raw"]
    arr = json.dumps([{c: r.get(c) for c in cols} for r in rows], ensure_ascii=False, separators=(",", ":"))
    sql = f"""-- biblio.bib_records load: 蔵書(books.json) → {len(rows)}件  source='{SOURCE}'
-- idempotent (ON CONFLICT), reversible: DELETE FROM biblio.bib_records WHERE source='{SOURCE}';
-- governance: register control.source_snapshots/ingest_jobs/releases(approval pending) per codex convention.
BEGIN;
INSERT INTO control.source_snapshots (source_snapshot_id, source_system, snapshot_kind, snapshot_label, storage_system, artifact_path, row_count, metadata_json)
VALUES ('snapshot:asai-bookshelf:books-json','asai-bookshelf','normalized_export','蔵書 books.json NDL-enriched','box','浅井/.../data/books.json',{len(rows)},'{{"producer":"transform_books_to_bib_records.py"}}')
ON CONFLICT (source_snapshot_id) DO NOTHING;
INSERT INTO control.ingest_jobs (ingest_job_id, job_kind, target_schema, target_table, source_snapshot_id, status, triggered_by, rows_expected, metadata_json)
VALUES ('ingest:biblio:bookshelf:'||to_char(now(),'YYYYMMDD'),'append_import','biblio','bib_records','snapshot:asai-bookshelf:books-json','running','owner',{len(rows)},'{{}}')
ON CONFLICT (ingest_job_id) DO NOTHING;
INSERT INTO biblio.bib_records (bib_id,title,title_yomi,subtitle,responsibility,edition,publisher,pub_place,pub_year,series,volume,physical,isbn,issn,ncid,ndl_bib_id,ndc,ndlc,language,note,source,raw,form_type,imported_at,updated_at)
SELECT x.bib_id,x.title,x.title_yomi,x.subtitle,x.responsibility,x.edition,x.publisher,x.pub_place,x.pub_year,x.series,x.volume,x.physical,x.isbn,x.issn,x.ncid,x.ndl_bib_id,x.ndc,x.ndlc,x.language,x.note,'{SOURCE}',x.raw,x.form_type,now(),now()
FROM jsonb_to_recordset($j${arr}$j$::jsonb)
  AS x(bib_id text,title text,title_yomi text,subtitle text,responsibility text,edition text,publisher text,pub_place text,pub_year int,series text,volume text,physical text,isbn text,issn text,ncid text,ndl_bib_id text,ndc text,ndlc text,language text,note text,form_type text,raw jsonb)
ON CONFLICT (bib_id) DO NOTHING;
COMMIT;
SELECT count(*) AS bib_loaded FROM biblio.bib_records WHERE source='{SOURCE}';
"""
    open("data/db_staging/bib_records_bookshelf_v1.sql", "w", encoding="utf-8").write(sql)

    print(f"=== transform_books_to_bib_records ===", file=sys.stderr)
    print(f"books {len(books)} → bib_records {len(rows)} (skipped {skipped}: no-title/dup-id)", file=sys.stderr)
    print(f"with isbn: {sum(1 for r in rows if r['isbn'])} / ndl_bib_id: {sum(1 for r in rows if r['ndl_bib_id'])}", file=sys.stderr)
    mapped = {kk for v in KNOWN.values() for kk in v} | set(_PUB_DATE)
    unmapped = [(k, n) for k, n in seen_keys.most_common() if k not in mapped]
    print(f"未マップの books.json キー（raw に保持。必要なら KNOWN に追加）: {unmapped[:20]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
