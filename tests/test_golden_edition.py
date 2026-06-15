"""edition golden 回帰 — Mac Phase 0 の known_conflict 実10冊で edition classifier を固定。

これらは『legallib と canonical で同一性/構造が割れる **実質的**危険ペア』(装飾差/副題差の
偽陽性は既に除外済)。安全不変条件:

  ★ v1 / v2 いずれも、この10ペアを **RESOLVED_SAME (=apply 可) へ昇格させてはならない**。

加えて、DD-EDIDENT-001 で共有モジュールを v2 へ昇格させる際の回帰可視化として、
v1→v2 の status 遷移分布を表示する (過検知是正が「危険ペアを緩めていない」ことの証跡)。
report-only・stdlib のみ。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from edition_identity import APPLY_OK_STATUS, SUSPECTED_DIFFERENT  # noqa: E402
from edition_select import classify_edition  # noqa: E402

_FIXTURE = Path(__file__).resolve().parent / "golden" / "edition" / "known_conflict_10.jsonl"

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


def _bib_pair(rec: dict) -> list[dict]:
    return [{"source": "legallib", **rec["legallib"], "isbn": rec["isbn"]},
            {"source": "canonical", **rec["canonical"], "isbn": rec["isbn"]}]


def test_known_conflict_10() -> None:
    recs = _load()
    check(len(recs) == 10, f"golden 10冊 (got {len(recs)})")

    transitions = {}
    for rec in recs:
        bib = _bib_pair(rec)
        v1 = classify_edition(bib, version="v1")
        v2 = classify_edition(bib, version="v2")
        isbn = rec["isbn"]

        # v1 は Phase0 で記録された status を再現する (凍結)。
        check(v1["status"] == rec["v1_status"],
              f"{isbn}: v1 {v1['status']} != 記録 {rec['v1_status']}")
        check(v1["status"] == SUSPECTED_DIFFERENT, f"{isbn}: v1 は別版疑い")

        # ★安全不変条件: v1/v2 とも apply 可 (RESOLVED_SAME/MANUAL) へ昇格させない。
        check(v1["status"] not in APPLY_OK_STATUS, f"{isbn}: v1 は apply 不可のまま")
        check(v2["status"] not in APPLY_OK_STATUS,
              f"{isbn}: v2 が危険ペアを apply 可へ昇格 ({v2['status']})")

        transitions.setdefault((rec["v1_status"], v2["status"]), []).append(isbn)

    # 遷移分布を可視化 (回帰時に「どこが動いたか」を一目で)。
    print("  v1 -> v2 status 遷移:")
    for (a, b), isbns in sorted(transitions.items()):
        print(f"    {a} -> {b}: {len(isbns)}冊")


def main() -> int:
    print("• test_known_conflict_10")
    test_known_conflict_10()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
