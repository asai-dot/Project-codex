"""repair_normalize — 決定的 repairer: 生 title から title_norm を再生成 (C0 dry-run)。

GPT 監査が auto 候補に明示: 「変化していない生 observation から決定的な正規化タイトル/
fingerprint を再生成」。生 title は触らず、派生 title_norm が欠落/陳腐化している node に
正しい normalize_title を **派生**する plan を返す。実書込なし・決定的・canonical 不変。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _toc_text import normalize_title  # noqa: E402
from repair_base import DET_NO_CANONICAL, Repairer, register  # noqa: E402


def _raw_title(n: dict) -> str:
    return n.get("t") or n.get("title") or n.get("label") or ""


class NormalizeTitleRegen(Repairer):
    name = "normalize_title_regen"
    repair_class = DET_NO_CANONICAL
    version = "0.1.0"

    def _targets(self, book: dict) -> list[tuple[str, int, str, str]]:
        out = []
        for src, nodes in book.get("sources", {}).items():
            for i, n in enumerate(nodes):
                if not isinstance(n, dict):
                    continue
                raw = _raw_title(n)
                if not raw:
                    continue
                want = normalize_title(raw)
                have = n.get("title_norm")
                if have != want:  # 欠落 or 陳腐化のみ対象 (一致なら冪等 no-op)
                    out.append((src, i, have, want))
        return out

    def detect(self, book: dict) -> bool:
        return bool(self._targets(book))

    def plan(self, book: dict) -> dict | None:
        targets = self._targets(book)
        if not targets:
            return None
        changes = [{
            "locator": f"{src}#{idx}",
            "field": "title_norm",
            "before": have,
            "after": want,
        } for (src, idx, have, want) in targets]
        return {
            "target": "derived.title_norm",
            "changes": changes,
            "basis": "normalize_title(raw title); 生 title は不変",
        }


normalize_title_regen = register(NormalizeTitleRegen())

__all__ = ["NormalizeTitleRegen", "normalize_title_regen"]
