#!/usr/bin/env python3
"""test_case_number_norm.py — N1〜N5 の fixture 回帰 (DD-CASEID-002 deterministic_self_verification)。

各 N 規則を最小 fixture で検証。実コーパス(NII/D1)解析率の回帰は Mac CC で別途。
実行: python3 scripts/test_case_number_norm.py  (exit 0 = 全PASS)。
"""
import sys
from case_number_norm import normalize

# (入力, 期待 norm, 効かせる規則)
CASES = [
    # N1 元号
    ("令和3年(ワ)第123号", "R3-ワ-123", "N1"),
    ("平成28年(行ケ)第10120号", "H28-行ケ-10120", "N1"),
    ("昭和56年(オ)第123号", "S56-オ-123", "N1"),
    ("令和元年(ワ)第1号", "R1-ワ-1", "N1元年=1"),
    # N2 全角数字/カッコ
    ("令和３年（ワ）第１２３号", "R3-ワ-123", "N2全角"),
    ("平成二十八年(行ケ)第10120号", "H28-行ケ-10120", "N2漢数字"),
    ("令和3年(ワ)第007号", "R3-ワ-7", "N2先頭ゼロ"),
    # N3 符号保持 (かな/漢字, ローマ字化しない)
    ("令和4年(行ウ)第5号", "R4-行ウ-5", "N3漢字+カナ符号"),
    ("令和2年(家イ)第99号", "R2-家イ-99", "N3家事符号"),
    # N4 区切り除去・再構成 (第/号/年/空白)
    ("  令和5年 (ネ) 第 45 号 ", "R5-ネ-45", "N4空白/第/号"),
    # N5 枝番
    ("令和3年(ワ)第123号の2", "R3-ワ-123-2", "N5枝番"),
    # 同字異義: 民事ワ と 刑事わ は別 norm (identity保持)
    ("令和3年(ワ)第1号", "R3-ワ-1", "同字異義(カナ)"),
    ("令和3年(わ)第1号", "R3-わ-1", "同字異義(かな)"),
    # 未解析 → None (provisional。捨てない・推測しない)
    ("事件番号不明", None, "未解析"),
    ("令和3年 ワ 123", None, "符号カッコ無し=未解析"),
    ("", None, "空"),
]


def run() -> int:
    fails = []
    for raw, expected, rule in CASES:
        got = normalize(raw)
        ok = got == expected
        print(f"  {'PASS' if ok else 'FAIL'}  [{rule}] {raw!r} -> {got!r}")
        if not ok:
            fails.append((raw, expected, got))
    # 不変条件: 民事ワ と 刑事わ が衝突しない (identity分離)
    assert normalize("令和3年(ワ)第1号") != normalize("令和3年(わ)第1号"), "同字異義が衝突"
    print()
    if fails:
        print(f"RESULT: FAIL ({len(fails)})")
        for raw, exp, got in fails:
            print(f"  {raw!r}: expected {exp!r}, got {got!r}")
        return 1
    print(f"RESULT: PASS ({len(CASES)} fixtures green; 民事ワ≠刑事わ 確認)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
