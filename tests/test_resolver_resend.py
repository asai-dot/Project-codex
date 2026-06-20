"""resolver_resend_candidates テスト — DD-EDIDENT-001 §4 + 監査 H6 是正を CI に凍結。

OQ-3 で resolver 差し戻しを本 DD スコープに含め、監査 H6 で次を是正:
  * 旧 v1 派生 (is_real_suspect) でなく **ratified classifier v2 で raw から再計算**。
  * `legallib_book_id` 一意性を fail-closed assert (後勝ち上書き禁止)。
  * classifier_version / 行数 conservation を成果物に固定。
原本 resolver_decisions は読むだけ・書込ゼロ (report-only)。stdlib のみ・決定的。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from edition_identity import APPLY_OK_STATUS  # noqa: E402
from resolver_resend_candidates import (  # noqa: E402
    AA_REASON, DN_REASON, RESEND_TO, DuplicateBookId, build_candidates, load_jsonl,
)

_SAMPLE = (Path(__file__).resolve().parents[1]
           / "handoff" / "legallibjoin_v0.3.1_phase0_20260615" / "edition_identity_sample.jsonl")

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def _cands():
    return build_candidates(load_jsonl(_SAMPLE))


def test_counts_frozen() -> None:
    """v2 再計算後の確定値 (auto_accept 27 / defer_new 58 / 計 85) を凍結。"""
    if not _SAMPLE.exists():
        check(False, f"sample 不在: {_SAMPLE}")
        return
    c = _cands()
    aa = [x for x in c if x["resend_reason"] == AA_REASON]
    dn = [x for x in c if x["resend_reason"] == DN_REASON]
    check(len(c) == 99, f"差し戻し候補 計 99 (実 {len(c)})")
    check(len(aa) == 41, f"auto_accept 偽陽性 41 (v2 再計算・Required note 2 で増) (実 {len(aa)})")
    check(len(dn) == 58, f"defer_new 取りこぼし 58 (実 {len(dn)})")


def test_recomputed_from_v2_not_v1() -> None:
    """H6: 候補は v2 status で再計算され、APPLY_OK でない (auto_accept 偽陽性)。"""
    c = _cands()
    check(all(x.get("classifier_version") for x in c), "classifier_version を記録")
    aa = [x for x in c if x["resend_reason"] == AA_REASON]
    check(all(x["edition_status"] not in APPLY_OK_STATUS for x in aa),
          "AA 偽陽性は v2 で APPLY_OK でない")
    check(all(x["to_bucket"] == RESEND_TO for x in c), "差し戻し先は human_review")


def test_book_id_uniqueness_failclosed() -> None:
    """H6: legallib_book_id 重複は fail-closed (後勝ち上書きしない)。"""
    dup = [{"legallib_book_id": "1", "isbn": "X", "resolver_bucket": "defer_new",
            "canonical": {"title": "A"}, "legallib": {"title": "A"}},
           {"legallib_book_id": "1", "isbn": "Y", "resolver_bucket": "defer_new",
            "canonical": {"title": "B"}, "legallib": {"title": "B"}}]
    raised = False
    try:
        build_candidates(dup)
    except DuplicateBookId:
        raised = True
    check(raised, "重複 book_id で DuplicateBookId を送出")


def test_deterministic_order() -> None:
    a = [(x["resend_reason"], x["legallib_book_id"]) for x in _cands()]
    b = [(x["resend_reason"], x["legallib_book_id"]) for x in _cands()]
    check(a == b, "build_candidates は決定的")
    check(a == sorted(a), "候補は (理由, book_id) でソート済み")


def main() -> int:
    for name, fn in (("test_counts_frozen", test_counts_frozen),
                     ("test_recomputed_from_v2_not_v1", test_recomputed_from_v2_not_v1),
                     ("test_book_id_uniqueness_failclosed", test_book_id_uniqueness_failclosed),
                     ("test_deterministic_order", test_deterministic_order)):
        print(f"• {name}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
