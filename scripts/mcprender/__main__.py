"""CLI: render assembler output into safe MCP both-sides payloads.

Usage:
    python -m scripts.mcprender --resolved out/resolved_assertions_RUN.jsonl \
        --disputes out/disputes_RUN.jsonl [--formal-notes notes.json] \
        --out out/ --run-id RUN

--formal-notes: optional JSON { "art:415": "2020-04-01 改正で条文変更（lawtime: superseded）" }
Output: mcp_provision_views JSONL + Markdown + summary with gate results. No DB writes.
"""
import argparse
import json
import sys

from .render import render_all
from .emit import write_artifacts


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mcprender")
    ap.add_argument("--resolved", required=True)
    ap.add_argument("--disputes", required=True)
    ap.add_argument("--formal-notes", default=None)
    ap.add_argument("--out", default="out")
    ap.add_argument("--run-id", default="render")
    args = ap.parse_args(argv)

    resolved = _read_jsonl(args.resolved)
    disputes = _read_jsonl(args.disputes)
    formal_notes = json.load(open(args.formal_notes, encoding="utf-8")) if args.formal_notes else {}
    views = render_all(resolved, disputes, formal_notes)
    summary = write_artifacts(views, args.out, args.run_id)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["all_gates_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
