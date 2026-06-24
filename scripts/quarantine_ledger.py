"""quarantine_ledger — 隔離ノードの状態遷移を残す append-only 台帳 (DDSELFHEAL C1 前提)。

GPT 監査 (DDSELFHEAL-C0_PASS_WITH_NOTES) が C1 quarantine write の **必須前提** に指定:
「quarantine 状態変更前に ledger 必須。age/escape/recurrence は履歴がないと出せない」。
corpus_health は KPI として age/escape_rate/recurrence_rate を要求するが、スナップショット
単体では算出できず needs_ledger を立てるだけ。本台帳がその履歴を供給する。

状態遷移 (一方向の事実を append するのみ・書換/削除なし):
  enter   … reason_code 付きで隔離に入った
  release … 正当に隔離解除された (修復/owner 承認で clean へ)
  recur   … release 後に同じ locator が再び隔離に入った (再発)
  escape  … 隔離中の locator が下流 (apply/clean) に漏れた (本来 0 であるべき事故)

各レコードは decision_log と同じく直前 hash を連結した chain hash を持つ (改竄検知)。
**本台帳は監査履歴であり、本番データには一切書き込まない。** stdlib のみ・決定的。
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

GENESIS = "sha256:0"

ENTER, RELEASE, RECUR, ESCAPE = "enter", "release", "recur", "escape"
_TRANSITIONS = (ENTER, RELEASE, RECUR, ESCAPE)
DAY_SECONDS = 86400.0


def _canon(rec: dict) -> str:
    return json.dumps(rec, ensure_ascii=False, sort_keys=True)


def _hash(prev_hash: str, rec: dict) -> str:
    return "sha256:" + hashlib.sha256((prev_hash + _canon(rec)).encode("utf-8")).hexdigest()


def item_key(isbn: str, locator: str) -> str:
    """台帳上の隔離アイテム単位 (本 × locator)。"""
    return f"{isbn}|{locator}"


class QuarantineLedger:
    """append-only な隔離台帳。`record` のみ。書換/削除はしない。"""

    def __init__(self, path: str | Path, *, clock=None):
        self.path = Path(path)
        # 決定的テストのため clock を注入可能 (既定は wall-clock)。
        self._clock = clock or time.time

    def _last_hash(self) -> str:
        if not self.path.exists():
            return GENESIS
        last = GENESIS
        for line in self.path.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if line:
                last = json.loads(line).get("hash", last)
        return last

    def record(self, *, isbn: str, locator: str, transition: str,
               reason_code: str, decided_by: str, **extra) -> dict:
        """1 件の状態遷移を追記。返り値は格納レコード。"""
        if transition not in _TRANSITIONS:
            raise ValueError(f"unknown transition: {transition}")
        prev = self._last_hash()
        epoch = float(self._clock())
        core = {
            "isbn": isbn, "locator": locator, "key": item_key(isbn, locator),
            "transition": transition, "reason_code": reason_code,
            "decided_by": decided_by,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(epoch)),
            "epoch": round(epoch, 3), "prev_hash": prev, **extra,
        }
        rec = {**core, "hash": _hash(prev, core)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:  # append-only
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec


def _read(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def verify_chain(path: str | Path) -> dict:
    """台帳の hash chain を検証 (改竄/欠落検知)。decision_log と同じ規約。"""
    recs = _read(path)
    prev = GENESIS
    for i, rec in enumerate(recs):
        stored = rec.get("hash")
        core = {k: v for k, v in rec.items() if k != "hash"}
        if core.get("prev_hash") != prev or _hash(prev, core) != stored:
            return {"ok": False, "count": i, "broken_at": i}
        prev = stored
    return {"ok": True, "count": len(recs), "broken_at": None}


def kpi(path: str | Path, *, now: float | None = None) -> dict:
    """corpus_health の needs_ledger (age/escape_rate/recurrence_rate) を履歴から算出。

    各 item_key の遷移列を畳み込み、現在 open な隔離・その滞留日数・escape/再発を数える。
    now は決定的テストのため注入可 (既定は wall-clock)。report-only。
    """
    recs = _read(path)
    now = float(now if now is not None else time.time())

    # key ごとに遷移を時系列で再生し、現在状態と各種カウントを得る。
    last_enter_epoch: dict[str, float] = {}
    open_keys: dict[str, float] = {}        # 現在 open な key → 最新 enter epoch
    ever_entered: set[str] = set()
    released_once: set[str] = set()
    recurred_keys: set[str] = set()
    escaped_events = 0
    reason_open: dict[str, int] = {}

    for r in recs:
        key, tr, epoch = r["key"], r["transition"], float(r.get("epoch", now))
        if tr == ENTER:
            # release 後の再 enter は recur とみなす (明示 recur と等価に扱う)。
            if key in released_once and key not in open_keys:
                recurred_keys.add(key)
            ever_entered.add(key)
            open_keys[key] = epoch
            last_enter_epoch[key] = epoch
        elif tr == RECUR:
            recurred_keys.add(key)
            ever_entered.add(key)
            open_keys[key] = epoch
            last_enter_epoch[key] = epoch
        elif tr == RELEASE:
            open_keys.pop(key, None)
            released_once.add(key)
        elif tr == ESCAPE:
            escaped_events += 1

    for key, enter_epoch in open_keys.items():
        rc = next((r["reason_code"] for r in reversed(recs)
                   if r["key"] == key and r["transition"] in (ENTER, RECUR)), "unknown")
        reason_open[rc] = reason_open.get(rc, 0) + 1

    ages = [max(0.0, (now - e) / DAY_SECONDS) for e in open_keys.values()]
    entered_n = len(ever_entered) or 1
    released_n = len(released_once) or 1
    return {
        "entries": len(recs),
        "distinct_items": len(ever_entered),
        "open_count": len(open_keys),
        "released_count": len(released_once),
        "mean_age_days": round(sum(ages) / len(ages), 2) if ages else 0.0,
        "max_age_days": round(max(ages), 2) if ages else 0.0,
        # escape は隔離中アイテムの下流漏れ = 事故。C1 では 0 を不変条件にする。
        "escape_events": escaped_events,
        "escape_rate": round(escaped_events / entered_n, 3),
        # 再発率 = 一度 release した後に再隔離された item の割合。
        "recurrence_rate": round(len(recurred_keys) / released_n, 3),
        "open_by_reason": dict(sorted(reason_open.items())),
        "chain": verify_chain(path),
        "report_only": True,
    }


__all__ = [
    "QuarantineLedger", "verify_chain", "kpi", "item_key",
    "ENTER", "RELEASE", "RECUR", "ESCAPE", "GENESIS",
]
