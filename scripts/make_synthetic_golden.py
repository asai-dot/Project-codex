"""make_synthetic_golden — DDSELFHEAL golden を 10→30 冊に拡張する合成 corpus 生成器。

GPT 監査 (DDSELFHEAL-C0) の C1 最小条件: 「golden 10→30 以上 (sparse / multi-volume /
page-offset / orphan / no-TOC / conflict 網羅)」。実データ30冊は統合 corpus 待ちのため、
6 カテゴリ × 5 冊 = 30 冊の **合成** fixture を決定的に生成する。

各行: {"category", "expected"(生成時の実パイプライン観測値=回帰ロック), "book"}。
test_golden_repair.py がこれを読み、(1) 観測値の不変 (2) カテゴリ別の安全不変条件を検証する。
合成データのみ・実依頼者データなし・本番書込なし。stdlib のみ・決定的。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _toc_text import normalize_title  # noqa: E402
from data_health import book_health  # noqa: E402
from repair_engine import run_repairs  # noqa: E402
from review_report import book_summary  # noqa: E402
from thresholds import load_thresholds  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "tests" / "golden" / "repair" / "synthetic_corpus_30.jsonl"

_FULL_META = {"publisher": "合成出版", "year": "2020",
              "page_basis": "print_page", "source_sha256": "sha256:fixture"}


def _node(title: str, depth: int, **extra) -> dict:
    """title_norm を正しく precompute したノード (normalize repairer を不用意に発火させない)。"""
    return {"title": title, "title_norm": normalize_title(title), "depth": depth, **extra}


def _book(isbn: str, title: str, sources: dict, source_meta: dict, **extra) -> dict:
    return {"isbn": isbn, "title": title, "sources": sources,
            "source_meta": source_meta, **extra}


def _meta(src_title: str, **over) -> dict:
    return {"title": src_title, **_FULL_META, **over}


def _rich_nodes(prefix: str, n: int) -> list[dict]:
    out = []
    for i in range(n):
        out.append(_node(f"第{i + 1}章 {prefix}{i + 1}", 1, print_page=1 + i * 10))
        out.append(_node(f"第{i + 1}節 {prefix}細目{i + 1}", 2, print_page=3 + i * 10))
    return out


def _category_books() -> list[tuple[str, dict]]:
    books: list[tuple[str, dict]] = []

    for i in range(5):
        n = i + 1
        # 1) sparse: 詳細TOC が浅く件数も少ない。source は sparse 印 (quarantine 除外)。
        #    title_norm を欠落させ NormalizeTitleRegen も golden で網羅する (希薄+正規化欠落)。
        isbn = f"978400010000{n}"
        books.append(("sparse", _book(
            isbn, f"合成希薄{n}",
            {"legallib": [{"title": f"第1章 概要{n}", "depth": 1, "print_page": 1}]},
            {"legallib": _meta(f"合成希薄{n}", sparse=True)})))

        # 2) multi_volume: 多巻物。node は豊富だが多巻印で orphan 隔離の対象外。
        isbn = f"978400020000{n}"
        books.append(("multi_volume", _book(
            isbn, f"合成多巻{n}",
            {"legallib": _rich_nodes("巻", 6)},
            {"legallib": _meta(f"合成多巻{n}", multi_volume=True)})))

        # 3) page_offset: 検証済 offset・pdf_page 持ち・print_page 未派生 → OffsetPageConvert。
        isbn = f"978400030000{n}"
        books.append(("page_offset", _book(
            isbn, f"合成頁{n}",
            {"legallib": [
                _node("第1章 序論", 1, pdf_page=9),
                _node("第2章 本論", 1, pdf_page=58)]},
            {"legallib": _meta(f"合成頁{n}", page_basis="pdf_page")},
            page_offset={"offset": 8, "confidence": 1.0, "validated": True, "anchors": 3})))

        # 4) orphan: 2ソースで章題が全く一致しない → QuarantineOrphan + chain 未充足 (P0)。
        isbn = f"978400040000{n}"
        books.append(("orphan", _book(
            isbn, f"合成孤立{n}",
            {"legallib": [_node("第1章 アルファ", 1, print_page=1)],
             "bencom": [_node("第X部 オメガ", 1, print_page=1)]},
            {"legallib": _meta(f"合成孤立{n}"),
             "bencom": _meta(f"合成孤立{n}", source_sha256="sha256:b")})))

        # 5) no_toc: 詳細TOC が皆無 (toc_absent)。source_content あり → BodyShaRecompute 余地。
        isbn = f"978400050000{n}"
        books.append(("no_toc", _book(
            isbn, f"合成無目次{n}",
            {"legallib": []},
            {"legallib": {"title": f"合成無目次{n}", "publisher": "合成出版",
                          "year": "2020", "page_basis": "print_page",
                          "source_content": f"無目次本文{n}"}})))

        # 6) conflict: 2ソースで page_basis が食い違う → unresolved conflict (P0 で apply 不可)。
        isbn = f"978400060000{n}"
        books.append(("conflict", _book(
            isbn, f"合成矛盾{n}",
            {"legallib": [_node("第1章 共通", 1, print_page=1)],
             "bencom": [_node("第1章 共通", 1, pdf_page=12)]},
            {"legallib": _meta(f"合成矛盾{n}", page_basis="print_page"),
             "bencom": _meta(f"合成矛盾{n}", page_basis="pdf_page", source_sha256="sha256:b")})))

    return books


def _expected(book: dict, t: dict) -> dict:
    """生成時の実パイプライン観測値 (回帰ロック用)。"""
    h = book_health(book, t)
    summary = book_summary(book["isbn"], book.get("title", ""),
                           book.get("sources", {}), book.get("source_meta", {}), t)
    res = run_repairs([book], rollback_present=True, phase="C0", thresholds=t)
    fired = sorted({m["repairer"] for m in res["manifests"]})
    return {
        "health_score": h["health_score"],
        "apply_eligible": h["apply_eligible"],
        "apply_blockers": h["apply_blockers"],
        "defects": h["defects"],
        "all_nodes_accounted_for": summary["all_nodes_accounted_for"],
        "unresolved_conflicts": summary["conflicts"]["unresolved"],
        "fired_repairers": fired,
        "all_no_op_second_run": res["all_no_op_second_run"],
        "all_rollback_verified": res["all_rollback_verified"],
        "all_health_non_decreasing": res["all_health_non_decreasing"],
        "no_repair_introduces_p0": res["no_repair_introduces_p0"],
    }


def build() -> list[dict]:
    t = load_thresholds()
    rows = []
    for category, book in _category_books():
        rows.append({"category": category, "expected": _expected(book, t), "book": book})
    return rows


def main() -> int:
    rows = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    cats: dict[str, int] = {}
    fired: dict[str, int] = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
        for rp in r["expected"]["fired_repairers"]:
            fired[rp] = fired.get(rp, 0) + 1
    print(json.dumps({"books": len(rows), "by_category": dict(sorted(cats.items())),
                      "repairer_coverage": dict(sorted(fired.items())),
                      "out": str(OUT.relative_to(OUT.parents[2]))},
                     ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
