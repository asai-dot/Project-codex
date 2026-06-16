"""make_tocadopt_golden — DD-TOCADOPT-001 採用ルールの合成 golden 生成器。

実 corpus (ALOBookDX 本流 projection・631クラスタ) は別環境のため、採用ルールの 5 ステップと
7 gate を刺激する **合成多源 corpus** を決定的に生成する。各シナリオは Step1〜4 の分岐
(基底選択 / granularity_guard / 別版除外 / 3源 consensus / pdf offset / protected base /
単一源不足) を1つずつ突く。生成時の実観測値を expected に焼き込み (回帰ロック)。

合成データのみ・実依頼者データなし・report-only。stdlib のみ・決定的。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from toc_adopt import adopt_book, load_policy  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "tests" / "golden" / "tocadopt" / "synthetic_multisource.jsonl"


def _meta(title, origin, *, year="2020", basis="print_page", pub="有斐閣", sha="sha256:x", **ov):
    return {"title": title, "publisher": pub, "year": year, "page_basis": basis,
            "provenance_origin": origin, "source_sha256": sha, **ov}


def _n(title, depth=1, **pg):
    return {"title": title, "depth": depth, **pg}


def _scenarios() -> list[tuple[str, dict]]:
    s: list[tuple[str, dict]] = []

    # 1) 基底=最富源 legallib、bencom/ndl から欠落ノードを補完。
    s.append(("merge_richest_base", {
        "isbn": "9784100000011", "title": "契約法",
        "source_meta": {
            "legallib": _meta("契約法", "legallib_extraction", sha="sha256:ll"),
            "bencom": _meta("契約法", "bengo4_redist", year="2021", sha="sha256:bc"),
            "ndl_partinfo": _meta("契約法", "ndl", sha="sha256:nd")},
        "sources": {
            "legallib": [_n("第1章 序論", 1, print_page=1), _n("第1節 沿革", 2, print_page=3),
                         _n("第2章 成立", 1, print_page=20)],
            "bencom": [_n("第1章 序論", 1, print_page=1)],
            "ndl_partinfo": [_n("補論 比較法", 1, print_page=80)]}}))

    # 2) granularity_guard: 1ノードの粗源は base 不可 (richest=8)、ただし votes には寄与。
    s.append(("guard_block", {
        "isbn": "9784100000022", "title": "会社法",
        "source_meta": {
            "legallib": _meta("会社法", "legallib_extraction", sha="sha256:ll"),
            "zosho_bib_toc": _meta("会社法", "zosho", sha="sha256:zo")},
        "sources": {
            "legallib": [_n(f"第{i+1}章 章{i+1}", 1, print_page=1 + i * 10) for i in range(8)],
            "zosho_bib_toc": [_n("第1章 章1", 1, print_page=1)]}}))

    # 3) 別版除外: bencom が〔第7版〕で legallib が〔第4版〕→ Step1 で human_review。
    s.append(("edition_exclude", {
        "isbn": "9784100000033", "title": "民事訴訟法",
        "source_meta": {
            "legallib": _meta("民事訴訟法〔第4版〕", "legallib_extraction", sha="sha256:ll"),
            "bencom": _meta("民事訴訟法〔第7版〕", "bengo4_redist", year="2024", sha="sha256:bc")},
        "sources": {
            "legallib": [_n("第1章 訴え", 1, print_page=1), _n("第2章 当事者", 1, print_page=30)],
            "bencom": [_n("第1章 訴え提起", 1, print_page=1)]}}))

    # 4) 3源 consensus: 独立3 origin が同一ノードを持つ → consensus True。
    s.append(("consensus3", {
        "isbn": "9784100000044", "title": "行政法",
        "source_meta": {
            "legallib": _meta("行政法", "legallib_extraction", sha="sha256:ll"),
            "lionbolt": _meta("行政法", "lionbolt", sha="sha256:li"),
            "openbd": _meta("行政法", "openbd", sha="sha256:op")},
        "sources": {
            "legallib": [_n("第1章 総論", 1, print_page=1)],
            "lionbolt": [_n("第1章 総論", 1, print_page=1)],
            "openbd": [_n("第1章 総論", 1, print_page=1)]}}))

    # 5) pdf offset: legallib が pdf_page + 検証済 offset=8 → print へ整合。
    s.append(("pdf_offset", {
        "isbn": "9784100000055", "title": "刑事訴訟法",
        "source_meta": {
            "legallib": _meta("刑事訴訟法", "legallib_extraction", basis="pdf_page", sha="sha256:ll"),
            "bencom": _meta("刑事訴訟法", "bengo4_redist", sha="sha256:bc")},
        "sources": {
            "legallib": [_n("第1章 捜査", 1, pdf_page=9), _n("第2章 公訴", 1, pdf_page=58)],
            "bencom": [_n("第1章 捜査", 1, print_page=1)]},
        "page_offset": {"offset": 8, "confidence": 1.0, "validated": True, "anchors": 3}}))

    # 6) protected base: ndl_partinfo(protected) が詳細 → 非 protected で base を奪わない。
    s.append(("protected_base", {
        "isbn": "9784100000066", "title": "労働法",
        "source_meta": {
            "ndl_partinfo": _meta("労働法", "ndl", sha="sha256:nd"),
            "bencom": _meta("労働法", "bengo4_redist", sha="sha256:bc")},
        "sources": {
            "ndl_partinfo": [_n("第1章 労働契約", 1, print_page=1), _n("第2章 賃金", 1, print_page=40)],
            "bencom": [_n("第1章 労働契約", 1, print_page=1), _n("第2章 賃金", 1, print_page=40)]}}))

    # 7) 単一源不足: 1源のみ → status insufficient・adoptable False (HOLD 不変条件)。
    s.append(("single_source_insufficient", {
        "isbn": "9784100000077", "title": "知的財産法",
        "source_meta": {"legallib": _meta("知的財産法", "legallib_extraction", sha="sha256:ll")},
        "sources": {"legallib": [_n("第1章 特許", 1, print_page=1)]}}))

    return s


def build() -> list[dict]:
    p = load_policy()
    rows = []
    for scenario, book in _scenarios():
        a = adopt_book(book, p)
        expected = {
            "status": a["step1"]["status"],
            "clustered_with_nodes": a["step1"]["clustered_with_nodes"],
            "human_review_sources": [h["source"] for h in a["step1"]["human_review"]],
            "base_source": a["base_source"],
            "guard_blocked": [b["source"] for b in a["step2"].get("guard_blocked", [])],
            "base_count": a["step3"].get("base_count", 0),
            "appended_count": a["step3"].get("appended_count", 0),
            "projection_node_count": a["projection_node_count"],
            "base_source_distribution": a["base_source_distribution"],
            "consensus_nodes": a["step4"].get("consensus_nodes", 0),
            "authority": a["step4"].get("authority"),
            "adoptable": a["adoptable"],
            "projection_sha": a["projection_sha"],
        }
        rows.append({"scenario": scenario, "expected": expected, "book": book})
    return rows


def main() -> int:
    rows = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"books": len(rows),
                      "scenarios": [r["scenario"] for r in rows],
                      "adoptable": sum(1 for r in rows if r["expected"]["adoptable"])},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
