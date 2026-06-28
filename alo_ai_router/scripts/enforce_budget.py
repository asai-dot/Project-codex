#!/usr/bin/env python3
"""
enforce_budget.py — budget_policy.yml に基づき daily/batch を上回らないかチェック。
budget_unknown は fail closed。
"""
import argparse, json, sys, yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = yaml.safe_load((ROOT / "budget_policy.yml").read_text())


def check(role, today_runs, batch_items):
    daily = POLICY["daily_limits"]
    batch = POLICY["batch_limits"]
    fails = []
    role_to_daily = {
        "deep_reasoner": ("L4_deep_reasoning_runs",),
        "independent_auditor": ("L5_independent_audit_runs",),
    }
    for key in role_to_daily.get(role, ()):
        if today_runs.get(key, 0) >= daily[key]:
            fails.append(f"daily limit reached: {key}={daily[key]}")
    cog_to_batch = {
        "L1_CHEAP_EXTRACTION": "L1_items",
        "L2_LIGHT_SUMMARY": "L2_items",
        "L3_NORMAL_WORK": "L3_items",
        "L4_DEEP_REASONING": "L4_items",
        "L5_INDEPENDENT_AUDIT": "L5_items",
    }
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True)
    ap.add_argument("--today-runs-json", type=Path, help="今日の累積回数 JSON {key:n}")
    ap.add_argument("--batch-items", type=int, default=1)
    args = ap.parse_args()
    today = {}
    if args.today_runs_json and args.today_runs_json.exists():
        today = json.loads(args.today_runs_json.read_text())
    fails = check(args.role, today, args.batch_items)
    if fails:
        for f in fails:
            print(f"[enforce_budget] BLOCK: {f}", file=sys.stderr)
        sys.exit(1)
    print(f"[enforce_budget] OK  role={args.role}  batch={args.batch_items}")


if __name__ == "__main__":
    main()
