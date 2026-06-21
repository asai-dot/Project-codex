"""床突合 — e-Gov 各号 anchor × 書式 → 記載事項の床 + 抜け漏れ + alias 要整備 (stdlib のみ).

§5(記載事項の床)の **last-mile**。`egov_fetch.py` が出した各号 anchor(top-down 正準) と、
N冊の書式(bottom-up 実務) を `requirement_floor` で突合し、さらに **curation レンズ**を足す:

  - 各号 anchor の `名称` は条文本文そのまま(長文)。書式の短い記載事項と部分一致しないことがある。
    被覆 0 の anchor を **alias 要整備**として surface し、人手 curation の的を絞る。

これは「e-Gov を回したら raw をコミット → 後続(床突合)は番頭が担当」の後続側。anchors が落ちれば
そのまま通る。anchors も forms も無い現状はテスト(合成 + fixture 由来 anchor)で配線を固定する。

入力:
  --anchors : egov_fetch の出力 JSON (items:[{id,名称,号,aliases}]) または同形 list
  --forms   : 書式 [{id,記載事項:[...],source_family?}]
  --draft   : (任意) ドラフトの記載事項 → 抜け漏れ検出
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from requirement_floor import _load, analyze_floor, check_omissions


def reconcile_floor(anchors: list[dict], forms: list[dict],
                    draft: list | None = None) -> dict:
    """各号 anchor × 書式 → 床 + (任意)抜け漏れ + alias 要整備。"""
    floor = analyze_floor(anchors, forms)
    # 被覆 0 の各号 = どの書式も書いていない。条件付の可能性もあるが、anchor 名称(長文)が
    # 書式の短語と一致しない「マッチ漏れ」が多い → alias 整備の的。
    curation_needed = [r for r in floor["statutory_conditional"]
                       if r["coverage"].startswith("0/")]
    out = {"floor": floor, "curation_needed": curation_needed}
    if draft is not None:
        out["omissions"] = check_omissions(draft, anchors, floor)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="床突合 (e-Gov 各号 × 書式)")
    ap.add_argument("--anchors", required=True, help="egov_fetch の anchors JSON (items:[...])")
    ap.add_argument("--forms", required=True, help="書式 JSON [{id,記載事項:[...]}]")
    ap.add_argument("--draft", help="ドラフトの記載事項 (抜け漏れ検出)")
    args = ap.parse_args(argv)

    anchors = _load(Path(args.anchors))
    forms = _load(Path(args.forms))
    res = reconcile_floor(anchors, forms, _load(Path(args.draft)) if args.draft else None)
    floor = res["floor"]

    print(f"各号 anchor {len(anchors)} × 書式 {floor['n_forms']}冊"
          + ("  ⚠独立性低" if floor["independence_warning"] else ""))
    print(f"■ 法定の床(全書式一致・落とせば無効) {len(floor['statutory_floor'])}件:")
    for r in floor["statutory_floor"]:
        print(f"    [{r.get('号','')}] {r['名称'][:40]}  ({r['coverage']})")
    if floor["established_practice_floor"]:
        print(f"■ 実務必須(条文外) {len(floor['established_practice_floor'])}件: "
              + ", ".join(r["名称"] for r in floor["established_practice_floor"]))
    if res["curation_needed"]:
        print(f"■ alias 要整備(被覆0・条文本文が書式短語と未マッチ) {len(res['curation_needed'])}件:")
        for r in res["curation_needed"]:
            print(f"    [{r.get('号','')}] {r['名称'][:40]} … aliases に短縮名を足すと拾える")
    if "omissions" in res:
        o = res["omissions"]
        print("\n=== 抜け漏れ ===" + ("  ✅床を満たす" if o["ok"] else ""))
        for r in o["missing_statutory"]:
            print(f"  ❌致命傷(無効): {r['名称'][:40]} [{r.get('号','')}] 欠落")
        for r in o["missing_practice"]:
            print(f"  ⚠却下リスク: {r['名称']}(実務必須) 欠落")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
