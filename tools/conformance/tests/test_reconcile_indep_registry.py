"""RECONCILE §1 family_kind→axis 語彙写像のテスト（カウントは indep_lineage が正本）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reconcile_indep_registry import (  # noqa: E402
    axis_for_kind, FAMILY_KIND_TO_AXIS, AXIS_CONTENT, AXIS_OBSERVATION, ReconcileValidationError,
)
from xmodal_agreement import FAMILY_KINDS as XMODAL_FAMILY_KINDS  # noqa: E402


class TestAxisVocab(unittest.TestCase):
    def test_every_kind_maps_to_one_axis(self):
        for kind, axis in FAMILY_KIND_TO_AXIS.items():
            self.assertIn(axis, (AXIS_CONTENT, AXIS_OBSERVATION), kind)

    def test_xmodal_kinds_covered(self):
        for kind in XMODAL_FAMILY_KINDS:
            self.assertIn(kind, FAMILY_KIND_TO_AXIS, f"XMODAL kind {kind} 未写像")

    def test_ocr_engine_is_observation(self):
        self.assertEqual(axis_for_kind("ocr_engine"), AXIS_OBSERVATION)
        self.assertEqual(axis_for_kind("statute_text"), AXIS_CONTENT)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ReconcileValidationError):
            axis_for_kind("nonsense")


if __name__ == "__main__":
    unittest.main()
