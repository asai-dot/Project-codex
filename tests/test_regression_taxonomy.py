"""regression_taxonomy テスト — defect 分類と修復前後の回帰検出を検証。

GPT 監査 (DDSELFHEAL-C0) が C1 前必須に指定した regression taxonomy。安全不変条件:
  ★ 決定的 repair が defect を消すのは可、新規 defect (特に P0) を作るのは回帰。
  ★ 未知 defect コードは黙って捨てず unknown_codes に出す。
report-only・stdlib のみ。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from data_health import book_health  # noqa: E402
from regression_taxonomy import classify, classify_defects, regression_diff  # noqa: E402
from thresholds import load_thresholds  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def test_classify_known_and_unknown() -> None:
    c = classify("L3:body_sha_absent")
    check(c["family"] == "body_integrity" and c["c1_relevant"], "sha は body_integrity / C1 対象")
    check(classify("L3:edition_unresolved")["severity"] == "P0", "edition 未解決は P0")
    # 可変サフィックス付き conflict は安定 key に畳む。
    check(classify("chain:unresolved_conflicts:3")["code"] == "chain:unresolved_conflicts",
          "unresolved_conflicts:N が安定 key に正規化")
    u = classify("L9:made_up_code")
    check(u["known"] is False and u["family"] == "unclassified", "未知コードは unclassified")


def test_classify_defects_aggregate() -> None:
    agg = classify_defects(["L3:edition_unresolved", "L3:body_sha_absent",
                            "chain:nodes_unaccounted", "L9:weird"])
    check(agg["total"] == 4, "総数 4")
    check(agg["p0_count"] == 2, f"P0 は edition+nodes_unaccounted の 2 (実 {agg['p0_count']})")
    check(agg["unknown_codes"] == ["L9:weird"], "未知コードを列挙")
    check(agg["by_family"].get("body_integrity") == 1, "family 集計")


def test_regression_diff_basic() -> None:
    before = ["L3:body_sha_absent", "L3:edition_unresolved"]
    after = ["L3:edition_unresolved"]  # sha が直り edition は残る
    d = regression_diff(before, after)
    check(d["fixed"] == ["L3:body_sha_absent"], "sha が fixed")
    check(d["persisted"] == ["L3:edition_unresolved"], "edition は persisted")
    check(d["has_regression"] is False, "新規なし → 回帰なし")
    check(d["net_defect_delta"] == -1, "defect 1 減")


def test_regression_diff_detects_new_p0() -> None:
    before = ["L3:body_sha_absent"]
    after = ["L3:body_sha_absent", "chain:nodes_unaccounted"]  # 新規 P0 を作ってしまった
    d = regression_diff(before, after)
    check(d["has_regression"] is True, "新規 defect → 回帰検出")
    check(d["introduces_p0"] is True, "新規 P0 を検出")
    check(d["new_p0"] == ["chain:nodes_unaccounted"], "新規 P0 を列挙")


def test_real_repairers_introduce_no_p0() -> None:
    """実 repairer (sha 補完) を当てても新規 P0 が出ないことを実データ流で確認。"""
    t = load_thresholds()
    book = {
        "isbn": "9784000000020", "title": "民法",
        "source_meta": {"legallib": {"isbn": "9784000000020", "title": "民法",
                                     "page_basis": "print_page", "source_content": "目次本文"}},
        "sources": {"legallib": [{"title": "第1章 総則", "title_norm": "第1章総則",
                                  "depth": 1, "print_page": 1}]},
    }
    before = book_health(book, t)["defects"]
    # sha を補完した after を手で作る (apply 相当)。
    after_book = {**book, "source_meta": {"legallib": {**book["source_meta"]["legallib"],
                                                        "source_sha256": "sha256:x"}}}
    after = book_health(after_book, t)["defects"]
    d = regression_diff(before, after)
    check(d["introduces_p0"] is False, "sha 補完は新規 P0 を作らない")
    check("L3:body_sha_absent" in d["fixed"], "sha 欠落が解消される")


def main() -> int:
    for name, fn in (("test_classify_known_and_unknown", test_classify_known_and_unknown),
                     ("test_classify_defects_aggregate", test_classify_defects_aggregate),
                     ("test_regression_diff_basic", test_regression_diff_basic),
                     ("test_regression_diff_detects_new_p0", test_regression_diff_detects_new_p0),
                     ("test_real_repairers_introduce_no_p0", test_real_repairers_introduce_no_p0)):
        print(f"• {name}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
