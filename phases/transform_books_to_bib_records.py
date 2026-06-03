#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
transform_books_to_bib_records.py — 蔵書 books.json → biblio.bib_records 投入成果物

書誌軸の第一歩。NDL正本enrich済の蔵書(books.json 6,537冊)を、実測した biblio.bib_records スキーマへ
マッピング。実データのキーに整合（2026-06-03 実物確認）。

設計判断（measure後）:
  - 蔵書は **source='asai-bookshelf'** で隔離投入（既存 codex の bencom-library 行〔bib_id=NOBN_*〕に触れない）。
  - bib_id = **alo_uri**（"alo:book:isbn:{ISBN}"。蔵書が既に持つALO URI）。NOBN_ と名前空間が違い衝突しない。
  - bencom 書誌(NOBN_)との名寄せ/dedup は後日 owner/codex が fingerprints 等で実施（raw に bencomId を保持）。
  - §8 の橋(bib_terms)は、本投入後に 巻末索引/ndl_subjects/genre → biblio.terms で張る（別ステップ）。

出力: data/db_staging/bib_records_bookshelf_v1.jsonl（フル）/ .sql（compact raw・冪等・可逆）。
冪等 ON CONFLICT / 可逆 DELETE FROM biblio.bib_records WHERE source='asai-bookshelf'。生データ非改変。

使い方（books.json がある手元で）:
  python3 phases/transform_books_to_bib_records.py \
    "/Users/yuta/Library/CloudStorage/Box-Box/浅井/claude/事務所内本棚DX化計画/app/data/books.json"
