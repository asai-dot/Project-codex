#!/usr/bin/env python3
"""
collect_run_result.py — worker が吐いた候補と run_summary を集めて、
schema検証 + self_grade と outcome の整合確認 + audit/finalization へ渡す状態に置く。
"""
import argparse, json, sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True, type=Path)
    ap.add_argument("--candidate", required=True, type=Path)
    args = ap.parse_args()
    s = json.loads(args.summary.read_text())
    out = {
        "request_id": s.get("request_id"),
        "run_id": s.get("run_id"),
        "executor": s.get("executor"),
        "outcome": s.get("outcome"),
        "self_grade": s.get("self_grade"),
        "caveats": s.get("caveats", []),
        "candidate_path": str(args.candidate),
        "ready_for_audit": s.get("outcome") == "candidate_produced" and s.get("self_grade") in ("A", "B"),
        "ready_for_finalization": False,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
