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
    # 通常清算/法人類型 は spine_ref=null → 未マップ。
    check(any("通常清算" in x for x in r["inventory_unmapped"]), "通常清算=spine未対応")


def test_synthetic():
    spine = {"procedure_types": [
        {"id": "a", "name": "A"}, {"id": "b", "name": "B"}, {"id": "c", "name": "C"}]}
    inv = {"procedures": [
        {"name": "p1", "spine_ref": "a", "kind": "procedure"},
        {"name": "p2", "spine_ref": "a", "kind": "procedure"},
        {"name": "p3", "spine_ref": "b", "kind": "procedure"},
        {"name": "p4", "spine_ref": None, "kind": "procedure"},      # 未マップ
        {"name": "p5", "spine_ref": "zzz", "kind": "procedure"}]}     # 未知ref→未マップ
    r = reconcile(spine, inv)
    check([u["spine"] for u in r["spine_underresolved"]] == ["a"], "a が過少解像(p1,p2)")
    check(set(r["inventory_unmapped"]) == {"p4", "p5"}, "null/未知ref は未マップ")
    check({x["id"] for x in r["spine_no_evidence"]} == {"c"}, "裏付け無し=c")


def main() -> int:
    for t in [test_real_inventory, test_synthetic]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
