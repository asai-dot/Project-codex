"""v0.3.1 安全コアのテスト: edition_identity + apply_guard (report-only).

DDLEGALLIBCONCORD v0.3.1 の P0-2 (edition identity gate) と
§3 blocking (apply_guard 7 gate) を合成ケースで固定する。stdlib のみ。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from apply_guard import GATES, evaluate_apply_gate, filter_appliable  # noqa: E402
from edition_identity import (  # noqa: E402
    INSUFFICIENT,
    MANUAL_RESOLVED,
    RESOLVED_SAME,
    SUSPECTED_DIFFERENT,
    classify_edition_identity,
    is_apply_allowed_identity,
)

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


# --- edition identity (P0-2) ---

def test_edition_identity() -> None:
    same = [
        {"source": "legallib", "isbn": "9784641046429", "title": "国際取引法", "publisher": "有斐閣", "year": "2018", "page_count": 380},
        {"source": "bencom", "isbn": "9784641046429", "title": "国際取引法", "publisher": "有斐閣", "year": "2018", "page_count": 384},
    ]
    check(classify_edition_identity(same)["status"] == RESOLVED_SAME, "ISBN一致→same")

    diff_isbn = [
        {"source": "a", "isbn": "9784641046429", "title": "国際取引法"},
        {"source": "b", "isbn": "9784641046436", "title": "国際取引法"},
    ]
    check(classify_edition_identity(diff_isbn)["status"] == SUSPECTED_DIFFERENT,
          "異なるISBN→suspected_different")

    diff_year = [
        {"source": "a", "title": "会社法", "publisher": "有斐閣", "year": "2015", "page_count": 500},
        {"source": "b", "title": "会社法", "publisher": "有斐閣", "year": "2021", "page_count": 560},
    ]
    check(classify_edition_identity(diff_year)["status"] == SUSPECTED_DIFFERENT,
          "刊行年違い→suspected_different (別版兆候)")

    big_page = [
        {"source": "a", "title": "民法", "publisher": "X", "year": "2020", "page_count": 200},
        {"source": "b", "title": "民法", "publisher": "X", "year": "2020", "page_count": 400},
    ]
    check(classify_edition_identity(big_page)["status"] == SUSPECTED_DIFFERENT,
          "page_count大幅差→suspected_different")

    single = [{"source": "a", "isbn": "9784641046429", "title": "X"}]
    check(classify_edition_identity(single)["status"] == INSUFFICIENT, "単一source→insufficient")

    weak = [{"source": "a", "title": "X"}, {"source": "b", "title": "X"}]
    check(classify_edition_identity(weak)["status"] == INSUFFICIENT,
          "title一致のみ(publisher無)→insufficient")

    check(classify_edition_identity(single, manual_override=MANUAL_RESOLVED)["status"]
          == MANUAL_RESOLVED, "owner手動解決→manual_resolved")

    check(is_apply_allowed_identity(RESOLVED_SAME) and is_apply_allowed_identity(MANUAL_RESOLVED),
          "resolved/manual は apply 可")
    check(not is_apply_allowed_identity(SUSPECTED_DIFFERENT)
          and not is_apply_allowed_identity(INSUFFICIENT), "suspected/insufficient は apply 不可")


# --- apply_guard 7 gate (§3) ---

def _ok_req(isbn="9784000000010"):
    return {
        "isbn": isbn,
        "unresolved_conflict_count": 0,
        "edition_identity_status": RESOLVED_SAME,
        "uses_pdf_authority": False,
        "pdf_observation_qualified": False,
        "rollback_bundle_present": True,
        "decision_log_append_only": True,
        "all_nodes_accounted_for": True,
    }


def test_apply_guard() -> None:
    wl = {"9784000000010"}
    r = evaluate_apply_gate(_ok_req(), whitelist=wl)
    check(r["allowed"] and not r["refusals"], "全 gate 通過→allowed")

    # whitelist 無し → 拒否 (create 含む全 write)
    check("whitelist_required" in evaluate_apply_gate(_ok_req(), whitelist=None)["refusals"],
          "whitelist None→拒否")
    check("whitelist_required" in evaluate_apply_gate(_ok_req("X"), whitelist=wl)["refusals"],
          "whitelist外→拒否")

    # unresolved conflict
    q = _ok_req(); q["unresolved_conflict_count"] = 2
    check("no_unresolved_conflict" in evaluate_apply_gate(q, whitelist=wl)["refusals"],
          "unresolved conflict→拒否")

    # edition identity 未解決
    q = _ok_req(); q["edition_identity_status"] = SUSPECTED_DIFFERENT
    check("edition_identity_resolved" in evaluate_apply_gate(q, whitelist=wl)["refusals"],
          "edition未解決→拒否")

    # PDF authority 使用だが unqualified
    q = _ok_req(); q["uses_pdf_authority"] = True; q["pdf_observation_qualified"] = False
    check("pdf_authority_qualified" in evaluate_apply_gate(q, whitelist=wl)["refusals"],
          "PDF unqualified→拒否")
    q["pdf_observation_qualified"] = True
    check(evaluate_apply_gate(q, whitelist=wl)["allowed"], "PDF qualified なら通過")

    # rollback / decision_log / accounting 欠如
    for k, gate in [("rollback_bundle_present", "rollback_bundle_present"),
                    ("decision_log_append_only", "decision_log_append_only"),
                    ("all_nodes_accounted_for", "all_nodes_accounted_for")]:
        q = _ok_req(); q[k] = False
        check(gate in evaluate_apply_gate(q, whitelist=wl)["refusals"], f"{k} 欠如→拒否")

    check(len(GATES) == 7, "gate は7つ")


def test_filter_appliable() -> None:
    wl = {"9784000000010", "9784000000027"}
    reqs = [
        _ok_req("9784000000010"),                                   # OK
        {**_ok_req("9784000000027"), "unresolved_conflict_count": 1},  # conflict
        _ok_req("9784000000099"),                                   # whitelist 外
    ]
    out = filter_appliable(reqs, whitelist=wl)
    check(out["allowed_isbns"] == ["9784000000010"], "通過は1件のみ")
    check(out["blocked_count"] == 2, "2件 blocked")
    check(out["refusal_counts"].get("no_unresolved_conflict") == 1, "conflict 集計")
    check(out["refusal_counts"].get("whitelist_required") == 1, "whitelist 集計")


def main() -> int:
    for t in [test_edition_identity, test_apply_guard, test_filter_appliable]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
