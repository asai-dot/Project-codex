"""CLI: extract drafter-intent substantive-change candidates from commentary.

Usage:
    python -m scripts.drafterintent TEXTFILE --doc-id <id> \
        [--source-hint 一問一答|逐条解説|国会審議|通達] \
        [--law-work-id W] [--locator p.123] [--source-uri URI] [--out out/]

Output: T5 evidence JSONL + T2 substantive_change_assertion (candidate) JSONL +
summary with gate results. No DB writes.
"""
import argparse
import json
import sys

from .extract import extract_drafter_intent
from .emit import write_artifacts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="drafterintent")
    ap.add_argument("textfile")
    ap.add_argument("--doc-id", required=True)
    ap.add_argument("--source-hint", default=None)
    ap.add_argument("--law-work-id", default=None)
    ap.add_argument("--locator", default=None)
    ap.add_argument("--source-uri", default=None)
    ap.add_argument("--out", default="out")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args(argv)

    with open(args.textfile, encoding="utf-8") as f:
        text = f.read()
    evidences, assertions = extract_drafter_intent(
        text, doc_id=args.doc_id, source_type_hint=args.source_hint,
        law_work_id=args.law_work_id, locator=args.locator,
        source_uri=args.source_uri)
    run_id = args.run_id or args.doc_id
    summary = write_artifacts(evidences, assertions, args.out, run_id)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["all_gates_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
