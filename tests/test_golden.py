"""golden 回帰テスト — tests/golden/*.json の既知 conflict を固定する。

Mac Phase 0 の known_conflict_golden 10冊が JSON で置かれたら自動で検証対象に入る。
seed が0件でも fixture loader は壊れないことを確認する。report-only。stdlib のみ。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from review_report import book_summary  # noqa: E402

_GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def load_goldens() -> list[dict]:
    out = []
    for p in sorted(_GOLDEN_DIR.glob("*.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def _run_one(g: dict) -> None:
    gid = g.get("id", "?")
    book = g["book"]
    exp = g.get("expect", {})
    s = book_summary(book["isbn"], book.get("title", ""),
                     book["sources"], book.get("source_meta", {}))

    if "risk" in exp:
        check(s["risk"] == exp["risk"], f"{gid}: risk {s['risk']} != {exp['risk']}")
    if "edition_identity_status" in exp:
        check(s["edition_identity_status"] == exp["edition_identity_status"],
              f"{gid}: edition {s['edition_identity_status']} != {exp['edition_identity_status']}")
    if "all_nodes_accounted_for" in exp:
        check(s["all_nodes_accounted_for"] == exp["all_nodes_accounted_for"],
              f"{gid}: accounted {s['all_nodes_accounted_for']} != {exp['all_nodes_accounted_for']}")

    patterns = set(s["conflicts"]["by_pattern"].keys())
    for want in exp.get("conflict_patterns", []):
        check(want in patterns, f"{gid}: conflict '{want}' 未検出 (got {sorted(patterns)})")

    unresolved = s["conflicts"]["unresolved"]
    if "min_unresolved" in exp:
        check(unresolved >= exp["min_unresolved"],
              f"{gid}: unresolved {unresolved} < min {exp['min_unresolved']}")
    if "max_unresolved" in exp:
        check(unresolved <= exp["max_unresolved"],
              f"{gid}: unresolved {unresolved} > max {exp['max_unresolved']}")


def test_goldens() -> None:
    goldens = load_goldens()
    # loader 健全性: ファイルが0でも例外を出さない。
    check(isinstance(goldens, list), "loader は list を返す")
    ids = [g.get("id") for g in goldens]
    check(len(ids) == len(set(ids)), f"golden id は一意 (dup: {ids})")
    for g in goldens:
        _run_one(g)
    print(f"  ({len(goldens)} golden fixtures)")


def main() -> int:
    print("• test_goldens")
    test_goldens()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
