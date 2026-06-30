#!/usr/bin/env python3
"""field_profile.py — raw_intake 投入前の read-only フィールドプロファイラ.

DD-LITID-PLAN 4ルート版同定パイプラインの Phase 0 ゲート (INGEST_SPEC v0.2 §7-A) 用.
JSONL/NDJSON を1行ずつストリームし (505MB級でも定数メモリ), 各フィールドの充足率,
ISBN被覆/形式妥当性, キー一意性, TOC構造/被覆を出力する. **読むだけ. 書き込み・突合・promote はしない.**

使い方:
  python3 field_profile.py CATALOG.jsonl --source bengo4 \
      --key content_id --isbn-field isbn --toc-field toc \
      --out-md report.md --out-json report.json --manifest-stub manifest.stub.json

キー/ISBN/TOC フィールドを省略すると候補名から自動推定する.
出力は read-only の知見のみ. manifest stub は §2 manifest の下書き (要手当て箇所は TODO 印).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from typing import Any

# --- フィールド自動推定の候補名 (監査 §7-A の route-local id / isbn / toc) -------------
KEY_CANDIDATES = ["content_id", "book_id", "isbn", "id", "scan_id", "legallib_book_id"]
ISBN_CANDIDATES = ["isbn13", "isbn_13", "isbn", "isbn10", "isbn_10"]
TOC_CANDIDATES = ["toc", "toc_nodes", "toc_items", "table_of_contents", "contents", "toc_html"]

ISBN13_RE = re.compile(r"^\d{13}$")
ISBN10_RE = re.compile(r"^\d{9}[\dXx]$")


def normalize_isbn(value: Any) -> str | None:
    """ISBN文字列を数字/Xだけに正規化. dict/list等は弾く."""
    if not isinstance(value, (str, int)):
        return None
    s = re.sub(r"[\s\-]", "", str(value))
    return s or None


def isbn13_checksum_ok(s: str) -> bool:
    if not ISBN13_RE.match(s):
        return False
    total = sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(s[:12]))
    return (10 - total % 10) % 10 == int(s[12])


def isbn10_checksum_ok(s: str) -> bool:
    if not ISBN10_RE.match(s):
        return False
    total = sum((10 - i) * (10 if c in "Xx" else int(c)) for i, c in enumerate(s))
    return total % 11 == 0


def flatten_top_paths(obj: dict, prefix: str = "", depth: int = 2) -> dict[str, Any]:
    """ネストを depth 段だけドット記法で平坦化. list は値ではなく型情報として扱う."""
    out: dict[str, Any] = {}
    for k, v in obj.items():
        path = f"{prefix}{k}"
        if isinstance(v, dict) and depth > 1:
            out.update(flatten_top_paths(v, prefix=path + ".", depth=depth - 1))
        else:
            out[path] = v
    return out


def is_empty(v: Any) -> bool:
    return v is None or v == "" or v == [] or v == {}


def guess_field(fieldnames: set[str], candidates: list[str]) -> str | None:
    lower = {f.lower(): f for f in fieldnames}
    for c in candidates:
        if c in lower:
            return lower[c]
    return None


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def profile(path: str, key: str | None, isbn_field: str | None,
            toc_field: str | None, max_examples: int = 3) -> dict:
    present: Counter = Counter()
    nonempty: Counter = Counter()
    examples: dict[str, list] = {}
    total = 0
    bad_json = 0

    key_values: Counter = Counter()
    isbn_total = isbn_valid = isbn_dupe = 0
    isbn_seen: set[str] = set()
    toc_present = 0
    toc_lens: list[int] = []

    autodetect = key is None or isbn_field is None or toc_field is None
    detect_budget = 200  # 先頭数百行でフィールド名集合を確定

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                bad_json += 1
                continue
            if not isinstance(rec, dict):
                bad_json += 1
                continue

            flat = flatten_top_paths(rec)

            if autodetect and total <= detect_budget:
                names = set(flat) | set(rec)
                key = key or guess_field(names, KEY_CANDIDATES)
                isbn_field = isbn_field or guess_field(names, ISBN_CANDIDATES)
                toc_field = toc_field or guess_field(names, TOC_CANDIDATES)

            for fpath, v in flat.items():
                present[fpath] += 1
                if not is_empty(v):
                    nonempty[fpath] += 1
                    ex = examples.setdefault(fpath, [])
                    if len(ex) < max_examples and not isinstance(v, (dict, list)):
                        if v not in ex:
                            ex.append(v)

            # キー一意性
            if key:
                kv = rec.get(key) if key in rec else flat.get(key)
                if not is_empty(kv):
                    key_values[str(kv)] += 1

            # ISBN 被覆/形式
            if isbn_field:
                raw = rec.get(isbn_field) if isbn_field in rec else flat.get(isbn_field)
                norm = normalize_isbn(raw)
                if norm:
                    isbn_total += 1
                    if isbn13_checksum_ok(norm) or isbn10_checksum_ok(norm):
                        isbn_valid += 1
                    if norm in isbn_seen:
                        isbn_dupe += 1
                    else:
                        isbn_seen.add(norm)

            # TOC 被覆/構造
            if toc_field:
                tv = rec.get(toc_field) if toc_field in rec else flat.get(toc_field)
                if not is_empty(tv):
                    toc_present += 1
                    if isinstance(tv, list):
                        toc_lens.append(len(tv))

    distinct_keys = len(key_values)
    key_dupe = sum(c - 1 for c in key_values.values() if c > 1)

    fields = []
    for fpath in sorted(present, key=lambda f: -present[f]):
        fields.append({
            "field": fpath,
            "present_pct": round(100 * present[fpath] / max(total, 1), 1),
            "nonempty_pct": round(100 * nonempty[fpath] / max(total, 1), 1),
            "examples": examples.get(fpath, []),
        })

    return {
        "path": path,
        "record_count": total,
        "bad_json_lines": bad_json,
        "key_field": key,
        "key_distinct": distinct_keys,
        "key_dupe_rows": key_dupe,
        "key_unique_pct": round(100 * distinct_keys / max(total, 1), 1) if key else None,
        "isbn_field": isbn_field,
        "isbn_coverage_pct": round(100 * isbn_total / max(total, 1), 1) if isbn_field else None,
        "isbn_valid_pct_of_present": round(100 * isbn_valid / max(isbn_total, 1), 1) if isbn_total else None,
        "isbn_duplicate_rows": isbn_dupe if isbn_field else None,
        "toc_field": toc_field,
        "toc_coverage_pct": round(100 * toc_present / max(total, 1), 1) if toc_field else None,
        "toc_avg_items": round(sum(toc_lens) / len(toc_lens), 1) if toc_lens else None,
        "fields": fields,
    }


def to_markdown(p: dict, source: str) -> str:
    lines = [
        f"# field-profile (read-only) — {source}",
        "",
        f"- file: `{p['path']}`",
        f"- records: **{p['record_count']:,}** (bad JSON lines: {p['bad_json_lines']})",
        f"- key field: `{p['key_field']}` — distinct {p['key_distinct']:,} "
        f"({p['key_unique_pct']}% unique, dupe rows {p['key_dupe_rows']})",
        f"- ISBN field: `{p['isbn_field']}` — coverage {p['isbn_coverage_pct']}% , "
        f"valid {p['isbn_valid_pct_of_present']}% of present, dupe {p['isbn_duplicate_rows']}",
        f"- TOC field: `{p['toc_field']}` — coverage {p['toc_coverage_pct']}% , "
        f"avg items {p['toc_avg_items']}",
        "",
        "## per-field presence",
        "",
        "| field | present% | nonempty% | examples |",
        "|---|---|---|---|",
    ]
    for f in p["fields"]:
        ex = ", ".join(str(e)[:40] for e in f["examples"])
        lines.append(f"| `{f['field']}` | {f['present_pct']} | {f['nonempty_pct']} | {ex} |")
    lines.append("")
    lines.append("> read-only profile. no matching / promotion performed. "
                 "INGEST_SPEC v0.2 §7-A field-profile gate input.")
    return "\n".join(lines)


def manifest_stub(p: dict, source: str, file_path: str) -> dict:
    """§2 manifest の下書き. 取得時メタ (TODO) は人が埋める."""
    toc = p["toc_field"]
    toc_origin = "publisher_html" if source == "bengo4" else (
        "own_ocr" if source in ("lionbolt", "self_scan") else "unknown")
    return {
        "source": source,
        "source_system": "TODO",
        "fetched_at": "TODO_capture_timestamp",
        "account": "TODO_owner_account",
        "fetch_method": "TODO_api|scrape|colophon_ocr",
        "acquisition_path": "TODO",
        "source_location": "TODO_url_or_box_or_local",
        "rights_class": "TODO_owned|subscription_access|mixed",
        "medium_origin": "TODO_digital|paper_scan",
        "route_local_id": p["key_field"],
        "key_field": p["isbn_field"] or p["key_field"],
        "toc_origin": toc_origin if toc else "unknown",
        "extractor_version": "TODO_parser_version",
        "record_count": p["record_count"],
        "files": [{"name": file_path.split("/")[-1],
                   "sha256": sha256_of(file_path),
                   "bytes": None}],
        "evidence_locator": "TODO",
        "notes": "auto-stub from field_profile.py; fill TODO before ingest (v0.2 §7-A gate)",
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="JSONL/NDJSON path")
    ap.add_argument("--source", required=True,
                    choices=["lionbolt", "bengo4", "legallib", "self_scan"])
    ap.add_argument("--key", default=None)
    ap.add_argument("--isbn-field", default=None)
    ap.add_argument("--toc-field", default=None)
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--manifest-stub", default=None,
                    help="manifest stub の出力先. 指定時のみ sha256 を計算")
    args = ap.parse_args(argv)

    p = profile(args.input, args.key, args.isbn_field, args.toc_field)
    md = to_markdown(p, args.source)

    if args.out_md:
        with open(args.out_md, "w", encoding="utf-8") as fh:
            fh.write(md)
    else:
        print(md)

    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as fh:
            json.dump(p, fh, ensure_ascii=False, indent=2)

    if args.manifest_stub:
        stub = manifest_stub(p, args.source, args.input)
        with open(args.manifest_stub, "w", encoding="utf-8") as fh:
            json.dump(stub, fh, ensure_ascii=False, indent=2)
        sys.stderr.write(f"manifest stub -> {args.manifest_stub}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
