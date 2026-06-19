"""silver_stage_write (P1) ユニットテスト.

実行: python3 -m unittest discover -s tools/silver_resolve/tests -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import silver_stage_write as sw  # noqa: E402

POLICY = {"accept_status": ["strong"], "min_confidence": 0.90,
          "source_scheme_version": "test", "reviewed_by": "owner"}


class TestRouting(unittest.TestCase):
    def test_cite_strong_single_accepted(self):
        c = {"lic_edge_id": "1", "resolved_hanrei_id": ["A"], "decision_status": "strong",
             "confidence": 0.95, "match_method": "issue_page_exact"}
        lane, sid, _ = sw._route_cite(c, POLICY)
        self.assertEqual(lane, "accepted")
        self.assertEqual(sid, "cite:1|A")

    def test_cite_review_goes_review(self):
        c = {"lic_edge_id": "2", "resolved_hanrei_id": ["X", "Y"], "decision_status": "review",
             "confidence": 0.6}
        lane, _, _ = sw._route_cite(c, POLICY)
        self.assertEqual(lane, "review")  # 多候補は accepted に入れない

    def test_cite_strong_but_multi_target_not_accepted(self):
        c = {"lic_edge_id": "3", "resolved_hanrei_id": ["X", "Y"], "decision_status": "strong",
             "confidence": 0.95}
        lane, _, _ = sw._route_cite(c, POLICY)
        self.assertEqual(lane, "review")  # 単一でなければ accepted 不可

    def test_cite_honest_empty_excluded(self):
        c = {"lic_edge_id": "4", "resolved_hanrei_id": [], "honest_empty": "db_unbuilt"}
        lane, _, _ = sw._route_cite(c, POLICY)
        self.assertEqual(lane, "exclude")

    def test_section_review_when_no_hyoshaku(self):
        c = {"issue_section_id": "s1", "member_hanrei_ids": ["A", "B"], "decision_status": "review"}
        lane, sid, _ = sw._route_section(c, POLICY)
        self.assertEqual(lane, "review")
        self.assertEqual(sid, "section:s1")

    def test_cooc_weightless_excluded(self):
        c = {"hanrei_a": "A", "hanrei_b": "B", "pair_weight": 0}
        lane, _, _ = sw._route_cooc(c, POLICY)
        self.assertEqual(lane, "exclude")


class TestApplyAndIdempotency(unittest.TestCase):
    def setUp(self):
        self.cite = [
            {"lic_edge_id": "1", "resolved_hanrei_id": ["A"], "decision_status": "strong", "confidence": 0.95},
            {"lic_edge_id": "2", "resolved_hanrei_id": ["X", "Y"], "decision_status": "review", "confidence": 0.6},
            {"lic_edge_id": "3", "resolved_hanrei_id": [], "honest_empty": "locator_unresolvable"},
        ]

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "s"
            already = sw.existing_silver_ids(staging)
            _, counts = sw.plan_writes(self.cite, [], [], POLICY, already)
            self.assertEqual(counts["accepted"], 1)
            self.assertEqual(counts["review"], 1)
            self.assertEqual(counts["exclude"], 1)
            self.assertFalse(staging.exists())  # plan のみ. 書込みなし

    def test_apply_writes_accepted_and_review(self):
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "s"
            plan, _ = sw.plan_writes(self.cite, [], [], POLICY, sw.existing_silver_ids(staging))
            sw.apply_writes(plan, staging)
            acc = list(staging.glob("silver_cite_resolved_accepted.jsonl"))
            rev = list(staging.glob("silver_cite_resolved_review_queue.jsonl"))
            self.assertEqual(len(acc), 1)
            self.assertEqual(len(rev), 1)
            rows = [json.loads(l) for l in acc[0].read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["assertion_kind"], "derived_match")
            self.assertEqual(rows[0]["reviewed_by"], "owner")
            self.assertTrue((staging / "_SILVER_WRITE_LEDGER.jsonl").exists())

    def test_idempotent_rerun_no_dup(self):
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "s"
            for _ in range(2):  # 2 回実行
                plan, _ = sw.plan_writes(self.cite, [], [], POLICY, sw.existing_silver_ids(staging))
                sw.apply_writes(plan, staging)
            rows = (staging / "silver_cite_resolved_accepted.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rows), 1)  # 二重書込みなし

    def test_no_honest_empty_in_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "s"
            plan, _ = sw.plan_writes(self.cite, [], [], POLICY, sw.existing_silver_ids(staging))
            sw.apply_writes(plan, staging)
            for p in staging.glob("silver_*_accepted.jsonl"):
                for line in p.read_text(encoding="utf-8").splitlines():
                    self.assertIsNone(json.loads(line)["honest_empty"])


if __name__ == "__main__":
    unittest.main()
