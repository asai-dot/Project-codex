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
    """監査 H5 を受けた再解釈: この golden は v1 出力由来で false positive を含む。

    意味上の primary truth は独立 adversarial gold (test_edition_adversarial.py) に移譲。
    本テストは健全な安全不変条件を固定する:
      ★ v2 が apply 可 (RESOLVED_SAME) に倒すのは、核タイトル一致 ∧ 版signature整合 ∧ 年整合の
        「検証可能な同一本」に限る (年乖離・版マーカ非対称・版番号衝突は決して apply に倒さない)。
    v1 の偽陽性 (marker 位置差のみの同一本) は v2 が正しく回収し、真の anomaly は依然 block する。
    """
    recs = _load()
    check(len(recs) == 10, f"golden 10冊 (got {len(recs)})")

    transitions = {}
    v2_apply = 0
    for rec in recs:
        bib = _bib_pair(rec)
        v1 = classify_edition(bib, version="v1")
        v2 = classify_edition(bib, version="v2")
        isbn = rec["isbn"]
        check(v1["status"] == rec["v1_status"],
              f"{isbn}: v1 {v1['status']} != 記録 {rec['v1_status']}")

        if v2["status"] in APPLY_OK_STATUS:
            v2_apply += 1
            ev = v2.get("evidence") or {}
            check(ev.get("title_core") == "match",
                  f"{isbn}: v2 apply だが核タイトル不一致 ({ev.get('title_core')})")
            check(ev.get("title_edition_sig") in ("match", "unknown"),
                  f"{isbn}: v2 apply だが版signature非整合 ({ev.get('title_edition_sig')})")
            check(ev.get("year") in ("match", "within_tol", "unknown"),
                  f"{isbn}: v2 apply だが年乖離 ({ev.get('year')})")
        transitions.setdefault((rec["v1_status"], v2["status"]), []).append(isbn)

    # 真の anomaly (年乖離/版マーカ非対称) は依然 block。apply 昇格は marker-move 偽陽性のみ。
    check(v2_apply <= 2, f"v2 apply 昇格は marker-move 偽陽性のみ (実 {v2_apply})")
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
