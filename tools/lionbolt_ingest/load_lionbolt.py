#!/usr/bin/env python3
"""load_lionbolt.py — LION BOLT 法律書カタログ (catalog_dedup.jsonl) を
Supabase biblio.bib_records / biblio.bib_toc / biblio.library_sources へ投入する
ローダ。DD-LIONBOLT-INGEST v0.1 (artifacts/lionbolt_ingest_20260622/) の実装。

設計ポリシー（DD §4–§6）:
  - lionbolt 行は source='lionbolt' として独立に着地。既存行は一切 UPDATE しない。
  - dedup（既存 isbn との一致）は **レポートのみ**。auto-merge / biblio_item mint はしない。
  - 冪等: bib_id = 'lionbolt:'+book_id, source_hash = sha256(record) で ON CONFLICT 更新。

既定は **dry-run**（DB 非接触）: 正規化・統計・検証・dedup レポート・サンプル SQL・
TSV(\\copy 用) を artifacts/ に書き出すのみ。
実 DB 投入は --apply かつ 明示フラグ + 接続情報が揃ったときだけ（DD §6 のゲート）。

使い方:
  # dry-run（既定。DB に触れない。TSV と load.sql を生成）
  python load_lionbolt.py --input ~/alo-ai/work/lionbolt_dl/catalog_dedup.jsonl

  # 既存 isbn 突合レポートも出す（既存 isbn を 1 行 1 isbn のファイルで渡す）
  python load_lionbolt.py --input catalog_dedup.jsonl --existing-isbns existing_isbns.txt

  # 実投入（owner ratify 後のみ。READ_ONLY 解除済み前提）
  python load_lionbolt.py --input catalog_dedup.jsonl --apply \\
      --i-understand-this-writes-prod --dsn "$SUPABASE_DSN"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SOURCE = "lionbolt"
LOADER_VERSION = "lionbolt_loader/0.1"
ISBN13_RE = re.compile(r"^[0-9]{13}$")

LIBRARY_SOURCE_ROW = {
    "id": "lionbolt",
    "label": "LION BOLT 法律書カタログ",
    "kind": "commercial_catalog",
    "tier": "subscription",
    "cost": "3278yen/month",
    "page_strategy": "print_page",
    "needs_auth": True,
    "url_template": "https://api.lionbolt.jp/v2/std/books/search/initial",
    "book_url_template": "https://law-books.lionbolt.jp/books/{book_id}",
    "note": ("著作権法47-5。書誌+構造化目次のみ、本文不取得。"
             "取得2026-06-09/10。external_share=false"),
}


def canonical_hash(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def norm_isbn(rec: dict) -> str | None:
    for k in ("isbn13", "isbn"):
        v = (rec.get(k) or "").strip().replace("-", "")
        if ISBN13_RE.match(v):
            return v
    return None


def pub_year(rec: dict) -> int | None:
    d = (rec.get("pub_date") or "").strip()
    if len(d) >= 4 and d[:4].isdigit():
        y = int(d[:4])
        if 1800 <= y <= 2100:
            return y
    return None


def mint_bib_id(rec: dict, isbn: str | None) -> str | None:
    bid = (rec.get("book_id") or "").strip()
    if bid:
        return f"lionbolt:{bid}"
    if isbn:
        return f"lionbolt:isbn:{isbn}"
    return None  # 識別子が無いレコードはスキップ対象


def make_note(rec: dict) -> str | None:
    parts = []
    genre = rec.get("genre")
    if isinstance(genre, list) and genre:
        parts.append("genre=[" + ",".join(str(g) for g in genre) + "]")
    ocr = "/".join(str(rec.get(k)) for k in ("source_type", "accuracy_rank")
                   if rec.get(k))
    if ocr:
        parts.append("ocr=" + ocr)
    return "; ".join(parts) or None


def to_bib_record(rec: dict) -> dict | None:
    isbn = norm_isbn(rec)
    bib_id = mint_bib_id(rec, isbn)
    if not bib_id or not (rec.get("title") or "").strip():
        return None
    pc = rec.get("page_count")
    book_id = (rec.get("book_id") or "").strip()
    return {
        "bib_id": bib_id,
        "title": (rec.get("title") or "").strip(),
        "responsibility": (rec.get("author") or "").strip() or None,
        "publisher": (rec.get("publisher") or "").strip() or None,
        "pub_year": pub_year(rec),
        "physical": (f"{pc}p" if isinstance(pc, int) and pc > 0 else None),
        "isbn": isbn,
        "note": make_note(rec),
        "source": SOURCE,
        "source_url": (f"https://law-books.lionbolt.jp/books/{book_id}"
                       if book_id else None),
        "source_hash": canonical_hash(rec),
        "form_type": "monograph",
        "raw": rec,
    }


def to_toc_rows(rec: dict, bib_id: str) -> list[dict]:
    toc = rec.get("toc") or {}
    items = toc.get("items") if isinstance(toc, dict) else None
    if not isinstance(items, list):
        return []
    out, ordinal = [], 0
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("disabled"):
            continue
        text = (it.get("text") or "").strip()
        if not text:
            continue
        page = it.get("startHeadlinePage")
        out.append({
            "bib_id": bib_id,
            "ordinal": ordinal,
            "level": int(it.get("level") or 0),
            "page": (int(page) if isinstance(page, int) and page > 0 else None),
            "text": text,
        })
        ordinal += 1
    return out


def tsv_escape(v) -> str:
    if v is None:
        return r"\N"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (dict, list)):
        v = json.dumps(v, ensure_ascii=False)
    return (str(v).replace("\\", "\\\\").replace("\t", " ")
            .replace("\n", " ").replace("\r", " "))


def write_tsv(path: Path, cols: list[str], rows) -> int:
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write("\t".join(tsv_escape(r.get(c)) for c in cols) + "\n")
            n += 1
    return n


BIB_COLS = ["bib_id", "title", "responsibility", "publisher", "pub_year",
            "physical", "isbn", "note", "source", "source_url",
            "source_hash", "form_type", "raw"]
TOC_COLS = ["bib_id", "ordinal", "level", "page", "text"]


def main() -> int:
    ap = argparse.ArgumentParser(description="LION BOLT カタログ → Supabase ローダ")
    ap.add_argument("--input", required=True,
                    help="catalog_dedup.jsonl のパス")
    ap.add_argument("--outdir", default="artifacts/lionbolt_ingest_20260622/build",
                    help="TSV / load.sql / レポート出力先")
    ap.add_argument("--existing-isbns",
                    help="既存 bib_records.isbn の一覧（1 行 1 isbn）。dedup レポート用")
    ap.add_argument("--apply", action="store_true",
                    help="実 DB に投入（owner ratify 後のみ）")
    ap.add_argument("--i-understand-this-writes-prod", action="store_true",
                    help="--apply の二重ガード")
    ap.add_argument("--dsn", help="Postgres DSN（--apply 時必須）")
    args = ap.parse_args()

    inp = Path(args.input).expanduser()
    if not inp.exists():
        print(f"ERROR: 入力が見つからない: {inp}", file=sys.stderr)
        print("  Mac の ~/alo-ai/work/lionbolt_dl/catalog_dedup.jsonl か、"
              "Box(file 2274970590283) から取得して渡してください。", file=sys.stderr)
        return 2

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    existing = set()
    if args.existing_isbns and Path(args.existing_isbns).exists():
        existing = {ln.strip() for ln in Path(args.existing_isbns).read_text(
            encoding="utf-8").splitlines() if ln.strip()}

    n_lines = n_books = n_skipped = n_with_toc = n_toc = 0
    isbn_seen, isbn_dups = set(), []
    bib_rows, toc_rows = [], []

    with inp.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n_lines += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                n_skipped += 1
                continue
            br = to_bib_record(rec)
            if br is None:
                n_skipped += 1
                continue
            n_books += 1
            bib_rows.append(br)
            if br["isbn"]:
                if br["isbn"] in existing:
                    isbn_dups.append(br["isbn"])
                isbn_seen.add(br["isbn"])
            trows = to_toc_rows(rec, br["bib_id"])
            if trows:
                n_with_toc += 1
                n_toc += len(trows)
                toc_rows.extend(trows)

    # --- 出力（TSV + load.sql） ---
    src_hash = hashlib.sha256(inp.read_bytes()).hexdigest()
    n_bib = write_tsv(outdir / "bib_records.tsv", BIB_COLS, bib_rows)
    n_toc_w = write_tsv(outdir / "bib_toc.tsv", TOC_COLS, toc_rows)
    (outdir / "library_source.json").write_text(
        json.dumps(LIBRARY_SOURCE_ROW, ensure_ascii=False, indent=2),
        encoding="utf-8")

    report = {
        "loader_version": LOADER_VERSION,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(inp),
        "input_sha256": src_hash,
        "lines_read": n_lines,
        "books_normalized": n_books,
        "skipped_no_id_or_title_or_badjson": n_skipped,
        "books_with_toc": n_with_toc,
        "toc_rows": n_toc,
        "distinct_isbn_in_lionbolt": len(isbn_seen),
        "isbn_collision_with_existing": len(isbn_dups),
        "isbn_collision_sample": sorted(set(isbn_dups))[:25],
        "tsv_bib_rows": n_bib,
        "tsv_toc_rows": n_toc_w,
        "expected_books_per_report_md": 22844,
        "expected_toc_items_per_report_md": 264555,
        "applied": False,
        "minted_biblio_items": 0,
        "db_mutations": 0,
    }
    (outdir / "load_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n[dry-run] 出力先: {outdir}/")
    print("  - bib_records.tsv / bib_toc.tsv / library_source.json / load_report.json")
    print("  実投入は migration_lionbolt.sql 適用後、--apply で。")

    if args.apply:
        if not (args.i_understand_this_writes_prod and args.dsn):
            print("\nABORT: --apply には --i-understand-this-writes-prod と --dsn が必須。",
                  file=sys.stderr)
            return 3
        return _apply(args.dsn, outdir, src_hash)
    return 0


def _apply(dsn: str, outdir: Path, src_hash: str) -> int:
    """owner ratify 後の実投入。staging→idempotent upsert（migration_lionbolt.sql と整合）。"""
    try:
        import psycopg  # type: ignore
    except ImportError:
        print("ERROR: psycopg(3) が必要。`pip install psycopg[binary]`", file=sys.stderr)
        return 4
    print("APPLY: migration_lionbolt.sql を先に適用済みであることを確認してください。")
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:  # pragma: no cover
        with cur.copy("COPY biblio._stg_lionbolt_bib FROM STDIN") as cp:
            cp.write((outdir / "bib_records.tsv").read_text(encoding="utf-8"))
        with cur.copy("COPY biblio._stg_lionbolt_toc FROM STDIN") as cp:
            cp.write((outdir / "bib_toc.tsv").read_text(encoding="utf-8"))
        cur.execute("SELECT biblio.fn_lionbolt_upsert(%s, %s)",
                    (LOADER_VERSION, src_hash))
        conn.commit()
    print("APPLY: 完了（migration の fn_lionbolt_upsert を実行）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
