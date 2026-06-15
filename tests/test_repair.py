"""repair 層 dry-run テスト (DDSELFHEAL Phase C0)。

固定する不変条件:
  * 物理書込ゼロ (writes_executed==0) / C0 では write_allowed 常に 0。
  * 各 repairer は raw を触らず派生フィールドのみ plan する・決定的・冪等。
  * whitelist 無しでは apply_guard が物理拒否。decision_log は append-only / chain ok。
stdlib のみ。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from repair_base import (  # noqa: E402
    DET_NO_CANONICAL, QUARANTINE_ONLY, SEMANTIC_IDENTITY, is_write_allowed_in_phase,
)
from repair_engine import _demo_books, run_repairs  # noqa: E402
from repair_normalize import NormalizeTitleRegen  # noqa: E402
from repair_offset import OffsetPageConvert  # noqa: E402
from repair_quarantine import QuarantineOrphan  # noqa: E402
from repair_sha import BodyShaRecompute  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


# ---- 各 repairer 独立 fixture -------------------------------------------------

def _offset_book(derived=False) -> dict:
    node = {"title": "第1章", "title_norm": "第1章", "depth": 1, "pdf_page": 9}
    if derived:
        node["print_page"] = 1
    return {"isbn": "1", "page_offset": {"offset": 8, "confidence": 1.0, "validated": True, "anchors": 3},
            "source_meta": {"s": {"isbn": "1", "title": "X", "source_sha256": "sha256:z"}},
            "sources": {"s": [node, {"title": "第2章", "title_norm": "第2章", "depth": 1, "pdf_page": 58}]}}


def test_offset_repairer() -> None:
    r = OffsetPageConvert()
    b = _offset_book()
    check(r.detect(b) is True, "offset: 検証済+未派生 → detect True")
    plan = r.plan(b)
    check(plan is not None and len(plan["changes"]) == 2, "offset: 2変更")
    check(all(c["field"] == "print_page" and c["before"] is None for c in plan["changes"]),
          "offset: 派生 print_page のみ")
    check(sorted(c["after"] for c in plan["changes"]) == [1, 50], "offset: 8 変換 (9->1,58->50)")
    check(r.plan(b) == plan, "offset: plan 決定的")
    check(b["sources"]["s"][0].get("print_page") is None, "offset: raw 無副作用")
    # 冪等: 既に派生済の node は対象外。
    b2 = _offset_book(derived=True)
    plan2 = r.plan(b2)
    check(plan2 is None or all(c["locator"] != "s#0" for c in plan2["changes"]),
          "offset: 派生済 node は再対象にしない (冪等)")
    # 未検証 offset は適用外。
    bad = _offset_book(); bad["page_offset"]["validated"] = False
    check(r.detect(bad) is False, "offset: 未検証は detect False")


def test_sha_repairer() -> None:
    r = BodyShaRecompute()
    b = {"isbn": "1", "source_meta": {"s": {"source_content": "abc"}}, "sources": {}}
    check(r.detect(b) is True, "sha: 内容あり・sha欠落 → detect True")
    plan = r.plan(b)
    check(plan["changes"][0]["field"] == "source_sha256", "sha: source_sha256 を派生")
    check(plan["changes"][0]["after"].startswith("sha256:"), "sha: sha256 値")
    check(r.plan(b) == plan, "sha: 決定的")
    # 冪等: sha 既存なら対象外。
    b2 = {"isbn": "1", "source_meta": {"s": {"source_content": "abc", "source_sha256": "sha256:x"}}, "sources": {}}
    check(r.detect(b2) is False, "sha: sha 既存は detect False")
    # 内容なしは推測しない。
    b3 = {"isbn": "1", "source_meta": {"s": {"title": "X"}}, "sources": {}}
    check(r.detect(b3) is False, "sha: 内容未解決は適用外")


def test_normalize_repairer() -> None:
    r = NormalizeTitleRegen()
    b = {"isbn": "1", "source_meta": {}, "sources": {"s": [{"title": "Ｑ＆Ａ　民法"}]}}
    check(r.detect(b) is True, "normalize: title_norm 欠落 → detect True")
    plan = r.plan(b)
    c = plan["changes"][0]
    check(c["field"] == "title_norm" and c["before"] is None, "normalize: title_norm を派生")
    check(c["after"] and "　" not in c["after"], "normalize: 正規化済 (空白除去)")
    check(r.plan(b) == plan, "normalize: 決定的")
    check(b["sources"]["s"][0].get("title_norm") is None, "normalize: raw title 無副作用")
    # 冪等: 一致済は対象外。
    b2 = {"isbn": "1", "source_meta": {}, "sources": {"s": [{"title": "民法", "title_norm": "民法"}]}}
    check(r.detect(b2) is False, "normalize: 一致済は detect False")


def test_quarantine_repairer() -> None:
    r = QuarantineOrphan()
    b = {"isbn": "1", "source_meta": {},
         "sources": {"a": [{"title": "甲", "title_norm": "甲"}], "b": [{"title": "乙", "title_norm": "乙"}]}}
    check(r.detect(b) is True, "quarantine: cross-source 不一致 → orphan detect True")
    plan = r.plan(b)
    check(all(c["field"] == "quarantine_reason" for c in plan["changes"]), "quarantine: reason 付与")
    check(all(c["after"] == "orphan_no_cross_source_match" for c in plan["changes"]), "quarantine: reason_code")
    check(r.repair_class == QUARANTINE_ONLY, "quarantine: class=quarantine_only")
    # 一致するソースは orphan でない。
    b2 = {"isbn": "1", "source_meta": {},
          "sources": {"a": [{"title": "甲", "title_norm": "甲"}], "b": [{"title": "甲", "title_norm": "甲"}]}}
    check(r.detect(b2) is False, "quarantine: cross-source 一致は orphan なし")
    # 冪等: 既に隔離印あり。
    b3 = {"isbn": "1", "source_meta": {},
          "sources": {"a": [{"title": "甲", "title_norm": "甲", "quarantine_reason": "x"}],
                      "b": [{"title": "乙", "title_norm": "乙", "quarantine_reason": "x"}]}}
    check(r.detect(b3) is False, "quarantine: 隔離済は detect False (冪等)")


# ---- engine (全 repairer dry-run) --------------------------------------------

def test_engine_dryrun_no_write() -> None:
    res = run_repairs(_demo_books(), whitelist={"9784000000010"}, rollback_present=True)
    check(res["report_only"] is True, "report-only")
    check(res["writes_executed"] == 0, "物理書込ゼロ")
    check(res["all_plans_deterministic"] is True, "全 plan 決定的")
    # 4 repairer すべてが showcase で発火。
    for name in ["offset_page_convert", "body_sha_recompute", "normalize_title_regen", "quarantine_orphan"]:
        check(name in res["by_repairer"], f"{name} が発火")
    # C0: 実書込許可は常に 0 / 各 manifest も write_executed False。
    check(res["write_allowed_count"] == 0, "C0 write_allowed_count=0")
    check(all(m["write_executed"] is False for m in res["manifests"]), "全 manifest write_executed False")
    check(all(m["write_allowed"] is False for m in res["manifests"]), "C0 全 manifest write_allowed False")
    # quarantine 系 manifest の class。
    qm = [m for m in res["manifests"] if m["repairer"] == "quarantine_orphan"]
    check(qm and qm[0]["repair_class"] == QUARANTINE_ONLY, "quarantine manifest class")


def test_whitelist_physical_refusal() -> None:
    res = run_repairs(_demo_books(), whitelist=None, rollback_present=True)
    check(all(m["gate_result"]["allowed"] is False for m in res["manifests"]),
          "whitelist 無しは全 gate 不許可")
    check(all("whitelist_required" in m["gate_result"]["refusals"] for m in res["manifests"]),
          "whitelist_required 拒否")


def test_phase_gate_semantics() -> None:
    check(is_write_allowed_in_phase(DET_NO_CANONICAL, "C0") is False, "C0 は DET 不可")
    check(is_write_allowed_in_phase(DET_NO_CANONICAL, "C1") is True, "C1 は DET 可")
    check(is_write_allowed_in_phase(QUARANTINE_ONLY, "C1") is True, "C1 は quarantine 可")
    check(is_write_allowed_in_phase(SEMANTIC_IDENTITY, "C2") is False, "semantic は C2 でも不可")


def test_decision_log_chain() -> None:
    with tempfile.TemporaryDirectory() as td:
        dl = Path(td) / "repair_decisions.jsonl"
        res = run_repairs(_demo_books(), whitelist={"9784000000010"},
                          rollback_present=True, decision_log_path=dl)
        check(res["decision_log_chain"]["ok"] is True, "decision_log chain ok")
        check(res["decision_log_chain"]["count"] == res["manifest_count"],
              "repair_planned が manifest 数だけ記録")
        check(all(m["decision_log_hash"] for m in res["manifests"]), "全 manifest に log hash")


def main() -> int:
    for t in [test_offset_repairer, test_sha_repairer, test_normalize_repairer,
              test_quarantine_repairer, test_engine_dryrun_no_write,
              test_whitelist_physical_refusal, test_phase_gate_semantics,
              test_decision_log_chain]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
