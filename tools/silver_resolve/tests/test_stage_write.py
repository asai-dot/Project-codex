"""silver_stage_write (P1) ユニットテスト. SILVER-RESOLUTION-KICKOFF v0.1.1 整合版.

実行: python3 -m unittest discover -s tools/silver_resolve/tests -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import silver_stage_write as sw  # noqa: E402

POLICY = {"accept_status": [sw.ST_CITE_A, sw.ST_SECTION],
          "source_scheme_version": "test", "suggested_by": "owner"}


def _cite(eid, targets, status, **extra):
    d = {"lic_edge_id": eid, "target_source_record_uri": targets,
         "suggestion_status": status, "evidence_tier": "A", "identity_scope": "src"}
    d.update(extra)
    return d


class TestRouting(unittest.TestCase):
    def test_cite_tierA_single_candidate(self):
        lane, sid, _ = sw._route_cite(_cite("1", ["d1hanrei:A"], sw.ST_CITE_A), POLICY)
        self.assertEqual(lane, "candidate")
        self.assertEqual(sid, "cite:1|d1hanrei:A")

    def test_cite_ambiguous_goes_ambiguity(self):
        lane, _, _ = sw._route_cite(_cite("2", ["d1hanrei:X", "d1hanrei:Y"],
                                          "ambiguous_or_unresolved"), POLICY)
        self.assertEqual(lane, "ambiguity")

    def test_cite_tierA_but_multi_target_not_candidate(self):
        lane, _, _ = sw._route_cite(_cite("3", ["d1hanrei:X", "d1hanrei:Y"], sw.ST_CITE_A), POLICY)
        self.assertEqual(lane, "ambiguity")  # 単一でなければ candidate 不可

    def test_cite_blocked_excluded(self):
        lane, _, _ = sw._route_cite(_cite("4", [], "blocked_by_policy_or_provenance",
                                          blocker_code="authority_snapshot_missing"), POLICY)
        self.assertEqual(lane, "exclude")

    def test_section_needs_review_goes_ambiguity(self):
        c = {"issue_section_id": "s1", "member_hanrei_ids": ["A", "B"],
             "decision_status": "needs_human_review"}
        lane, sid, _ = sw._route_section(c, POLICY)
        self.assertEqual(lane, "ambiguity")
        self.assertEqual(sid, "section:s1")

    def test_cooc_weightless_excluded(self):
        lane, _, _ = sw._route_cooc({"hanrei_a": "A", "hanrei_b": "B", "pair_weight": 0}, POLICY)
        self.assertEqual(lane, "exclude")


class TestApplyAndIdempotency(unittest.TestCase):
    def setUp(self):
        self.cite = [
            _cite("1", ["d1hanrei:A"], sw.ST_CITE_A),
            _cite("2", ["d1hanrei:X", "d1hanrei:Y"], "ambiguous_or_unresolved"),
            _cite("3", [], "blocked_by_policy_or_provenance", blocker_code="authority_snapshot_missing"),
        ]

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "s"
            _, counts = sw.plan_writes(self.cite, [], [], POLICY, sw.existing_silver_ids(staging))
            self.assertEqual(counts["candidate"], 1)
            self.assertEqual(counts["ambiguity"], 1)
            self.assertEqual(counts["exclude"], 1)
            self.assertFalse(staging.exists())

    def test_apply_writes_candidate_and_ambiguity_reviewed_false(self):
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "s"
            plan, _ = sw.plan_writes(self.cite, [], [], POLICY, sw.existing_silver_ids(staging))
            sw.apply_writes(plan, staging)
            cand = list(staging.glob("silver_cite_resolved_candidate.jsonl"))
            amb = list(staging.glob("silver_cite_resolved_ambiguity_queue.jsonl"))
            self.assertEqual(len(cand), 1)
            self.assertEqual(len(amb), 1)
            rows = [json.loads(x) for x in cand[0].read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertFalse(rows[0]["reviewed"])  # ★ reviewed=true にしない
            self.assertEqual(rows[0]["assertion_kind"], "derived_match")
            self.assertTrue((staging / "_SILVER_WRITE_LEDGER.jsonl").exists())

    def test_idempotent_rerun_no_dup(self):
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "s"
            for _ in range(2):
                plan, _ = sw.plan_writes(self.cite, [], [], POLICY, sw.existing_silver_ids(staging))
                sw.apply_writes(plan, staging)
            rows = (staging / "silver_cite_resolved_candidate.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rows), 1)

    def test_no_reviewed_true_anywhere(self):
        with tempfile.TemporaryDirectory() as td:
            staging = Path(td) / "s"
            plan, _ = sw.plan_writes(self.cite, [], [], POLICY, sw.existing_silver_ids(staging))
            sw.apply_writes(plan, staging)
            for p in staging.glob("silver_*.jsonl"):
                for line in p.read_text(encoding="utf-8").splitlines():
                    self.assertFalse(json.loads(line)["reviewed"])


if __name__ == "__main__":
    unittest.main()
