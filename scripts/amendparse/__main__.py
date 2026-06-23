"""CLI: 改め文テキスト → gold-shaped (article_path, delta_kind) JSONL.

    python -m scripts.amendparse --in amendment.txt --out out/gold_from_amendment

Emits:
  <out>.gold.jsonl   {article_path, delta_kind, operation, new_path, source}
                     ＝scripts.eval の gold として使える（--key article_path --label delta_kind）
  <out>_summary.json operation/delta_kind 別件数・unknown 件数

入力は改正法の改め文テキスト（改正法 標準 XML から Sentence を連結したものでも可）。
real 改め文 の取得は e-Gov 法令API v2（改正履歴）等が一次源（本サンドボックスは allowlist 外 403）。
"""
from __future__ import annotations

import argparse
import json
import os

from .parse import parse_amendments


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="scripts.amendparse")
    ap.add_argument("--in", dest="inp", required=True, help="改め文テキストファイル")
    ap.add_argument("--out", required=True, help="出力プレフィックス")
    ap.add_argument("--source", default=None, help="出典ラベル（改正法令番号など）")
    args = ap.parse_args(argv)

    with open(args.inp, encoding="utf-8") as f:
        text = f.read()
    amends = parse_amendments(text)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    n_unknown = 0
    by_kind: dict = {}
    by_op: dict = {}
    with open(f"{args.out}.gold.jsonl", "w", encoding="utf-8") as f:
        for a in amends:
            by_kind[a.delta_kind] = by_kind.get(a.delta_kind, 0) + 1
            by_op[a.operation] = by_op.get(a.operation, 0) + 1
            if a.delta_kind == "unknown":
                n_unknown += 1
            row = a.to_dict()
            row["source"] = args.source
            row["verified"] = "official_amendment_text"  # provenance, not eyeballed
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "input": args.inp, "source": args.source,
        "operations": len(amends),
        "unknown": n_unknown,
        "by_delta_kind": dict(sorted(by_kind.items())),
        "by_operation": dict(sorted(by_op.items())),
    }
    with open(f"{args.out}_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
