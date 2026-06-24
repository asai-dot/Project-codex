"""repair_sha — 決定的 repairer: 解決済みソース内容から欠落 body_sha を再計算 (C0 dry-run)。

GPT 監査が auto 候補に明示: 「ソースファイルが既に解決済みのとき欠落 body_sha を再計算」。
ソース内容 (source_content) があり source_sha256 が欠落しているときだけ、内容の sha256 を
**派生**する plan を返す。内容自体は触らない (hard rule #2)。実書込なし・決定的。
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from repair_base import DET_NO_CANONICAL, Repairer, register  # noqa: E402


def _sha256_text(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


class BodyShaRecompute(Repairer):
    name = "body_sha_recompute"
    repair_class = DET_NO_CANONICAL
    version = "0.1.0"

    def _targets(self, book: dict) -> list[tuple[str, str]]:
        out = []
        for src, m in book.get("source_meta", {}).items():
            if not isinstance(m, dict):
                continue
            content = m.get("source_content")
            if content is None:
                continue  # 内容が解決していない → 適用外 (推測しない)
            if str(m.get("source_sha256") or "").strip():
                continue  # 既に sha あり → 冪等
            out.append((src, str(content)))
        return out

    def detect(self, book: dict) -> bool:
        return bool(self._targets(book))

    def plan(self, book: dict) -> dict | None:
        targets = self._targets(book)
        if not targets:
            return None
        changes = [{
            "locator": f"source_meta.{src}",
            "field": "source_sha256",
            "before": None,
            "after": _sha256_text(content),
        } for (src, content) in targets]
        return {
            "target": "derived.source_sha256",
            "changes": changes,
            "basis": "sha256(source_content); 解決済み内容のみ・内容は不変",
        }


body_sha_recompute = register(BodyShaRecompute())

__all__ = ["BodyShaRecompute", "body_sha_recompute"]
