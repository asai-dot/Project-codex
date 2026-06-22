#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
load_to_supabase.py — books.json / bencom を private `bookdx` schema へ投入

**お手元PC/Box同期環境で実行する**（実行環境にはBox大容量ファイルを持ち込めない）。
books.json は SoT のまま。bookdx.* はそこからの一方向リードレプリカで、write-back しない。

監査(PASS_WITH_NOTES)反映:
  - load_run を1行作成し、各行に load_run_id / source_record_hash を付与（再現性） [F6]
  - profile_source / profile_confidence は engine と同じ純関数で計算（ドリフト防止）[F3]
  - 接続は loader role（GRANT 済）。env BOOKDX_DB_URL。psycopg は遅延import。

スキーマは term_dict/sql/supabase_bookdx_schema.sql（先に適用しておく）。

Usage:
    export BOOKDX_DB_URL="postgresql://bookdx_loader:...@db.<ref>.supabase.co:5432/postgres"
    python load_to_supabase.py --base "C:/Users/Asai/Box/.../事務所内本棚DX化計画"
    python load_to_supabase.py --base ... --dry-run   # DBに触れず件数だけ確認
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
from pathlib import Path

from purchase_recommender import (
    REL,
    DEFAULT_BASE,
    normalize_isbn,
    normalize_title,
    flatten_toc,
    _as_list,
    compute_candidate_profile,
)

LOADER_VERSION = "load_to_supabase/0.1"


# ---------------------------------------------------------------------------
# pure transforms（DB非依存・テスト対象）
# ---------------------------------------------------------------------------
def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _record_hash(obj) -> str:
    return _sha256_text(json.dumps(obj, sort_keys=True, ensure_ascii=False))


def holding_row(book: dict, load_run_id: str = "") -> dict:
    """books.json の1冊 → bookdx.holdings 行。"""
    isbn = normalize_isbn(book.get("isbn") or (book.get("external_refs") or {}).get("isbn"))
    title = book.get("title", "") or ""
    st = book.get("status") or {}
    return {
        "internal_id": str(book.get("id", "")),
        "isbn": isbn or None,
        "bencom_id": (str(book.get("bencomId")).strip() or None) if book.get("bencomId") else None,
        "title": title,
        "title_norm": normalize_title(title) or None,
        "author": book.get("author", "") or None,
        "author_norm": normalize_title(book.get("author", "")) or None,
        "publisher": book.get("publisher", "") or None,
        "publisher_norm": normalize_title(book.get("publisher", "")) or None,
        "genre": _as_list(book.get("genre")),
        "ndc": _as_list(book.get("ndc")),
        "physical": bool(st.get("physical")) if st.get("physical") is not None else None,
        "cut": bool(st.get("cut")) if st.get("cut") is not None else None,
        "scanned": bool(st.get("scanned")) if st.get("scanned") is not None else None,
        "has_toc": bool(book.get("hasToc")) if book.get("hasToc") is not None else None,
        "source_record_hash": _record_hash(book),
        "load_run_id": load_run_id or None,
    }


def candidate_row(book: dict, cov: dict, tag_domain: dict, load_run_id: str = "") -> dict:
    """bencom の1冊 + coverage → bookdx.candidates 行。profile_* を共有純関数で計算。"""
    isbn = normalize_isbn(book.get("isbn"))
    title = book.get("title", "") or ""
    cov = cov or {}
    dist = cov.get("domain_hits") or cov.get("domain_distribution") or cov.get("domains")
    dist = dist if isinstance(dist, dict) else {}
    total_toc = int(cov.get("total_toc") or len(flatten_toc(book.get("toc"))))
    matched_toc = int(cov.get("matched_toc") or 0)
    coverage = float(cov.get("coverage") or 0.0)
    _, source, confidence = compute_candidate_profile(
        primary_domain=cov.get("primary_domain"),
        domain_hits=dist,
        tags=book.get("tags"),
        tag_domain=tag_domain,
        matched_toc=matched_toc,
        coverage=coverage,
    )
    return {
        "book_id": str(book.get("id", "")),
        "isbn": isbn or None,
        "title": title,
        "title_norm": normalize_title(title) or None,
        "author": book.get("author", "") or None,
        "author_norm": normalize_title(book.get("author", "")) or None,
        "publisher": book.get("publisher", "") or None,
        "publisher_norm": normalize_title(book.get("publisher", "")) or None,
        "tags": _as_list(book.get("tags")),
        "bencom_url": book.get("bencomUrl") or book.get("url") or None,
        "primary_domain": cov.get("primary_domain"),
        "domain_hits": dist,
        "total_toc": total_toc,
        "matched_toc": matched_toc,
        "coverage": coverage,
        "profile_source": source,
        "profile_confidence": confidence,
        "source_record_hash": _record_hash({"b": book, "c": cov}),
        "load_run_id": load_run_id or None,
    }


def tag_domain_rows(mapping: dict) -> list[dict]:
    out = []
    for tag, entry in (mapping or {}).items():
        if isinstance(entry, dict):
            out.append({"tag": tag, "domain_l1": entry.get("domain_l1"),
                        "count": entry.get("count")})
        else:
            out.append({"tag": tag, "domain_l1": entry, "count": None})
    return out


