# -*- coding: utf-8 -*-
"""Tests for scripts.articlepath — canonicalization across the 3 input forms,
numeric sort key, 条 root, and crosswalk from lawdelta rows.
"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from scripts.articlepath import parse, ParseError, ArticlePath  # noqa: E402
from scripts.articlepath.crosswalk import build_crosswalk, old_to_new_index  # noqa: E402


class TestParseForms(unittest.TestCase):
    def test_egov_num(self):
        self.assertEqual(parse("398_22").canonical(), "art:398-22")
        self.assertEqual(parse("709").canonical(), "art:709")

    def test_house_path(self):
        self.assertEqual(parse("art:415:para:1:item:2").canonical(), "art:415:para:1:item:2")
        self.assertEqual(parse("art:3-2").canonical(), "art:3-2")

    def test_bare_tail(self):
        self.assertEqual(parse("3-2").canonical(), "art:3-2")

    def test_kanji_text_ref(self):
        self.assertEqual(parse("第三百九十八条の二十二").canonical(), "art:398-22")
        self.assertEqual(parse("民法第七百九条").canonical(), "art:709")
        self.assertEqual(parse("第五条第二項第一号").canonical(), "art:5:para:2:item:1")

    def test_all_three_forms_agree(self):
        a, b, c = parse("398_22"), parse("art:398-22"), parse("第三百九十八条の二十二")
        self.assertEqual(a, b)
        self.assertEqual(b, c)

    def test_deep_branch_raises(self):
        with self.assertRaises(ParseError):
            parse("398_22_2")  # の M の K not yet modelled -> flagged, not silent

    def test_garbage_raises(self):
        with self.assertRaises(ParseError):
            parse("not an article")


class TestSortAndRoot(unittest.TestCase):
    def test_numeric_sort_beats_string_sort(self):
        paths = ["art:10", "art:2", "art:100", "art:3-2", "art:3"]
        num = sorted(paths, key=lambda p: parse(p).sort_key())
        self.assertEqual(num, ["art:2", "art:3", "art:3-2", "art:10", "art:100"])
        # string sort would (wrongly) put art:10/art:100 before art:2
        self.assertNotEqual(sorted(paths), num)

    def test_branch_orders_numerically(self):
        paths = ["art:398-2", "art:398-22", "art:398-3"]
        self.assertEqual(sorted(paths, key=lambda p: parse(p).sort_key()),
                         ["art:398-2", "art:398-3", "art:398-22"])

    def test_bare_article_precedes_its_paragraphs(self):
        paths = ["art:5:para:1", "art:5"]
        self.assertEqual(sorted(paths, key=lambda p: parse(p).sort_key()),
                         ["art:5", "art:5:para:1"])

    def test_root_drops_para_item_keeps_branch(self):
        self.assertEqual(parse("art:415:para:1:item:2").root().canonical(), "art:415")
        self.assertEqual(parse("art:3-2:para:1").root().canonical(), "art:3-2")


class TestCrosswalk(unittest.TestCase):
    def test_build_from_delta_kinds(self):
        rows = [
            {"article_path": "art:5", "delta_kind": "no_change", "text_changed": False},
            {"article_path": "art:733", "delta_kind": "repeal", "text_changed": True,
             "counterpart_paths": []},
            {"article_path": "art:3-2", "delta_kind": "insertion", "text_changed": True,
             "counterpart_paths": []},
            {"article_path": "art:415", "delta_kind": "substitution", "text_changed": True,
             "counterpart_paths": []},
            {"article_path": "art:570", "delta_kind": "split", "text_changed": True,
             "counterpart_paths": ["art:570", "art:570-2"]},
        ]
        entries = build_crosswalk(rows)
        rels = {e.relation: e for e in entries}
        self.assertNotIn("no_change", rels)  # unchanged not in crosswalk
        self.assertEqual(rels["repeal"].new_paths, [])
        self.assertIsNone(rels["insertion"].old_path)
        self.assertEqual(rels["split"].new_paths, ["art:570", "art:570-2"])
        idx = old_to_new_index(entries)
        self.assertEqual(idx["art:570"], ["art:570", "art:570-2"])
        self.assertNotIn(None, idx)  # insertion has no old key


if __name__ == "__main__":
    unittest.main()
