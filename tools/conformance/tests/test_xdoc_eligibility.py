"""DD-XDOC-001 v0.7 受入試験のうち eligibility 系（2, 3, 6, 12 + invalid global）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xdoc_eligibility import (  # noqa: E402
    EligContext, IndependenceAxis, evaluate, is_positive,
    use_assessment_key_id, XdocCompatibilityError,
    ELIG_ELIGIBLE, ELIG_INELIGIBLE, ELIG_HOLD,
)

IND = IndependenceAxis  # (effective_value, effective_status)


class TestProofCorroboration(unittest.TestCase):
    def test_03_shared_origin_ineligible(self):
        """受入試験3: shared origin 2 passage を proof → CONTENT_NOT_INDEPENDENT ineligible。"""
        r = evaluate(EligContext(
            "proof_corroboration", "proof",
            content_independence=IND("shared", "current"),
            observation_independence=IND("independent", "current"),
            reviewed_relation_type="quote", review_state="reviewed",
        ))
        self.assertEqual(r.eligibility, ELIG_INELIGIBLE)
        self.assertEqual(r.reason_code, "CONTENT_NOT_INDEPENDENT")

    def test_03_unknown_origin_hold(self):
        r = evaluate(EligContext(
            "proof_corroboration", "proof",
            content_independence=IND("unknown", "current"),
            observation_independence=IND("independent", "current"),
            reviewed_relation_type="quote", review_state="reviewed",
        ))
        self.assertEqual(r.eligibility, ELIG_HOLD)
        self.assertEqual(r.reason_code, "CONTENT_INDEPENDENCE_UNKNOWN")

    def test_independent_corroboration_eligible(self):
        r = evaluate(EligContext(
            "proof_corroboration", "proof",
            content_independence=IND("independent", "current"),
            observation_independence=IND("independent", "current"),
            reviewed_relation_type="quote", review_state="reviewed",
        ))
        self.assertEqual(r.eligibility, ELIG_ELIGIBLE)
        self.assertEqual(r.reason_code, "INDEPENDENT_CORROBORATION")

    def test_invalid_axis_global_block(self):
        """受入試験3 末尾: 任意軸 invalid → priority 110 ineligible（eligible 条件を満たしても）。"""
        r = evaluate(EligContext(
            "proof_corroboration", "proof",
            content_independence=IND("independent", "current"),
            observation_independence=IND("independent", "invalid"),
            reviewed_relation_type="quote", review_state="reviewed",
        ))
        self.assertEqual(r.eligibility, ELIG_INELIGIBLE)
        self.assertEqual(r.reason_code, "INDEPENDENCE_INVALID_GLOBAL")


class TestReviewedNone(unittest.TestCase):
    def test_12_none_ineligible_on_positive_target(self):
        """受入試験12: reviewed=none + reviewed → positive target で priority 85 ineligible。"""
        r = evaluate(EligContext(
            "litlink_candidate", "litlink",
            reviewed_relation_type="none", review_state="reviewed",
        ))
        self.assertEqual(r.eligibility, ELIG_INELIGIBLE)
        self.assertEqual(r.reason_code, "REVIEWED_RELATION_NONE")

    def test_none_not_positive(self):
        self.assertFalse(is_positive("litlink_candidate", "none"))
        self.assertFalse(is_positive("proof_corroboration", None))
        self.assertTrue(is_positive("litlink_candidate", "quote"))

    def test_null_reviewed_required_target(self):
        r = evaluate(EligContext("litlink_candidate", "litlink",
                                 reviewed_relation_type=None, review_state="reviewed"))
        self.assertEqual(r.eligibility, ELIG_INELIGIBLE)
        self.assertEqual(r.reason_code, "REVIEWED_RELATION_REQUIRED")


class TestCoverageAndKeys(unittest.TestCase):
    def test_06_absence_with_incomplete_coverage_ineligible(self):
        """受入試験6: absence/difference 主張 + coverage 不完全 → priority 90 ineligible。"""
        r = evaluate(EligContext(
            "litlink_candidate", "litlink",
            reviewed_relation_type="quote", review_state="reviewed",
            claim_is_absence_or_difference=True,
            coverage_complete_for_use_assessment=False,
        ))
        self.assertEqual(r.eligibility, ELIG_INELIGIBLE)
        self.assertEqual(r.reason_code, "COVERAGE_INCOMPLETE")

    def test_02_distinct_keys_per_purpose_target(self):
        """受入試験2: 同一 alignment を別 purpose×target で別 key。"""
        obs = "deadbeef"
        k1 = use_assessment_key_id(obs, "litlink_candidate", "litlink", "XDOC-ELIG-001", "v1")
        k2 = use_assessment_key_id(obs, "proof_corroboration", "proof", "XDOC-ELIG-001", "v1")
        self.assertNotEqual(k1, k2)

    def test_compatibility_false_rejected(self):
        with self.assertRaises(XdocCompatibilityError):
            evaluate(EligContext("proof_corroboration", "litlink"))  # 非互換組合せ


if __name__ == "__main__":
    unittest.main()
