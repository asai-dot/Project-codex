"""page_basis / authority_resolver / decision_log のテスト (v0.3.1 report-only)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from authority_resolver import (  # noqa: E402
    AUTH_CONSENSUS, AUTH_HUMAN_REVIEW, AUTH_PDF_PRIMARY, resolve_authority,
)
from decision_log import DecisionLog, verify_chain  # noqa: E402
from page_basis import (  # noqa: E402
    PDF_OBSERVED, PDF_PRIMARY, normalize_page_basis, page_basis_consistent,
    qualify_pdf_observation, to_print_page,
)

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def _good_pdf():
    return {"source": "pdf", "extraction_method": "publisher_pdf_toc",
            "extraction_confidence": "high", "page_basis": "print_page",
            "coverage": "full_toc", "source_sha256": "sha256:abc"}


def test_page_basis() -> None:
    check(normalize_page_basis("PDF") == "pdf_page", "PDF→pdf_page")
    check(normalize_page_basis("印刷ページ") == "print_page", "印刷→print_page")
    check(normalize_page_basis("???") == "unknown", "不明→unknown")
    check(to_print_page(15, 3) == 12, "pdf15-offset3=print12")

    q = qualify_pdf_observation(_good_pdf())
    check(q["qualified"] and q["authority_label"] == PDF_PRIMARY, "good PDF→qualified/primary")
    bad = _good_pdf(); bad["extraction_confidence"] = "low"
    qb = qualify_pdf_observation(bad)
    check(not qb["qualified"] and qb["authority_label"] == PDF_OBSERVED, "low conf→observed")
    nb = _good_pdf(); del nb["source_sha256"]
    check(not qualify_pdf_observation(nb)["qualified"], "sha欠如→unqualified")

    check(page_basis_consistent({"a": {"page_basis": "print_page"}, "b": {"page_basis": "unknown"}}),
          "unknown は整合判定から除外")
    check(not page_basis_consistent({"a": {"page_basis": "print_page"}, "b": {"page_basis": "pdf_page"}}),
          "print と pdf 混在→不整合")


def test_authority() -> None:
    # qualified PDF + edition resolved + page_basis consistent → pdf_primary
    meta = {"pdf": _good_pdf(),
            "legallib": {"page_basis": "print_page", "provenance_origin": "legallib"}}
    r = resolve_authority(meta, edition_status="resolved_same_manifestation")
    check(r["authority"] == AUTH_PDF_PRIMARY, "qualified PDF→pdf_primary")

    # PDF unqualified → human_review (independent sources 不足)
    bad = {"pdf": {**_good_pdf(), "extraction_confidence": "low"},
           "legallib": {"provenance_origin": "legallib"}}
    r2 = resolve_authority(bad, edition_status="resolved_same_manifestation")
    check(r2["authority"] == AUTH_HUMAN_REVIEW, "unqualified PDF+独立不足→human_review")

    # PDF なし・3独立ソース → consensus
    three = {"a": {"provenance_origin": "ndl"}, "b": {"provenance_origin": "publisher"},
             "c": {"provenance_origin": "scan"}}
    r3 = resolve_authority(three, edition_status="resolved_same_manifestation")
    check(r3["authority"] == AUTH_CONSENSUS, "3独立→consensus")

    # 独立性未宣言は consensus に数えない (安全側)
    undecl = {"a": {}, "b": {}, "c": {}}
    r4 = resolve_authority(undecl, edition_status="resolved_same_manifestation")
    check(r4["authority"] == AUTH_HUMAN_REVIEW, "独立性未宣言→human_review")

    # edition 未解決 → 何があっても human_review (PDF primary にもしない)
    r5 = resolve_authority({"pdf": _good_pdf()}, edition_status="suspected_different_manifestation")
    check(r5["authority"] != AUTH_PDF_PRIMARY, "edition未解決→pdf_primaryにしない")


def test_decision_log() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "decision_log.jsonl"
        log = DecisionLog(p)
        r1 = log.append(isbn="9784000000010", conflict_id="c1", decision="keep_existing",
                        decided_by="owner", basis="既存の方が詳細")
        r2 = log.append(isbn="9784000000010", conflict_id="c2", decision="accept_legallib",
                        decided_by="owner", basis="legallib が上位")
        check(r1["prev_hash"].startswith("sha256:") and r2["prev_hash"] == r1["hash"],
              "chain で前レコード hash を連結")
        v = verify_chain(p)
        check(v["ok"] and v["count"] == 2, "正常 chain 検証")

        # 改竄を検知
        lines = p.read_text(encoding="utf-8").splitlines()
        tampered = lines[0].replace("keep_existing", "accept_legallib")
        p.write_text(tampered + "\n" + lines[1] + "\n", encoding="utf-8")
        check(not verify_chain(p)["ok"], "改竄を検知")


def main() -> int:
    for t in [test_page_basis, test_authority, test_decision_log]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
