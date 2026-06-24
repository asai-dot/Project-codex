"""repair_quarantine — quarantine repairer: orphan ノードを理由付きで隔離 (C0 dry-run)。

GPT 監査が auto 候補に明示: 「unaccounted/orphan ノードを reason_code 付きで quarantine へ。
silent drop はしない」。cross-source 一致のない orphan ノードに quarantine_reason を **派生**
で付すだけ (削除も canonical 変更もしない)。repair_class=quarantine_only。実書込なし・決定的。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import re  # noqa: E402

from concordance import build_concordance  # noqa: E402
from repair_base import QUARANTINE_ONLY, Repairer, register  # noqa: E402

# DDSELFHEAL-C0 review #2: 索引/別表/付録/前付後付は orphan でも隔離対象から除外。
_APPENDIX_RX = re.compile(r"(索引|別表|凡例|書式|資料編?|付録|附録|参考文献|奥付|目次|はしがき|序文|あとがき)")


def _orphan_keys(book: dict) -> set[str]:
    conc = build_concordance(book.get("sources", {}))
    return {c["title_norm"] for c in conc["clusters"] if c["kind"] == "orphan"}


def _orphan_nodes(book: dict) -> list[tuple[str, int, str]]:
    """orphan クラスタに属し、まだ quarantine 印の無い node。

    単一ソース本は全 node が自明に orphan (cross-source 照合相手が居ない) になるが、
    それは『未照合だが正当』であって隔離対象ではない。**2ソース以上**で初めて
    『多源照合に失敗した orphan』= 隔離対象とみなす (過剰隔離を防ぐ)。
    """
    sources_with_nodes = [s for s, ns in book.get("sources", {}).items() if ns]
    if len(sources_with_nodes) < 2:
        return []
    keys = _orphan_keys(book)
    if not keys:
        return []
    source_meta = book.get("source_meta", {})
    norm = build_concordance(book.get("sources", {}))["normalized"]
    out = []
    for src, nodes in norm.items():
        # 既知 sparse / 多巻物 source は隔離対象外 (corpus メタで明示された場合)。
        sm = source_meta.get(src, {})
        if sm.get("sparse") or sm.get("multi_volume"):
            continue
        for n in nodes:
            if n["title_norm"] not in keys:
                continue
            raw = book["sources"][src][n["idx"]]
            if isinstance(raw, dict) and raw.get("quarantine_reason"):
                continue  # 既に隔離印あり → 冪等
            # 索引/別表/付録/前付後付は orphan でも隔離しない (構造上 cross-source 不一致が正常)。
            if _APPENDIX_RX.search(raw.get("title") or raw.get("t") or ""):
                continue
            out.append((src, n["idx"], n["title_norm"]))
    return out


class QuarantineOrphan(Repairer):
    name = "quarantine_orphan"
    repair_class = QUARANTINE_ONLY
    version = "0.1.0"

    def detect(self, book: dict) -> bool:
        return bool(_orphan_nodes(book))

    def plan(self, book: dict) -> dict | None:
        nodes = _orphan_nodes(book)
        if not nodes:
            return None
        changes = [{
            "locator": f"{src}#{idx}",
            "field": "quarantine_reason",
            "before": None,
            "after": "orphan_no_cross_source_match",
        } for (src, idx, _key) in nodes]
        return {
            "target": "derived.quarantine_reason",
            "changes": changes,
            "basis": "cross-source 一致のない orphan を reason_code 付きで隔離 "
                     "(silent drop せず・clean を汚さない)",
        }


quarantine_orphan = register(QuarantineOrphan())

__all__ = ["QuarantineOrphan", "quarantine_orphan"]
