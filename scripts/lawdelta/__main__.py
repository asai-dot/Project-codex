"""CLI: compute textual deltas between two consolidated revisions.

Usage:
    python -m scripts.lawdelta OLD NEW --law-id 129AC0000000089 \
        --from-rev <law_revision_id> --to-rev <law_revision_id> \
        --snapshot-id <source_snapshot_id> [--law-work-id W] [--out out/]

OLD/NEW: e-Gov 法令標準XML (.xml) or article JSONL fixtures (.jsonl).
Output: JSONL rows (T1 contract) + summary with gate results. No DB writes.
"""
import argparse
import sys

from .parse_egov import load_articles
from .align import compute_deltas
from .emit import write_artifacts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="lawdelta")
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--law-id", required=True)
    ap.add_argument("--from-rev", required=True)
    ap.add_argument("--to-rev", required=True)
    ap.add_argument("--snapshot-id", required=True)
    ap.add_argument("--law-work-id", default=None)
    ap.add_argument("--out", default="out")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args(argv)

    old_units = load_articles(args.old)
    new_units = load_articles(args.new)
    records = compute_deltas(
        old_units, new_units,
        law_id=args.law_id, from_rev=args.from_rev, to_rev=args.to_rev,
        snapshot_id=args.snapshot_id, law_work_id=args.law_work_id,
    )
    run_id = args.run_id or f"{args.law_id}_{args.from_rev[-8:]}_{args.to_rev[-8:]}"
    summary = write_artifacts(records, args.out, run_id)
    import json
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["all_gates_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
