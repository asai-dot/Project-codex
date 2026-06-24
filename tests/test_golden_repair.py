"""repair golden 回帰 — 合成 corpus 30 冊で自己浄化ループの安全不変条件を固定。

GPT 監査 (DDSELFHEAL-C0) の C1 最小条件「golden 10→30 以上 (sparse / multi-volume /
page-offset / orphan / no-TOC / conflict 網羅)」に応える合成 fixture。実データ30冊は統合
corpus 待ちのため、6 カテゴリ × 5 冊 を make_synthetic_golden.py で決定的生成する。

検証は2層:
  (A) 回帰ロック … 生成時に焼き込んだ実パイプライン観測値 (health/apply/fired 等) を再現する。
  (B) 安全不変条件 … カテゴリに依らず守るべき物理則:
        ★ orphan / conflict は P0 ブロッカーで apply 不適格のまま。
        ★ 決定的 repair は新規 P0 defect を作らない (no_repair_introduces_p0)。
        ★ 適用シミュレーションで apply 不適格本を適格へ昇格させない。
        ★ 全 plan が no-op 二度がけ / rollback 原状復帰 / health 非悪化。

report-only・stdlib のみ・合成データのみ (実依頼者データなし)。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from data_health import book_health  # noqa: E402
from repair_base import apply_plan  # noqa: E402
from repair_engine import run_repairs  # noqa: E402
from thresholds import load_thresholds  # noqa: E402

_FIXTURE = Path(__file__).resolve().parent / "golden" / "repair" / "synthetic_corpus_30.jsonl"
_CATEGORIES = {"sparse", "multi_volume", "page_offset", "orphan", "no_toc", "conflict"}
_P0_CATEGORIES = {"orphan", "conflict"}  # 必ず apply 不適格であるべきカテゴリ

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def _load() -> list[dict]:
    return [json.loads(ln) for ln in _FIXTURE.read_text(encoding="utf-8").split("\n") if ln.strip()]


def test_corpus_shape() -> None:
    rows = _load()
    check(len(rows) >= 30, f"golden は 30 冊以上 (実際 {len(rows)})")
    cats = {r["category"] for r in rows}
    check(cats == _CATEGORIES, f"6 カテゴリ網羅 (欠け: {_CATEGORIES - cats})")
    isbns = [r["book"]["isbn"] for r in rows]
    check(len(set(isbns)) == len(isbns), "ISBN は一意")
    # 4 repairer すべてが golden のどこかで発火する (C1 候補の coverage)。
    fired = {rp for r in rows for rp in r["expected"]["fired_repairers"]}
    for rp in ("body_sha_recompute", "normalize_title_regen",
               "offset_page_convert", "quarantine_orphan"):
        check(rp in fired, f"{rp} が golden で発火する")


def test_regression_lock() -> None:
    """(A) 焼き込んだ観測値をパイプラインが再現する (挙動が動いたら気づく)。"""
    t = load_thresholds()
    for r in _load():
        book, exp, cat = r["book"], r["expected"], r["category"]
        isbn = book["isbn"]
        h = book_health(book, t)
        check(h["health_score"] == exp["health_score"],
              f"{cat}/{isbn}: health {h['health_score']} != 記録 {exp['health_score']}")
        check(h["apply_eligible"] == exp["apply_eligible"],
              f"{cat}/{isbn}: apply_eligible 不一致")
        check(sorted(h["defects"]) == sorted(exp["defects"]),
              f"{cat}/{isbn}: defects 不一致")
        res = run_repairs([book], rollback_present=True, phase="C0", thresholds=t)
        fired = sorted({m["repairer"] for m in res["manifests"]})
        check(fired == sorted(exp["fired_repairers"]),
              f"{cat}/{isbn}: fired {fired} != 記録 {exp['fired_repairers']}")


def test_safety_invariants() -> None:
    """(B) カテゴリ非依存の安全不変条件 (golden を blessing し直しても破れない物理則)。"""
    t = load_thresholds()
    rows = _load()

    # P0 カテゴリは必ず apply 不適格。
    for r in rows:
        if r["category"] in _P0_CATEGORIES:
            check(not r["expected"]["apply_eligible"],
                  f"{r['category']}/{r['book']['isbn']}: P0 カテゴリが apply 適格になっている")

    # corpus 一括 dry-run の集計不変条件。
    res = run_repairs([r["book"] for r in rows], rollback_present=True, phase="C0", thresholds=t)
    check(res["writes_executed"] == 0, "C0: 物理書込ゼロ")
    check(res["write_allowed_count"] == 0, "C0: write_allowed は 0 (phase が常に不許可)")
    check(res["all_plans_deterministic"], "全 plan が決定的")
    check(res["all_no_op_second_run"], "全 plan が no-op 二度がけ")
    check(res["all_rollback_verified"], "全 plan が rollback で原状復帰")
    check(res["all_health_non_decreasing"], "全 plan が health 非悪化")
    check(res["no_repair_introduces_p0"], "決定的 repair は新規 P0 defect を作らない")

    # 各 plan を適用シミュレーションしても apply 不適格本は適格へ昇格しない。
    for r in rows:
        book = r["book"]
        before = book_health(book, t)["apply_eligible"]
        if before:
            continue
        eng = run_repairs([book], rollback_present=True, phase="C0", thresholds=t)
        for m in eng["manifests"]:
            applied = apply_plan(book, {"changes": m["changes"]})
            after = book_health(applied, t)["apply_eligible"]
            check(after is False,
                  f"{r['category']}/{book['isbn']}: repair {m['repairer']} が "
                  f"apply 不適格本を適格へ昇格させた")


def main() -> int:
    for name, fn in (("test_corpus_shape", test_corpus_shape),
                     ("test_regression_lock", test_regression_lock),
                     ("test_safety_invariants", test_safety_invariants)):
        print(f"• {name}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
