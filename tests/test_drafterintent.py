# -*- coding: utf-8 -*-
"""Tests for scripts.drafterintent — article ref parsing (kanji+arabic),
drafter-claim cue classification, tier-2 discipline, candidate-only gates."""
import unittest

from scripts.drafterintent.patterns import kanji_to_int, ARTICLE_RE, article_path
from scripts.drafterintent.extract import extract_drafter_intent
from scripts.drafterintent.emit import run_gates


def run(text, hint=None):
    return extract_drafter_intent(text, doc_id="fixture", source_type_hint=hint)


class TestKanji(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(kanji_to_int("七百九"), "709")
        self.assertEqual(kanji_to_int("四百十五"), "415")
        self.assertEqual(kanji_to_int("三"), "3")
        self.assertEqual(kanji_to_int("二"), "2")
        self.assertEqual(kanji_to_int("709"), "709")
        self.assertEqual(kanji_to_int("４１５"), "415")
        self.assertEqual(kanji_to_int("千二百三十四"), "1234")

    def test_article_path_kanji_branch(self):
        m = ARTICLE_RE.search("改正後の民法第三条の二は")
        self.assertEqual(article_path(m), "art:3-2")

    def test_article_path_para_item(self):
        m = ARTICLE_RE.search("第415条第2項第1号により")
        self.assertEqual(article_path(m), "art:415:para:2:item:1")


class TestClaimClassification(unittest.TestCase):
    def test_no_substantive_change_confirmatory(self):
        t = ("改正後の民法第415条第1項のただし書は、従来の判例法理を確認的に規定したものであり、"
             "実質的な変更を伴うものではない。")
        ev, a = run(t, hint="逐条解説")
        # the 415 ref should yield a no_substantive_change candidate
        types = {x.change_type for x in a}
        self.assertIn("no_substantive_change", types)
        one = [x for x in a if x.change_type == "no_substantive_change"][0]
        self.assertTrue(one.confirmatory)
        self.assertEqual(one.source_tier, 2)
        self.assertEqual(one.confidence, "medium")
        self.assertEqual(one.revision_side, "after")

    def test_clarification(self):
        t = "改正後の民法第3条の2は、確立した判例・通説を明文化したものである。"
        ev, a = run(t)
        self.assertEqual(a[0].change_type, "wording_clarification")
        self.assertEqual(a[0].article_path, "art:3-2")

    def test_substantive_change_kaeru(self):
        t = ("改正後の民法第466条第2項については、規律を改め、譲渡制限の意思表示がされた場合"
             "であっても債権譲渡の効力を妨げられないこととした点で、従来の取扱いを変更するものである。")
        ev, a = run(t)
        # 「効力を…改め」or「効果を改め」 -> effect_changed expected
        self.assertIn(a[0].change_type,
                      ("effect_changed", "substantive_change_unspecified"))

    def test_constitutive_new_provision(self):
        t = "改正後の第562条は、買主の追完請求権を新たに設けた創設的な規定である。"
        ev, a = run(t)
        self.assertEqual(a[0].change_type, "substantive_change_unspecified")
        self.assertFalse(a[0].confirmatory)

    def test_scope_expansion(self):
        t = "本条の改正は、対象を拡大し、これまで含まれていなかった無償契約も対象とすることとした。"
        # no explicit article ref -> no assertion (needs an article anchor)
        ev, a = run(t)
        self.assertEqual(a, [])

    def test_scope_expansion_with_article(self):
        t = "改正後の民法第550条は、対象を拡大することとした。"
        ev, a = run(t)
        self.assertEqual(a[0].change_type, "scope_expansion")

    def test_bare_mention_no_assertion(self):
        t = "なお、本改正は条番号の整理にとどまり、第709条には触れていない。"
        ev, a = run(t)
        # 「整理」 is a clarification cue, but it must attach to the article in
        # the window; 709 sentence has no substantive claim about 709 itself.
        # Either way, no high-confidence fabricated change.
        for x in a:
            self.assertNotEqual(x.confidence, "high")


class TestSourceTypeInference(unittest.TestCase):
    def test_kokkai_record(self):
        t = "国会審議において、政府参考人は、改正後の民法第415条は実質的な変更はないと答弁した。"
        ev, a = run(t, hint="国会審議")
        self.assertEqual(a[0].asserted_by_source_type, "legislative_record")
        self.assertEqual(a[0].source_tier, 2)

    def test_ministry(self):
        t = "所管庁の通達は、第3条の2の趣旨を明確化したものと説明する。"
        ev, a = run(t, hint="通達")
        self.assertEqual(a[0].asserted_by_source_type, "ministry_commentary")


class TestGatesAndContract(unittest.TestCase):
    def _sample(self):
        import os
        p = os.path.join(os.path.dirname(__file__), "fixtures",
                         "drafter_commentary_sample.txt")
        with open(p, encoding="utf-8") as f:
            return run(f.read(), hint="逐条解説")

    def test_all_gates_pass(self):
        ev, a = self._sample()
        res = run_gates(ev, a)
        self.assertTrue(all(g["pass"] for g in res.values()))

    def test_candidates_never_claim_support(self):
        ev, a = self._sample()
        self.assertTrue(a)
        for x in a:
            self.assertEqual(x.assertion_status, "candidate")
            self.assertFalse(x.claim_support_eligible)
            self.assertEqual(x.source_tier, 2)
            self.assertNotEqual(x.confidence, "high")

    def test_every_assertion_links_real_evidence(self):
        ev, a = self._sample()
        keys = {e.evidence_key for e in ev}
        for x in a:
            self.assertIn(x.evidence_key, keys)

    def test_evidence_span_roundtrip(self):
        t = ("改正後の民法第415条第1項は、従来の判例法理を確認的に規定したものであり、"
             "実質的な変更を伴うものではない。")
        ev, a = run(t)
        e = ev[0]
        self.assertEqual(e.source_span_hash,
                         __import__("hashlib").sha1(e.quoted_text.encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()
