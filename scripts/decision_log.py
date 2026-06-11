"""decision_log — conflict 解決の append-only 監査ログ (v0.3.1 §8 / P1)。

誰が・どの conflict を・どの根拠で解いたかを append-only で残す。各レコードに
直前レコードの hash を連結した chain hash を持たせ、改竄を検知可能にする
(append-only の機械的裏付け)。stdlib のみ。
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

GENESIS = "sha256:0" * 1  # 先頭の prev_hash


def _canon(rec: dict) -> str:
    return json.dumps(rec, ensure_ascii=False, sort_keys=True)


def _hash(prev_hash: str, rec: dict) -> str:
    return "sha256:" + hashlib.sha256((prev_hash + _canon(rec)).encode("utf-8")).hexdigest()


class DecisionLog:
    """append-only な決定ログ。`append` のみ。書き換え/削除はしない。"""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _last_hash(self) -> str:
        if not self.path.exists():
            return GENESIS
        last = GENESIS
        for line in self.path.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if line:
                last = json.loads(line).get("hash", last)
        return last

    def append(self, *, isbn: str, conflict_id: str, decision: str,
               decided_by: str, basis: str, **extra) -> dict:
        """1 件の決定を追記。返り値は格納されたレコード。"""
        prev = self._last_hash()
        core = {
            "isbn": isbn, "conflict_id": conflict_id, "decision": decision,
            "decided_by": decided_by, "basis": basis,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "prev_hash": prev, **extra,
        }
        rec = {**core, "hash": _hash(prev, core)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:  # append-only
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec


def verify_chain(path: str | Path) -> dict:
    """ログの hash chain を検証 (改竄/欠落検知)。"""
    p = Path(path)
    if not p.exists():
        return {"ok": True, "count": 0, "broken_at": None}
    prev = GENESIS
    count = 0
    for i, line in enumerate(p.read_text(encoding="utf-8").split("\n")):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        stored = rec.get("hash")
        core = {k: v for k, v in rec.items() if k != "hash"}
        if core.get("prev_hash") != prev or _hash(prev, core) != stored:
            return {"ok": False, "count": count, "broken_at": i}
        prev = stored
        count += 1
    return {"ok": True, "count": count, "broken_at": None}


__all__ = ["DecisionLog", "verify_chain", "GENESIS"]