def build_rows(base: Path) -> tuple[list[dict], list[dict], list[dict], dict]:
    """4ファイルを読み、holdings/candidates/tag_domain 行と source_files メタを返す。"""
    p = {k: base / REL[k] for k in ("holdings", "bencom", "coverage", "tag_domain")}
    holdings_json = json.loads(p["holdings"].read_text(encoding="utf-8"))
    bencom_json = json.loads(p["bencom"].read_text(encoding="utf-8"))
    cov_json = json.loads(p["coverage"].read_text(encoding="utf-8"))
    tagmap = json.loads(p["tag_domain"].read_text(encoding="utf-8")) if p["tag_domain"].exists() else {}

    coverage = {}
    for bk in cov_json.get("books", cov_json if isinstance(cov_json, list) else []):
        bid = bk.get("book_id") or bk.get("id")
        if bid:
            coverage[str(bid)] = bk

    source_files = {}
    for k, path in p.items():
        if path.exists():
            data = path.read_bytes()
            source_files[REL[k]] = {
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
                "mtime": _dt.datetime.utcfromtimestamp(path.stat().st_mtime).isoformat() + "Z",
            }
    run_hash = _sha256_text("".join(v["sha256"] for v in source_files.values()))
    run_id = _dt.datetime.now().strftime("%Y%m%dT%H%M%S")

    # compute_candidate_profile は {tag: domain_l1} を期待（{tag:{domain_l1}} を平坦化）
    tagmap_norm = {t: (e.get("domain_l1") if isinstance(e, dict) else e)
                   for t, e in tagmap.items()}
    h_rows = [holding_row(b, run_id) for b in holdings_json]
    c_rows = [candidate_row(b, coverage.get(str(b.get("id", "")), {}), tagmap_norm, run_id)
              for b in bencom_json]
    t_rows = tag_domain_rows(tagmap)
    meta = {"load_run_id": run_id, "source_hash": run_hash, "source_files": source_files}
    return h_rows, c_rows, t_rows, meta


# ---------------------------------------------------------------------------
# DB upsert（psycopg 遅延import・本番のみ）
# ---------------------------------------------------------------------------
_UPSERT_COLS = {
    "holdings": ["internal_id", "isbn", "bencom_id", "title", "title_norm",
                 "author", "author_norm", "publisher", "publisher_norm", "genre", "ndc",
                 "physical", "cut", "scanned", "has_toc",
                 "source_record_hash", "load_run_id"],
    "candidates": ["book_id", "isbn", "title", "title_norm", "author", "author_norm",
                   "publisher", "publisher_norm", "tags", "bencom_url",
                   "primary_domain", "domain_hits", "total_toc", "matched_toc",
                   "coverage", "profile_source", "profile_confidence",
                   "source_record_hash", "load_run_id"],
    "tag_domain": ["tag", "domain_l1", "count"],
}
_PK = {"holdings": "internal_id", "candidates": "book_id", "tag_domain": "tag"}
_JSONB = {"genre", "ndc", "tags", "domain_hits"}


def _upsert(cur, schema: str, table: str, rows: list[dict], batch: int = 500):
    import json as _json
    cols = _UPSERT_COLS[table]
    pk = _PK[table]
    setcl = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c != pk)
    placeholders = ", ".join(["%s"] * len(cols))
    sql = (f"INSERT INTO {schema}.{table} ({', '.join(cols)}) VALUES ({placeholders}) "
           f"ON CONFLICT ({pk}) DO UPDATE SET {setcl}")
    buf = []
    for r in rows:
        buf.append([_json.dumps(r.get(c), ensure_ascii=False) if c in _JSONB else r.get(c)
                    for c in cols])
        if len(buf) >= batch:
            cur.executemany(sql, buf); buf = []
    if buf:
        cur.executemany(sql, buf)


def main(argv=None):
    ap = argparse.ArgumentParser(description="bookdx schema へ投入")
    ap.add_argument("--base", default=str(DEFAULT_BASE))
    ap.add_argument("--db-url", default=os.environ.get("BOOKDX_DB_URL", ""))
    ap.add_argument("--schema", default="bookdx")
    ap.add_argument("--dry-run", action="store_true", help="DBに触れず件数のみ")
    args = ap.parse_args(argv)

    h_rows, c_rows, t_rows, meta = build_rows(Path(args.base))
    print(f"holdings={len(h_rows)}  candidates={len(c_rows)}  tag_domain={len(t_rows)}")
    print(f"load_run_id={meta['load_run_id']}  source_hash={meta['source_hash'][:16]}…")
    if args.dry_run:
        print("dry-run: DB未接続。")
        return
    if not args.db_url:
        ap.error("--db-url か env BOOKDX_DB_URL が必要（loader role 推奨）")

    import json as _json
    try:
        import psycopg
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("pip install 'psycopg[binary]' が必要です") from e

    with psycopg.connect(args.db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {args.schema}.load_run "
                f"(load_run_id, source_hash, source_files, loader_version) "
                f"VALUES (%s, %s, %s, %s) ON CONFLICT (load_run_id) DO NOTHING",
                [meta["load_run_id"], meta["source_hash"],
                 _json.dumps(meta["source_files"], ensure_ascii=False), LOADER_VERSION],
            )
            _upsert(cur, args.schema, "tag_domain", t_rows)
            _upsert(cur, args.schema, "holdings", h_rows)
            _upsert(cur, args.schema, "candidates", c_rows)
        conn.commit()
    print("done.")


if __name__ == "__main__":
    main()
