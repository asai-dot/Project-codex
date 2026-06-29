"""DD-XMODAL-001 v0.4 confirmed/possible 判定の適合性テスト（反こたつ記事の核）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xmodal_agreement import (  # noqa: E402
    ExternalSourceFamilyRegistry, D2Evidence, AgreementInput, decide,
    DEC_CONFIRMED, DEC_POSSIBLE, DEC_ABSTAIN,
    PR_NO_D2, PR_SINGLE_FAMILY, PR_LOW_PROB, PR_ABSTAIN_MAJORITY,
    PR_GRANULARITY, PR_TAXONOMY_CONFLICT, XmodalValidationError,
)


def _reg(*pairs):
    r = ExternalSourceFamilyRegistry()
    for fid, kind in pairs:
        r.register(fid, kind)
    return r


def _d2(eid, fam):
    return D2Evidence(eid, fam, law_snapshot="2026-04-01", source_version="v1", valid_at="2026-04-01")


class TestConfirmed(unittest.TestCase):
    def test_confirmed_requires_two_distinct_families(self):
        """confirmed = V/T 一致 + D2 で DISTINCT registered family ≥ 2。"""
        reg = _reg(("statute_db", "statute_text"), ("commentary_x", "commentary_publisher"))
        r = decide(AgreementInput(
            v_agrees=True, t_agrees=True,
            d2_evidences=[_d2("e1", "statute_db"), _d2("e2", "commentary_x")],
            label_model_prob=0.95,
        ), reg)
        self.assertEqual(r.decision, DEC_CONFIRMED)
        self.assertEqual(r.distinct_registered_families, 2)

    def test_single_family_not_confirmed(self):
        """同一 family の複数源は1票（独立2源でない）→ possible/single_external_family。"""
        reg = _reg(("statute_db", "statute_text"))
        r = decide(AgreementInput(
            v_agrees=True, t_agrees=True,
            d2_evidences=[_d2("e1", "statute_db"), _d2("e2", "statute_db")],
            label_model_prob=0.95,
        ), reg)
        self.assertEqual(r.decision, DEC_POSSIBLE)
        self.assertEqual(r.possible_reason, PR_SINGLE_FAMILY)
        self.assertEqual(r.distinct_registered_families, 1)

    def test_unregistered_family_not_counted(self):
        """未登録 family は independent と見なさない（registry gate）。"""
        reg = _reg(("statute_db", "statute_text"))  # commentary_x 未登録
        r = decide(AgreementInput(
            v_agrees=True, t_agrees=True,
            d2_evidences=[_d2("e1", "statute_db"), _d2("e2", "commentary_x")],
            label_model_prob=0.95,
        ), reg)
        self.assertEqual(r.decision, DEC_POSSIBLE)
        self.assertEqual(r.distinct_registered_families, 1)  # 登録済みは1のみ
        self.assertEqual(r.possible_reason, PR_SINGLE_FAMILY)


class TestNoVTConfirmation(unittest.TestCase):
    def test_vt_alone_not_confirmed(self):
        """G_XMODAL_NO_VT_CONFIRMATION: V+T 一致だけでは confirmed にしない。"""
        reg = _reg()
        r = decide(AgreementInput(v_agrees=True, t_agrees=True, d2_evidences=[]), reg)
        self.assertEqual(r.decision, DEC_POSSIBLE)
        self.assertEqual(r.possible_reason, PR_NO_D2)
        self.assertEqual(r.distinct_registered_families, 0)


class TestPossibleReasons(unittest.TestCase):
    def _two_fam(self):
        return _reg(("a", "statute_text"), ("b", "commentary_publisher"))

    def test_taxonomy_conflict_priority(self):
        r = decide(AgreementInput(True, True, [_d2("e1", "a"), _d2("e2", "b")],
                                  label_model_prob=0.95, taxonomy_conflict=True), self._two_fam())
        self.assertEqual(r.decision, DEC_POSSIBLE)
        self.assertEqual(r.possible_reason, PR_TAXONOMY_CONFLICT)

    def test_granularity_mismatch(self):
        r = decide(AgreementInput(True, True, [_d2("e1", "a"), _d2("e2", "b")],
                                  label_model_prob=0.95, granularity_match=False), self._two_fam())
        self.assertEqual(r.possible_reason, PR_GRANULARITY)

    def test_low_prob_midband(self):
        r = decide(AgreementInput(True, True, [_d2("e1", "a"), _d2("e2", "b")],
                                  label_model_prob=0.55), self._two_fam())
        self.assertEqual(r.decision, DEC_POSSIBLE)
        self.assertEqual(r.possible_reason, PR_LOW_PROB)

    def test_abstain_majority_decision(self):
        reg = _reg()
        r = decide(AgreementInput(v_agrees=False, t_agrees=False, d2_evidences=[],
                                  abstain_majority=True), reg)
        self.assertEqual(r.decision, DEC_ABSTAIN)
        self.assertEqual(r.possible_reason, PR_ABSTAIN_MAJORITY)


class TestRegistry(unittest.TestCase):
    def test_unknown_family_kind_rejected(self):
        reg = ExternalSourceFamilyRegistry()
        with self.assertRaises(XmodalValidationError):
            reg.register("x", "not_a_kind")


if __name__ == "__main__":
    unittest.main()
