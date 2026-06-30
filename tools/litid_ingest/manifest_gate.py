#!/usr/bin/env python3
"""manifest_gate.py — raw_intake 投入の §7-A 契約ゲート (enforcement).

field_profile.py が出す manifest stub は「下書き」. 取得時メタ (TODO) が埋まらないまま
投入されると, append-only でも永久に取り戻せない (監査 must_fix #1). 本ゲートは manifest.json を
検証し, 必須フィールド欠落 / TODO 残り / 値域違反があれば **exit 1 で投入をブロック**する.

使い方:
  python3 manifest_gate.py raw_intake/legallib/20260618/manifest.json
  # PASS -> exit 0,  FAIL -> 違反を列挙して exit 1 (パイプラインの前段に置く)

read-only. manifest を書き換えない. 突合・promote もしない (監査 HOLD 据置).
"""
from __future__ import annotations

import argparse
import json
import re
import sys

# INGEST_SPEC v0.2 §7-A の必須フィールド
REQUIRED = [
    "source", "source_system", "fetched_at", "account", "fetch_method",
    "acquisition_path", "source_location", "rights_class", "medium_origin",
    "route_local_id", "key_field", "toc_origin", "extractor_version",
    "record_count", "files", "evidence_locator",
]

ENUMS = {
    "source": {"lionbolt", "bengo4", "legallib", "self_scan"},
    "rights_class": {"owned", "subscription_access", "mixed"},
    "medium_origin": {"digital", "paper_scan"},
    "toc_origin": {"publisher_html", "own_ocr", "unknown"},
}

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# 緩い ISO8601 (日付 or 日時, TZ任意). 厳密な暦検証はしない.
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?([.+\-Z].*)?)?$")


def _is_blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "") or v == [] or v == {}


def _has_todo(v) -> bool:
    return isinstance(v, str) and "TODO" in v


def validate(manifest: dict) -> list[str]:
    """違反メッセージのリストを返す. 空なら PASS."""
    errs: list[str] = []

    for f in REQUIRED:
        if f not in manifest:
            errs.append(f"missing required field: {f}")
        elif _is_blank(manifest[f]):
            errs.append(f"empty required field: {f}")
        elif _has_todo(manifest[f]):
            errs.append(f"unfilled TODO in field: {f}")

    for f, allowed in ENUMS.items():
        if f in manifest and not _is_blank(manifest[f]) and manifest[f] not in allowed:
            errs.append(f"{f}={manifest[f]!r} not in {sorted(allowed)}")

    # record_count: 正の整数
    rc = manifest.get("record_count")
    if rc is not None and not _is_blank(rc):
        if not isinstance(rc, int) or isinstance(rc, bool) or rc <= 0:
            errs.append(f"record_count must be positive int, got {rc!r}")

    # fetched_at: ISO 風
    fa = manifest.get("fetched_at")
    if isinstance(fa, str) and not _has_todo(fa) and fa.strip() and not ISO_RE.match(fa.strip()):
        errs.append(f"fetched_at not ISO-like: {fa!r}")

    # files[]: 非空リスト, 各 name + sha256(64hex)
    files = manifest.get("files")
    if isinstance(files, list) and files:
        for i, fe in enumerate(files):
            if not isinstance(fe, dict):
                errs.append(f"files[{i}] not an object")
                continue
            if _is_blank(fe.get("name")):
                errs.append(f"files[{i}].name empty")
            sha = fe.get("sha256")
            if _is_blank(sha) or _has_todo(sha):
                errs.append(f"files[{i}].sha256 missing")
            elif not SHA256_RE.match(str(sha)):
                errs.append(f"files[{i}].sha256 not 64-hex: {sha!r}")
    elif "files" in manifest and not isinstance(files, list):
        errs.append("files must be a non-empty list")

    return errs


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", help="manifest.json path")
    ap.add_argument("--quiet", action="store_true", help="PASS時に何も出さない")
    args = ap.parse_args(argv)

    try:
        with open(args.manifest, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"FAIL: cannot read manifest: {e}\n")
        return 1

    if not isinstance(manifest, dict):
        sys.stderr.write("FAIL: manifest must be a JSON object\n")
        return 1

    errs = validate(manifest)
    if errs:
        sys.stderr.write(f"GATE FAIL ({len(errs)}) — ingest blocked (v0.2 §7-A):\n")
        for e in errs:
            sys.stderr.write(f"  - {e}\n")
        return 1

    if not args.quiet:
        sys.stdout.write(
            f"GATE PASS — {args.manifest} "
            f"[source={manifest['source']}, records={manifest['record_count']}, "
            f"files={len(manifest['files'])}]\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
