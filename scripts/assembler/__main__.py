"""CLI: assemble producer outputs into disputes.

Usage:
    python -m scripts.assembler --out out/ --run-id RUN \
        [--drafter FILE ...] [--interpretation FILE ...] \
        [--treatment FILE --bindings BINDINGS.json]

- --drafter         drafterintent substantive-assertion JSONL (tier-2)
- --interpretation  pre-normalized interpretation_transition JSONL (court/scholar)
- --treatment       casetreatment candidate JSONL (needs --bindings)
- --bindings        JSON: { dedup_key: {article_path, law_work_id?, doctrine_label?} }

Output: resolved_assertions / assertion_review_events / disputes JSONL +
summary with gate results. No DB writes.
"""
import argparse
import json
import sys
from datetime import datetime, timezone

from .adapters import (from_drafter_rows, from_interpretation_rows,
                       from_treatment_rows)
from .assemble import assemble
from .emit import write_artifacts


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="assembler")
    ap.add_argument("--drafter", action="append", default=[])
    ap.add_argument("--interpretation", action="append", default=[])
    ap.add_argument("--treatment", default=None)
    ap.add_argument("--bindings", default=None)
    ap.add_argument("--out", default="out")
    ap.add_argument("--run-id", default="assemble")
    ap.add_argument("--now", default=None, help="ISO timestamp (test determinism)")
    args = ap.parse_args(argv)

    norm = []
    for p in args.drafter:
        norm += from_drafter_rows(_read_jsonl(p))
    for p in args.interpretation:
        norm += from_interpretation_rows(_read_jsonl(p))
    if args.treatment:
        bindings = json.load(open(args.bindings, encoding="utf-8")) if args.bindings else {}
        norm += from_treatment_rows(_read_jsonl(args.treatment), bindings)

    now_iso = args.now or datetime.now(timezone.utc).isoformat()
    resolved, events, disputes = assemble(norm, now_iso=now_iso)
    summary = write_artifacts(resolved, events, disputes, args.out, args.run_id)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["all_gates_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
