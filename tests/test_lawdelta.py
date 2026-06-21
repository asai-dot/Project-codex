# -*- coding: utf-8 -*-
"""Tests for scripts.lawdelta — every delta_kind plus gates.

Fixtures emulate realistic Japanese amendment shapes (2017 債権法改正型:
in-place rewrite, insertion of 枝番条文, 「削除」shells, 繰下げ block shift,
split of one article into two).
"""
import unittest

from scripts.lawdelta.model import ArticleUnit
from scripts.lawdelta.align import compute_deltas
from scripts.lawdelta.emit import run_gates, FORBIDDEN_SUBSTANTIVE_FIELDS


def A(num, text, caption="", deleted=False, idx=0):
    return ArticleUnit(article_path=f"art:{num}", article_number=str(num),
                       caption=caption, text=text, deleted=deleted,
                       order_index=idx)


def kinds(records):
    return {r.article_path: r.delta_kind for r in records}


def run(old, new):
    return compute_deltas(old, new, law_id="129AC0000000089",
                          from_rev="129AC0000000089_20170602_000000000000000",
                          to_rev="129AC0000000089_20200401_429AC0000000044",
                          snapshot_id="egov_fixture_20260608")


OLD_415 = ("債務者がその債務の本旨に従った履行をしないときは、債権者は、"
           "これによって生じた損害の賠償を請求することができる。"
           "債務者の責めに帰すべき事由によって履行をすることができなくなったときも、同様とする。")
NEW_415 = ("債務者がその債務の本旨に従った履行をしないとき又は債務の履行が不能であるときは、"
           "債権者は、これによって生じた損害の賠償を請求することができる。"
           "ただし、その債務の不履行が契約その他の債務の発生原因及び取引上の社会通念に照らして"
           "債務者の責めに帰することができない事由によるものであるときは、この限りでない。")
TEXT_709 = ("故意又は過失によって他人の権利又は法律上保護される利益を侵害した者は、"
            "これによって生じた損害を賠償する責任を負う。")
NEW_3_2 = ("法律行為の当事者が意思表示をした時に意思能力を有しなかったときは、"
           "その法律行為は、無効とする。")


class TestPhaseA(unittest.TestCase):
    def test_no_change_and_substitution(self):
        old = [A(709, TEXT_709), A(415, OLD_415)]
        new = [A(709, TEXT_709), A(415, NEW_415)]
        k = kinds(run(old, new))
        self.assertEqual(k["art:709"], "no_change")
        self.assertEqual(k["art:415"], "substitution")

    def test_whitespace_only_is_no_change(self):
        old = [A(709, TEXT_709)]
        new = [A(709, TEXT_709[:10] + "\n　" + TEXT_709[10:])]
        self.assertEqual(kinds(run(old, new))["art:709"], "no_change")

    def test_repeal_shell(self):
        # 「第170条 削除」型: number persists, body becomes 削除
        old = [A(170, "次に掲げる債権は、三年間行使しないときは、消滅する。…")]
        new = [A(170, "削除", deleted=True)]
        self.assertEqual(kinds(run(old, new))["art:170"], "repeal")

    def test_reuse_of_deleted_number_is_insertion(self):
        old = [A(38, "削除", deleted=True)]
        new = [A(38, "新しい規定の本文がここに置かれる。")]
        self.assertEqual(kinds(run(old, new))["art:38"], "insertion")


