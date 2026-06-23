# -*- coding: utf-8 -*-
"""Tests for scripts.amendparse — 改め文 → (article_path, delta_kind).

Fixtures are synthetic but follow real 改め文 grammar (削る / 次のように改める /
中「」を「」に改める / の次に…加える / 第Y条とする 等). They are NOT quotations
of any specific act; real gold comes from official 改め文 (e-Gov v2).
"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from scripts.amendparse import parse_amendments  # noqa: E402


def kinds(text):
    return [(a.article_path, a.delta_kind) for a in parse_amendments(text)]


class TestOperations(unittest.TestCase):
    def test_repeal(self):
        self.assertEqual(kinds("第七百三十三条を削る。"), [("art:733", "repeal")])

    def test_repeal_multiple(self):
        self.assertEqual(
            kinds("第七百四十四条及び第七百四十六条を削る。"),
            [("art:744", "repeal"), ("art:746", "repeal")],
        )

    def test_substitution_full(self):
        self.assertEqual(kinds("第七百七十二条を次のように改める。"),
                         [("art:772", "substitution")])

    def test_substitution_partial(self):
        self.assertEqual(
            kinds("第七百四十三条中「取り消す」を「取り消すことができる」に改める。"),
            [("art:743", "substitution")],
        )

    def test_substitution_caption(self):
        self.assertEqual(kinds("第七百七十四条の見出しを「（嫡出の否認）」に改める。"),
                         [("art:774", "substitution")])

    def test_add_paragraph_is_substitution(self):
        self.assertEqual(kinds("第七百七十二条に次の一項を加える。"),
                         [("art:772", "substitution")])

    def test_insertion_added_article(self):
        # 第778条の次に「第778条の2」を加える → insertion keyed on the added article
        out = kinds("第七百七十八条の次に次の一条を加える。第七百七十八条の二　…")
        self.assertEqual(out[0], ("art:778-2", "insertion"))

    def test_renumber(self):
        self.assertEqual(kinds("第七百八十四条を第七百八十五条とする。"),
                         [("art:784", "renumber")])
        a = parse_amendments("第七百八十四条を第七百八十五条とする。")[0]
        self.assertEqual(a.new_path, "art:785")

    def test_branch_article_repeal(self):
        self.assertEqual(kinds("第三百九十八条の二十二を削る。"),
                         [("art:398-22", "repeal")])

    def test_unknown_when_unrecognized_operation(self):
        out = parse_amendments("第九百条の規定の適用については、なお従前の例による。")
        self.assertEqual(out[0].delta_kind, "unknown")

    def test_non_operation_sentence_skipped(self):
        self.assertEqual(parse_amendments("この法律は、公布の日から施行する。"), [])

    def test_phrase_deletion_is_substitution_not_repeal(self):
        # 中「X」を削る は語句削除 = substitution。条そのものの削除と区別する。
        out = parse_amendments("第七百四十条中「届け出なければならない」を削る。")
        self.assertEqual([(a.article_path, a.delta_kind) for a in out],
                         [("art:740", "substitution")])

    def test_range_substitution(self):
        out = parse_amendments("第七百七十二条から第七百七十四条までを次のように改める。")
        self.assertEqual([(a.article_path, a.delta_kind) for a in out],
                         [("art:772", "substitution"), ("art:773", "substitution"),
                          ("art:774", "substitution")])


class TestGoldShape(unittest.TestCase):
    def test_delta_kind_in_lawdelta_domain(self):
        from scripts.lawdelta.model import DeltaRecord
        text = ("第七百三十三条を削る。第七百七十二条を次のように改める。"
                "第七百八十四条を第七百八十五条とする。")
        for a in parse_amendments(text):
            self.assertIn(a.delta_kind, DeltaRecord.DELTA_KIND_DOMAIN)


if __name__ == "__main__":
    unittest.main()
