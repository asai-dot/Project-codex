"""tocadopt 回帰 + 安全不変条件 — DD-TOCADOPT-001 統一採用ルール実装を固定。

DD-TOCADOPT-001-IMPL の GPT 監査 (MODIFY_REQUIRED) 反映後の挙動を固定する。
安全不変条件 (監査の must_fix を物理化):
  ★ C1: source_sha256 欠落ノードは捏造せず pending (accepted に入らない・source_hash は実値のみ)。
  ★ C4: partinfo volume_structure は rejected (採用も pending もしない)。
  ★ D1: accepted には consensus かつ provenance 健全なノードのみ。非合議は pending lane。
  ★ D2: adoptable = identity ∧ consensus ∧ authority≠HR ∧ provenance。
  ★ A1: 別版疑い源は connected component から外れ human_review。
  ★ B1: guard-blocked / 最富源より浅い源は base にならない。
  ★ projection_sha は source 入力順に非依存。何も書かない (report_only)。

report-only・stdlib のみ・合成データのみ。
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from edition_identity import APPLY_OK_STATUS  # noqa: E402
from toc_adopt import (  # noqa: E402
    adopt_book, adopt_corpus, export_baseline, load_policy,
)
from toc_adopt_gates import run_gates  # noqa: E402

_FIXTURE = Path(__file__).resolve().parent / "golden" / "tocadopt" / "synthetic_multisource.jsonl"
_KNOWN_CONFLICT = Path(__file__).resolve().parent / "golden" / "edition" / "adversarial_gold.jsonl"
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
    check(len(rows) >= 12, f"golden は 12 シナリオ以上 (実 {len(rows)})")
    isbns = [r["book"]["isbn"] for r in rows]
    check(len(set(isbns)) == len(isbns), "ISBN は一意")
    scns = {r["scenario"] for r in rows}
    for need in ("merge_richest_base", "guard_block", "edition_exclude", "consensus3",
                 "pdf_offset", "protected_base", "single_source_insufficient",
                 "partinfo_volume_structure", "missing_source_hash", "title_collision",
                 "duplicate_provenance_origin", "partinfo_mixed_small"):
        check(need in scns, f"シナリオ {need} を含む")


def test_regression_lock() -> None:
    p = load_policy()
    for r in _load(_FIXTURE):
        a = adopt_book(r["book"], p)
        e, sc = r["expected"], r["scenario"]
        check(a["step1"]["status"] == e["status"], f"{sc}: status {a['step1']['status']}")
        check(a["base_source"] == e["base_source"], f"{sc}: base {a['base_source']}")
        check(a["step1"]["clustered_with_nodes"] == e["clustered_with_nodes"], f"{sc}: clustered")
        check(a["projection_node_count"] == e["projection_node_count"], f"{sc}: accepted 数")
        check(a["pending_node_count"] == e["pending_node_count"], f"{sc}: pending 数")
        check(a["rejected_node_count"] == e["rejected_count"], f"{sc}: rejected 数")
        check(a["non_adoptable_node_count"] == e["non_adoptable_node_count"], f"{sc}: non_adoptable 数")
        check(a["projection_sha"] == e["projection_sha"], f"{sc}: projection_sha")
        check(a["adoptable"] == e["adoptable"], f"{sc}: adoptable")
        check(sorted(a["adoptable_blockers"]) == sorted(e["adoptable_blockers"]), f"{sc}: blockers")


def test_must_fix_invariants() -> None:
    """監査 must_fix (C1/C4/D1/D2/A1/B1) を直接突く。"""
    p = load_policy()
    rows = {r["scenario"]: r["book"] for r in _load(_FIXTURE)}

    # C1: missing_source_hash → 該当ノードは non_adoptable レーン (捏造せず)。accepted は実 sha のみ。
    a = adopt_book(rows["missing_source_hash"], p)
    check(all(n.get("source_hash") for n in a["accepted"]), "C1: accepted は実 source_hash のみ")
    check(a["non_adoptable_node_count"] == 1, "C1: 欠落ノードは non_adoptable レーン")
    check(all(n.get("snapshot_missing") for n in a["non_adoptable"]), "C1: non_adoptable=snapshot_missing")
    check("non_adoptable_nodes_present" in a["adoptable_blockers"], "C1: hard blocker 立つ")

    # C4: partinfo volume_structure は rejected (採用も pending もしない)。
    a = adopt_book(rows["partinfo_volume_structure"], p)
    rej_titles = {r["title_norm"] for r in a["rejected"]}
    check(rej_titles == {"上巻"}, f"C4: 上巻(volume_structure) を reject (実 {rej_titles})")
    allnodes = a["accepted"] + a["pending"]
    check(all(n["title_norm"] != "上巻" for n in allnodes), "C4: 上巻 は採用/pending に出ない")

    # N1/D1: 4 レーンが構造分離。各 node はちょうど1レーン。projection==accepted。
    for sc, book in rows.items():
        a = adopt_book(book, p)
        lanes = a["lanes"]
        check(a["projection"] is lanes["accepted"], f"N1/{sc}: projection==accepted lane")
        all_ln = lanes["accepted"] + lanes["pending_human_review"] + lanes["non_adoptable"]
        ids = [n["toc_node_id"] for n in all_ln]
        check(len(ids) == len(set(ids)), f"N1/{sc}: node は1レーンのみ")
        check(all(n.get("consensus") and n.get("source_hash") for n in lanes["accepted"]),
              f"D1/{sc}: accepted は consensus∧provenance")
        check(all(n.get("lane_reason") for n in lanes["pending_human_review"]),
              f"D1/{sc}: pending は理由付き")
        env = a["envelope"]
        check(env["apply_unit"] == "book_envelope" and env["apply_target"] == "accepted_node_set",
              f"N1/{sc}: envelope は book単位・accepted対象")
        check(env["apply_eligibility"]["adoptable"] == a["adoptable"], f"N1/{sc}: envelope 整合")

    # D2: adoptable = 5 名前付き条件 AND。consensus3 のみ True、他は blocker 付き。
    a = adopt_book(rows["consensus3"], p)
    check(a["adoptable"] and not a["adoptable_blockers"], "D2: consensus3 は adoptable")
    check(all(a["envelope"]["apply_eligibility"]["conditions"].values()), "D2: consensus3 は全条件 True")
    a = adopt_book(rows["edition_exclude"], p)
    check("identity_unresolved" in a["adoptable_blockers"], "D2: 別版は identity blocker")

    # G1 敵対: 同名節は locator 違いで別 toc_node_id (base 内重複を残す)。
    a = adopt_book(rows["title_collision"], p)
    coll = a["accepted"] + a["pending"]
    check(len(coll) == 2 and len({n["toc_node_id"] for n in coll}) == 2,
          "G1: 同名2節が別 toc_node_id で保持")

    # G1 敵対: 同一 provenance_origin の二重申告は votes を二重計上しない。
    a = adopt_book(rows["duplicate_provenance_origin"], p)
    alln = a["accepted"] + a["pending"] + a["non_adoptable"]
    check(all(n["votes_by_provenance_origin"] <= 1 for n in alln),
          "G1: 同一 origin は votes 二重計上しない")

    # A1: edition_exclude で別版源は human_review・clustered から外れる。
    a = adopt_book(rows["edition_exclude"], p)
    check("bencom" not in a["step1"]["clustered_with_nodes"], "A1: 別版源は合議外")
    check(any(h["source"] == "bencom" for h in a["step1"]["human_review"]), "A1: 別版源は human_review")

    # B1: guard_block で粗源 zosho は base にならない。
    a = adopt_book(rows["guard_block"], p)
    check(a["base_source"] != "zosho_bib_toc", "B1: guard-blocked 源は base でない")
    check("zosho_bib_toc" in [b["source"] for b in a["step2"]["guard_blocked"]], "B1: zosho は guard_blocked")


def test_safety_invariants() -> None:
    p = load_policy()
    for r in _load(_FIXTURE):
        book, sc = r["book"], r["scenario"]
        a = adopt_book(book, p)
        if a["step1"]["status"] not in APPLY_OK_STATUS:
            check(a["adoptable"] is False, f"{sc}: 同一性未解決なら adoptable False")
        blocked = {b["source"] for b in a["step2"].get("guard_blocked", [])}
        check(a["base_source"] not in blocked, f"{sc}: guard-blocked 源が base")
        for n in a["accepted"]:
            check(all(n.get(f) for f in _PROVENANCE), f"{sc}: accepted provenance 欠落")
            src, _, idx = n["locator"].partition("#")
            try:
                _ = book["sources"][src][int(idx)]
                exists = True
            except (KeyError, IndexError, ValueError):
                exists = False
            check(exists, f"{sc}: invention {n['locator']}")
        check(a["report_only"] is True, f"{sc}: report_only でない")


def test_projection_sha_order_independent() -> None:
    p = load_policy()
    for r in _load(_FIXTURE):
        book = r["book"]
        rev = copy.deepcopy(book)
        rev["sources"] = dict(reversed(list(rev["sources"].items())))
        rev["source_meta"] = dict(reversed(list(rev["source_meta"].items())))
        check(adopt_book(book, p)["projection_sha"] == adopt_book(rev, p)["projection_sha"],
              f"{r['scenario']}: projection_sha が source 順依存")


def test_release_guard() -> None:
    """REAUDIT2 must_fix#3: unified DRAFT policy が本番 policy として参照されないことを固定。

    confidence map 未使用 (REAUDIT2 should_fix#1) も policy `confidence_usage` で明示。
    """
    p = load_policy()
    check(p.get("_draft", {}).get("production_use_allowed") is False, "DRAFT: production 不許可")
    check("DRAFT" in (p.get("policy_version") or ""), "DRAFT: policy_version に DRAFT")
    check(p.get("release_boundary", {}).get("report_only") is True, "DRAFT: report_only")
    for must in ("production apply", "canonical projection apply", "policy本番切替"):
        check(must in p["release_boundary"]["hold"], f"DRAFT: HOLD に {must}")
    # 本流 production policy パスと別物 (このファイルは *_DRAFT.json)。
    from toc_adopt import _DEFAULT_POLICY  # noqa
    check("DRAFT" in _DEFAULT_POLICY.name and _DEFAULT_POLICY.name != "toc_merge_policy.json",
          "DRAFT: 本流 production policy ファイルと別物")
    # confidence map は未使用であることを policy に明記 (should_fix#1)。
    check("confidence_usage" in p, "should_fix: confidence 未使用を明記")


def test_unresolved_manifestation_excluded() -> None:
    """REAUDIT2 must_fix#4: 同定未解決 manifestation は合議・projection に参加しない。"""
    p = load_policy()
    # 別版疑い (suspected_different) の源は connected component 外 → human_review。
    book = {
        "isbn": "9784100009001", "title": "未解決版テスト",
        "source_meta": {
            "legallib": {"title": "民法", "publisher": "有斐閣", "year": "2018",
                         "page_basis": "print_page", "provenance_origin": "legallib_extraction",
                         "source_sha256": "sha256:ll", "edition": "第4版"},
            "bencom": {"title": "民法", "publisher": "有斐閣", "year": "2023",
                       "page_basis": "print_page", "provenance_origin": "bengo4_redist",
                       "source_sha256": "sha256:bc", "edition": "第7版"}},
        "sources": {
            "legallib": [{"title": "第1章 総則", "depth": 1, "print_page": 1}],
            "bencom": [{"title": "別版限定章", "depth": 1, "print_page": 1}]}}
    a = adopt_book(book, p)
    check(a["step1"]["status"] not in APPLY_OK_STATUS, "未解決: identity 未解決")
    check("bencom" not in a["step1"]["clustered_with_nodes"], "未解決: 別版源は合議外")
    # 別版源 (bencom) の固有 node は accepted/pending/projection のどこにも出ない。
    titles = {n["title_norm"] for n in a["accepted"] + a["pending"] + a["non_adoptable"]}
    check("別版限定章" not in titles, "未解決: 別版源の node は採用候補に出ない")
    check(a["projection_node_count"] == 0 or all(
        n["provenance_origin"] != "bengo4_redist" for n in a["accepted"]),
        "未解決: 別版源は projection に参加しない")
    check(a["adoptable"] is False and "identity_unresolved" in a["adoptable_blockers"],
          "未解決: adoptable False (identity blocker)")


def test_all_gates() -> None:
    """§4 の 7 gate + N1 lane 分離 gate8 を実走 (gate1=export_baseline / gate2=known_conflict)。"""
    p = load_policy()
    rows = _load(_FIXTURE)
    books = [r["book"] for r in rows]
    corpus = adopt_corpus(books, p)
    adoptions = corpus["rows"]

    # gate1: source 順を変えた candidate を export_baseline で同値比較。
    baseline = export_baseline(adoptions)
    cand_rows = []
    for r in rows:
        rev = copy.deepcopy(r["book"])
        rev["sources"] = dict(reversed(list(rev["sources"].items())))
        cand_rows.append(adopt_book(rev, p))
    candidate = export_baseline(cand_rows)

    known_conflict = _load(_KNOWN_CONFLICT)
    g = run_gates(books, adoptions, policy=p, corpus_result=corpus,
                  baseline_projection=baseline, candidate_projection=candidate,
                  known_conflict_rows=known_conflict)
    check(g["checked"] == 8, f"8 gate 全て実走 (skipped: {g['skipped']})")
    check(g["all_checked_pass"], "全 gate pass")
    for gate in g["gates"]:
        check(gate["pass"] is True, f"{gate['gate']} = {gate['pass']}")


def main() -> int:
    for name, fn in (("test_shape", test_shape),
                     ("test_regression_lock", test_regression_lock),
                     ("test_must_fix_invariants", test_must_fix_invariants),
                     ("test_safety_invariants", test_safety_invariants),
                     ("test_projection_sha_order_independent", test_projection_sha_order_independent),
                     ("test_release_guard", test_release_guard),
                     ("test_unresolved_manifestation_excluded", test_unresolved_manifestation_excluded),
                     ("test_all_gates", test_all_gates)):
        print(f"• {name}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
