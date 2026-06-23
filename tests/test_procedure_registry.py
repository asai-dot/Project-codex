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
    crosswalk, promotion_report, validate_family_membership, validate_registry,
    validate_transition)

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


def test_real_registry_v02_healthy():
    """v0.2 registry(商事再分類 candidate)が不変条件を満たす。owner_ratified は依然0件。"""
    reg = _load("pipeline/procedure_registry.json")
    spine_ids = {t["id"] for t in _load("pipeline/procedure_spine.json")["procedure_types"]}
    check(validate_registry(reg, spine_ids) == [], "v0.2 registry は健全")
    ratified = [e for e in reg["entries"] if e.get("status") == "owner_ratified"]
    check(ratified == [], "owner_ratified 0件のまま(本番 HOLD・自動鋳造しない)")
    check(all(e.get("status") == "candidate" for e in reg["entries"]), "全 entry が candidate 止め")
    # MF-1: family membership が family→6手続を張る。
    members = [m["procedure_id"] for m in reg["family_membership"]
               if m["family_id"] == "corporate_reorganization"]
    check(set(members) == {"merger", "company_split", "share_exchange", "share_transfer",
                           "entity_conversion", "share_delivery"}, "組織再編 family に6手続が membership")
    # MF-4: ordinary_liquidation は candidate。
    ol = next(e for e in reg["entries"] if e["id"] == "ordinary_liquidation")
    check(ol["status"] == "candidate" and ol.get("definition"), "通常清算=candidate+操作的定義")


def test_validate_invariants():
    # owner_ratified なのに ratify メタ無し → 違反。
    bad = {"entries": [{"id": "x", "name": "X", "kind": "procedure", "status": "owner_ratified"}]}
    errs = validate_registry(bad)
    check(any("ratified_by" in e for e in errs), "owner_ratified に ratify メタ必須")
    # MF-3: ratified_by/at だけでは不足(根拠類型/refs/note が要る)。
    meta_only = {"entries": [{"id": "x", "name": "X", "kind": "procedure", "status": "owner_ratified",
                              "ratified_by": "asai", "ratified_at": "2026-06-20"}]}
    check(any("ratification_basis_type" in e for e in validate_registry(meta_only)),
          "owner_ratified に ratification_basis_type 必須(MF-3)")
    # 根拠まで揃えば通る。
    good = {"entries": [{"id": "x", "name": "X", "kind": "procedure", "status": "owner_ratified",
                         "ratified_by": "asai", "ratified_at": "2026-06-20",
                         "ratification_basis_type": "owner_legal_judgment",
                         "ratification_basis_refs": ["owner note 1"],
                         "ratification_note": "owner の独立判断"}]}
    check(validate_registry(good) == [], "根拠付き owner_ratified は健全")
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


def test_family_membership_invariants():
    """MF-1: membership の参照/kind/自己参照/重複 を検査。"""
    base = [
        {"id": "fam", "name": "F", "kind": "procedure_family", "status": "candidate"},
        {"id": "p1", "name": "P1", "kind": "procedure", "status": "candidate"},
    ]
    ok = {"entries": base, "family_membership": [{"family_id": "fam", "procedure_id": "p1"}]}
    check(validate_family_membership(ok) == [], "正しい membership は健全")
    # 参照先なし。
    bad_ref = {"entries": base, "family_membership": [{"family_id": "fam", "procedure_id": "ghost"}]}
    check(any("ghost" in e for e in validate_family_membership(bad_ref)), "member 参照先なしを検出")
    # family_id が procedure_family でない。
    bad_kind = {"entries": base, "family_membership": [{"family_id": "p1", "procedure_id": "p1"}]}
    errs = validate_family_membership(bad_kind)
    check(any("procedure_family でない" in e for e in errs), "family が procedure_family 種でないと違反")
    check(any("自己参照" in e for e in errs), "自己参照を検出")
    # 重複。
    dup = {"entries": base, "family_membership": [
        {"family_id": "fam", "procedure_id": "p1"}, {"family_id": "fam", "procedure_id": "p1"}]}
    check(any("重複" in e for e in validate_family_membership(dup)), "重複 membership を検出")


def test_rollup_silent_narrowing_guard():
    """MF-2: rollup の意味縮小には supersession 記録を要求(説明文だけの暗黙縮小を弾く)。"""
    spine_ids = {"commercial_nonlitigation"}
    # keep_unchanged は supersession 不要。
    keep = {"entries": [], "rollup_notes": [
        {"rollup_id": "commercial_nonlitigation", "action": "keep_unchanged", "semantic": "..."}]}
    check(validate_registry(keep, spine_ids) == [], "keep_unchanged は記録不要で健全")
    # narrow なのに supersession 無し → 違反。
    narrow = {"entries": [], "rollup_notes": [
        {"rollup_id": "commercial_nonlitigation", "action": "narrow", "semantic": "..."}]}
    check(any("silent narrowing" in e for e in validate_registry(narrow, spine_ids)),
          "narrow に supersession 無しは違反(MF-2)")
    # supersession 記録を添えれば通る。
    narrow_ok = {"entries": [], "rollup_notes": [
        {"rollup_id": "commercial_nonlitigation", "action": "narrow", "semantic": "..."}],
        "supersession": [{"rollup_id": "commercial_nonlitigation", "note": "split 記録"}]}
    check(not any("silent narrowing" in e for e in validate_registry(narrow_ok, spine_ids)),
          "supersession 付き narrow は許容")


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
    for t in [test_lifecycle_transitions, test_real_registry_v02_healthy, test_validate_invariants,
              test_family_membership_invariants, test_rollup_silent_narrowing_guard,
              test_promotion_real_inventory_holds, test_promotion_eligibility_rules, test_crosswalk]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
