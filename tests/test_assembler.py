# -*- coding: utf-8 -*-
"""Tests for scripts.assembler — stance mapping, dispute formation, the
no-auto-resolution / disputed-blocks-claim invariants."""
import os
import unittest

from scripts.assembler.model import (NormAssertion, stance_of, article_root,
                                      CONTINUES, CHANGED, QUALIFIED)
from scripts.assembler.adapters import (from_drafter_rows,
                                        from_interpretation_rows,
                                        from_treatment_rows)
from scripts.assembler.assemble import assemble
from scripts.assembler.emit import run_gates

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def N(key, path, source, value, src_type, tier, conf="medium"):
    return NormAssertion(assertion_key=key, kind="x", article_path=path,
                         law_work_id=None, stance_source=source, value=value,
                         asserted_by_source_type=src_type, source_tier=tier,
                         evidence_key="ev-" + key, confidence=conf)


def go(assertions):
    return assemble(assertions, now_iso="2026-06-10T00:00:00+00:00")


class TestStance(unittest.TestCase):
    def test_change_type_stance(self):
        self.assertEqual(stance_of("change_type", "no_substantive_change"), CONTINUES)
        self.assertEqual(stance_of("change_type", "requirement_added"), CHANGED)

    def test_transition_stance(self):
        self.assertEqual(stance_of("transition_type", "interpretation_continues"), CONTINUES)
        self.assertEqual(stance_of("transition_type", "interpretation_discontinued"), CHANGED)
        self.assertEqual(stance_of("transition_type", "interpretation_modified"), QUALIFIED)

    def test_treatment_stance(self):
        self.assertEqual(stance_of("treatment_relation", "followed"), CONTINUES)
        self.assertEqual(stance_of("treatment_relation", "overruled"), CHANGED)
        self.assertEqual(stance_of("treatment_relation", "distinguished"), QUALIFIED)

    def test_article_root(self):
        self.assertEqual(article_root("art:415:para:1:item:2"), "art:415")
        self.assertEqual(article_root("art:3-2"), "art:3-2")


class TestDisputeFormation(unittest.TestCase):
    def test_drafter_vs_court_forms_dispute(self):
        a = [
            N("d1", "art:415:para:1", "change_type", "no_substantive_change",
              "legislative_drafter", 2),
            N("c1", "art:415", "transition_type", "interpretation_discontinued",
              "court", 3),
        ]
        resolved, events, disputes = go(a)
        self.assertEqual(len(disputes), 1)
        d = disputes[0]
        self.assertEqual(d.target_key, "art:415")
        self.assertIn("d1", d.continuity_side)
        self.assertIn("c1", d.change_side)
        self.assertCountEqual(d.tiers_involved, [2, 3])
        for r in resolved:
            self.assertEqual(r.current_status, "disputed")
            self.assertFalse(r.claim_support_eligible)
            self.assertIsNotNone(r.counter_assertion_id)
            self.assertNotEqual(r.counter_assertion_id, r.assertion_key)

    def test_counter_links_point_to_opposite_side(self):
        a = [
            N("d1", "art:415", "change_type", "no_substantive_change", "legislative_drafter", 2),
            N("c1", "art:415", "transition_type", "interpretation_discontinued", "court", 3),
        ]
        resolved, _, _ = go(a)
        by = {r.assertion_key: r for r in resolved}
        self.assertEqual(by["d1"].counter_assertion_id, "c1")
        self.assertEqual(by["c1"].counter_assertion_id, "d1")

    def test_agreement_no_dispute(self):
        a = [
            N("d1", "art:3-2", "change_type", "substantive_change_unspecified",
              "legislative_drafter", 2),
            N("c1", "art:3-2", "transition_type", "interpretation_discontinued",
              "court", 3),
        ]
        resolved, events, disputes = go(a)
        self.assertEqual(disputes, [])
        self.assertEqual(events, [])
        for r in resolved:
            self.assertEqual(r.current_status, "candidate")
            self.assertIsNone(r.counter_assertion_id)

    def test_neutral_does_not_create_dispute(self):
        a = [
            N("d1", "art:709", "change_type", "no_substantive_change", "legislative_drafter", 2),
            N("c1", "art:709", "treatment_relation", "cited", "court", 3),
        ]
        _, _, disputes = go(a)
        self.assertEqual(disputes, [])

    def test_self_disputed_value(self):
        a = [N("d1", "art:90", "change_type", "disputed", "scholar", 4)]
        resolved, events, disputes = go(a)
        # a lone self-disputed claim: change-side present, continuity absent ->
        # not a two-sided dispute, so no dispute row (gate keeps disputes 2-sided)
        self.assertEqual(disputes, [])

    def test_no_auto_resolution_tier_does_not_win(self):
        # even though court (tier3) and drafter (tier2) disagree, neither is
        # promoted; both stay disputed, claim_support false.
        a = [
            N("d1", "art:415", "change_type", "no_substantive_change", "legislative_drafter", 2),
            N("c1", "art:415", "transition_type", "interpretation_discontinued", "court", 3),
            N("s1", "art:415", "transition_type", "interpretation_modified", "scholar", 4),
        ]
        resolved, _, disputes = go(a)
        self.assertEqual(len(disputes), 1)
        self.assertEqual({r.current_status for r in resolved}, {"disputed"})
        self.assertTrue(all(not r.claim_support_eligible for r in resolved))


