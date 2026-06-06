#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_book_links.py — books.json から「所有側2図書館」のリンクを自動生成

4図書館のうち、有償DL（ベンコム/リーガル）は外部キー・校正が要るが、
**自炊PDF と 物理本は books.json に所在情報がある**ため、機械的に book_links.json を生成できる。
これで全蔵書について「該当PDFを開く」「棚位置がわかる」が校正ゼロで揃う。

books.json のスキーマには揺れ（canonical v1 / legacy）があるため、各フィールドは
候補パスを順に試す（最初に見つかった非空値を採用）。実データに合わせて CANDIDATES を調整可。

- office_pdf : {folder, file}（offset は null=未設定→トップ着地。ノードに pdf_page があれば直着地）
- physical_shelf : {location}

既存 book_links.json の有償DLエントリ（book_key/offset 校正済）は保持してマージする。

使い方:
  BOOKS_JSON=~/Box/.../app/data/books.json OUT=data/book_links.json \
    python3 scripts/generate_book_links.py [--dry-run]
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BOOKS_JSON = Path(os.environ.get("BOOKS_JSON", REPO / "data" / "books.json"))
OUT = Path(os.environ.get("OUT", REPO / "data" / "book_links.json"))
DRY = "--dry-run" in sys.argv

# 各論理フィールドの候補パス（dotted）。canonical v1 を先頭、legacy を後段に。
CANDIDATES = {
    "pdf_present": ["digital.pdf_present", "storage.digital.pdf_present", "status.scanned", "hasPdf", "pdf_present"],
    "pdf_folder":  ["digital.pdf_folder", "storage.pdf.folder", "storage.digital.folder", "pdf_folder", "pdfFolder"],
    "pdf_files":   ["digital.pdf_files", "storage.pdf.files", "pdf_files"],
    "pdf_file":    ["digital.pdf_file", "storage.pdf.file", "pdf_file", "pdfFile"],
    "phys_present":["physical.present", "status.physical", "storage.physical.present", "physical_present"],
    "shelf_label": ["physical.shelf_label", "storage.physical.location", "storage.physical.shelf", "shelfLabel", "shelf"],
    "shelf_zone":  ["physical.shelf_zone", "storage.physical.zone", "shelfZone", "zone"],
}


def dig(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def first(obj, key):
    for path in CANDIDATES[key]:
        v = dig(obj, path)
        if v not in (None, "", [], {}):
            return v
    return None


def pdf_filename(book):
    files = first(book, "pdf_files")
    if isinstance(files, list) and files:
        f0 = files[0]
        if isinstance(f0, dict):
            return f0.get("filename") or f0.get("name") or f0.get("file")
        if isinstance(f0, str):
            return f0
    return first(book, "pdf_file")


def book_id_of(book):
    return (book.get("book_id") or book.get("internal_id")
            or (f"isbn_{book['isbn']}" if book.get("isbn") else None))


def main():
    raw = json.loads(BOOKS_JSON.read_text(encoding="utf-8"))
    books = raw.get("books", raw) if isinstance(raw, dict) else raw
    if not isinstance(books, list):
        print(f"books.json の形式を解釈できません: {type(books)}", file=sys.stderr)
        sys.exit(1)

    existing = {}
    if OUT.exists():
        try:
            existing = (json.loads(OUT.read_text(encoding="utf-8")).get("links") or {})
        except Exception:
            existing = {}

    links = {}
    n_pdf = n_phys = 0
    for book in books:
        bid = book_id_of(book)
        if not bid:
            continue
        entry = dict(existing.get(bid, {}))  # 既存（校正済み有償DL等）を継承

        if first(book, "pdf_present"):
            folder = first(book, "pdf_folder")
            fname = pdf_filename(book)
            if folder and fname:
                prev = entry.get("office_pdf", {})
                entry["office_pdf"] = {"folder": folder, "file": fname,
                                        "offset": prev.get("offset")}  # 既存offsetは保持、無ければnull
                n_pdf += 1

        if first(book, "phys_present"):
            loc = first(book, "shelf_label")
            zone = first(book, "shelf_zone")
            location = " ".join(str(x) for x in [zone, loc] if x) or None
            if location:
                entry["physical_shelf"] = {"location": location}
                n_phys += 1

        if entry:
            links[bid] = entry

    # 既存にしか無い本（books.jsonに無い）も失わない
    for bid, e in existing.items():
        if bid not in links:
            links[bid] = e

    print(f"対象 {len(books)} 冊 → 自炊PDF {n_pdf} 冊 / 物理本 {n_phys} 冊 / リンク総数 {len(links)} 冊")
    if DRY:
        sample = dict(list(links.items())[:3])
        print(json.dumps(sample, ensure_ascii=False, indent=2))
        print("(--dry-run のため書き込みなし)")
        return
    doc = {"$comment": "generate_book_links.py が books.json から自動生成（有償DLの校正値はマージ保持）。",
           "links": links}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
