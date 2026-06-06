"""Fork 1 接合の検収テスト (合成フィクスチャ・実データ不要・stdlib のみ).

検収条件をコードで固定する:
  1. level 入れ子から parent_toc_node_id を正しく再構築 (converter)。
  2. 既存の人手/NDL TOC (非simple) を 1 件も劣化させない = overwrite 候補に
     入らず diff 0 (policy / dryrun)。
  3. simple のみの既存だけが昇格上書きされる。
  4. book_id ↔ ISBN の誤マージ 0 (missing/ambiguous は blocked)。
  5. 変換は決定的 (冪等)。

実行: ``python tests/test_legallib_join.py`` (assert ベース、外部依存なし)。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from legallib_join_apply import apply_join  # noqa: E402
from legallib_join_dryrun import detect_mismerge, run_dryrun, _demo_inputs  # noqa: E402
from legallib_join_policy import (  # noqa: E402
    WRITE_ACTIONS,
    decide_join_action,
    load_policy,
)
from legallib_to_canonical import (  # noqa: E402
    convert_legallib_nodes,
    to_canonical_bib_extra_toc,
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


# --- 1. converter: level → parent 再構築 ------------------------------------

def test_parent_reconstruction() -> None:
    raw = [
        {"level": 1, "t": "第1編 総則", "p": 1},
        {"level": 2, "t": "第1章 通則", "p": 3},
        {"level": 3, "t": "第1節", "p": 4},
        {"level": 2, "t": "第2章", "p": 20},
        {"level": 1, "t": "第2編", "p": 50},
    ]
    nodes = convert_legallib_nodes(raw, "9784000000010")
    by_path = {n["toc_path_id"]: n for n in nodes}

    check(len(nodes) == 5, "node 数 5")
    check(nodes[0]["parent_toc_node_id"] == "", "編はトップ (親なし)")
    check(nodes[0]["toc_path_id"] == "c01", "1つ目 path = c01")
    check(nodes[1]["parent_toc_node_id"] == nodes[0]["toc_node_id"], "章の親 = 編")
    check(nodes[1]["toc_path_id"] == "c01.01", "章 path = c01.01")
    check(nodes[2]["parent_toc_node_id"] == nodes[1]["toc_node_id"], "節の親 = 章")
    check(nodes[2]["depth"] == 3, "節 depth = 3")
    check(nodes[3]["parent_toc_node_id"] == nodes[0]["toc_node_id"], "第2章の親 = 第1編")
    check(nodes[3]["toc_path_id"] == "c01.02", "第2章 path = c01.02")
    check(nodes[4]["parent_toc_node_id"] == "", "第2編はトップ")
    check(nodes[4]["toc_path_id"] == "c02", "第2編 path = c02")
    check(nodes[4]["page_start"] == 50, "page_start 転載")
    check(all(n["toc_source"] == "legallib" for n in nodes), "source=legallib")
    check(all(n["toc_status"] == "legallib" for n in nodes), "status=legallib(非simple)")
    check("9784000000010:toc:003" in by_path["c01.01.01"]["toc_node_id"], "連番 toc_node_id")


def test_level_jump_clamp() -> None:
    # 1 -> 3 の飛び。depth は親+1 にクランプされる。
    warnings: list[str] = []
    raw = [{"level": 1, "t": "A"}, {"level": 3, "t": "B"}]
    nodes = convert_legallib_nodes(raw, "9784000000010", warnings=warnings)
    check(nodes[1]["depth"] == 2, "level飛びは depth=2 にクランプ")
    check(nodes[1]["parent_toc_node_id"] == nodes[0]["toc_node_id"], "クランプ後も親=A")
    check(len(warnings) == 1, "warning 記録あり")


def test_deterministic() -> None:
    raw = [{"level": 1, "t": "X"}, {"level": 2, "t": "Y"}]
    a = convert_legallib_nodes(raw, "9784000000010")
    b = convert_legallib_nodes(raw, "9784000000010")
    check(a == b, "変換は決定的")


def test_empty_and_projection() -> None:
    check(convert_legallib_nodes([], "9784000000010") == [], "空入力→空")
    check(convert_legallib_nodes([{"level": 1, "t": "  "}], "9784000000010") == [],
          "空タイトルは捨てる")
    nodes = convert_legallib_nodes([{"level": 1, "t": "章", "p": 9}], "9784000000010")
    proj = to_canonical_bib_extra_toc(nodes)
    check(proj == [{"depth": 1, "label": "章", "page": 9}], "canonical 射影")


# --- 2/3. policy: 非simple 保護 / simple 昇格 --------------------------------

def test_policy_gate() -> None:
    simple = [{"toc_source": "openbd", "toc_status": "simple"}]
    manual = [{"toc_source": "manual", "toc_status": "curated"}]
    ndl = [{"toc_source": "ndl", "toc_status": "simple"}]  # NDL は simple でも保護
    pub = [{"toc_source": "publisher", "toc_status": "simple"}]
    already = [{"toc_source": "legallib", "toc_status": "legallib"}]
    mixed = [
        {"toc_source": "openbd", "toc_status": "simple"},
        {"toc_source": "openbd", "toc_status": "ocr"},  # 非simple 混在 → 保護
    ]

    check(decide_join_action(None) == "create", "既存なし→create")
    check(decide_join_action([]) == "create", "空→create")
    check(decide_join_action(simple) == "overwrite_simple", "simpleのみ→昇格上書き")
    check(decide_join_action(manual) == "route_human_review", "人手→保護(レビュー)")
    check(decide_join_action(ndl) == "route_human_review", "NDL→保護(simpleでも)")
    check(decide_join_action(pub) == "route_human_review", "出版社→保護")
    check(decide_join_action(already) == "skip_idempotent", "既legallib→冪等skip")
    check(decide_join_action(mixed) == "route_human_review", "非simple混在→保護")


# --- 4. 誤マージ0ガード ------------------------------------------------------

def test_mismerge_guard() -> None:
    known = {"9784000000010", "9784000000027"}
    rows = [
        {"legallib_book_id": "A", "isbn": "9784000000010", "bucket": "auto_accept"},
        {"legallib_book_id": "B", "isbn": "9784000099999", "bucket": "auto_accept"},  # 未登録
        {"legallib_book_id": "C", "isbn": "badisbn", "bucket": "auto_accept"},        # 不正
        # 同一 ISBN に 2 book_id (D,E) → 両方 ambiguous
        {"legallib_book_id": "D", "isbn": "9784000000027", "bucket": "auto_accept"},
        {"legallib_book_id": "E", "isbn": "9784000000027", "bucket": "auto_accept"},
    ]
    blocked = detect_mismerge(rows, known)
    check("A" not in blocked, "正当な突合は通る")
    check(blocked.get("B") == "blocked_missing_isbn", "未登録ISBNはblock")
    check(blocked.get("C") == "blocked_bad_isbn", "不正ISBNはblock")
    check(blocked.get("D") == "blocked_ambiguous_isbn", "曖昧ISBN(D)はblock")
    check(blocked.get("E") == "blocked_ambiguous_isbn", "曖昧ISBN(E)はblock")


# --- 統合: dryrun が検収不変条件を守る --------------------------------------

def test_dryrun_invariants() -> None:
    import tempfile

    policy = load_policy(None)
    with tempfile.TemporaryDirectory() as td:
        resolver, legallib_dir, toc_dir, known = _demo_inputs(Path(td))
        result = run_dryrun(resolver, legallib_dir, toc_dir, known, policy)

        # 検収核心: 保護対象への書き込みは 0。
        check(result["invariant_violations"] == [], "不変条件違反 0")

        by_book = {a["book_id"]: a for a in result["actions"]}
        # L100: 既存 simple → overwrite_simple (書き込み候補)。
        check(by_book["L100"]["action"] == "overwrite_simple", "L100 昇格上書き")
        check("9784000000010" in result["proposed_files"], "L100 提案あり")
        # L200: 既存なし → create。
        check(by_book["L200"]["action"] == "create", "L200 新規作成")
        # L300: 既存 manual → route_human_review (上書きしない)。
        check(by_book["L300"]["action"] == "route_human_review", "L300 人手保護")
        check("9784000000027" not in result["proposed_files"], "L300 提案に出ない(diff0)")
        # L900: ISBN 未登録 → blocked_missing_isbn。
        check(by_book["L900"]["action"] == "blocked_missing_isbn", "L900 誤マージ防止")
        # human_review / defer_new の振り分け。
        check(by_book["L777"]["action"] == "route_human_review", "L777 human_review")
        check(by_book["L888"]["action"] == "defer_staging", "L888 defer staging")
        check(len(result["defer_staging"]) == 1, "defer staging 1 件")

        # 書き込み候補は WRITE_ACTIONS のみ、かつ提案ファイルの ISBN と一致。
        write_isbns = {a["isbn"] for a in result["actions"] if a["action"] in WRITE_ACTIONS}
        check(write_isbns == set(result["proposed_files"]), "書込候補とproposed一致")


def test_tree_validity() -> None:
    # 変換結果が妥当な木か: 親参照は必ず既出ノード、depth は親+1 以内、
    # toc_path_id は親 path の接頭。深い入れ子と飛びを混在させる。
    raw = [
        {"level": 1, "t": "A"},
        {"level": 2, "t": "A1"},
        {"level": 4, "t": "A1a(飛び)"},   # 2 -> 4 飛び → depth=3 にクランプ
        {"level": 1, "t": "B"},
        {"level": 2, "t": "B1"},
    ]
    nodes = convert_legallib_nodes(raw, "9784000000010")
    seen: dict[str, dict] = {}
    by_id = {n["toc_node_id"]: n for n in nodes}
    for n in nodes:
        pid = n["parent_toc_node_id"]
        if pid:
            check(pid in seen, f"親 {pid} は既出 (forward ref 禁止)")
            parent = by_id[pid]
            check(n["depth"] == parent["depth"] + 1, "depth は親+1")
            check(n["toc_path_id"].startswith(parent["toc_path_id"] + "."),
                  "path は親 path の接頭")
        else:
            check(n["depth"] == 1, "親なしは depth=1")
        seen[n["toc_node_id"]] = n
    # toc_node_id は一意。
    check(len(by_id) == len(nodes), "toc_node_id 一意")
    # path_id も一意。
    paths = [n["toc_path_id"] for n in nodes]
    check(len(set(paths)) == len(paths), "toc_path_id 一意")


def test_dryrun_idempotent() -> None:
    import tempfile

    policy = load_policy(None)
    with tempfile.TemporaryDirectory() as td:
        resolver, legallib_dir, toc_dir, known = _demo_inputs(Path(td))
        r1 = run_dryrun(resolver, legallib_dir, toc_dir, known, policy)
        r2 = run_dryrun(resolver, legallib_dir, toc_dir, known, policy)
        check(r1["counts"] == r2["counts"], "dryrun カウント冪等")
        check(r1["proposed_files"] == r2["proposed_files"], "提案ファイル冪等")


def test_apply_safety() -> None:
    import tempfile

    policy = load_policy(None)
    with tempfile.TemporaryDirectory() as td:
        resolver, legallib_dir, toc_dir, known = _demo_inputs(Path(td))

        # dry-run (commit=False): 1 バイトも書かない。
        before = {p.name: p.read_text() for p in toc_dir.glob("*.json")}
        res = apply_join(resolver, legallib_dir, toc_dir, known, policy,
                         commit=False, whitelist=None)
        after = {p.name: p.read_text() for p in toc_dir.glob("*.json")}
        check(before == after, "dry-run は既存ファイル不変")
        check("isbn_9784000000034.json" not in after, "dry-run は新規も作らない")
        check(res["status_counts"].get("would_write") == 2, "would_write 2 件 (L100,L200)")
        # 人手保護 (9784000000027) は applied に出ない (書き込み候補ですらない)。
        check(all(a["isbn"] != "9784000000027" for a in res["applied"]),
              "人手TOC は適用候補に入らない")

        # commit=True: simple/新規のみ書く。人手は触らない。
        manual_before = (toc_dir / "isbn_9784000000027.json").read_text()
        res2 = apply_join(resolver, legallib_dir, toc_dir, known, policy,
                          commit=True, whitelist=None)
        check(res2["status_counts"].get("written") == 2, "written 2 件")
        manual_after = (toc_dir / "isbn_9784000000027.json").read_text()
        check(manual_before == manual_after, "人手TOC は commit でも不変 (diff 0)")
        # 上書きされた simple は legallib になっている。
        written = json.loads((toc_dir / "isbn_9784000000010.json").read_text())
        check(written[0]["toc_source"] == "legallib", "simple→legallib 昇格")
        # 再実行は冪等 (既 legallib → skip、書き込み 0)。
        res3 = apply_join(resolver, legallib_dir, toc_dir, known, policy,
                          commit=True, whitelist=None)
        check(res3["status_counts"].get("written", 0) == 0, "再commit は書き込み0 (冪等)")


def test_apply_whitelist() -> None:
    import tempfile

    policy = load_policy(None)
    with tempfile.TemporaryDirectory() as td:
        resolver, legallib_dir, toc_dir, known = _demo_inputs(Path(td))
        # L200 の ISBN のみ承認。
        res = apply_join(resolver, legallib_dir, toc_dir, known, policy,
                         commit=True, whitelist={"9784000000034"})
        check(res["status_counts"].get("written") == 1, "whitelist で1件のみ書込")
        check(res["status_counts"].get("needs_approval") == 1, "未承認は needs_approval")
        check((toc_dir / "isbn_9784000000034.json").exists(), "承認分は作成された")


def test_unreadable_existing_protected() -> None:
    # 既存ファイルが存在するが parse 不能 → 絶対に上書きしない (route_human_review)。
    import tempfile

    from legallib_join_apply import apply_join
    from legallib_join_dryrun import decide_for_isbn

    policy = load_policy(None)
    with tempfile.TemporaryDirectory() as td:
        resolver, legallib_dir, toc_dir, known = _demo_inputs(Path(td))
        # L100 の宛先 ISBN ファイルを壊す (truncated JSON)。
        corrupt = toc_dir / "isbn_9784000000010.json"
        corrupt.write_text('[{"t": "壊れ', encoding="utf-8")  # 不正 JSON

        protected = frozenset(policy["protected_sources"])
        action, state, nodes = decide_for_isbn(toc_dir, "9784000000010", protected)
        check(state == "unreadable", "parse 不能を unreadable と判定")
        check(action == "route_human_review", "unreadable は上書きせずレビューへ")

        res = run_dryrun(resolver, legallib_dir, toc_dir, known, policy)
        by_book = {a["book_id"]: a for a in res["actions"]}
        check(by_book["L100"]["action"] == "route_human_review", "L100 はレビュー行き")
        check("9784000000010" not in res["proposed_files"], "壊れたファイルは書き込み候補外")
        check(res["invariant_violations"] == [], "不変条件違反 0 (保護)")

        # apply commit でも壊れたファイルは触らない。
        before = corrupt.read_text()
        apply_join(resolver, legallib_dir, toc_dir, known, policy,
                   commit=True, whitelist=None)
        check(corrupt.read_text() == before, "commit でも壊れた保護ファイル不変")


def test_empty_book_id_blocked_individually() -> None:
    # 空 book_id の auto_accept 行が衝突せず行ごとに blocked される。
    import tempfile

    policy = load_policy(None)
    with tempfile.TemporaryDirectory() as td:
        _, legallib_dir, toc_dir, known = _demo_inputs(Path(td))
        rows = [
            {"legallib_book_id": "", "isbn": "9784000000010", "bucket": "auto_accept"},
            {"legallib_book_id": "", "isbn": "badisbn", "bucket": "auto_accept"},
        ]
        res = run_dryrun(rows, legallib_dir, toc_dir, known, policy)
        empties = [a for a in res["actions"] if a["action"] == "blocked_no_book_id"]
        check(len(empties) == 2, "空 book_id 2 行が各々 blocked (衝突なし)")
        check("9784000000010" not in res["proposed_files"], "空 book_id では書かない")


def main() -> int:
    tests = [
        test_parent_reconstruction,
        test_level_jump_clamp,
        test_deterministic,
        test_empty_and_projection,
        test_tree_validity,
        test_policy_gate,
        test_mismerge_guard,
        test_dryrun_invariants,
        test_dryrun_idempotent,
        test_unreadable_existing_protected,
        test_empty_book_id_blocked_individually,
        test_apply_safety,
        test_apply_whitelist,
    ]
    for t in tests:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
