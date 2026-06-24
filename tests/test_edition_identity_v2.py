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


def _s2(title, year="", isbn="", publisher="", page_count=None):
    return {"title": title, "year": year, "isbn": isbn, "publisher": publisher, "page_count": page_count}


def test_unit_cases() -> None:
    check(classify_edition_identity_v2([_s("民法")])["status"] == INSUFFICIENT,
          "single source → insufficient")
    check(classify_edition_identity_v2([_s("刑法各論講義 第7版", "2020"),
                                        _s("刑法各論講義 (第4版)", "2007")])["status"] == SUSPECTED_DIFFERENT,
          "第7版 vs 第4版 → suspected")
    check(classify_edition_identity_v2([_s("特許法 第2版", "2017", "有斐閣"),
                                        _s("特許法〔第2版〕", "2017", "有斐閣")])["status"] == RESOLVED_SAME,
          "cosmetic 隅付き括弧差 → resolved_same")
    # H2: substring 包含は positive 同一性証拠でない (ISBN 不明なら review)。
    check(classify_edition_identity_v2([
        _s("実務裁判例 交通事故における過失相殺率 自転車・駐車場事故を中心にして", "2020"),
        _s("実務裁判例 交通事故における過失相殺率", "2020")])["status"] == INSUFFICIENT,
          "subtitle 包含・ISBN不明 → insufficient (H2)")
    # ただし同 ISBN なら同一本として resolved。
    check(classify_edition_identity_v2([
        _s2("実務裁判例 過失相殺率 自転車編", "2020", isbn="978X"),
        _s2("実務裁判例 過失相殺率", "2020", isbn="978X")])["status"] == RESOLVED_SAME,
          "subtitle 包含・同ISBN → resolved")
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


def test_phase0_behavior_lock() -> None:
    """実 2,082 対の挙動ロック (二次回帰)。

    監査 H5 を受け、意味上の primary truth は独立 adversarial gold
    (test_edition_adversarial.py) に移譲。本テストは「大きな回帰がないこと」の二次ロック。
    Phase0 sample は resolver が **ISBN 一致**で対にしたものなので、共有 ISBN を両レコードに
    注入して classifier に渡す (H1: classifier は isbn を読む)。
    """
    if not _SAMPLE.exists():
        check(False, f"sample 不在: {_SAMPLE}")
        return
    rows = [json.loads(ln) for ln in _SAMPLE.read_text(encoding="utf-8").split("\n") if ln.strip()]
    check(len(rows) == 2082, f"2,082 対 (実 {len(rows)})")

    overall = {RESOLVED_SAME: 0, SUSPECTED_DIFFERENT: 0, INSUFFICIENT: 0}
    ednum_status = {}
    title_sig_mismatch_resolved = 0
    for d in rows:
        a = dict(d["canonical"], isbn=d["isbn"])
        b = dict(d["legallib"], isbn=d["isbn"])
        r = classify_edition_identity_v2([a, b])
        overall[r["status"]] = overall.get(r["status"], 0) + 1
        if d.get("title_diff_kind") == "edition_number_conflict":
            ednum_status[r["status"]] = ednum_status.get(r["status"], 0) + 1
        ev = r.get("evidence") or {}
        if ev.get("title_edition_sig") == "mismatch" and r["status"] == RESOLVED_SAME:
            title_sig_mismatch_resolved += 1

    # 不変条件1: title 版番号衝突 26 は ISBN 一致でも resolved に倒さない (矛盾データを検出)。
    check(ednum_status.get(SUSPECTED_DIFFERENT, 0) == 26 and sum(ednum_status.values()) == 26,
          f"版番号衝突 26/26 を suspected 保持 (実 {ednum_status})")
    # 不変条件2: title 版 signature mismatch のペアは決して resolved にならない。
    check(title_sig_mismatch_resolved == 0, f"版signature mismatch を resolved にしない (実 {title_sig_mismatch_resolved})")
    # 挙動ロック (観測値: isbn 注入で resolved 1917 / suspected 60 / insufficient 105。
    # insufficient が多いのは Required note 2: 同 isbn でも年/頁/出版社の大差は review)。
    check(overall[RESOLVED_SAME] == 1917, f"resolved_same 1917 (実 {overall[RESOLVED_SAME]})")
    check(overall[SUSPECTED_DIFFERENT] == 60, f"suspected 60 (実 {overall[SUSPECTED_DIFFERENT]})")
    check(overall[INSUFFICIENT] == 105, f"insufficient 105 (実 {overall[INSUFFICIENT]})")


def main() -> int:
    for name, fn in (("test_unit_cases", test_unit_cases),
                     ("test_phase0_behavior_lock", test_phase0_behavior_lock)):
        print(f"• {name}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
