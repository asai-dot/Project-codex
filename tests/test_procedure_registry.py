"""procedure registry(L1) のテスト (合成 + 実データ・stdlib のみ).

三層化(L0観測→L1 registry→L2 roll-up)のゲートを検算。最重要の不変条件:
  - **自動昇格しない**: 実 inventory(単一source中心)からは candidate に1件も上がらない。
  - **owner_ratified は ratify メタ必須**: 自動で owner_ratified を鋳造できない。
実行: ``python tests/test_procedure_registry.py``。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from procedure_registry import (  # noqa: E402
    crosswalk, promotion_report, validate_registry, validate_transition)

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def _load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def test_lifecycle_transitions():
    check(validate_transition("observed", "candidate"), "observed→candidate 可")
    check(validate_transition("candidate", "owner_ratified"), "candidate→owner_ratified 可")
    check(not validate_transition("observed", "owner_ratified"), "observed→owner_ratified 直行不可")
    check(not validate_transition("superseded", "candidate"), "superseded は終端")


def test_validate_empty_registry_ok():
    reg = _load("pipeline/procedure_registry.json")
    check(validate_registry(reg) == [], "起票時の空 registry は健全")
    check(reg["entries"] == [], "owner_ratified 0件で起票(自動鋳造しない)")


def test_validate_invariants():
    # owner_ratified なのに ratify メタ無し → 違反。
    bad = {"entries": [{"id": "x", "name": "X", "kind": "procedure", "status": "owner_ratified"}]}
    errs = validate_registry(bad)
    check(any("ratified_by" in e for e in errs), "owner_ratified に ratify メタ必須")
    # ratify メタ付きなら通る。
    good = {"entries": [{"id": "x", "name": "X", "kind": "procedure", "status": "owner_ratified",
                         "ratified_by": "asai", "ratified_at": "2026-06-20"}]}
    check(validate_registry(good) == [], "ratify メタ付き owner_ratified は健全")
    # superseded の参照先が無い → 違反。
    dangling = {"entries": [{"id": "x", "name": "X", "kind": "procedure",
                             "status": "superseded", "superseded_by": "zzz"}]}
    check(any("superseded_by" in e for e in errs) or
          any("superseded_by=zzz" in e for e in validate_registry(dangling)), "supersession dangling 検出")
    # supersession 循環 → 違反。
    cyc = {"entries": [
        {"id": "a", "name": "A", "kind": "procedure", "status": "superseded", "superseded_by": "b"},
        {"id": "b", "name": "B", "kind": "procedure", "status": "superseded", "superseded_by": "a"}]}
    check(any("循環" in e for e in validate_registry(cyc)), "supersession 循環 検出")
    # legacy_rollup_id が spine に無い → 違反(spine_ids 指定時)。
    badroll = {"entries": [{"id": "x", "name": "X", "kind": "procedure", "status": "candidate",
                            "legacy_rollup_id": "nope"}]}
    check(any("legacy_rollup_id" in e for e in validate_registry(badroll, {"commercial_nonlitigation"})),
          "存在しない roll-up 参照を検出")


def test_promotion_real_inventory_holds():
    """実 inventory(単一source中心)からは candidate に1件も上がらない(must_fix7)。"""
    inv = _load("pipeline/procedure_inventory.json")
    rep = promotion_report(inv["procedures"], _load("pipeline/procedure_registry.json"))
    # procedure kind は8件(facet/局面は除外)。
    check(len(rep) == 8, "手続(kind=procedure)8件のみ評価")
    check(all(not r["eligible_for_candidate"] for r in rep), "単一source→自動昇格ゼロ(HOLD)")
    names = {r["name"] for r in rep}
    check("合併" in names and "清算(法人類型別" not in str(names), "facet/局面は候補に出さない")


def test_promotion_eligibility_rules():
    obs = [
        # 独立2族 → 適格。
        {"name": "p_two", "kind": "procedure", "source_book": "BookA"},
        {"name": "p_two", "kind": "procedure", "source_book": "BookB"},
        # 法令1 + 実務書1 → 適格。
        {"name": "p_auth", "kind": "procedure", "source_book": "e-Gov", "source_kind": "statutory"},
        {"name": "p_auth", "kind": "procedure", "source_book": "BookC", "source_kind": "practice"},
        # 単一族 → 不適格。
        {"name": "p_one", "kind": "procedure", "source_book": "BookA"},
        # 同一族2回 → 独立でないので不適格。
        {"name": "p_same", "kind": "procedure", "source_family": "Fam", "source_book": "B1"},
        {"name": "p_same", "kind": "procedure", "source_family": "Fam", "source_book": "B2"},
    ]
    rep = {r["name"]: r for r in promotion_report(obs)}
    check(rep["p_two"]["eligible_for_candidate"], "独立2族=適格")
    check(rep["p_auth"]["eligible_for_candidate"], "法令+実務=適格")
    check(not rep["p_one"]["eligible_for_candidate"], "単一source=不適格")
    check(not rep["p_same"]["eligible_for_candidate"], "同一上流2回は独立でない=不適格")


def test_crosswalk():
    spine = _load("pipeline/procedure_spine.json")
    reg = {"entries": [
        {"id": "merger", "name": "合併", "kind": "procedure", "status": "candidate",
         "legacy_rollup_id": "commercial_nonlitigation"},
        {"id": "orphan", "name": "O", "kind": "procedure", "status": "candidate"}]}
    cw = crosswalk(reg, spine)
    check(cw["mapped"] == 1 and cw["unmapped_entries"] == ["orphan"], "roll-up 対応/未対応を分離")
    check("commercial_nonlitigation" in cw["rollups_used"], "使用 roll-up を記録")


def main() -> int:
    for t in [test_lifecycle_transitions, test_validate_empty_registry_ok, test_validate_invariants,
              test_promotion_real_inventory_holds, test_promotion_eligibility_rules, test_crosswalk]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
