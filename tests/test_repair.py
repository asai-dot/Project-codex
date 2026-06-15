"""repair 層 dry-run テスト (DDSELFHEAL Phase C0)。

固定する不変条件:
  * 物理書込ゼロ (writes_executed==0)。
  * C0 では write_allowed が常に 0 (phase が実書込を許さない)。
  * raw pdf_page を触らず print_page を派生する plan のみ。
  * 冪等: print_page 派生済の book は detect False (no-op)。plan は決定的。
  * whitelist 無しでは apply_guard が物理拒否 (whitelist_required)。
  * decision_log は append-only / chain ok。
stdlib のみ。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from repair_base import DET_NO_CANONICAL, SEMANTIC_IDENTITY, is_write_allowed_in_phase  # noqa: E402
from repair_engine import _demo_books, run_repairs  # noqa: E402
from repair_offset import OffsetPageConvert  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def test_repairer_detect_and_plan() -> None:
    r = OffsetPageConvert()
    books = _demo_books()
    b0, b1, b2 = books
    check(r.detect(b0) is True, "検証済 offset + 未派生ノード → detect True")
    check(r.detect(b1) is False, "print_page 派生済 → detect False (冪等)")
    check(r.detect(b2) is False, "offset 未検証 → detect False")

    plan = r.plan(b0)
    check(plan is not None and len(plan["changes"]) == 2, "2ノード分の plan")
    # raw pdf_page を触らない: change は print_page のみ、before は None。
    check(all(c["field"] == "print_page" and c["before"] is None for c in plan["changes"]),
          "派生 print_page のみ (raw 不変)")
    # offset=8: pdf 9 -> print 1, pdf 58 -> print 50。
    afters = sorted(c["after"] for c in plan["changes"])
    check(afters == [1, 50], f"offset 変換が正しい (got {afters})")
    # plan は決定的。
    check(r.plan(b0) == plan, "plan は決定的")
    # raw データが書き換わっていない (plan は副作用なし)。
    check(b0["sources"]["legallib"][0].get("print_page") is None, "raw に副作用なし")


def test_engine_dryrun_no_write() -> None:
    res = run_repairs(_demo_books(), whitelist={"9784000000010"}, rollback_present=True)
    check(res["report_only"] is True, "report-only")
    check(res["writes_executed"] == 0, "物理書込ゼロ")
    check(res["manifest_count"] == 1, "plan 対象は1冊のみ (b0)")
    check(res["all_plans_deterministic"] is True, "全 plan 決定的")
    m = res["manifests"][0]
    check(m["repair_class"] == DET_NO_CANONICAL, "class=deterministic_no_canonical_write")
    check(m["write_executed"] is False, "manifest write_executed False")
    # C0 は実書込を許さない → whitelist 通過でも write_allowed False。
    check(m["write_allowed"] is False, "C0 は write_allowed False (phase gate)")
    check(m["rollback_bundle"] is not None, "rollback bundle あり")
    # rollback は before/after を入替 (可逆)。
    rb = m["rollback_bundle"]["changes"][0]
    check(rb["before"] is not None and rb["after"] is None, "rollback は print_page を戻す")
    check(res["write_allowed_count"] == 0, "C0 write_allowed_count=0")


def test_whitelist_physical_refusal() -> None:
    # whitelist 無し → apply_guard が whitelist_required で拒否。
    res = run_repairs(_demo_books(), whitelist=None, rollback_present=True)
    m = res["manifests"][0]
    check(m["gate_result"]["allowed"] is False, "whitelist 無しは gate 不許可")
    check("whitelist_required" in m["gate_result"]["refusals"], "whitelist_required 拒否")


def test_phase_gate_semantics() -> None:
    # C0: 何も実書込許可しない。C1: DET_NO_CANONICAL 許可。semantic はどの phase も不可。
    check(is_write_allowed_in_phase(DET_NO_CANONICAL, "C0") is False, "C0 は DET 不可")
    check(is_write_allowed_in_phase(DET_NO_CANONICAL, "C1") is True, "C1 は DET 可")
    check(is_write_allowed_in_phase(SEMANTIC_IDENTITY, "C2") is False, "semantic は C2 でも不可")


def test_decision_log_chain() -> None:
    with tempfile.TemporaryDirectory() as td:
        dl = Path(td) / "repair_decisions.jsonl"
        res = run_repairs(_demo_books(), whitelist={"9784000000010"},
                          rollback_present=True, decision_log_path=dl)
        check(res["decision_log_chain"]["ok"] is True, "decision_log chain ok")
        check(res["decision_log_chain"]["count"] == 1, "repair_planned 1件記録")
        check(res["manifests"][0]["decision_log_hash"] is not None, "manifest に log hash")


def main() -> int:
    for t in [test_repairer_detect_and_plan, test_engine_dryrun_no_write,
              test_whitelist_physical_refusal, test_phase_gate_semantics,
              test_decision_log_chain]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
