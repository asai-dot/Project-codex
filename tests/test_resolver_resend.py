"""resolver_resend_candidates テスト — DD-EDIDENT-001 §4 (resolver 差し戻し) を CI に凍結。

OQ-3 (owner ratify 2026-06-17) で resolver 差し戻しを本 DD スコープに含めたため、
§4 の確定値を certified Phase0 サンプル (sha256 固定) で機械検証する:
  * auto_accept 偽陽性 12 件 → human_review (apply 時 edition gate が物理拒否すべき対象)。
  * defer_new 取りこぼし 58 件 (isbn が canonical に存在) → human_review。
原本 resolver_decisions は読むだけ・書込ゼロ (report-only)。stdlib のみ・決定的。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from resolver_resend_candidates import (  # noqa: E402
    AA_REASON, DN_REASON, RESEND_TO, build_candidates, load_jsonl,
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
    """§4 の確定値 (auto_accept 12 / defer_new 58 / 計 70) を凍結。"""
    if not _SAMPLE.exists():
        check(False, f"sample 不在: {_SAMPLE}")
        return
    c = _cands()
    check(len(c) == 70, f"差し戻し候補 計 70 (実 {len(c)})")
    aa = [x for x in c if x["resend_reason"] == AA_REASON]
    dn = [x for x in c if x["resend_reason"] == DN_REASON]
    check(len(aa) == 12, f"auto_accept 偽陽性 12 (実 {len(aa)})")
    check(len(dn) == 58, f"defer_new 取りこぼし 58 (実 {len(dn)})")


def test_resend_semantics() -> None:
    c = _cands()
    # 差し戻し先は全て human_review。
    check(all(x["to_bucket"] == RESEND_TO for x in c), "差し戻し先は human_review")
    # auto_accept 候補は from_bucket=auto_accept、defer_new 候補は from_bucket=defer_new。
    check(all(x["from_bucket"] == "auto_accept" for x in c if x["resend_reason"] == AA_REASON),
          "AA 候補の from_bucket=auto_accept")
    check(all(x["from_bucket"] == "defer_new" for x in c if x["resend_reason"] == DN_REASON),
          "DN 候補の from_bucket=defer_new")
    # auto_accept 偽陽性は edition gate 非 apply (suspected/insufficient) のはず。
    apply_ok = {"resolved_same_manifestation", "manual_resolved"}
    check(all(x["edition_status"] not in apply_ok for x in c if x["resend_reason"] == AA_REASON),
          "AA 偽陽性は edition gate で apply 不可")
    # isbn は正規化済み・空でない。
    check(all(x["isbn"] for x in c), "全候補 isbn 非空")


def test_deterministic_order() -> None:
    a = [(x["resend_reason"], x["legallib_book_id"]) for x in _cands()]
    b = [(x["resend_reason"], x["legallib_book_id"]) for x in _cands()]
    check(a == b, "build_candidates は決定的")
    check(a == sorted(a), "候補は (理由, book_id) でソート済み")


def main() -> int:
    for name, fn in (("test_counts_frozen", test_counts_frozen),
                     ("test_resend_semantics", test_resend_semantics),
                     ("test_deterministic_order", test_deterministic_order)):
        print(f"• {name}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
