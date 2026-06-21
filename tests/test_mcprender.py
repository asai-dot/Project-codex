# -*- coding: utf-8 -*-
"""Tests for scripts.mcprender — safe both-sides rendering and no-assertion gates."""
import unittest

from scripts.mcprender.render import render_all, render_provision, render_markdown
from scripts.mcprender.emit import run_gates


def R(key, target, src, tier, value, stance, status, claim=False, conf="medium"):
    return {"assertion_key": key, "target_key": target, "article_path": target,
            "asserted_by_source_type": src, "source_tier": tier, "value": value,
            "stance": stance, "current_status": status, "confidence": conf,
            "evidence_key": "ev-" + key, "claim_support_eligible": claim}


DISPUTED = [
    R("d1", "art:415", "legislative_drafter", 2, "no_substantive_change", "continues", "disputed"),
    R("c1", "art:415", "court", 3, "interpretation_discontinued", "changed", "disputed"),
    R("s1", "art:415", "scholar", 4, "interpretation_modified", "qualified", "disputed"),
]
AGREED = [
    R("a1", "art:3-2", "legislative_drafter", 2, "substantive_change_unspecified", "changed", "candidate"),
]


class TestRender(unittest.TestCase):
    def test_disputed_renders_both_sides(self):
        dispute = {"target_key": "art:415", "basis": "continuity[...] vs change[...]"}
        v = render_provision("art:415", DISPUTED, dispute,
                             formal_note="2020-04-01 改正で条文変更（lawtime: superseded）")
        self.assertTrue(v["both_sides_required"])
        self.assertEqual(v["disposition"], "disputed")
        self.assertEqual(len(v["claims"]), 3)
        self.assertFalse(v["assertive_output_allowed"])
        # formal fact stated; substantive summary hedged
        self.assertIn("分かれています", v["safe_summary"])
        self.assertIn("断定はできません", v["safe_summary"])

    def test_markdown_contains_sources_and_no_verdict(self):
        dispute = {"target_key": "art:415", "basis": "x"}
        v = render_provision("art:415", DISPUTED, dispute)
        v["markdown"] = render_markdown(v)
        md = v["markdown"]
        self.assertIn("立案担当者解説(T2)", md)
        self.assertIn("裁判例(T3)", md)
        self.assertIn("両論併記", md)
        self.assertNotIn("旧法理は現在も有効です", md)

    def test_non_disputed_is_candidate_not_verdict(self):
        v = render_provision("art:3-2", AGREED, None)
        self.assertEqual(v["disposition"], "candidate")
        self.assertFalse(v["both_sides_required"])
        self.assertIn("確定見解ではありません", v["safe_summary"])

    def test_usage_label_cautious_when_no_claim_support(self):
        v = render_provision("art:415", DISPUTED, {"target_key": "art:415", "basis": "x"})
        for c in v["claims"]:
            self.assertEqual(c["usage"], "参考（要確認・断定不可）")


class TestGates(unittest.TestCase):
    def _views(self):
        disputes = [{"target_key": "art:415", "basis": "continuity vs change"}]
        return render_all(DISPUTED + AGREED, disputes,
                          {"art:415": "2020-04-01 改正（lawtime: superseded）"})

    def test_all_gates_pass(self):
        res = run_gates(self._views())
        self.assertTrue(all(g["pass"] for g in res.values()))

    def test_gate_catches_relied_upon_leak(self):
        leaked = [R("x", "art:9", "court", 3, "overruled", "changed", "accepted", claim=True)]
        views = render_all(leaked, [])
        with self.assertRaises(Exception):
            run_gates(views)

    def test_gate_catches_one_sided_dispute(self):
        # a target marked disputed but with only one stance present
        one = [R("x", "art:9", "court", 3, "overruled", "changed", "disputed")]
        views = render_all(one, [{"target_key": "art:9", "basis": "x"}])
        with self.assertRaises(Exception):
            run_gates(views)

    def test_disputed_summary_never_asserts(self):
        for v in self._views():
            if v["disposition"] == "disputed":
                self.assertNotIn("有効です", v["safe_summary"])


if __name__ == "__main__":
    unittest.main()
