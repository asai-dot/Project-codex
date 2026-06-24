"""edition identity 独立 adversarial 回帰 — DD-EDIDENT-001-IMPL H5 + re-audit gates。

監査 H5: classifier と独立な人手 truth で意味上の正しさを固定する。
`tests/golden/edition/adversarial_gold.jsonl` (make_edition_adversarial_gold.py 生成) を真とし、
監査 §7 re-audit acceptance gates を機械化:
  * 10 adversarial class が全件 expected と一致。
  * ISBN / edition / volume mismatch の false merge = 0。
  * substring-only の apply = 0。
  * same signature + large divergence の apply = 0。
  * parser unknown / parse_error が silent same に入らない。
  * v1 が維持すべき hard checks の parity matrix を提示。
stdlib のみ・決定的・合成データ。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from edition_identity import APPLY_OK_STATUS, RESOLVED_SAME, SUSPECTED_DIFFERENT  # noqa: E402
from edition_identity_v2 import classify_edition_identity_v2 as cls  # noqa: E402

_GOLD = Path(__file__).resolve().parents[1] / "tests" / "golden" / "edition" / "adversarial_gold.jsonl"

_PASS = 0
_FAIL = 0


def check(cond, msg):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def _gold():
    return [json.loads(ln) for ln in _GOLD.read_text(encoding="utf-8").split("\n") if ln.strip()]


def test_gold_all_match() -> None:
    rows = _gold()
    check(len(rows) >= 16, f"adversarial gold >=16 (実 {len(rows)})")
    ids = [r["case_id"] for r in rows]
    check(len(ids) == len(set(ids)), "case_id 一意")
    for r in rows:
        got = cls([r["a"], r["b"]])["status"]
        check(got == r["expected"], f"{r['case_id']}: got={got} exp={r['expected']}")


def test_reaudit_acceptance_gates() -> None:
    """監査 §7 の受入ゲートを class 単位で機械化。"""
    rows = {r["case_id"]: r for r in _gold()}

    def status(cid):
        r = rows[cid]
        return cls([r["a"], r["b"]])["status"]

    # ISBN / edition / volume mismatch の false merge = 0。
    for cid in ("isbn_mismatch", "explicit_edition_mismatch", "volume_mismatch"):
        check(status(cid) not in APPLY_OK_STATUS, f"{cid}: APPLY_OK へ false merge しない")
    # substring-only の apply = 0。
    check(status("title_containment_no_isbn") not in APPLY_OK_STATUS, "substring-only は apply 不可")
    # same signature + large divergence の apply = 0。
    check(status("same_sig_large_year_gap") not in APPLY_OK_STATUS, "同sig+大年差は apply 不可")
    # parser unknown / parse_error は silent same に入らない。
    check(status("unknown_marker") not in APPLY_OK_STATUS, "unknown marker は apply 不可")
    check(status("wareki_parse_error") not in APPLY_OK_STATUS, "year parse_error は apply 不可")
    # true same は正しく resolved (false split しない)。
    for cid in ("marker_move_same", "true_same_isbn_reprint", "true_same_multi_signal", "cosmetic_same_isbn"):
        check(status(cid) == RESOLVED_SAME, f"{cid}: 真の同一を resolved にする")


def test_v1_hard_check_parity() -> None:
    """v1 から維持すべき hard checks の parity matrix (監査 H1 復元の証跡)。

    v1 (素朴) が別版/別物にしていた次の信号を v2 が **少なくとも同等に保守的**に扱う:
      ISBN 不一致 / explicit edition 不一致 / volume 不一致 / title 版番号衝突 / 核タイトル相違。
    いずれも v2 で APPLY_OK に昇格しない (= apply 不可) ことを matrix で固定。
    """
    matrix = [
        ("isbn_divergence", {"title": "A", "isbn": "1", "year": "2020"},
         {"title": "A", "isbn": "2", "year": "2020"}),
        ("explicit_edition", {"title": "A", "isbn": "X", "edition": "第1版"},
         {"title": "A", "isbn": "X", "edition": "第2版"}),
        ("volume", {"title": "A", "isbn": "X", "volume": "上巻"},
         {"title": "A", "isbn": "X", "volume": "下巻"}),
        ("title_edition_conflict", {"title": "A 第2版", "year": "2020"},
         {"title": "A 第5版", "year": "2020"}),
        ("core_title_diff", {"title": "民法", "isbn": "X"},
         {"title": "刑法", "isbn": "X"}),
    ]
    for name, a, b in matrix:
        res = cls([a, b])
        check(res["status"] not in APPLY_OK_STATUS,
              f"parity[{name}]: v1 hard check を維持 (apply 不可) got={res['status']}")
        check(res["status"] == SUSPECTED_DIFFERENT,
              f"parity[{name}]: suspected_different で検出 got={res['status']}")


def test_pair_trace_present() -> None:
    """H7: pair-level decision trace と version が出力される。"""
    r = cls([{"title": "民法", "isbn": "1"}, {"title": "民法", "isbn": "2"}])
    check(r.get("classifier_version") is not None, "classifier_version 出力")
    check(r.get("evidence") is not None, "worst pair evidence trace 出力")
    check("isbn" in (r.get("evidence") or {}), "evidence に isbn 信号")
    check(isinstance(r.get("pair_traces"), list) and r["pair_traces"], "pair_traces 出力")


def main() -> int:
    for name, fn in (("test_gold_all_match", test_gold_all_match),
                     ("test_reaudit_acceptance_gates", test_reaudit_acceptance_gates),
                     ("test_v1_hard_check_parity", test_v1_hard_check_parity),
                     ("test_pair_trace_present", test_pair_trace_present)):
        print(f"• {name}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
