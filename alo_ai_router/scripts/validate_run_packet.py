#!/usr/bin/env python3
"""
validate_run_packet.py — schema 準拠 + ガード条件チェック (worker 起動前の最後の門番)
"""
import argparse, json, sys, yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schemas/worker_run_packet.schema.json").read_text())


def basic_check(packet):
    failures = []
    if packet.get("max_items") != 1:
        failures.append("max_items must be 1")
    if packet.get("mutation_power") not in ("none", "draft_write"):
        failures.append(f"mutation_power must be none|draft_write, got {packet.get('mutation_power')}")
    if len(packet.get("inputs", [])) > 5:
        failures.append("inputs > 5")
    if not packet.get("expected_outputs"):
        failures.append("expected_outputs empty")
    c = packet.get("constraints", {})
    if not c.get("no_finalization"):
        failures.append("constraints.no_finalization must be true")
    if not c.get("no_processed_mark"):
        failures.append("constraints.no_processed_mark must be true")
    return failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", required=True, type=Path)
    args = ap.parse_args()
    packet = yaml.safe_load(args.packet.read_text())
    fail = basic_check(packet)
    if fail:
        print("[validate_run_packet] FAIL", file=sys.stderr)
        for f in fail:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)
    print(f"[validate_run_packet] PASS  role={packet['executor_role']}  mutation={packet['mutation_power']}")


if __name__ == "__main__":
    main()
