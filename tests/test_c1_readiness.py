"""DDSELFHEAL C1 readiness — BodyShaRecompute が C1 write 第一候補であることを CI に凍結。

DDSELFHEAL-C0 PASS_WITH_NOTES の「BodyShaRecompute を最初の C1 write 候補」を、合成 golden 30 で
機械検証する。重要なのは **C1 write が EDIDENT(T2) に正確に依存する**ことの固定:
  * BodyShaRecompute は安全 (health_delta>0 / idempotent / reversible / 新規 P0 ゼロ / 決定的)。
  * C1 phase + owner whitelist + rollback を与えても、apply gate の 7 条件のうち
    `edition_identity_resolved` と `no_unresolved_conflict` が残り、write は依然不許可。
  * → C1 write 解禁は T2 (DD-EDIDENT-001 ratify+統合) と conflict 解消が前提、と CI が示す。
report-only・engine writes_executed は常に 0。stdlib のみ・決定的。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from repair_base import is_write_allowed_in_phase  # noqa: E402
from repair_engine import run_repairs  # noqa: E402

_CORPUS = Path(__file__).resolve().parents[1] / "tests" / "golden" / "repair" / "synthetic_corpus_30.jsonl"

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def _books():
    return [json.loads(ln)["book"]
            for ln in _CORPUS.read_text(encoding="utf-8").split("\n") if ln.strip()]


def test_bodysha_is_safe_c1_candidate() -> None:
    """BodyShaRecompute は決定的 repair の安全証明をすべて満たす。"""
    books = _books()
    res = run_repairs(books, rollback_present=True, phase="C0")
    sha = [m for m in res["manifests"] if m["repairer"] == "body_sha_recompute"]
    check(len(sha) == 5, f"golden 30 中 body_sha 対象 5 (実 {len(sha)})")
    check(sha[0]["repair_class"] == "deterministic_no_canonical_write", "class=deterministic_no_canonical_write")
    check(all(m["health_delta"] > 0 for m in sha), "health_delta>0 (健全度を上げる)")
    check(all(m["no_op_second_run"] for m in sha), "二度がけ no-op (冪等)")
    check(all(m["rollback_verified"] for m in sha), "rollback 検証済 (可逆)")
    check(all(m["plan_deterministic"] for m in sha), "plan 決定的")
    check(all(not (m.get("regression") or {}).get("introduces_p0") for m in sha), "新規 P0 ゼロ")
    # class 自体は C1 で write 解禁、C0 では不許可。
    check(not is_write_allowed_in_phase("deterministic_no_canonical_write", "C0"), "C0: class write 不許可")
    check(is_write_allowed_in_phase("deterministic_no_canonical_write", "C1"), "C1: class write 解禁")


def test_c1_write_still_gated_by_edition_identity() -> None:
    """C1 + whitelist + rollback でも edition_identity 未解決なら write は不許可 (T2 依存の固定)。"""
    books = _books()
    wl = {b["isbn"] for b in books}
    res = run_repairs(books, rollback_present=True, phase="C1", whitelist=wl)
    sha = [m for m in res["manifests"] if m["repairer"] == "body_sha_recompute"]
    check(res["writes_executed"] == 0, "report-only: writes_executed=0")
    check(all(not m["write_allowed"] for m in sha), "C1+whitelist+rollback でも write 不許可")
    # 残る refusal が edition_identity_resolved (= T2 依存) であることを固定。
    for m in sha:
        refusals = set(m["gate_result"].get("refusals", []))
        passed = set(m["gate_result"].get("passed", []))
        check("edition_identity_resolved" in refusals, "残り refusal に edition_identity_resolved (T2 依存)")
        check("whitelist_required" in passed, "whitelist gate は通過済")
        check("rollback_bundle_present" in passed, "rollback gate は通過済")
        check("decision_log_append_only" in passed, "decision_log gate は通過済")


def main() -> int:
    for name, fn in (("test_bodysha_is_safe_c1_candidate", test_bodysha_is_safe_c1_candidate),
                     ("test_c1_write_still_gated_by_edition_identity", test_c1_write_still_gated_by_edition_identity)):
        print(f"• {name}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