"""
import json
import os
import re
import sys
import hashlib
from collections import Counter

SOURCE = "asai-bookshelf"

# bib_records列 → books.json実キー（先頭優先・実物確認済）
MAP = {
    "title": ["title"],
    "title_yomi": ["ndl_title_yomi"],
    "subtitle": ["subtitle"],
    "responsibility": ["author"],
    "edition": ["edition"],
    "publisher": ["publisher"],
    "pub_place": ["ndl_publication_place"],
    "physical": ["ndl_pages", "ndl_extent_raw"],
    "isbn": ["isbn"],
    "ndl_bib_id": ["ndl_bib_id"],
    "ndc": ["ndc10", "ndc", "ndc9"],
    "ndlc": ["ndl_ndlc"],
    "note": ["abstract"],
    "form_type": ["lit_type", "mediaType"],
}
# raw に残す重要キー（abstract/searchText/revision_history 等の大物は除いてペースト可能に）
RAW_KEEP = ["isbn", "alo_uri", "lit_id", "bencomId", "ndl_bib_id", "ndl_jpno", "ndc10", "ndl_ndlc",
            "ndl_title_yomi", "ndl_creators_yomi", "ndl_subjects", "ndl_issued", "status", "storage",
            "field_provenance", "genre", "genre_sub", "hasToc", "hasCover", "lit_type",
            "data_completeness", "shelfLabel", "mediaType", "date"]


def first(rec, keys):
    for k in keys:
        v = rec.get(k)
        if v not in (None, "", [], {}):
            return v
    return None


def as_text(v):
    if isinstance(v, list):
        return "・".join(as_text(x) for x in v if x)
    if isinstance(v, dict):
        return v.get("name") or v.get("text") or json.dumps(v, ensure_ascii=False)
    return str(v) if v is not None else None


def year_of(rec):
    s = as_text(first(rec, ["date", "ndl_issued"])) or ""
    m = re.search(r"(1[89]\d\d|20\d\d)", s)
    return int(m.group(1)) if m else None


def bib_id_of(rec):
    u = rec.get("alo_uri") or rec.get("lit_id")
    if u:
        return u
    isbn = as_text(rec.get("isbn"))
    if isbn:
        return "alo:book:isbn:" + re.sub(r"[^0-9Xx]", "", isbn)
    return "BOOK_" + hashlib.sha1((as_text(rec.get("title")) or "").encode("utf-8")).hexdigest()[:12]


def transform(rec):
    title = as_text(first(rec, MAP["title"]))
    if not title:
        return None
    row = {"bib_id": bib_id_of(rec), "title": title, "source": SOURCE}
    for col, keys in MAP.items():
        if col == "title":
            continue
        row[col] = as_text(first(rec, keys))
    row["pub_year"] = year_of(rec)
    for col in ("series", "volume", "issn", "ncid", "language"):
        row[col] = "ja" if col == "language" else None
    row["raw_full"] = rec
    row["raw_compact"] = {k: rec[k] for k in RAW_KEEP if k in rec and rec[k] not in (None, "", [], {})}
    return row


def main(argv=None):
    args = argv or sys.argv[1:]
    if not args:
        sys.exit("usage: transform_books_to_bib_records.py /path/to/books.json")
    d = json.load(open(args[0], encoding="utf-8"))
    books = d if isinstance(d, list) else (d.get("books") or d.get("records") or list(d.values()))
    os.makedirs("data/db_staging", exist_ok=True)

    rows, skipped, seen_id, seen_keys = [], 0, set(), Counter()
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
            o = {k: v for k, v in r.items() if k != "raw_full"}
            o["raw"] = r["raw_full"]
            f.write(json.dumps(o, ensure_ascii=False) + "\n")

    cols = ["bib_id", "title", "title_yomi", "subtitle", "responsibility", "edition", "publisher",
            "pub_place", "pub_year", "series", "volume", "physical", "isbn", "issn", "ncid",
            "ndl_bib_id", "ndc", "ndlc", "language", "note", "form_type"]
    arr = json.dumps([{**{c: r.get(c) for c in cols}, "raw": r["raw_compact"]} for r in rows],
                     ensure_ascii=False, separators=(",", ":"))
    assert "$j$" not in arr
    coldef = ",".join(f"{c} {'int' if c=='pub_year' else 'text'}" for c in cols) + ",raw jsonb"
    sql = "\n".join([
        f"-- biblio.bib_records load: 蔵書 books.json → {len(rows)}件  source='{SOURCE}'  bib_id=alo_uri",
        f"-- idempotent (ON CONFLICT), reversible: DELETE FROM biblio.bib_records WHERE source='{SOURCE}';",
        "BEGIN;",
        "INSERT INTO control.source_snapshots (source_snapshot_id,source_system,snapshot_kind,snapshot_label,storage_system,artifact_path,row_count,metadata_json)",
        f"VALUES ('snapshot:asai-bookshelf:books-json','asai-bookshelf','normalized_export','蔵書 books.json NDL-enriched 6537','box','app/data/books.json',{len(rows)},'{{\"producer\":\"transform_books_to_bib_records.py\"}}') ON CONFLICT (source_snapshot_id) DO NOTHING;",
        "INSERT INTO control.ingest_jobs (ingest_job_id,job_kind,target_schema,target_table,source_snapshot_id,status,triggered_by,rows_expected,metadata_json)",
        f"VALUES ('ingest:biblio:bookshelf:20260603','append_import','biblio','bib_records','snapshot:asai-bookshelf:books-json','running','owner',{len(rows)},'{{}}') ON CONFLICT (ingest_job_id) DO NOTHING;",
        "INSERT INTO biblio.bib_records (" + ",".join(cols) + ",source,raw,imported_at,updated_at)",
        "SELECT " + ",".join(f"x.{c}" for c in cols) + f",'{SOURCE}',x.raw,now(),now()",
        f"FROM jsonb_to_recordset($j${arr}$j$::jsonb) AS x({coldef})",
        "ON CONFLICT (bib_id) DO NOTHING;",
        "UPDATE control.ingest_jobs SET status='succeeded',finished_at=now(),",
        f"  rows_inserted=(SELECT count(*) FROM biblio.bib_records WHERE source='{SOURCE}')",
        "WHERE ingest_job_id='ingest:biblio:bookshelf:20260603';",
        "COMMIT;",
        f"SELECT count(*) AS bib_loaded FROM biblio.bib_records WHERE source='{SOURCE}';",
        "",
    ])
    open("data/db_staging/bib_records_bookshelf_v1.sql", "w", encoding="utf-8").write(sql)

    print("=== transform_books_to_bib_records ===", file=sys.stderr)
    print(f"books {len(books)} → bib_records {len(rows)} (skipped {skipped}: no-title/dup-id)", file=sys.stderr)
    print(f"with isbn: {sum(1 for r in rows if r['isbn'])} / ndl_bib_id: {sum(1 for r in rows if r['ndl_bib_id'])}"
          f" / yomi: {sum(1 for r in rows if r['title_yomi'])}", file=sys.stderr)
    print(f"SQL bytes: {len(sql.encode('utf-8')):,} (.sql) ; check it fits the paste path", file=sys.stderr)
    mapped = {kk for v in MAP.values() for kk in v} | set(RAW_KEEP) | {"alo_uri", "lit_id"}
    unmapped = [(k, n) for k, n in seen_keys.most_common() if k not in mapped]
    print(f"未マップキー（raw_full に保持・必要なら追加検討）: {[k for k,_ in unmapped]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
