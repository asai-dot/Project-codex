"""preflight バリデータ・差分バンドル・下流レビューツールのテスト.

Mac セッション前後でこちら側が使う道具一式を、合成フィクスチャで検証する。
実行: ``python tests/test_handoff_tools.py``。
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from inspect_legallib_dir import inspect_dir  # noqa: E402
from legallib_join_dryrun import _demo_inputs, run_dryrun  # noqa: E402
from legallib_join_policy import load_policy  # noqa: E402
from render_proposed_diff import classify as diff_classify, render  # noqa: E402
from triage_review_queue import triage  # noqa: E402
from validate_resolver import validate  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def test_validate_resolver() -> None:
    good = [
        {"legallib_book_id": "A", "isbn": "9784000000010", "bucket": "auto_accept"},
        {"legallib_book_id": "B", "isbn": "", "bucket": "human_review"},
        {"legallib_book_id": "C", "isbn": "", "bucket": "defer_new"},
    ]
    r = validate(good, expect=(1, 1, 1))
    check(r["ok"], "正常 resolver は ok")
    check(r["buckets"]["auto_accept"] == 1, "bucket 件数")

    bad = [
        {"legallib_book_id": "A", "isbn": "9784000000010", "bucket": "auto_accept"},
        {"legallib_book_id": "A", "isbn": "9784000000027", "bucket": "auto_accept"},  # dup book_id
        {"legallib_book_id": "D", "isbn": "x", "bucket": "weird"},  # unknown bucket
    ]
    r2 = validate(bad)
    check(not r2["ok"], "dup book_id / 未知 bucket は ok=False")
    check(r2["dup_book_ids"] == 1, "dup book_id 検出")
    check(any("未知の bucket" in e for e in r2["errors"]), "未知 bucket をエラー化")

    # 期待件数の不一致は warning (ハードエラーではない)。
    r3 = validate(good, expect=(1839, 305, 616))
    check(r3["ok"] and any("件数が期待と不一致" in w for w in r3["warnings"]),
          "件数不一致は warning")


def test_inspect_legallib_dir() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "1.json").write_text(json.dumps({
            "content_type": "book",
            "toc": [{"level": 1, "t": "章", "print_page": 3},
                    {"level": 2, "t": "節"}],
        }, ensure_ascii=False), encoding="utf-8")
        (d / "2.json").write_text(json.dumps({
            "content_type": "journal",
            "toc": [{"level": 1, "t": "論文　著者"}, {"level": 1, "t": ""}],  # 空1
        }, ensure_ascii=False), encoding="utf-8")
        res = inspect_dir(d)
        check(res["files"] == 2, "ファイル数 2")
        check(res["content_types"] == {"book": 1, "journal": 1}, "book/journal 内訳")
        check(res["node_list_keys"] == {"toc": 2}, "node list key = toc")
        check(res["total_nodes"] == 4, "総ノード 4")
        check(res["level_histogram"].get(1) == 3 and res["level_histogram"].get(2) == 1,
              "level 分布")
        check(abs(res["empty_title_rate"] - 0.25) < 1e-6, "空タイトル率 1/4")
        check(res["page_keys"].get("print_page") == 1, "print_page 検出")


def test_bundles_emitted() -> None:
    policy = load_policy(None)
    with tempfile.TemporaryDirectory() as td:
        resolver, legallib_dir, toc_dir, known = _demo_inputs(Path(td))
        res = run_dryrun(resolver, legallib_dir, toc_dir, known, policy)
        # L100 (simple→legallib) は overwrites_bundle に旧+新が入る。
        ob = res["overwrites_bundle"]
        check(len(ob) == 1 and ob[0]["isbn"] == "9784000000010", "overwrites_bundle に L100")
        check(ob[0]["existing_nodes"] and ob[0]["new_nodes"], "旧+新ノード同梱")
        # L300 (manual 衝突) は review_bundle に既存+候補が入る。
        rb = res["review_bundle"]
        check(len(rb) == 1 and rb[0]["isbn"] == "9784000000027", "review_bundle に L300")
        check(rb[0]["existing_primary_source"] == "manual", "既存ソース manual")
        check(rb[0]["existing_nodes"] and rb[0]["candidate_nodes"], "既存+候補同梱")


def test_render_diff() -> None:
    # enrich: 新が旧を包含し増える。
    existing = [{"t": "第1章"}]
    new = [{"t": "第1章"}, {"t": "第1章 第1節"}, {"t": "第2章"}]
    c = diff_classify(existing, new)
    check(c["kind"] == "enrich", "包含+増加=enrich")
    check(c["removed_titles"] == [], "失われるタイトルなし")
    # replace: 旧の一部が新に無い。
    c2 = diff_classify([{"t": "旧A"}, {"t": "旧B"}], [{"t": "新X"}])
    check(c2["kind"] == "replace", "入れ替わり=replace")
    check(len(c2["removed_titles"]) == 2, "失われるタイトル2件")

    with tempfile.TemporaryDirectory() as td:
        bundle = Path(td) / "ob.jsonl"
        bundle.write_text(json.dumps({
            "isbn": "9784000000010", "existing_nodes": existing, "new_nodes": new,
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        md = render(bundle)
        check("enrich" in md and "9784000000010" in md, "markdown 生成")


def test_triage() -> None:
    with tempfile.TemporaryDirectory() as td:
        bundle = Path(td) / "rb.jsonl"
        lines = [
            # candidate_richer: 既存被覆 1.0 かつ候補ノード増。
            {"isbn": "9784000000001", "existing_primary_source": "manual",
             "existing_nodes": [{"t": "第1章"}],
             "candidate_nodes": [{"t": "第1章"}, {"t": "第1節"}, {"t": "第2章"}]},
            # conflict: 重なりゼロ → 突合疑い、最優先。
            {"isbn": "9784000000002", "existing_primary_source": "ndl",
             "existing_nodes": [{"t": "全く別の本A"}, {"t": "別B"}],
             "candidate_nodes": [{"t": "無関係X"}, {"t": "無関係Y"}]},
        ]
        bundle.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines),
                          encoding="utf-8")
        rows = triage(bundle)
        check(rows[0]["kind"] == "conflict", "conflict が先頭 (最優先)")
        check(rows[0]["isbn"] == "9784000000002", "conflict の isbn")
        kinds = {r["isbn"]: r["kind"] for r in rows}
        check(kinds["9784000000001"] == "candidate_richer", "richer 判定")


def main() -> int:
    for t in [
        test_validate_resolver,
        test_inspect_legallib_dir,
        test_bundles_emitted,
        test_render_diff,
        test_triage,
    ]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
