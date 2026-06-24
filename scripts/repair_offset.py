"""repair_offset — 最初の決定的 repairer: 検証済み本単位 offset で print_page を派生。

GPT 監査が auto 候補に明示: 「book-level offset が confidence 1.0 かつ複数アンカー検証済の
ときの print/pdf 変換」。Phase0 所見6 (book TOC の 94.9% が単一 offset・両ページ持ち) が根拠。

**raw pdf_page は触らない** (hard rule #2)。派生フィールド print_page を before/after で示す
plan を返すだけ。実書込はしない (repair_class=deterministic_no_canonical_write, C0 は dry-run)。
stdlib のみ・決定的。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from page_basis import to_print_page  # noqa: E402
from repair_base import DET_NO_CANONICAL, Repairer, register  # noqa: E402


def _validated_offset(book: dict) -> int | None:
    """confidence 1.0 かつ validated な本単位 offset のみ採用 (それ以外は None=適用外)。"""
    po = book.get("page_offset")
    if not isinstance(po, dict):
        return None
    try:
        conf = float(po.get("confidence", 0))
        validated = bool(po.get("validated"))
        anchors = int(po.get("anchors", 0))
        offset = int(po["offset"])
    except (TypeError, ValueError, KeyError):
        return None
    # 決定的・高信頼のみ: confidence 1.0 / validated / アンカー2点以上。
    if conf >= 1.0 and validated and anchors >= 2:
        return offset
    return None


def _eligible_nodes(book: dict) -> list[tuple[str, int, int]]:
    """pdf_page を持ち print_page 未設定のノード (locator src, idx, pdf_page)。"""
    out = []
    for src, nodes in book.get("sources", {}).items():
        for i, n in enumerate(nodes):
            if not isinstance(n, dict):
                continue
            pdf = n.get("pdf_page")
            if pdf is None:
                continue
            if n.get("print_page") is not None:
                continue  # 既に派生済 → 冪等 (再適用しない)
            try:
                out.append((src, i, int(pdf)))
            except (TypeError, ValueError):
                continue
    return out


class OffsetPageConvert(Repairer):
    name = "offset_page_convert"
    repair_class = DET_NO_CANONICAL
    version = "0.1.0"

    def detect(self, book: dict) -> bool:
        return _validated_offset(book) is not None and bool(_eligible_nodes(book))

    def plan(self, book: dict) -> dict | None:
        offset = _validated_offset(book)
        if offset is None:
            return None
        nodes = _eligible_nodes(book)
        if not nodes:
            return None
        changes = [{
            "locator": f"{src}#{idx}",
            "field": "print_page",
            "before": None,
            "after": to_print_page(pdf, offset),
        } for (src, idx, pdf) in nodes]
        return {
            "target": "derived.print_page",
            "changes": changes,
            "basis": f"validated book offset={offset} (confidence=1.0, "
                     f"anchors>=2); raw pdf_page 不変",
        }


offset_page_convert = register(OffsetPageConvert())

__all__ = ["OffsetPageConvert", "offset_page_convert"]
