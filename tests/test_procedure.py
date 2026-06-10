"""⑥手続 wedge のテスト (合成書式タイトル・stdlib のみ).

spine の alias 突合で、申立/保全/破産系は手続に当たり、取引文書(契約)は当たらない
(＝「契約は手続でない」がデータ上自然に出る) ことを検証する。
実行: ``python tests/test_procedure.py``。
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from procedure_match import load_spine, match_title, run  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def _spine() -> list[dict]:
    return load_spine(Path(__file__).resolve().parents[1] / "pipeline" / "procedure_spine.json")


def test_spine_loads() -> None:
    spine = _spine()
    check(len(spine) == 24, "spine 24 類型")
    ids = [p["id"] for p in spine]
    check(len(ids) == len(set(ids)), "id 一意")
    check(all(p.get("根拠法令") for p in spine), "全類型に根拠法令")


def test_match_procedural_titles() -> None:
    spine = _spine()
    # 申立/保全/破産系 = 手続に当たる。
    check(match_title("破産手続開始申立書", spine)[0]["procedure_id"] == "insolvency_bankruptcy",
          "破産申立→破産")
    check(match_title("不動産仮差押命令申立書", spine)[0]["procedure_id"] == "civil_preservation",
          "仮差押→民事保全")
    check(match_title("債権差押命令申立書", spine)[0]["procedure_id"] == "civil_execution",
          "差押→民事執行")
    check(match_title("離婚調停申立書", spine)[0]["procedure_id"] == "family_mediation",
          "離婚調停→家事調停")


def test_transactional_titles_unmatched() -> None:
    spine = _spine()
    # 取引文書 (契約/規程) は手続 alias に当たらない = 手続でない。
    check(match_title("不動産売買契約書", spine) == [], "売買契約→手続なし")
    check(match_title("就業規則", spine) == [], "規程→手続なし")


def test_run_coverage() -> None:
    spine = _spine()
    templates = [
        {"id": "1", "title": "破産手続開始申立書"},
        {"id": "2", "title": "仮差押命令申立書"},
        {"id": "3", "title": "金銭消費貸借契約書"},   # unmatched
        {"id": "4", "title": "建物明渡請求訴訟 訴状"},  # 訴訟→通常訴訟
    ]
    res = run(spine, templates)
    check(res["total"] == 4 and res["matched"] == 3 and res["unmatched"] == 1,
          "4件中 3一致 1未一致 (契約は未一致)")
    check(res["coverage"].get("insolvency_bankruptcy") == 1, "破産 1件")
    check(res["coverage"].get("civil_preservation") == 1, "保全 1件")

    with tempfile.TemporaryDirectory() as td:
        # csv 入力も読めること。
        p = Path(td) / "t.csv"
        p.write_text("id,title\n9,破産手続開始申立書\n", encoding="utf-8")
        from procedure_match import load_templates
        rows = load_templates(p)
        check(run(spine, rows)["matched"] == 1, "csv 入力 OK")


def main() -> int:
    for t in [test_spine_loads, test_match_procedural_titles,
              test_transactional_titles_unmatched, test_run_coverage]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