class TestAdaptersAndGates(unittest.TestCase):
    def _pipeline(self):
        drafter = from_drafter_rows([
            {"assertion_key": "d415", "article_path": "art:415:para:1",
             "law_work_id": None, "change_type": "no_substantive_change",
             "asserted_by_source_type": "legislative_drafter", "source_tier": 2,
             "evidence_key": "evd415", "confidence": "medium"},
            {"assertion_key": "d32", "article_path": "art:3-2",
             "law_work_id": None, "change_type": "substantive_change_unspecified",
             "asserted_by_source_type": "legislative_drafter", "source_tier": 2,
             "evidence_key": "evd32", "confidence": "low"},
        ])
        with open(os.path.join(FIX, "interpretation_court_scholar.jsonl"),
                  encoding="utf-8") as f:
            import json
            interp = from_interpretation_rows([json.loads(x) for x in f if x.strip()])
        return drafter + interp

    def test_pipeline_forms_415_dispute_and_gates_pass(self):
        resolved, events, disputes = go(self._pipeline())
        targets = {d.target_key for d in disputes}
        self.assertIn("art:415", targets)        # drafter no-change vs court discontinued
        self.assertIn("art:3-2", targets)        # drafter change vs scholar continues
        res = run_gates(resolved, events, disputes)
        self.assertTrue(all(g["pass"] for g in res.values()))

    def test_3_2_is_dispute_change_vs_continue(self):
        # drafter says substantive_change_unspecified (change), scholar says
        # interpretation_continues (continuity) -> dispute on art:3-2
        resolved, _, disputes = go(self._pipeline())
        d32 = [d for d in disputes if d.target_key == "art:3-2"]
        self.assertEqual(len(d32), 1)

    def test_treatment_adapter_requires_binding(self):
        rows = [{"dedup_key": "t1", "treatment_relation": "overruled",
                 "source_type": "court", "confidence": "medium"}]
        self.assertEqual(from_treatment_rows(rows, {}), [])
        bound = from_treatment_rows(rows, {"t1": {"article_path": "art:415"}})
        self.assertEqual(bound[0].article_path, "art:415")
        self.assertEqual(bound[0].source_tier, 3)
        self.assertEqual(bound[0].stance, CHANGED)

    def test_claim_support_never_granted(self):
        resolved, events, disputes = go(self._pipeline())
        self.assertEqual(sum(1 for r in resolved if r.claim_support_eligible), 0)
        self.assertEqual([e for e in events if e.new_status == "accepted"], [])


if __name__ == "__main__":
    unittest.main()
