"""tocadopt 回帰 + 安全不変条件 — DD-TOCADOPT-001 統一採用ルールの実装を固定。

owner ratify 済み設計 (v0.2 ACCEPTED) の 5 ステップ採用関数と §4 の 7 gate を、合成多源
golden で検証する。安全不変条件 (設計の HOLD / Required note を物理化):
  ★ 別版疑い/不足 source は合議に入れず adoptable=False。
  ★ granularity_guard 未満の源は base にならない (詳細→浅い劣化 0)。
  ★ 全採用ノードに provenance 5 項目 + source snapshot 実在 locator (invention 禁止)。
  ★ votes は provenance_origin 単位で distinct origin 数を超えない。
  ★ projection_sha は source 入力順に非依存。
  ★ 何も書かない (report_only)。

report-only・stdlib のみ・合成データのみ。
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from edition_identity import APPLY_OK_STATUS  # noqa: E402
from toc_adopt import adopt_book, adopt_corpus, load_policy  # noqa: E402
from toc_adopt_gates import run_gates  # noqa: E402

_FIXTURE = Path(__file__).resolve().parent / "golden" / "tocadopt" / "synthetic_multisource.jsonl"
_KNOWN_CONFLICT = Path(__file__).resolve().parent / "golden" / "edition" / "known_conflict_10.jsonl"
_PROVENANCE = ("source_system", "provenance_origin", "locator", "page_basis", "source_hash")

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def _load(path) -> list[dict]:
    return [json.loads(ln) for ln in Path(path).read_text(encoding="utf-8").split("\n") if ln.strip()]


def test_shape() -> None:
    rows = _load(_FIXTURE)
    check(len(rows) >= 7, f"golden は 7 シナリオ以上 (実 {len(rows)})")
    isbns = [r["book"]["isbn"] for r in rows]
    check(len(set(isbns)) == len(isbns), "ISBN は一意")
    scns = {r["scenario"] for r in rows}
    for need in ("merge_richest_base", "guard_block", "edition_exclude",
                 "consensus3", "pdf_offset", "protected_base", "single_source_insufficient"):
        check(need in scns, f"シナリオ {need} を含む")


def test_regression_lock() -> None:
    """焼き込んだ観測値を採用関数が再現する。"""
    p = load_policy()
    for r in _load(_FIXTURE):
        a = adopt_book(r["book"], p)
        e, sc = r["expected"], r["scenario"]
        check(a["step1"]["status"] == e["status"], f"{sc}: status {a['step1']['status']}")
        check(a["base_source"] == e["base_source"], f"{sc}: base {a['base_source']}")
        check(a["step1"]["clustered_with_nodes"] == e["clustered_with_nodes"],
              f"{sc}: clustered 不一致")
        check(a["projection_node_count"] == e["projection_node_count"],
              f"{sc}: projection nodes {a['projection_node_count']} != {e['projection_node_count']}")
        check(a["projection_sha"] == e["projection_sha"], f"{sc}: projection_sha 不一致")
        check(a["adoptable"] == e["adoptable"], f"{sc}: adoptable 不一致")


def test_safety_invariants() -> None:
    p = load_policy()
    rows = _load(_FIXTURE)
    for r in rows:
        book, sc = r["book"], r["scenario"]
        a = adopt_book(book, p)

        # ★ 別版疑い/不足 → adoptable False + 該当源は合議外。
        if a["step1"]["status"] not in APPLY_OK_STATUS:
            check(a["adoptable"] is False, f"{sc}: 同一性未解決なら adoptable False")

        # ★ guard-blocked 源は base にならない。
        blocked = {b["source"] for b in a["step2"].get("guard_blocked", [])}
        check(a["base_source"] not in blocked, f"{sc}: guard-blocked 源が base になった")

        # ★ 全ノードに provenance 5 項目 + locator が source snapshot に実在。
        for n in a["projection"]:
            check(all(n.get(f) for f in _PROVENANCE), f"{sc}: provenance 欠落 {n.get('title_norm')}")
            src, _, idx = n["locator"].partition("#")
            try:
                _ = book["sources"][src][int(idx)]
                exists = True
            except (KeyError, IndexError, ValueError):
                exists = False
            check(exists, f"{sc}: invention (snapshot に無い) {n['locator']}")

        # ★ votes は distinct provenance_origin 数を超えない。
        meta = book.get("source_meta", {})
        distinct = len({meta.get(s, {}).get("provenance_origin", s)
                        for s in a["step1"]["clustered_with_nodes"]})
        for n in a["projection"]:
            v = n.get("votes_by_provenance_origin", 0)
            check(v <= distinct, f"{sc}: votes {v} > distinct origins {distinct}")

        # ★ report_only。
        check(a["report_only"] is True, f"{sc}: report_only でない")


def test_projection_sha_order_independent() -> None:
    """source 入力順を反転しても projection_sha が一致する (gate1 の核)。"""
    p = load_policy()
    for r in _load(_FIXTURE):
        book = r["book"]
        rev = copy.deepcopy(book)
        rev["sources"] = dict(reversed(list(rev["sources"].items())))
        rev["source_meta"] = dict(reversed(list(rev["source_meta"].items())))
        check(adopt_book(book, p)["projection_sha"] == adopt_book(rev, p)["projection_sha"],
              f"{r['scenario']}: projection_sha が source 順に依存している")


def test_all_seven_gates() -> None:
    """§4 の 7 gate を実走 (gate1=自己再現 baseline / gate2=known_conflict fixture)。"""
    p = load_policy()
    rows = _load(_FIXTURE)
    books = [r["book"] for r in rows]
    corpus = adopt_corpus(books, p)
    adoptions = corpus["rows"]

    # gate1 baseline: source 順を変えた candidate と自己再現比較。
    baseline = {a["isbn"]: {"projection_sha": a["projection_sha"], "base_source": a["base_source"]}
                for a in adoptions}
    cand_rows = []
    for r in rows:
        rev = copy.deepcopy(r["book"])
        rev["sources"] = dict(reversed(list(rev["sources"].items())))
        cand_rows.append(adopt_book(rev, p))
    candidate = {a["isbn"]: {"projection_sha": a["projection_sha"], "base_source": a["base_source"]}
                 for a in cand_rows}

    known_conflict = _load(_KNOWN_CONFLICT)
    g = run_gates(books, adoptions, corpus_result=corpus,
                  baseline_projection=baseline, candidate_projection=candidate,
                  known_conflict_rows=known_conflict)

    check(g["checked"] == 7, f"7 gate 全て実走 (skipped: {g['skipped']})")
    check(g["all_checked_pass"], "全 gate pass")
    for gate in g["gates"]:
        check(gate["pass"] is True, f"{gate['gate']} = {gate['pass']}")


def main() -> int:
    for name, fn in (("test_shape", test_shape),
                     ("test_regression_lock", test_regression_lock),
                     ("test_safety_invariants", test_safety_invariants),
                     ("test_projection_sha_order_independent", test_projection_sha_order_independent),
                     ("test_all_seven_gates", test_all_seven_gates)):
        print(f"• {name}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
