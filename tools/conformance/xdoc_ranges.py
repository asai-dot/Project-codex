"""xdoc_ranges — DD-XDOC-001 v0.8 §9-1 の range_class 別 set 演算 adapter（依存ゼロ・純関数）。

coordinate_space → range_class の3系統を、contains / intersects / check_nonempty で統一契約化。
- interval_1d (page/char_offset/token): half-open [start,end)
- grid_2d (table_cell): row×col half-open グリッド矩形 → 単位セル集合で厳密判定
- rect_2d (figure_region): 同一 page・同一 coordinate_system の軸平行矩形 → 座標圧縮で厳密判定

range 表現（tuple）:
  interval_1d : (start, end)
  grid_2d     : (row_start, row_end, col_start, col_end)
  rect_2d     : (page, x0, y0, x1, y1, coordinate_system)
異 range_class 間演算は禁止（呼び出し側が coordinate_space で adapter を選ぶ）。
"""
from __future__ import annotations

from typing import List, Sequence, Tuple


class RangeError(ValueError):
    pass


# ---- interval_1d -------------------------------------------------------------------
def _iv_check(ranges: Sequence[Tuple[int, int]]) -> None:
    for s, e in ranges:
        if not (s < e):
            raise RangeError(f"degenerate interval [{s},{e})")


def _iv_union(ranges: Sequence[Tuple[int, int]]) -> List[Tuple[int, int]]:
    _iv_check(ranges)
    out: List[Tuple[int, int]] = []
    for s, e in sorted(ranges):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def _iv_contains(covered, required) -> bool:
    cov = _iv_union(covered)
    for s, e in _iv_union(required):
        if not any(cs <= s and e <= ce for cs, ce in cov):
            return False
    return True


def _iv_intersects(a, b) -> bool:
    ua, ub = _iv_union(a), _iv_union(b)
    return any(as_ < be and bs < ae for as_, ae in ua for bs, be in ub)


# ---- grid_2d（単位セル集合・厳密） ------------------------------------------------
def _grid_check(ranges) -> None:
    for rs, re, cs, ce in ranges:
        if not (rs < re and cs < ce):
            raise RangeError(f"degenerate grid cell ({rs},{re},{cs},{ce})")


def _grid_cells(ranges) -> set:
    _grid_check(ranges)
    cells = set()
    for rs, re, cs, ce in ranges:
        for r in range(rs, re):
            for c in range(cs, ce):
                cells.add((r, c))
    return cells


def _grid_contains(covered, required) -> bool:
    return _grid_cells(required) <= _grid_cells(covered)


def _grid_intersects(a, b) -> bool:
    return bool(_grid_cells(a) & _grid_cells(b))


# ---- rect_2d（座標圧縮・厳密） ----------------------------------------------------
def _rect_check(ranges) -> None:
    for _p, x0, y0, x1, y1, _cs in ranges:
        if not (x0 < x1 and y0 < y1):
            raise RangeError(f"degenerate rect ({x0},{y0},{x1},{y1})")


def _rect_group(ranges):
    """page × coordinate_system でグループ化（異 system は混在不可）。"""
    _rect_check(ranges)
    groups = {}
    for p, x0, y0, x1, y1, cs in ranges:
        groups.setdefault((p, cs), []).append((x0, y0, x1, y1))
    return groups


def _rect_contains(covered, required) -> bool:
    cov_g = _rect_group(covered)
    for key, reqs in _rect_group(required).items():
        cov = cov_g.get(key, [])
        for rx0, ry0, rx1, ry1 in reqs:
            # 座標圧縮: required 矩形内を covered で覆えるか（セル中心判定）
            xs = sorted({rx0, rx1} | {x for (x0, _, x1, _) in cov for x in (x0, x1) if rx0 < x < rx1})
            ys = sorted({ry0, ry1} | {y for (_, y0, _, y1) in cov for y in (y0, y1) if ry0 < y < ry1})
            for i in range(len(xs) - 1):
                for j in range(len(ys) - 1):
                    cx = (xs[i] + xs[i + 1]) / 2.0
                    cy = (ys[j] + ys[j + 1]) / 2.0
                    inside = any(x0 <= cx <= x1 and y0 <= cy <= y1 for (x0, y0, x1, y1) in cov)
                    if not inside:
                        return False
    return True


def _rect_intersects(a, b) -> bool:
    a_g = _rect_group(a)
    for key, breqs in _rect_group(b).items():
        for (ax0, ay0, ax1, ay1) in a_g.get(key, []):
            for (bx0, by0, bx1, by1) in breqs:
                if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                    return True
    return False


# ---- dispatch ----------------------------------------------------------------------
_SPACE_TO_CLASS = {
    "page": "interval_1d", "char_offset": "interval_1d", "token": "interval_1d",
    "table_cell": "grid_2d", "figure_region": "rect_2d",
}
_ADAPTERS = {
    "interval_1d": (_iv_check, _iv_contains, _iv_intersects),
    "grid_2d": (_grid_check, _grid_contains, _grid_intersects),
    "rect_2d": (_rect_check, _rect_contains, _rect_intersects),
}


class RangeAdapter:
    def __init__(self, range_class: str):
        self.range_class = range_class
        self._check, self._contains, self._intersects = _ADAPTERS[range_class]

    def check_nonempty(self, ranges) -> None:
        self._check(ranges)

    def contains(self, covered, required) -> bool:
        return self._contains(covered, required)

    def intersects(self, a, b) -> bool:
        return self._intersects(a, b)


def range_class_for(coordinate_space: str) -> str:
    if coordinate_space not in _SPACE_TO_CLASS:
        raise RangeError(f"未知の coordinate_space: {coordinate_space}")
    return _SPACE_TO_CLASS[coordinate_space]


def get_adapter(coordinate_space: str) -> RangeAdapter:
    return RangeAdapter(range_class_for(coordinate_space))
