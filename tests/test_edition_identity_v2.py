"""edition_identity_v2 強化版 manifestation 同定テスト (DD-EDIDENT-001 §6 を CI に凍結)。

stdlib check()/main() ハーネス (CI は pytest 無しで各 test_*.py を実行するため、pytest の
assert 形式だと実行されず素通りする。phase0/tocadopt と同じ形式に統一)。

2 部構成:
  1. Phase0 実例で凍結した単体ケース (版衝突 / cosmetic / subtitle / 年±1 / 非対称 / 頁・出版社)。
  2. **§6 受入の回帰凍結**: 実 2,082 対 (`handoff/.../edition_identity_sample.jsonl`) に v2 を適用し、
     確実な別版 26/26 保持・cosmetic 全回収・別版疑い総数=72・insufficient=53 を固定。
report-only・stdlib のみ・決定的。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from edition_identity import INSUFFICIENT, RESOLVED_SAME, SUSPECTED_DIFFERENT  # noqa: E402
from edition_identity_v2 import classify_edition_identity_v2  # noqa: E402

_SAMPLE = (Path(__file__).resolve().parents[1]
           / "handoff" / "legallibjoin_v0.3.1_phase0_20260615" / "edition_identity_sample.jsonl")

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


def _s(title, year="", publisher="", page_count=None):
    return {"title": title, "year": year, "publisher": publisher, "page_count": page_count}


def test_unit_cases() -> None:
    check(classify_edition_identity_v2([_s("民法")])["status"] == INSUFFICIENT,
          "single source → insufficient")
    check(classify_edition_identity_v2([_s("刑法各論講義 第7版", "2020"),
                                        _s("刑法各論講義 (第4版)", "2007")])["status"] == SUSPECTED_DIFFERENT,
          "第7版 vs 第4版 → suspected")
    check(classify_edition_identity_v2([_s("特許法 第2版", "2017", "有斐閣"),
                                        _s("特許法〔第2版〕", "2017", "有斐閣")])["status"] == RESOLVED_SAME,
          "cosmetic 隅付き括弧差 → resolved_same")
    check(classify_edition_identity_v2([
        _s("実務裁判例 交通事故における過失相殺率 自転車・駐車場事故を中心にして", "2020"),
        _s("実務裁判例 交通事故における過失相殺率", "2020")])["status"] == RESOLVED_SAME,
          "subtitle 包含 → resolved_same")
    check(classify_edition_identity_v2([_s("意匠出願のてびき 第36版", "2022"),
                                        _s("意匠出願のてびき 第36版", "2023")])["status"] == RESOLVED_SAME,
          "同版で年±1 → 重版 resolved_same")
    check(classify_edition_identity_v2([_s("アメリカにおける第二の親の決定", "2022"),
                                        _s("アメリカにおける第二の親の決定", "2020")])["status"] == SUSPECTED_DIFFERENT,
          "版なし年差2 → suspected")
    check(classify_edition_identity_v2([_s("家族法", "2020"),
                                        _s("家族法〔第4版〕", "2020")])["status"] == INSUFFICIENT,
          "版マーカ非対称 → insufficient (OQ-1: 要レビュー)")
    check(classify_edition_identity_v2([_s("会社法", "2020", "有斐閣", 600),
                                        _s("会社法", "2020", "有斐閣", 300)])["status"] == INSUFFICIENT,
          "page_count 大差 → insufficient (Required note 2)")
    check(classify_edition_identity_v2([_s("会社法", "2020", "有斐閣"),
                                        _s("会社法", "2020", "別の出版社")])["status"] == INSUFFICIENT,
          "publisher 相違 → insufficient")


def test_phase0_regression_freeze() -> None:
    """§6 受入を実 2,082 対で凍結 (確実な別版を取りこぼさず偽陽性を回収)。"""
    if not _SAMPLE.exists():
        check(False, f"sample 不在: {_SAMPLE}")
        return
    rows = [json.loads(ln) for ln in _SAMPLE.read_text(encoding="utf-8").split("\n") if ln.strip()]
    check(len(rows) == 2082, f"2,082 対 (実 {len(rows)})")

    overall = {RESOLVED_SAME: 0, SUSPECTED_DIFFERENT: 0, INSUFFICIENT: 0}
    by_kind: dict = {}
    for d in rows:
        r = classify_edition_identity_v2([d["canonical"], d["legallib"]])
        st = r["status"]
        overall[st] = overall.get(st, 0) + 1
        k = d.get("title_diff_kind")
        by_kind.setdefault(k, {}).setdefault(st, 0)
        by_kind[k][st] += 1

    # §6.1 確実な別版 (edition_number_conflict 26) を 1 件も取りこぼさない。
    ednum = by_kind.get("edition_number_conflict", {})
    check(ednum.get(SUSPECTED_DIFFERENT, 0) == 26 and sum(ednum.values()) == 26,
          f"§6.1 真の別版 26/26 を suspected 保持 (実 {ednum})")
    # §6.2 cosmetic 123 を全て resolved_same へ回収 (過検知 0)。
    cos = by_kind.get("cosmetic", {})
    check(cos.get(RESOLVED_SAME, 0) == 123 and sum(cos.values()) == 123,
          f"§6.2 cosmetic 123 全回収 (実 {cos})")
    # edition_marker_asymmetry 53 は全て insufficient (要レビュー・apply 不可)。
    asym = by_kind.get("edition_marker_asymmetry", {})
    check(asym.get(INSUFFICIENT, 0) == 53 and sum(asym.values()) == 53,
          f"非対称 53 全 insufficient (実 {asym})")
    # genuine_title_diff 30 は全て suspected (核相違は混ぜない)。
    gen = by_kind.get("genuine_title_diff", {})
    check(gen.get(SUSPECTED_DIFFERENT, 0) == 30 and sum(gen.values()) == 30,
          f"genuine_title_diff 30 全 suspected (実 {gen})")
    # 全体分布の凍結 (別版疑い v1 344 → v2 72)。
    check(overall[SUSPECTED_DIFFERENT] == 72, f"suspected 総数 72 (実 {overall[SUSPECTED_DIFFERENT]})")
    check(overall[INSUFFICIENT] == 53, f"insufficient 総数 53 (実 {overall[INSUFFICIENT]})")
    check(overall[RESOLVED_SAME] == 1957, f"resolved_same 総数 1957 (実 {overall[RESOLVED_SAME]})")
    # apply 許可集合は広がっていない (resolved_same のみが apply_ok、suspected/insufficient は不可)。
    from edition_identity_v2 import is_apply_allowed_identity
    check(not is_apply_allowed_identity(SUSPECTED_DIFFERENT)
          and not is_apply_allowed_identity(INSUFFICIENT),
          "§6.2 apply 許可集合不変 (suspected/insufficient は apply 不可)")


def main() -> int:
    for name, fn in (("test_unit_cases", test_unit_cases),
                     ("test_phase0_regression_freeze", test_phase0_regression_freeze)):
        print(f"• {name}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
