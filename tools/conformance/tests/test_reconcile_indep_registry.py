"""DD-TRILOGY-RECONCILE-001 v0.1 §1 受入試験（独立性 共有 registry・2軸 consumer 規約）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reconcile_indep_registry import (  # noqa: E402
    SharedExternalSourceFamilyRegistry, FAMILY_KIND_TO_AXIS, axis_for_kind,
    AXIS_CONTENT, AXIS_OBSERVATION, ReconcileValidationError,
)
# XMODAL 既存の family_kind が全て写像対象に含まれるか（横断整合）
from xmodal_agreement import FAMILY_KINDS as XMODAL_FAMILY_KINDS  # noqa: E402


class TestAxisMapping(unittest.TestCase):
    def test_1_every_kind_maps_to_one_axis(self):
        """受入試験1: 全 family_kind が content_origin / observation_pipeline に一意写像。"""
        for kind, axis in FAMILY_KIND_TO_AXIS.items():
            self.assertIn(axis, (AXIS_CONTENT, AXIS_OBSERVATION), kind)

    def test_xmodal_kinds_covered(self):
        """XMODAL v0.4 の family_kind が全て共有 registry に写像される（取りこぼしなし）。"""
        for kind in XMODAL_FAMILY_KINDS:
            self.assertIn(kind, FAMILY_KIND_TO_AXIS, f"XMODAL kind {kind} が未写像")

    def test_ocr_engine_is_observation(self):
        self.assertEqual(axis_for_kind("ocr_engine"), AXIS_OBSERVATION)
        self.assertEqual(axis_for_kind("statute_text"), AXIS_CONTENT)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ReconcileValidationError):
            axis_for_kind("nonsense")


class TestConsumerRules(unittest.TestCase):
    def _reg(self):
        r = SharedExternalSourceFamilyRegistry()
        r.register("statute_db", "statute_text")        # content
        r.register("commentary_x", "commentary_publisher")  # content
        r.register("tesseract", "ocr_engine")           # observation
        r.register("abbyy", "ocr_engine")               # observation
        return r

    def test_2_confirmed_counts_content_only(self):
        """受入試験2: confirmed は content_origin DISTINCT のみ・observation は数えない。"""
        r = self._reg()
        # content 2源 + observation 2源 → content distinct=2 → confirmed-independent
        self.assertTrue(r.xmodal_confirmed_independent(
            ["statute_db", "commentary_x", "tesseract", "abbyy"]))
        # content 1源 + observation 2源 → content distinct=1 → NOT confirmed（observation は数えない）
        self.assertFalse(r.xmodal_confirmed_independent(
            ["statute_db", "tesseract", "abbyy"]))

    def test_distinct_on_axis(self):
        r = self._reg()
        self.assertEqual(r.distinct_on_axis(["statute_db", "commentary_x"], AXIS_CONTENT), 2)
        self.assertEqual(r.distinct_on_axis(["tesseract", "abbyy"], AXIS_OBSERVATION), 2)
        # 別 axis は混在カウントしない
        self.assertEqual(r.distinct_on_axis(["statute_db", "tesseract"], AXIS_CONTENT), 1)

    def test_xdoc_two_axes_separate(self):
        r = self._reg()
        self.assertTrue(r.xdoc_content_independent(["statute_db", "commentary_x"]))
        self.assertTrue(r.xdoc_observation_independent(["tesseract", "abbyy"]))
        # content 独立だが observation は1源 → observation は非独立
        self.assertFalse(r.xdoc_observation_independent(["tesseract"]))

    def test_unregistered_not_counted(self):
        r = self._reg()
        self.assertEqual(r.distinct_on_axis(["unknown_fam", "statute_db"], AXIS_CONTENT), 1)

    def test_unknown_family_kind_rejected(self):
        r = SharedExternalSourceFamilyRegistry()
        with self.assertRaises(ReconcileValidationError):
            r.register("x", "not_a_kind")


if __name__ == "__main__":
    unittest.main()
