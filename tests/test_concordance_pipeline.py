"""concordance_pipeline 統合テスト (v0.3.1 Phase0 evidence ハーネス, report-only).

9モジュールを束ねた end-to-end で、apply_guard の物理拒否ログ・accounting 照合・
evidence 出力・decision_log chain 検証を固定する。stdlib のみ。
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from concordance_pipeline import _demo_books, run_pipeline, write_evidence  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def test_pipeline_gate_logic() -> None:
    books = _demo_books()
    # 低リスク本(9784000000010)だけ whitelist 承認、rollback あり。
    res = run_pipeline(books, whitelist={"9784000000010"}, rollback_present=True)
    g = {r["isbn"]: r for r in res["apply_guard"]}

    # 低リスク・whitelist・rollback・全gate通過 → allowed
    check(g["9784000000010"]["allowed"], "低リスク+承認+rollback → apply 可")
    # 中リスク本(会社法)は whitelist 外 かつ unresolved conflict → blocked
    check(not g["9784000000027"]["allowed"], "中リスク本は blocked")
    check("whitelist_required" in g["9784000000027"]["refusals"], "whitelist外で拒否")
    check("no_unresolved_conflict" in g["9784000000027"]["refusals"], "未解決conflictで拒否")
    # 高リスク本(別版疑い)は edition 未解決 で blocked
    check(not g["9784000000034"]["allowed"], "別版疑い本は blocked")
    check("edition_identity_resolved" in g["9784000000034"]["refusals"], "edition未解決で拒否")

    check(res["apply_allowed_isbns"] == ["9784000000010"], "apply 可は1冊のみ")
    check(res["report_only"] and res["final_toc_written"] is False
          and res["toc_dir_written"] is False, "report-only / toc 未書込")


def test_rollback_and_whitelist_required() -> None:
    books = _demo_books()
    # rollback 無し → 低リスク本でも rollback_bundle_present で拒否
    res = run_pipeline(books, whitelist={"9784000000010"}, rollback_present=False)
    g = {r["isbn"]: r for r in res["apply_guard"]}
    check("rollback_bundle_present" in g["9784000000010"]["refusals"], "rollback無しは拒否")
    # whitelist None → 全冊 whitelist_required で拒否
    res2 = run_pipeline(books, whitelist=None, rollback_present=True)
    check(all(not r["allowed"] for r in res2["apply_guard"]), "whitelist None は全拒否")


def test_evidence_output() -> None:
    books = _demo_books()
    res = run_pipeline(books, whitelist={"9784000000010"}, rollback_present=True)
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        meta = write_evidence(res, out)
        ev = out / "evidence"
        for f in ["source_inventory.csv", "parser_histogram.csv",
                  "accounting_reconciliation.csv", "apply_guard_log.jsonl",
                  "decision_log.jsonl"]:
            check((ev / f).exists(), f"evidence/{f} 出力")
        check((out / "EVIDENCE_README.md").exists(), "EVIDENCE_README 出力")
        check((out / "conflicts.jsonl").exists(), "conflicts.jsonl 出力")
        # decision_log は blocked 2冊分 (会社法/民法) を記録、chain ok
        check(meta["chain"]["ok"] and meta["chain"]["count"] == 2, "decision_log chain ok=2件")
        # accounting は全冊 all_nodes_accounted_for=True
        body = (ev / "accounting_reconciliation.csv").read_text()
        check(body.count("True") == 3 and "False" not in body, "全冊 accounted=True")


def main() -> int:
    for t in [test_pipeline_gate_logic, test_rollback_and_whitelist_required, test_evidence_output]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
