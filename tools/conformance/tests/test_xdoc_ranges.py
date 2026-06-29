"""DD-XDOC-001 v0.8 §9-1 range_class adapter（interval_1d / grid_2d / rect_2d）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xdoc_ranges import get_adapter, range_class_for, RangeError  # noqa: E402
from xdoc_coverage import (  # noqa: E402
    CoveragePolicy, CoverageAssessment, CoverageClaimScope, ClaimContext, CoverageStore,
)


class TestDispatch(unittest.TestCase):
    def test_space_to_class(self):
        self.assertEqual(range_class_for("char_offset"), "interval_1d")
        self.assertEqual(range_class_for("table_cell"), "grid_2d")
        self.assertEqual(range_class_for("figure_region"), "rect_2d")
        with self.assertRaises(RangeError):
            range_class_for("bogus")


class TestGrid2D(unittest.TestCase):
    def setUp(self):
        self.a = get_adapter("table_cell")

    def test_contains_cells(self):
        # covered rows0-2 cols0-2 (4 cells) contains required row0-1 col0-1 (1 cell)
        self.assertTrue(self.a.contains([(0, 2, 0, 2)], [(0, 1, 0, 1)]))
        self.assertFalse(self.a.contains([(0, 1, 0, 1)], [(0, 2, 0, 2)]))

    def test_intersects(self):
        self.assertTrue(self.a.intersects([(0, 2, 0, 2)], [(1, 3, 1, 3)]))
        self.assertFalse(self.a.intersects([(0, 1, 0, 1)], [(5, 6, 5, 6)]))

    def test_degenerate_rejected(self):
        with self.assertRaises(RangeError):
            self.a.check_nonempty([(1, 1, 0, 2)])


class TestRect2D(unittest.TestCase):
    def setUp(self):
        self.a = get_adapter("figure_region")

    def _r(self, p, x0, y0, x1, y1, cs="img"):
        return (p, x0, y0, x1, y1, cs)

    def test_contains_single(self):
        self.assertTrue(self.a.contains([self._r(1, 0, 0, 10, 10)], [self._r(1, 2, 2, 5, 5)]))
        self.assertFalse(self.a.contains([self._r(1, 0, 0, 4, 4)], [self._r(1, 2, 2, 6, 6)]))

    def test_contains_tiled(self):
        # two covered rects tile a required rect
        covered = [self._r(1, 0, 0, 5, 10), self._r(1, 5, 0, 10, 10)]
        self.assertTrue(self.a.contains(covered, [self._r(1, 1, 1, 9, 9)]))

    def test_different_page_not_contained(self):
        self.assertFalse(self.a.contains([self._r(1, 0, 0, 10, 10)], [self._r(2, 2, 2, 5, 5)]))

    def test_different_coordsys_not_contained(self):
        self.assertFalse(self.a.contains([self._r(1, 0, 0, 10, 10, "A")], [self._r(1, 2, 2, 5, 5, "B")]))

    def test_intersects(self):
        self.assertTrue(self.a.intersects([self._r(1, 0, 0, 5, 5)], [self._r(1, 4, 4, 9, 9)]))
        self.assertFalse(self.a.intersects([self._r(1, 0, 0, 2, 2)], [self._r(1, 8, 8, 9, 9)]))


class TestCoverageWithTableCell(unittest.TestCase):
    """grid_2d coverage が coverage_complete_for_use_assessment を通る（table facet 前提）。"""
    def test_table_cell_completeness(self):
        policy = CoveragePolicy("COV-T", "v1", "table", "table_cell", 0.7, 0.7)
        st = CoverageStore(policy)
        ca = CoverageAssessment(
            alignment_observation_id="obs", member_ref="m1", side="a", facet="table",
            coordinate_space="table_cell", asset_hash="h", source_text_revision_id="r1",
            selector_state="complete", covered_ranges=[(0, 5, 0, 4)], unknown_ranges=[(9, 10, 9, 10)],
            ocr_quality_score=0.9, layout_quality_score=0.9, coverage_policy_id="COV-T",
            coverage_policy_version="v1", coverage_revision_seq=1,
        )
        st.add_assessment(ca)
        st.add_scope(CoverageClaimScope("uak1", "m1", "table_cell", [(0, 2, 0, 2)], ca.assessment_id))
        ctx = ClaimContext("uak1", "difference", "a", ["m1"], "table_cell")
        self.assertTrue(st.coverage_complete_for_use_assessment(ctx))

    def test_table_cell_incomplete(self):
        policy = CoveragePolicy("COV-T", "v1", "table", "table_cell", 0.7, 0.7)
        st = CoverageStore(policy)
        ca = CoverageAssessment(
            alignment_observation_id="obs", member_ref="m1", side="a", facet="table",
            coordinate_space="table_cell", asset_hash="h", source_text_revision_id="r1",
            selector_state="complete", covered_ranges=[(0, 1, 0, 1)], unknown_ranges=[(9, 10, 9, 10)],
            ocr_quality_score=0.9, layout_quality_score=0.9, coverage_policy_id="COV-T",
            coverage_policy_version="v1", coverage_revision_seq=1,
        )
        st.add_assessment(ca)
        # required は covered より広い → contains 不成立
        st.add_scope(CoverageClaimScope("uak1", "m1", "table_cell", [(0, 3, 0, 3)], ca.assessment_id))
        ctx = ClaimContext("uak1", "difference", "a", ["m1"], "table_cell")
        self.assertFalse(st.coverage_complete_for_use_assessment(ctx))


if __name__ == "__main__":
    unittest.main()
