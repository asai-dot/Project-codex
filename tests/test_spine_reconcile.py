"""spine × inventory 照合のテスト (同梱実データ + 合成・stdlib のみ)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from spine_reconcile import load, reconcile  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def test_real_inventory():
    root = Path(__file__).resolve().parents[1]
    spine = load(root / "pipeline" / "procedure_spine.json")
    inv = load(root / "pipeline" / "procedure_inventory.json")
    r = reconcile(spine, inv)
    # commercial_nonlitigation が過少解像(組織再編6手続)で検出される。
    under = {u["spine"] for u in r["spine_underresolved"]}
    check("commercial_nonlitigation" in under, "商事1類型の過少解像を検出")
    cn = next(u for u in r["spine_underresolved"] if u["spine"] == "commercial_nonlitigation")
    check(cn["n"] >= 5 and "合併" in cn["procedures"], "商事に合併等6手続がぶら下がる")
    # 通常清算(kind=procedure, spine_ref=null) は未マップ手続。
    check(any("通常清算" in x for x in r["unmapped_procedures"]), "通常清算=未マップ手続")
    # must_fix1: 観測10件 ≠ 手続8件(procedure=8 / dimension=1 / flow_steps=1)。
    check(r["procedure_items"] < r["inventory_items"], "観測件数と手続件数を分離")
    check(r["kind_counts"].get("procedure") == 8, "procedure は8件")
    # must_fix2: 法人類型 dimension を「未マップ実手続」に混ぜない。
    check(not any("法人類型" in x for x in r["unmapped_procedures"]), "dimensionは未マップ手続に入れない")
    check(any(o["kind"] == "dimension" for o in r["non_procedure_observations"]), "dimensionは別枠")
    # must_fix3: 旧 spine_no_evidence は not_observed_in_current_sample に改称。
    check("not_observed_in_current_sample" in r and "spine_no_evidence" not in r, "改称された")
    # must_fix4: source coverage を出す。
    check(r["source_book_count"] >= 1 and len(r["domain_coverage"]) >= 1, "coverage指標を出力")


def test_synthetic():
    spine = {"procedure_types": [
        {"id": "a", "name": "A"}, {"id": "b", "name": "B"}, {"id": "c", "name": "C"}]}
    inv = {"procedures": [
        {"name": "p1", "spine_ref": "a", "kind": "procedure", "source_book": "X", "系統": "民事"},
        {"name": "p2", "spine_ref": "a", "kind": "procedure", "source_book": "X", "系統": "民事"},
        {"name": "p3", "spine_ref": "b", "kind": "procedure", "source_book": "Y", "系統": "刑事"},
        {"name": "p4", "spine_ref": None, "kind": "procedure"},       # 未マップ手続
        {"name": "p5", "spine_ref": "zzz", "kind": "procedure"},      # 未知ref→未マップ手続
        {"name": "d1", "spine_ref": None, "kind": "dimension"},       # facet(手続でない)
        {"name": "s1", "spine_ref": "a", "kind": "flow_step"}]}       # 局面(手続でない)
    r = reconcile(spine, inv)
    check([u["spine"] for u in r["spine_underresolved"]] == ["a"], "a が過少解像(p1,p2)")
    check(set(r["unmapped_procedures"]) == {"p4", "p5"}, "null/未知refの手続のみ未マップ")
    check({o["name"] for o in r["non_procedure_observations"]} == {"d1", "s1"}, "dim/stepは別枠")
    check({x["id"] for x in r["not_observed_in_current_sample"]} == {"c"}, "未観測=c")
    check(r["procedure_items"] == 5 and r["inventory_items"] == 7, "手続5/観測7を分離")
    check(r["source_book_count"] == 2 and set(r["domain_coverage"]) == {"民事", "刑事"}, "coverage")


def main() -> int:
    for t in [test_real_inventory, test_synthetic]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
