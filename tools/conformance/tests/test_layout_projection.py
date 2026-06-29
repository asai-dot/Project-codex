"""DD-LAYOUT-001 v0.5 reading projection（型別読み + coverage 可視化）の適合性テスト。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from layout_projection import (  # noqa: E402
    PageBlock, reading_projection, reading_order_between, LayoutValidationError,
)


def _blocks():
    return [
        PageBlock("b1", "1.0", "body", "Text"),
        PageBlock("b2", "2.0", "body", "Section-header"),
        PageBlock("b3", "3.0", "footnote", "Footnote"),
        PageBlock("b4", "4.0", "body", "Table"),
        PageBlock("b5", "5.0", "body", None),          # 未型付け
        PageBlock("b6", "6.0", "footnote", "Footnote.note"),  # ALO subtype
    ]


class TestProjection(unittest.TestCase):
    def test_footnote_only(self):
        """脚注だけ読む: scope=footnote → 2件（Footnote / Footnote.note）。"""
        r = reading_projection(_blocks(), block_types={"Footnote"}, scope="footnote")
        self.assertEqual([b.block_id for b in r.items], ["b3", "b6"])

    def test_table_only(self):
        r = reading_projection(_blocks(), block_types={"Table"})
        self.assertEqual([b.block_id for b in r.items], ["b4"])

    def test_body_text_ordered(self):
        r = reading_projection(_blocks(), block_types={"Text", "Section-header", "Table"}, scope="body")
        self.assertEqual([b.block_id for b in r.items], ["b1", "b2", "b4"])  # reading_order 昇順

    def test_coverage_visible_not_absence(self):
        """G_LAYOUT_PROJECTION_COVERAGE_VISIBLE: 未型付けがあれば coverage に現れ、欠落を断定しない。"""
        r = reading_projection(_blocks(), block_types={"Table"}, scope="body")
        # body 母集団は b1,b2,b4,b5（4件）のうち b5 が未型付け
        self.assertEqual(r.coverage.blocks_total, 4)
        self.assertEqual(r.coverage.blocks_untyped, 1)
        self.assertLess(r.coverage.scope_coverage, 1.0)  # 不完全 → 「Table は1件だけ」と断定不可

    def test_full_coverage(self):
        blocks = [PageBlock("a", "1.0", "body", "Text"), PageBlock("b", "2.0", "body", "Table")]
        r = reading_projection(blocks, scope="body")
        self.assertEqual(r.coverage.scope_coverage, 1.0)


class TestReadingOrderInsertion(unittest.TestCase):
    def test_between_is_insertion_tolerant(self):
        mid = reading_order_between("1.0", "2.0")
        self.assertTrue(1.0 < float(mid) < 2.0)
        # さらにその間にも挿入できる
        mid2 = reading_order_between("1.0", mid)
        self.assertTrue(1.0 < float(mid2) < float(mid))

    def test_invalid_order_rejected(self):
        with self.assertRaises(LayoutValidationError):
            reading_order_between("2.0", "1.0")


class TestBlockTypeGuard(unittest.TestCase):
    def test_unknown_block_type_rejected(self):
        with self.assertRaises(LayoutValidationError):
            PageBlock("x", "1.0", "body", "NotALabel")


if __name__ == "__main__":
    unittest.main()