class TestPhaseB(unittest.TestCase):
    def test_pure_insertion_and_repeal(self):
        old = [A(3, "私権の享有は、出生に始まる。"), A(900, "相続分は…")]
        new = [A(3, "私権の享有は、出生に始まる。"),
               A("3-2", NEW_3_2), A(900, "相続分は…")]
        k = kinds(run(old, new))
        self.assertEqual(k["art:3-2"], "insertion")

        k2 = kinds(run(new, old))
        self.assertEqual(k2["art:3-2"], "repeal")

    def test_renumber_identical_text(self):
        old = [A(10, TEXT_709)]
        new = [A(11, TEXT_709)]
        recs = run(old, new)
        self.assertEqual(kinds(recs)["art:10"], "renumber")
        self.assertEqual(recs[0].counterpart_paths, ["art:11"])
        self.assertFalse(recs[0].text_changed)

    def test_block_shift_kurisage(self):
        # 繰下げ: arts 20,21 shift to 21,22 (same +1 offset) with small edits;
        # a new art 20 is inserted.
        t20 = "保佐人の同意を要する行為について、その同意を得なければならない。"
        t21 = "被保佐人が前条の規定に違反してした行為は、取り消すことができる。"
        old = [A(20, t20), A(21, t21)]
        new = [A(20, NEW_3_2),
               A(21, t20 + "ただし、日用品の購入については、この限りでない。"),
               A(22, t21)]
        k = kinds(run(old, new))
        # old 20/21 should map forward as a coherent +1 block shift
        self.assertEqual(k["art:21"], "renumber")          # 21->22 identical
        self.assertIn(k["art:20"], ("renumber",))          # edited but in block
        # art:20(new content) consumed neither -> handled via phase A? no:
        # old art:20 was matched to new art:21 in phase B, so new art:20 is insertion
        ins = [r for r in run(old, new) if r.delta_kind == "insertion"]
        self.assertEqual([r.article_path for r in ins], ["art:20"])

    def test_relocate_moved_and_edited(self):
        base = ("当事者の一方がその解除権を行使したときは、各当事者は、"
                "その相手方を原状に復させる義務を負う。")
        old = [A(100, base), A(200, "別の規定")]
        new = [A(150, base[:30] + "この場合において、金銭を返還するときは利息を付さなければならない。"),
               A(200, "別の規定")]
        k = kinds(run(old, new))
        self.assertIn(k["art:100"], ("relocate", "renumber"))


class TestPhaseC(unittest.TestCase):
    def test_split_one_to_two(self):
        part1 = ("売買の目的物が種類、品質又は数量に関して契約の内容に適合しないものであるときは、"
                 "買主は、売主に対し、目的物の修補、代替物の引渡し又は不足分の引渡しによる"
                 "履行の追完を請求することができる。")
        part2 = ("前条本文に規定する場合において、買主が相当の期間を定めて履行の追完の催告をし、"
                 "その期間内に履行の追完がないときは、買主は、その不適合の程度に応じて"
                 "代金の減額を請求することができる。")
        old = [A(570, part1 + part2)]
        new = [A(562, part1), A(563, part2)]
        recs = run(old, new)
        k = kinds(recs)
        self.assertEqual(k["art:570"], "split")
        split = [r for r in recs if r.delta_kind == "split"][0]
        self.assertEqual(split.counterpart_paths, ["art:562", "art:563"])

    def test_join_two_to_one(self):
        p1 = "債権者代位権の行使の要件について定める長めの規定文がここに続くものとする。"
        p2 = "債権者代位権の行使の範囲について定める別の長めの規定文がここに続くものとする。"
        old = [A(423, p1), A(424, p2)]
        new = [A(423, p1 + p2)]
        recs = run(old, new)
        joins = [r for r in recs if r.delta_kind == "join"]
        self.assertEqual(len(joins), 1)
        self.assertEqual(joins[0].article_path, "art:423")
        self.assertEqual(joins[0].counterpart_paths, ["art:423", "art:424"])


class TestGates(unittest.TestCase):
    def test_gates_pass_on_mixed_run(self):
        old = [A(709, TEXT_709), A(415, OLD_415), A(170, "三年間…時効…")]
        new = [A(709, TEXT_709), A(415, NEW_415), A(170, "削除", deleted=True),
               A("3-2", NEW_3_2)]
        results = run_gates(run(old, new))
        self.assertTrue(all(g["pass"] for g in results.values()))

    def test_no_substantive_fields_in_output(self):
        old = [A(415, OLD_415)]
        new = [A(415, NEW_415)]
        row = run(old, new)[0].to_dict()
        leaked = set(row) & FORBIDDEN_SUBSTANTIVE_FIELDS
        self.assertEqual(leaked, set())
        # and the textual layer never opines on substance:
        self.assertNotIn("substantive", " ".join(row.keys()))


if __name__ == "__main__":
    unittest.main()
