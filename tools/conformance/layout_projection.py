"""layout_projection — DD-LAYOUT-001 v0.5 §3 reading projection（型別読み + coverage）。

依存ゼロ・read-only 純関数。位置情報（page_block）で「脚注だけ/図表だけ/本文だけ」を型別に
射影し、**coverage を必ず伴わせて「未型付け＝存在しない」と断定させない**（G_LAYOUT_PROJECTION
_COVERAGE_VISIBLE）。reading_order_key は挿入耐性（LexoRank/decimal）で並べる。

参照: docs/dd_candidates/DD-LAYOUT-001_..._v0.5_20260619.md §2,§3
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set

# DocLayNet 11 ラベル（verbatim・block_type 正準）
DOCLAYNET_LABELS = {
    "Caption", "Footnote", "Formula", "List-item", "Page-footer", "Page-header",
    "Picture", "Section-header", "Table", "Text", "Title",
}
READING_SCOPES = {"body", "footnote", "marginal"}  # column:N は別途


class LayoutValidationError(ValueError):
    pass


@dataclass
class PageBlock:
    block_id: str
    reading_order_key: str          # 挿入耐性キー（decimal path / LexoRank）
    reading_order_scope: str        # body | footnote | marginal | column:N
    block_type: Optional[str] = None  # None = 未型付け（射影で「存在しない」と断定しない）

    def __post_init__(self):
        if self.block_type is not None and self.block_type not in DOCLAYNET_LABELS:
            # ALO subtype は "Footnote.note" のように prefix 一致を許容
            base = self.block_type.split(".", 1)[0]
            if base not in DOCLAYNET_LABELS:
                raise LayoutValidationError(f"未知の block_type: {self.block_type}")


@dataclass
class Coverage:
    blocks_total: int
    blocks_typed: int
    blocks_untyped: int
    scope_coverage: float  # 射影 scope 内で型付け済みの割合（不完全なら欠落を断定しない）


@dataclass
class ProjectionResult:
    items: List[PageBlock]
    coverage: Coverage


def reading_order_between(lo: Optional[str], hi: Optional[str]) -> str:
    """挿入耐性: lo と hi の間の decimal key を返す（LexoRank の最小実装）。"""
    lo_v = float(lo) if lo is not None else 0.0
    hi_v = float(hi) if hi is not None else (lo_v + 2.0)
    if lo is not None and hi is not None and not (lo_v < hi_v):
        raise LayoutValidationError("lo < hi 必須")
    return f"{(lo_v + hi_v) / 2.0:.6f}"


def reading_projection(blocks: List[PageBlock],
                       block_types: Optional[Set[str]] = None,
                       scope: Optional[str] = None) -> ProjectionResult:
    """(block_type, scope) クエリで型別読み。結果は reading_order_key 昇順 + coverage 付き。"""
    # scope フィルタ（射影母集団）
    scoped = [b for b in blocks if scope is None or b.reading_order_scope == scope]

    # 型フィルタ（block_type 一致。ALO subtype は base 一致も許容）
    def _match(b: PageBlock) -> bool:
        if block_types is None:
            return b.block_type is not None
        if b.block_type is None:
            return False
        base = b.block_type.split(".", 1)[0]
        return b.block_type in block_types or base in block_types

    items = sorted([b for b in scoped if _match(b)], key=lambda b: float(b.reading_order_key))

    typed = sum(1 for b in scoped if b.block_type is not None)
    total = len(scoped)
    untyped = total - typed
    cov = Coverage(
        blocks_total=total, blocks_typed=typed, blocks_untyped=untyped,
        scope_coverage=(typed / total) if total else 1.0,
    )
    return ProjectionResult(items=items, coverage=cov)
