#!/usr/bin/env python3
"""test_case_number_norm.py — N1〜N5 + MF-1/MF-4 の fixture 回帰 v0.2。

N規則 ↔ fixture 対応 (MF-5):
  N1 元号       : tags N1, N1元年
  N2 数字       : tags N2全角, N2漢数字, N2先頭ゼロ
  N3 符号保持   : tags N3
  N4 区切り除去 : tags N4
  N5 枝番       : tags N5
  MF-1 西暦逆引き禁止 : tags MF1
  MF-4 多docket      : tags MF4 (normalize_dockets)
  同字異義/未解析     : tags 同字異義, 未解析

実行: python3 scripts/test_case_number_norm.py  (exit 0 = 全PASS)。
"""
import sys
from case_number_norm import normalize, normalize_dockets

CASES = [
    ("令和3年(ワ)第123号", "R3-ワ-123", "N1"),
    ("平成28年(行ケ)第10120号", "H28-行ケ-10120", "N1"),
    ("昭和56年(オ)第123号", "S56-オ-123", "N1"),
    ("令和元年(ワ)第1号", "R1-ワ-1", "N1元年"),
    ("令和３年（ワ）第１２３号", "R3-ワ-123", "N2全角"),
    ("平成二十八年(行ケ)第10120号", "H28-行ケ-10120", "N2漢数字"),
    ("令和3年(ワ)第007号", "R3-ワ-7", "N2先頭ゼロ"),
    ("令和4年(行ウ)第5号", "R4-行ウ-5", "N3"),
    ("令和2年(家イ)第99号", "R2-家イ-99", "N3"),
    ("  令和5年 (ネ) 第 45 号 ", "R5-ネ-45", "N4"),
    ("令和3年(ワ)第123号の2", "R3-ワ-123-2", "N5"),
    ("令和3年(ワ)第1号", "R3-ワ-1", "同字異義"),
    ("令和3年(わ)第1号", "R3-わ-1", "同字異義"),
    ("平成31(行ケ)10003", "H31-行ケ-10003", "N1元号年保持"),  # MF-1: 西暦化しない
    ("事件番号不明", None, "未解析"),
    ("令和3年 ワ 123", None, "未解析"),
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

    # MF-1: 西暦のみ → unresolved / norm=None (決定日から推測しない)
    ds = normalize_dockets("2019(行ケ)10003")
    check("[MF1] 西暦のみ→unresolved/None",
          len(ds) == 1 and ds[0].norm is None and ds[0].era_resolution_status == "unresolved")

    # MF-4: 併合事件 → 1:N。全 docket 正規化、primary/ordinal 保持、era/sym 継承
    ds = normalize_dockets("令和3年(ワ)第1号、第2号")
    norms = [d.norm for d in ds]
    check("[MF4] 併合(裸番号継承)→2 docket",
          norms == ["R3-ワ-1", "R3-ワ-2"]
          and ds[0].is_primary and not ds[1].is_primary
          and [d.ordinal for d in ds] == [0, 1])

    ds2 = normalize_dockets("平成31(行ケ)10003、10004")
    check("[MF4] 併合(行ケ継承)→H31-行ケ-10003/10004",
          [d.norm for d in ds2] == ["H31-行ケ-10003", "H31-行ケ-10004"])

    ds3 = normalize_dockets("令和3年(ワ)第1号・(ネ)第9号")
    check("[MF4] 併合(別符号明示)→ワ/ネ",
          [d.norm for d in ds3] == ["R3-ワ-1", "R3-ネ-9"])

    # 同字異義の identity 分離
    check("[同字異義] 民事ワ≠刑事わ",
          normalize("令和3年(ワ)第1号") != normalize("令和3年(わ)第1号"))

    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)}): {fails}")
        return 1
    print(f"RESULT: PASS ({len(CASES)} fixtures + MF-1/MF-4/同字異義 green)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
