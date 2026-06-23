"""CLI: score a producer's JSONL against a gold JSONL on a key/label pair.

Examples
--------
lawdelta delta_kind precision/recall, keyed by article_path::

    python -m scripts.eval --task lawdelta \
        --gold tests/gold/lawdelta_demo_minpo.gold.jsonl \
        --pred out/law_textual_delta_demo_minpo.jsonl \
        --key article_path --label delta_kind \
        --out out/eval_lawdelta_demo

drafterintent change_type, keyed by assertion_key (pattern_id also works)::

    python -m scripts.eval --task drafter \
        --gold tests/gold/drafter_demo.gold.jsonl \
        --pred out/drafter_substantive_assertions_ichimon_minpo_2017.jsonl \
        --key assertion_key --label change_type --out out/eval_drafter_demo

An empty / missing gold file is a no-op (exit 0): the harness can sit in CI
before any labels exist. ``--min-f1`` only bites once gold is non-empty.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .metrics import evaluate, load_labeled


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="scripts.eval")
    ap.add_argument("--task", required=True, help="label for the report (e.g. lawdelta)")
    ap.add_argument("--gold", required=True, help="gold JSONL path")
    ap.add_argument("--pred", required=True, help="prediction JSONL path")
    ap.add_argument("--key", required=True, help="join field (e.g. article_path)")
    ap.add_argument("--label", required=True, help="compared field (e.g. delta_kind)")
    ap.add_argument("--out", default=None, help="output prefix (writes <prefix>_summary.json)")
    ap.add_argument("--min-f1", type=float, default=None,
                    help="fail (exit 2) if micro-F1 below this AND gold is non-empty")
    args = ap.parse_args(argv)

    gold = load_labeled(args.gold, args.key, args.label)
    pred = load_labeled(args.pred, args.key, args.label)
    ev = evaluate(gold, pred)
    report = {"task": args.task, "key": args.key, "label": args.label,
              "gold_path": args.gold, "pred_path": args.pred, **ev.to_dict()}

    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(f"{args.out}_summary.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    if ev.empty:
        print(f"[eval:{args.task}] no gold labels yet "
              f"(pred rows={ev.n_pred}); skipping scoring.")
        return 0

    micro = ev.micro()
    print(f"[eval:{args.task}] keys={ev.n_keys} gold={ev.n_gold} pred={ev.n_pred} "
          f"micro_P={micro['precision']} micro_R={micro['recall']} micro_F1={micro['f1']}")
    for s in report["per_label"]:
        print(f"  {s['label']:<28} P={s['precision']:.3f} "
              f"R={s['recall']:.3f} F1={s['f1']:.3f} (n={s['support']})")

    if args.min_f1 is not None and micro["f1"] < args.min_f1:
        print(f"[eval:{args.task}] micro-F1 {micro['f1']} < min {args.min_f1}",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
