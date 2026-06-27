#!/usr/bin/env python3
"""test_case_number_norm.py — N1〜N5 + MF-1/MF-4/P0-1/P0-2 の fixture 回帰 v0.3。

N規則・MF ↔ fixture 対応 (MF-5):
  N1 元号: N1,N1元年 / N2 数字: N2全角,N2漢数字(年),N2先頭ゼロ / N3 符号: N3
  N4 区切り: N4 / N5 枝番: N5 / MF-1 西暦逆引き禁止: MF1
  MF-4-1 後続full(同era別year/元号跨ぎ): MF41 / MF-4-2 component basis: MF42
  MF-4-3 raw span: MF43 / MF-4-4 fail-closed: MF44
  P0-1 互換字(半角カタカナ): P01 / P0-2 漢数字番号 fail-closed: P02 / 同字異義: 同字異義

実行: python3 scripts/test_case_number_norm.py  (exit 0 = 全PASS)。
"""
import sys
from case_number_norm import normalize, normalize_dockets

CASES = [
    ("令和3年(ワ)第123号", "R3-ワ-123", "N1"),
    ("平成28年(行ケ)第10120号", "H28-行ケ-10120", "N1"),
    ("令和元年(ワ)第1号", "R1-ワ-1", "N1元年"),
    ("令和３年（ワ）第１２３号", "R3-ワ-123", "N2全角"),
    ("平成二十八年(行ケ)第10120号", "H28-行ケ-10120", "N2漢数字(年)"),
    ("令和3年(ワ)第007号", "R3-ワ-7", "N2先頭ゼロ"),
    ("令和4年(行ウ)第5号", "R4-行ウ-5", "N3"),
    ("  令和5年 (ネ) 第 45 号 ", "R5-ネ-45", "N4"),
    ("令和3年(ワ)第123号の2", "R3-ワ-123-2", "N5"),
    ("平成31(行ケ)10003", "H31-行ケ-10003", "MF1元号年保持"),
    ("令和3年(ワ)第1号", "R3-ワ-1", "同字異義"),
    ("令和3年(わ)第1号", "R3-わ-1", "同字異義"),
    ("令和3年(ﾜ)第1号", "R3-ワ-1", "P01"),          # 半角カタカナ→NFKC畳み込み
    ("令和3年(ワ)第十二号", None, "P02"),            # 漢数字の事件番号→fail-closed
    ("事件番号不明", None, "未解析"),
    ("", None, "未解析"),
]


def run() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    for raw, expected, tag in CASES:
        got = normalize(raw)
        check(f"[{tag}] {raw!r} -> {got!r}", got == expected)

    # MF-1 西暦のみ → unresolved/None
    ds = normalize_dockets("2019(行ケ)10003")
    check("[MF1] 西暦のみ→unresolved/None",
          len(ds) == 1 and ds[0].norm is None and ds[0].era_resolution_status == "unresolved")

    # MF-4-1 後続 full docket・同era別year
    ds = normalize_dockets("令和3年(ワ)第1号、令和4年(ネ)第2号")
    check("[MF41] 後続full同era別year→R3-ワ-1/R4-ネ-2",
          [d.norm for d in ds] == ["R3-ワ-1", "R4-ネ-2"]
          and ds[1].parse_status == "parsed"
          and ds[1].component_basis["era"] == "observed")

    # MF-4-1 元号跨ぎ
    ds = normalize_dockets("平成31年(行ケ)第10003号、令和元年(行ケ)第10004号")
    check("[MF41] 元号跨ぎ→H31/R1",
          [d.norm for d in ds] == ["H31-行ケ-10003", "R1-行ケ-10004"])

    # MF-4-2 component basis: 裸番号継承(era/year/symbol inherited)
    ds = normalize_dockets("令和3年(ワ)第1号、第2号")
    b = ds[1].component_basis
    check("[MF42] 裸番号継承 basis",
          [d.norm for d in ds] == ["R3-ワ-1", "R3-ワ-2"]
          and b["era"] == "inherited" and b["year"] == "inherited"
          and b["symbol"] == "inherited" and b["number"] == "observed"
          and ds[1].parse_status == "partial" and ds[1].review_status == "review_required")

    # MF-4-2 symbol のみ observed (別符号明示)、era/year inherited
    ds = normalize_dockets("令和3年(ワ)第1号・(ネ)第9号")
    b = ds[1].component_basis
    check("[MF42] 別符号明示 basis",
          [d.norm for d in ds] == ["R3-ワ-1", "R3-ネ-9"]
          and b["symbol"] == "observed" and b["era"] == "inherited")

    # MF-4-3 raw span 保存
    ds = normalize_dockets("令和3年(ワ)第1号、第2号")
    raw = "令和3年(ワ)第1号、第2号"
    check("[MF43] raw span offset 保存",
          raw[ds[1].raw_start:ds[1].raw_end] == ds[1].raw_segment == "第2号")

    # MF-4-4 未知 tail → fail-closed (unresolved/review)
    ds = normalize_dockets("令和3年(ワ)第1号、ほか")
    check("[MF44] 未知tail fail-closed",
          ds[0].norm == "R3-ワ-1" and ds[1].norm is None
          and ds[1].parse_status == "unresolved" and ds[1].review_status == "review_required")

    # P1-1 is_display_primary
    ds = normalize_dockets("令和3年(ワ)第1号、第2号")
    check("[P11] is_display_primary は先頭のみ",
          ds[0].is_display_primary and not ds[1].is_display_primary)

    # 同字異義
    check("[同字異義] 民事ワ≠刑事わ",
          normalize("令和3年(ワ)第1号") != normalize("令和3年(わ)第1号"))

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print(f"RESULT: PASS ({len(CASES)} fixtures + MF-1/MF-4-1..4/P0-1/P0-2/P1-1/同字異義 green)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
