"""spine(a-priori 24類型) × procedure_inventory(本から bottom-up) の照合 (stdlib のみ).

ドクトリン §5前の止揚「spine は上から作るな、本の業務一覧から立ち上げろ」の検算ツール。
経験的インベントリ(実データ)で、a-priori spine の **過少解像・欠落・未対応** を機械的に炙り出す。

- spine_underresolved : 1 spine 類型に複数の実手続がぶら下がる → 分割候補
- spine_no_evidence   : spine にあるが本の裏付けが無い類型
- inventory_unmapped  : 実手続だが spine に対応類型が無い(spine_ref が null/未知)
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def reconcile(spine: dict, inventory: dict, underresolved_threshold: int = 2) -> dict:
    spine_ids = {t["id"] for t in spine.get("procedure_types", [])}
    spine_label = {t["id"]: t.get("name", t["id"]) for t in spine.get("procedure_types", [])}
    procs = inventory.get("procedures", [])

    # spine_ref ごとに、ぶら下がる実手続(kind=procedure のみを解像度の対象に)。
    by_ref: dict[str, list[str]] = {}
    unmapped: list[str] = []
    for p in procs:
        ref = p.get("spine_ref")
        if ref and ref in spine_ids:
            if p.get("kind") == "procedure":
                by_ref.setdefault(ref, []).append(p["name"])
        else:
            unmapped.append(p["name"])

    underresolved = [{"spine": rid, "spine_label": spine_label[rid], "n": len(names),
                      "procedures": names}
                     for rid, names in by_ref.items() if len(names) >= underresolved_threshold]
    underresolved.sort(key=lambda x: -x["n"])
    no_evidence = sorted(spine_ids - set(by_ref))
    return {
        "spine_types": len(spine_ids), "inventory_procedures": len(procs),
        "spine_underresolved": underresolved,
        "spine_no_evidence": [{"id": i, "label": spine_label[i]} for i in no_evidence],
        "inventory_unmapped": unmapped,
    }


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="spine × inventory 照合")
    ap.add_argument("--spine", default=str(here / "pipeline" / "procedure_spine.json"))
    ap.add_argument("--inventory", default=str(here / "pipeline" / "procedure_inventory.json"))
    args = ap.parse_args(argv)
    r = reconcile(load(Path(args.spine)), load(Path(args.inventory)))
    print(f"spine {r['spine_types']}類型 / 実手続 {r['inventory_procedures']}件")
    print(f"■ 過少解像(分割候補) {len(r['spine_underresolved'])}件:")
    for u in r["spine_underresolved"]:
        print(f"    {u['spine_label']} に {u['n']}手続: {', '.join(u['procedures'])}")
    print(f"■ spine 対応無し(未マップ実手続) {len(r['inventory_unmapped'])}件: "
          + ", ".join(r["inventory_unmapped"]))
    print(f"■ 裏付け無し spine 類型 {len(r['spine_no_evidence'])}件 (本がまだ無い)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
