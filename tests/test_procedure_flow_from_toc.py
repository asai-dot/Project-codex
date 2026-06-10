"""詳細TOC → 手続フロー雛形 生成のテスト (stdlib のみ)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from procedure_flow import validate_flow  # noqa: E402
from procedure_flow_from_toc import build_flows  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def _toc() -> list[dict]:
    return [
        {"title": "募集株式の発行", "level": 0, "page": 120},
        {"title": "発行の決定", "level": 1, "page": 121},
        {"title": "募集事項の決定", "level": 1, "page": 124},
        {"title": "変更登記", "level": 1, "page": 138},
        {"title": "吸収合併", "level": 0, "page": 200},
        {"title": "合併契約の締結", "level": 1, "page": 201},
        {"title": "効力発生・登記", "level": 1, "page": 220},
    ]


def test_build_flows() -> None:
    flows = build_flows(_toc(), "会社法実務スケジュール", "978-X")
    check(len(flows) == 2, "上位2章=業務2件")
    f = flows[0]
    check(f["title"] == "募集株式の発行" and len(f["nodes"]) == 3, "募集株式の発行=3局面")
    check(f["status"] == "toc_stub", "status=toc_stub (分岐は監査で後付け)")
    # 局面が TOC 順で線形に連なる。
    check(f["entry"] == "n001" and f["terminal"] == ["n003"], "entry/terminal")
    check(f["nodes"][0]["次"] == [{"to": "n002"}], "線形遷移")
    # 各 node に出典(書名+頁)。
    check(all("会社法実務スケジュール" in n["source"] for n in f["nodes"]), "出典に書名")
    check("p121" in f["nodes"][0]["source"], "出典に頁番号")
    # 生成 stub は flow 検証を通る。
    check(validate_flow(f) == [], "生成 stub は validate OK")


def test_loose_keys() -> None:
    # キーの揺れ (t/p/d) を受ける。
    toc = [{"t": "解散・清算", "d": 0, "p": 300}, {"t": "解散決議", "d": 1, "p": 301}]
    flows = build_flows(toc, "会社法実務スケジュール", None)
    check(len(flows) == 1 and flows[0]["title"] == "解散・清算", "t/d/p キーで解釈")


def main() -> int:
    for t in [test_build_flows, test_loose_keys]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
