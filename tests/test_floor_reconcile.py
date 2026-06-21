"""床突合(e-Gov 各号 anchor × 書式)のテスト (fixture anchor + 合成書式・stdlib のみ).

egov_fetch の各号 anchor が requirement_floor にそのまま流れること、curation レンズ(被覆0=
alias 要整備)が効くこと、抜け漏れ検出が通ることを固定する。実行: ``python tests/test_floor_reconcile.py``。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from egov_fetch import parse_items  # noqa: E402
from floor_reconcile import reconcile_floor  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


FIXTURE = (ROOT / "tests" / "fixtures" / "egov_kaishaho_199.xml").read_text(encoding="utf-8")
ANCHORS = parse_items(FIXTURE, law_id="K", article="199", paragraph="1")


def _forms():
    # 2書式とも 一号(募集株式の数)・二号(払込金額…) を短語で書く。三号(現物出資・長文)は
    # 短語「現物出資」で書く → anchor の長文名称と未マッチ(=alias 要整備として出るはず)。
    return [
        {"id": "f1", "source_family": "X", "記載事項": ["募集株式の数", "募集株式の払込金額又はその算定方法"]},
        {"id": "f2", "source_family": "Y", "記載事項": ["募集株式の数", "募集株式の払込金額又はその算定方法", "現物出資"]},
    ]


def test_anchors_flow_into_floor():
    res = reconcile_floor(ANCHORS, _forms())
    floor = res["floor"]
    check(floor["n_forms"] == 2, "書式2冊を認識")
    names = {r["名称"] for r in floor["statutory_floor"]}
    check("募集株式の数" in names, "全書式一致の一号が法定の床に乗る")


def test_curation_lens_flags_unmatched_long_anchor():
    res = reconcile_floor(ANCHORS, _forms())
    cur = res["curation_needed"]
    # 四号・五号は誰も書かない(被覆0)。三号は長文で短語「現物出資」と未マッチ→被覆0。
    gos = {r.get("号") for r in cur}
    check("四" in gos and "五" in gos, "誰も書かない号は curation 対象(被覆0)")
    check("三" in gos, "長文 anchor が書式短語と未マッチ→alias 要整備として surface")
    check(all(r["coverage"].startswith("0/") for r in cur), "curation_needed は被覆0のみ")


def test_omission_detection():
    # ドラフトが一号を落とす → 致命傷として撃つ(一号は床に乗っている前提)。
    draft = ["募集株式の払込金額又はその算定方法"]  # 一号(募集株式の数)を欠落
    res = reconcile_floor(ANCHORS, _forms(), draft=draft)
    miss = {r["名称"] for r in res["omissions"]["missing_statutory"]}
    check("募集株式の数" in miss, "床にある一号の欠落を致命傷として検出")
    check(not res["omissions"]["ok"], "床を満たさない")


def test_anchors_dict_payload_shape():
    # egov_fetch の --out は {items:[...]} 形。requirement_floor._load 経由で list に展開される。
    payload_items = ANCHORS  # reconcile_floor は list を直接受ける
    res = reconcile_floor(payload_items, _forms())
    check(isinstance(res["floor"]["statutory_floor"], list), "anchors(list)をそのまま消費")


def main() -> int:
    for t in [test_anchors_flow_into_floor, test_curation_lens_flags_unmatched_long_anchor,
              test_omission_detection, test_anchors_dict_payload_shape]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
