#!/usr/bin/env python3
"""
verify_processed_mark.py — processed化が controller/head 以外で起きてないか監査。
finalization_record の finalized_by を見る。
"""
import argparse, json, sys
from pathlib import Path

ALLOWED_FINALIZERS = {"head", "controller", "human", "head_controller"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True, type=Path)
    args = ap.parse_args()
    rec = json.loads(args.record.read_text())
    finalizer = rec.get("finalized_by")
    if rec.get("processed_mark_applied") and finalizer not in ALLOWED_FINALIZERS:
        print(f"[verify_processed_mark] VIOLATION: processed_mark by {finalizer}", file=sys.stderr)
        sys.exit(1)
    if rec.get("canonical_write_applied") and finalizer not in {"head", "controller", "human"}:
        print(f"[verify_processed_mark] VIOLATION: canonical_write by {finalizer}", file=sys.stderr)
        sys.exit(1)
    if not rec.get("request_sha256") or not rec.get("candidate_sha256"):
        print("[verify_processed_mark] VIOLATION: request_sha256/candidate_sha256 missing", file=sys.stderr)
        sys.exit(1)
    print("[verify_processed_mark] OK")


if __name__ == "__main__":
    main()
