"""CLI: extract case-treatment candidates from a Japanese legal text file.

Usage:
    python -m scripts.casetreatment TEXTFILE --doc-id <id> \
        [--source-type court|scholar|treatise|practitioner] [--out out/]

Output: candidate JSONL + summary with gate results. No DB writes.
"""
import argparse
import json
import sys

from .extract import extract_treatments
from .emit import write_artifacts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="casetreatment")
    ap.add_argument("textfile")
    ap.add_argument("--doc-id", required=True)
    ap.add_argument("--source-type", default="court")
    ap.add_argument("--out", default="out")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args(argv)

    with open(args.textfile, encoding="utf-8") as f:
        text = f.read()
    cands = extract_treatments(text, doc_id=args.doc_id,
                               source_type=args.source_type)
    run_id = args.run_id or args.doc_id
    summary = write_artifacts(cands, args.out, run_id)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["all_gates_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
