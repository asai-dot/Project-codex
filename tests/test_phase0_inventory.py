"""phase0_inventory の版判定ロジック単体テスト (実データ点検で観測した実例を凍結)。

本 repo の他テストと同じく **stdlib のみ** (pytest 非依存) の check ハーネスで走る。
CI は `for t in tests/test_*.py; do python "$t"; done` を pip install なしで回すため、
pytest を import するとここだけ ModuleNotFoundError で落ちていた (それを解消)。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from phase0_inventory import (  # noqa: E402
    edition_signature,
    is_real_suspect,
    norm_isbn,
    parse_year,
    title_diff_kind,
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


def test_edition_signature() -> None:
    cases = [
        ("刑法各論講義 第7版", "v7"),
        ("刑法各論講義 (第4版)", "v4"),
        ("環境訴訟法［第２版］", "v2"),       # 全角 + 隅付き
        ("労働法[第2版]", "v2"),
        ("家族法〔第4版〕", "v4"),
        ("業務委託契約書作成のポイント〈第２版〉", "v2"),
        ("労働法 第13版", "v13"),            # 2桁
        ("金融法講義 新版", "rev"),
        ("契約法〔新版〕", "rev"),
        ("国際取引法", ""),                  # 版表記なし
    ]
    for title, sig in cases:
        check(edition_signature(title) == sig, f"edition_signature({title!r}) == {sig!r}")


def test_title_diff_kind_cosmetic() -> None:
    # 全半角・読点・隅付き括弧だけの差 → 同一
    check(title_diff_kind("特許法 第2版", "特許法〔第2版〕") == "cosmetic", "cosmetic 隅付き")
    check(title_diff_kind(
        "第３版 Ｑ＆Ａ 遺言・信託 税金、執行",
        "第3版 Q&A 遺言・信託 税金,執行") == "cosmetic", "cosmetic 全半角")


def test_title_diff_kind_edition_number_conflict() -> None:
    check(title_diff_kind("刑法各論講義 第7版", "刑法各論講義 (第4版)") == "edition_number_conflict",
          "v7 vs v4")
    check(title_diff_kind("商標 第6版", "商標 第5版") == "edition_number_conflict", "v6 vs v5")


def test_title_diff_kind_subtitle() -> None:
    check(title_diff_kind(
        "実務裁判例 交通事故における過失相殺率 自転車・駐車場事故を中心にして",
        "実務裁判例 交通事故における過失相殺率") == "subtitle_difference", "subtitle 差")


def test_title_diff_kind_marker_asymmetry() -> None:
    check(title_diff_kind("家族法", "家族法〔第4版〕") == "edition_marker_asymmetry", "片側のみ版表記")


def _row(reason, **kw):
    base = {"status": "suspected_different_manifestation", "reason": reason,
            "title_diff_kind": None, "year_gap": None,
            "legallib_edition_sig": "", "canonical_edition_sig": ""}
    base.update(kw)
    return base


def test_is_real_suspect_filters_artifacts() -> None:
    check(is_real_suspect(_row("title divergence", title_diff_kind="cosmetic")) is False, "cosmetic→偽")
    check(is_real_suspect(_row("title divergence", title_diff_kind="subtitle_difference")) is False,
          "subtitle→偽")
    check(is_real_suspect(_row("title divergence", title_diff_kind="edition_number_conflict")) is True,
          "version衝突→真")


def test_is_real_suspect_year_rule() -> None:
    check(is_real_suspect(_row("year divergence", year_gap=1)) is False, "±1年は弱信号")
    check(is_real_suspect(_row("year divergence", year_gap=8)) is True, "年差≧2は要レビュー")
    # 版番号一致なら年差が大きくても重版扱い (= not real)
    check(is_real_suspect(_row("year divergence", year_gap=8,
                               legallib_edition_sig="v3", canonical_edition_sig="v3")) is False,
          "版一致なら重版")


def test_is_real_suspect_resolved_same() -> None:
    check(is_real_suspect({"status": "resolved_same_manifestation", "reason": "x"}) is False,
          "resolved_same→偽")


def test_norm_isbn_and_year() -> None:
    check(norm_isbn("978-4-8178-4197-1") == "9784817841971", "norm_isbn")
    check(parse_year("2014年 11月") == "2014", "parse_year 和暦表記")
    check(parse_year("2014-11-28") == "2014", "parse_year ISO")
    check(parse_year("") == "", "parse_year 空")


def main() -> int:
    for name, fn in sorted((n, f) for n, f in globals().items()
                           if n.startswith("test_") and callable(f)):
        print(f"• {name}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
