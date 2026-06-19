"""spine(a-priori 24類型) × procedure_inventory(本から bottom-up) の照合 (stdlib のみ).

ドクトリン §5前の止揚「spine は上から作るな、本の業務一覧から立ち上げろ」の検算ツール。
経験的インベントリ(実データ)で、a-priori spine の **過少解像・欠落・未対応** を機械的に炙り出す。

GPT お目付け (20260619 DDPROGRESS PASS_WITH_NOTES) の意味補正を反映:
- inventory は kind 混在(procedure / dimension / flow_step)。**procedure だけを手続として数える**
  (`inventory_items` ≠ `procedure_items`)。dimension/flow_step を「未マップ実手続」と呼ばない。
- spine 側の未観測は「裏付け無し」ではなく **`not_observed_in_current_sample`**
  (現サンプル=数冊での未観測。粗さの実証ではない)。
- source coverage(冊数/系統)を併記し、サンプル依存を可視化する。

用語(kind の操作的定義は RESULT Q4 / dd_procedure_design §9 を正本とする):
- procedure   : 固有の目的・開始契機・根拠・局面列・終局状態を持つ過程(= 手続単位)。
- procedure_family : 複数 procedure を束ねる navigation 単位。
- procedure_variant: 同一 procedure の主体/法人類型/route 差で局面分岐するもの。
- flow_step   : procedure 内部の局面。単独で procedure ID を鋳造しない。
- dimension   : entity type / forum 等の直交 facet。
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

PROCEDURE_KIND = "procedure"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def reconcile(spine: dict, inventory: dict, underresolved_threshold: int = 2) -> dict:
    spine_ids = {t["id"] for t in spine.get("procedure_types", [])}
    spine_label = {t["id"]: t.get("name", t["id"]) for t in spine.get("procedure_types", [])}
    items = inventory.get("procedures", [])

    kind_counts = Counter(it.get("kind", "unknown") for it in items)

    # 解像度の対象は kind=procedure のみ。spine_ref ごとに手続を束ねる。
    by_ref: dict[str, list[str]] = {}
    unmapped_procedures: list[str] = []          # 手続なのに spine 対応類型が無い(真の欠落)
    non_procedure_observations: list[dict] = []   # dimension / flow_step 等(手続ではない観測)
    for it in items:
        kind = it.get("kind", "unknown")
        if kind != PROCEDURE_KIND:
            non_procedure_observations.append({"name": it["name"], "kind": kind})
            continue
        ref = it.get("spine_ref")
        if ref and ref in spine_ids:
            by_ref.setdefault(ref, []).append(it["name"])
        else:
            unmapped_procedures.append(it["name"])

    underresolved = [{"spine": rid, "spine_label": spine_label[rid], "n": len(names),
                      "procedures": names}
                     for rid, names in by_ref.items() if len(names) >= underresolved_threshold]
    underresolved.sort(key=lambda x: -x["n"])
    not_observed = sorted(spine_ids - set(by_ref))

    # source coverage: サンプル依存(数冊由来)を可視化。source_family が無ければ source_book を族とみなす。
    proc_items = [it for it in items if it.get("kind") == PROCEDURE_KIND]
    books = {it.get("source_book") for it in proc_items if it.get("source_book")}
    families = {it.get("source_family") or it.get("source_book")
                for it in proc_items if (it.get("source_family") or it.get("source_book"))}
    domains = {it.get("系統") for it in items if it.get("系統")}

    return {
        "spine_types": len(spine_ids),
        "inventory_items": len(items),
        "procedure_items": kind_counts.get(PROCEDURE_KIND, 0),
        "kind_counts": dict(kind_counts),
        "source_book_count": len(books),
        "source_family_count": len(families),
        "domain_coverage": sorted(d for d in domains if d),
        "spine_underresolved": underresolved,
        # 旧 spine_no_evidence。現サンプル(数冊)での未観測であり、粗さの実証ではない。
        "not_observed_in_current_sample": [{"id": i, "label": spine_label[i]} for i in not_observed],
        "unmapped_procedures": unmapped_procedures,
        "non_procedure_observations": non_procedure_observations,
    }


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="spine × inventory 照合")
    ap.add_argument("--spine", default=str(here / "pipeline" / "procedure_spine.json"))
    ap.add_argument("--inventory", default=str(here / "pipeline" / "procedure_inventory.json"))
    args = ap.parse_args(argv)
    r = reconcile(load(Path(args.spine)), load(Path(args.inventory)))
    kinds = " / ".join(f"{k}={v}" for k, v in sorted(r["kind_counts"].items()))
    print(f"spine {r['spine_types']}類型(roll-up) / 観測 {r['inventory_items']}件({kinds}) "
          f"→ 手続 {r['procedure_items']}件")
    print(f"  coverage: {r['source_book_count']}冊 / {r['source_family_count']}族 / "
          f"系統 {len(r['domain_coverage'])}({', '.join(r['domain_coverage'])})")
    print(f"■ 過少解像(分割/再分類 候補) {len(r['spine_underresolved'])}件:")
    for u in r["spine_underresolved"]:
        print(f"    {u['spine_label']} に {u['n']}手続: {', '.join(u['procedures'])}")
    print(f"■ 未マップ手続(spine 対応類型なし=欠落候補) {len(r['unmapped_procedures'])}件: "
          + ", ".join(r["unmapped_procedures"]))
    if r["non_procedure_observations"]:
        labels = [f"{o['name']}[{o['kind']}]" for o in r["non_procedure_observations"]]
        print(f"■ 手続でない観測(facet/局面) {len(labels)}件: " + ", ".join(labels))
    print(f"■ 現サンプル未観測の spine 類型 {len(r['not_observed_in_current_sample'])}件 "
          f"(not_observed_in_current_sample。粗さの実証ではない)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
