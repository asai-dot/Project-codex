"""DD-TRILOGY-RECONCILE-001 §1（lineage 正本・R1 監査反映）の適合性テスト。

監査 RESULT（Box 2306465882050）必須 fixture:
 1. 同一 publisher 由来の provider 転載と self OCR を二票に数えない。
 2. 同一 raw scan の OCR/parser 違いを独立観測に数えない。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reconcile_indep_registry import (  # noqa: E402
    ContentOrigin, ObservationRun, content_independent, observation_independent,
    xmodal_confirmed_independent, axis_for_kind, FAMILY_KIND_TO_AXIS,
    AXIS_CONTENT, AXIS_OBSERVATION, ReconcileValidationError,
)
from xmodal_agreement import FAMILY_KINDS as XMODAL_FAMILY_KINDS  # noqa: E402


class TestContentSameOriginCollapse(unittest.TestCase):
    def test_fixture1_same_statute_two_books_is_one_source(self):
        """2冊が同一条文を引く → 同一 origin_root → 1源（独立でない）。"""
        a = ContentOrigin("statute:民法541", "publisherA")
        b = ContentOrigin("statute:民法541", "publisherB")  # 別版元だが同一条文
        self.assertFalse(content_independent([a, b]))

    def test_fixture1_provider_reprint_one_vote(self):
        """同一 origin の版元転載は1票（同一条文の転載を二票に数えない）。"""
        orig = ContentOrigin("edition:X", "publisherA")
        reprint = ContentOrigin("edition:X", "publisherA")  # 転載
        self.assertFalse(content_independent([orig, reprint]))

    def test_distinct_origins_independent(self):
        a = ContentOrigin("statute:民法541", "pa")
        b = ContentOrigin("case:最判平X", "pb")
        self.assertTrue(content_independent([a, b]))


class TestObservationLineage(unittest.TestCase):
    def test_fixture2_same_scan_two_engines_not_independent(self):
        """同一 raw scan に tesseract / abbyy → lineage 根が同一 → 独立でない。"""
        r1 = ObservationRun("scan#1", "tesseract", "parserA", "normA")
        r2 = ObservationRun("scan#1", "abbyy", "parserB", "normB")  # 部品違い・同一 scan
        self.assertFalse(observation_independent([r1, r2]))

    def test_distinct_scans_independent(self):
        r1 = ObservationRun("scan#1", "tesseract", "p", "n")
        r2 = ObservationRun("scan#2", "tesseract", "p", "n")  # 別 scan（別冊/別取り込み）
        self.assertTrue(observation_independent([r1, r2]))


class TestXmodalConfirmed(unittest.TestCase):
    def test_confirmed_uses_content_not_observation(self):
        """confirmed は content 起源の独立（observation pipeline は数えない）。"""
        # content 1源（同一条文）＋ observation 2 scan でも confirmed-independent でない
        same_statute = [ContentOrigin("statute:民法541", "pa"),
                        ContentOrigin("statute:民法541", "pb")]
        self.assertFalse(xmodal_confirmed_independent(same_statute))
        # content 2源 → confirmed-independent
        two = [ContentOrigin("statute:民法541", "pa"), ContentOrigin("case:最判", "pb")]
        self.assertTrue(xmodal_confirmed_independent(two))


class TestAxisVocab(unittest.TestCase):
    def test_axis_mapping_complete(self):
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
