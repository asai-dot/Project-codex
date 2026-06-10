"""⑥手続 フローモデルのテスト (stdlib のみ).

同梱の scaffold フローが検証を通り、分岐が描画され、出典(source)欠落を検出することを確認。
実行: ``python tests/test_procedure_flow.py``。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from procedure_flow import load_flow, render_text, validate_flow  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def test_example_flow_valid() -> None:
    root = Path(__file__).resolve().parents[1]
    flow = load_flow(root / "pipeline" / "procedure_flow"
                     / "commercial_share_issue.example.json")
    check(validate_flow(flow) == [], "同梱 scaffold は検証エラー無し")
    md = render_text(flow)
    check("公開会社" in md and "非公開会社" in md, "分岐(公開/非公開)が描画される")
    check("変更登記" in md, "終局(変更登記)まで描画")


def test_source_required() -> None:
    # 出典(source)の無い node は捏造防止のため error。
    bad = {"entry": "a", "terminal": ["a"],
           "nodes": [{"id": "a", "局面": "x", "次": []}]}  # source 無し
    errs = validate_flow(bad)
    check(any("source" in e for e in errs), "source 欠落を検出")


def test_structure_checks() -> None:
    bad = {"entry": "a", "terminal": ["z"], "nodes": [
        {"id": "a", "source": "s", "次": [{"to": "ghost"}]},
        {"id": "b", "source": "s", "次": []},  # entry から到達不能
    ]}
    errs = validate_flow(bad)
    check(any("unknown 遷移先" in e and "ghost" in e for e in errs), "未知の遷移先検出")
    check(any("terminal が node に無い" in e for e in errs), "不正 terminal 検出")
    check(any("到達できない" in e and "b" in e for e in errs), "到達不能 node 検出")


def main() -> int:
    for t in [test_example_flow_valid, test_source_required, test_structure_checks]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
