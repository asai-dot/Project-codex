"""記載事項の床 / 抜け漏れ検出のテスト (合成データ・stdlib のみ).

§5(ドクトリン)の実装。条文各号×N書式の収束で「法定の床」「実務必須」「裁量帯」を分け、
ドラフトの欠落を撃つ。実行: ``python tests/test_requirement_floor.py``。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from requirement_floor import analyze_floor, check_omissions  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


# 会社法199①各号 を模した法定記載事項 (合成)。
CANON = [
    {"id": "199-1-1", "号": "一", "名称": "募集株式の数", "aliases": ["株式の数"]},
    {"id": "199-1-2", "号": "二", "名称": "払込金額又はその算定方法", "aliases": ["払込金額", "出資の額"]},
    {"id": "199-1-3", "号": "三", "名称": "現物出資の定め", "aliases": ["現物出資"]},
    {"id": "199-1-4", "号": "四", "名称": "払込期日又は払込期間", "aliases": ["払込期日", "払込期間"]},
]


def _forms():
    # 3冊の書式。全冊が一〜二・四を書く。三(現物出資)は1冊のみ(条件付)。
    # 全冊が条文外の「発行可能株式総数の確認」を書く = 実務必須。1冊だけ「収入印紙」= 裁量。
    return [
        {"id": "bookA", "source_family": "X", "記載事項": [
            "募集株式の数", "払込金額", "払込期日", "発行可能株式総数の確認"]},
        {"id": "bookB", "source_family": "Y", "記載事項": [
            "株式の数", "出資の額", "払込期間", "発行可能株式総数の確認", "収入印紙"]},
        {"id": "bookC", "source_family": "Z", "記載事項": [
            "募集株式の数", "払込金額", "払込期日", "現物出資", "発行可能株式総数の確認"]},
    ]


def test_floor():
    f = analyze_floor(CANON, _forms())
    sf = {r["id"] for r in f["statutory_floor"]}
    cond = {r["id"] for r in f["statutory_conditional"]}
    check(sf == {"199-1-1", "199-1-2", "199-1-4"}, "法定の床=全冊一致の各号(数/金額/期日)")
    check(cond == {"199-1-3"}, "現物出資は1冊のみ→条件付")
    names = {r["名称"] for r in f["established_practice_floor"]}
    check(names == {"発行可能株式総数の確認"}, "全冊一致の条文外=実務必須")
    disc = {r["名称"] for r in f["discretion"]}
    check(disc == {"収入印紙"}, "一部のみ=裁量帯")
    check(f["independent_sources"] == 3 and not f["independence_warning"], "独立3源→警告なし")


def test_independence_warning():
    forms = _forms()
    for x in forms:
        x["source_family"] = "SAME"   # 全部同一上流
    f = analyze_floor(CANON, forms)
    check(f["independence_warning"], "同一上流→独立性警告(F4)")


def test_omissions():
    f = analyze_floor(CANON, _forms())
    # ドラフトが「払込金額」と「発行可能株式総数」を落とした → 致命傷+却下リスク。
    draft = ["募集株式の数", "払込期日"]
    res = check_omissions(draft, CANON, f)
    miss_stat = {r["id"] for r in res["missing_statutory"]}
    check(miss_stat == {"199-1-2"}, "払込金額の欠落=致命傷で検出")
    miss_prac = {r["名称"] for r in res["missing_practice"]}
    check(miss_prac == {"発行可能株式総数の確認"}, "実務必須の欠落=却下リスクで検出")
    check(not res["ok"], "欠落あり→ok=False")
    # 床を満たすドラフト。
    full = ["募集株式の数", "出資の額", "払込期日", "発行可能株式総数の確認"]
    check(check_omissions(full, CANON, f)["ok"], "床を満たせば ok")


def test_check_against_statute():
    from requirement_floor import check_against_statute
    canon = [
        {"id": "1", "号": "一", "名称": "募集株式の数", "aliases": ["募集株式の数"]},
        {"id": "2", "号": "二", "名称": "払込金額", "aliases": ["払込金額", "1株につき金"]},
        {"id": "3", "号": "三", "名称": "現物出資に関する事項", "条件付": True,
         "条件": ["現物出資", "金銭以外の財産"], "aliases": ["現物出資の内容及び価額", "現物出資財産"]},
        {"id": "4", "号": "四", "名称": "払込期日", "aliases": ["払込期日", "払込期間"]},
    ]
    # 現物出資なしの完全ドラフト → 三号は条件付で不要、欠落なし。
    ok = "募集株式の数 100株 払込金額 1株につき金5万円 払込期日 令和8年7月31日"
    r = check_against_statute(ok, canon)
    check(r["ok"], "現物出資なしの完全ドラフトは床を満たす")
    three = next(x for x in r["rows"] if x["号"] == "三")
    check(not three["required"] and not three["missing"], "三号は条件付・非該当でスルー(誤検出しない)")
    # 払込期日を落とす → 四号を致命傷で検出。
    miss = check_against_statute("募集株式の数 100株 払込金額 金5万円", canon)
    check({m["号"] for m in miss["missing"]} == {"四"}, "払込期日の欠落を検出")
    check(not miss["ok"], "欠落あり→ok=False")
    # 現物出資の語が出たら三号が必須化(条件付トリガ)。
    trig = check_against_statute("募集株式の数 100株 払込金額 金5万円 払込期日 7月 現物出資あり", canon)
    check(any(m["号"] == "三" for m in trig["missing"]), "現物出資の語→三号の内容欠落を必須化して検出")


def main() -> int:
    for t in [test_floor, test_independence_warning, test_omissions, test_check_against_statute]:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
