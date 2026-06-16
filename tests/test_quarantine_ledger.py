"""quarantine_ledger テスト — 隔離台帳の append-only / chain / KPI 算出を検証。

GPT 監査 (DDSELFHEAL-C0) が C1 quarantine write の必須前提に指定した age/escape_rate/
recurrence_rate を、履歴から決定的に再現できることを固定する。clock/now を注入して
wall-clock 非依存にする。report-only・stdlib のみ。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from quarantine_ledger import (  # noqa: E402
    ENTER, ESCAPE, RECUR, RELEASE, QuarantineLedger, item_key, kpi, verify_chain,
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


def _ledger(tmp: Path, t0: list):
    """単調増加の擬似 clock を注入した台帳 (t0[0] を呼ぶたび +1 日)。"""
    def clock():
        v = t0[0]
        t0[0] += 86400.0
        return v
    return QuarantineLedger(tmp / "q.jsonl", clock=clock)


def test_append_and_chain() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        lg = _ledger(tmp, [1_000_000.0])
        r1 = lg.record(isbn="A", locator="legallib#0", transition=ENTER,
                       reason_code="orphan_no_cross_source_match", decided_by="engine")
        r2 = lg.record(isbn="A", locator="legallib#1", transition=ENTER,
                       reason_code="orphan_no_cross_source_match", decided_by="engine")
        check(r1["hash"] != r2["hash"], "各レコードは異なる hash")
        check(r2["prev_hash"] == r1["hash"], "chain: prev_hash が直前 hash を指す")
        chain = verify_chain(tmp / "q.jsonl")
        check(chain["ok"] and chain["count"] == 2, "chain 検証 OK / 2 件")


def test_tamper_detected() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        lg = _ledger(tmp, [1_000_000.0])
        lg.record(isbn="A", locator="x#0", transition=ENTER,
                  reason_code="r", decided_by="e")
        lg.record(isbn="A", locator="x#1", transition=ENTER,
                  reason_code="r", decided_by="e")
        p = tmp / "q.jsonl"
        lines = p.read_text(encoding="utf-8").split("\n")
        lines[0] = lines[0].replace('"x#0"', '"x#9"')  # 1 行目を改竄
        p.write_text("\n".join(lines), encoding="utf-8")
        check(verify_chain(p)["ok"] is False, "改竄が chain で検知される")


def test_kpi_open_age_and_recurrence() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        # 各 record で epoch が +1日ずつ進む。
        lg = _ledger(tmp, [0.0])
        loc = "legallib#0"
        lg.record(isbn="A", locator=loc, transition=ENTER, reason_code="orphan", decided_by="e")        # day0
        lg.record(isbn="A", locator="legallib#1", transition=ENTER, reason_code="orphan", decided_by="e")  # day1 open
        lg.record(isbn="A", locator=loc, transition=RELEASE, reason_code="orphan", decided_by="owner")    # day2 release loc
        lg.record(isbn="A", locator=loc, transition=ENTER, reason_code="orphan", decided_by="e")          # day3 recur loc
        # now = day10 (epoch 10*86400)
        k = kpi(tmp / "q.jsonl", now=10 * 86400.0)
        check(k["distinct_items"] == 2, f"distinct=2 (実 {k['distinct_items']})")
        check(k["open_count"] == 2, f"open=2 (loc 再 enter + legallib#1) 実 {k['open_count']}")
        check(k["released_count"] == 1, f"released=1 実 {k['released_count']}")
        # loc は release 後に再 enter → recurrence。released_n=1。
        check(k["recurrence_rate"] == 1.0, f"recurrence=1.0 実 {k['recurrence_rate']}")
        check(k["escape_events"] == 0, "escape は 0")
        check(k["escape_rate"] == 0.0, "escape_rate 0")
        # open の age: loc は day3 enter→day10 で 7日、legallib#1 は day1→day10 で 9日。
        check(k["max_age_days"] == 9.0, f"max_age=9 実 {k['max_age_days']}")
        check(k["mean_age_days"] == 8.0, f"mean_age=8 実 {k['mean_age_days']}")
        check(k["chain"]["ok"], "kpi の chain 検証 OK")


def test_escape_is_counted() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        lg = _ledger(tmp, [0.0])
        lg.record(isbn="B", locator="b#0", transition=ENTER, reason_code="orphan", decided_by="e")
        lg.record(isbn="B", locator="b#0", transition=ESCAPE, reason_code="orphan", decided_by="?")
        k = kpi(tmp / "q.jsonl", now=86400.0)
        check(k["escape_events"] == 1, "escape 計上")
        check(k["escape_rate"] == 1.0, "escape_rate = 1/1")


def test_empty_ledger() -> None:
    with tempfile.TemporaryDirectory() as d:
        k = kpi(Path(d) / "none.jsonl", now=0.0)
        check(k["entries"] == 0 and k["open_count"] == 0, "空台帳でも安全に 0")
        check(k["chain"]["ok"], "空台帳の chain は OK")
        check(item_key("X", "y#0") == "X|y#0", "item_key 形式")
        _ = RECUR  # 参照 (lint)


def main() -> int:
    for name, fn in (("test_append_and_chain", test_append_and_chain),
                     ("test_tamper_detected", test_tamper_detected),
                     ("test_kpi_open_age_and_recurrence", test_kpi_open_age_and_recurrence),
                     ("test_escape_is_counted", test_escape_is_counted),
                     ("test_empty_ledger", test_empty_ledger)):
        print(f"• {name}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
