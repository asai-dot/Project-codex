# -*- coding: utf-8 -*-
"""Cross-producer safety invariants over the committed demo artifacts (out/).

This is the CI floor asked for by DD-LAWSUBTRANS-001 §10.1 (5,6) and
PLAN_lawobject_precision_v0.1 L2: a snapshot test that no producer artifact
ever ships an over-confident assertion. Each producer already runs its own
gates at write time; this re-asserts the *system-wide* contract against what
is actually committed, so a regenerated-with-a-violation artifact turns CI red.

Reads only committed JSONL/JSON under out/ — stdlib only, no DB, no network.
"""
import glob
import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)  # runnable via `python tests/...py` or `-m unittest`

from scripts.lawdelta.emit import FORBIDDEN_SUBSTANTIVE_FIELDS  # noqa: E402
from scripts.mcprender.emit import ASSERTIVE_BANNED  # noqa: E402

OUT = os.path.join(REPO, "out")


def _jsonl(pattern):
    """Yield (path, row) for every JSONL row matching out/<pattern>."""
    for path in sorted(glob.glob(os.path.join(OUT, pattern))):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield path, json.loads(line)


def _summaries():
    # Producer summaries only. The eval harness (scripts.eval) also writes
    # out/eval_*_summary.json, which has a different shape (no db_writes /
    # all_gates_pass) — it is not a producer and is excluded here.
    for path in sorted(glob.glob(os.path.join(OUT, "*_summary.json"))):
        if os.path.basename(path).startswith("eval_"):
            continue
        with open(path, encoding="utf-8") as f:
            yield path, json.load(f)


class TestSummaries(unittest.TestCase):
    def test_summaries_exist(self):
        self.assertTrue(list(_summaries()), "no producer summaries in out/")

    def test_zero_db_writes_everywhere(self):
        for path, s in _summaries():
            self.assertEqual(s.get("db_writes"), 0,
                             f"{os.path.basename(path)} reports DB writes")

    def test_all_gates_pass_everywhere(self):
        for path, s in _summaries():
            self.assertTrue(s.get("all_gates_pass"),
                            f"{os.path.basename(path)} has a failing gate")


class TestTextualDeltaStaysFormal(unittest.TestCase):
    def test_no_substantive_fields_leak(self):
        for path, row in _jsonl("law_textual_delta_*.jsonl"):
            leaked = set(row) & FORBIDDEN_SUBSTANTIVE_FIELDS
            self.assertEqual(leaked, set(),
                             f"{os.path.basename(path)} smuggles {leaked}")


class TestProducersNeverOverCommit(unittest.TestCase):
    """No tier-2/3/4 producer may ship accepted / claim_support=true."""

    def test_drafter_candidate_only(self):
        rows = 0
        for path, row in _jsonl("drafter_substantive_assertions_*.jsonl"):
            rows += 1
            self.assertEqual(row["assertion_status"], "candidate")
            self.assertFalse(row["claim_support_eligible"])
            self.assertEqual(row["source_tier"], 2)
        self.assertGreater(rows, 0, "expected committed drafter artifact")

    def test_treatment_candidate_only(self):
        rows = 0
        for path, row in _jsonl("case_treatment_candidates_*.jsonl"):
            rows += 1
            self.assertEqual(row["assertion_status"], "candidate")
            self.assertFalse(row["claim_support_eligible"])
        self.assertGreater(rows, 0, "expected committed treatment artifact")

    def test_assembler_resolved_never_accepted_or_claim_supported(self):
        rows = 0
        for path, row in _jsonl("resolved_assertions_*.jsonl"):
            rows += 1
            self.assertNotEqual(row["current_status"], "accepted",
                                "assembler must not grant accepted")
            self.assertFalse(row["claim_support_eligible"],
                             "assembler must not grant claim_support")
        self.assertGreater(rows, 0, "expected committed resolved artifact")

    def test_review_events_never_accept(self):
        for path, ev in _jsonl("assertion_review_events_*.jsonl"):
            # accepted is a human-only transition (gate accepted_requires_review_event
            # with a human review_basis); machine producers must never emit it.
            self.assertNotEqual(ev["new_status"], "accepted",
                                f"{os.path.basename(path)}: machine-accepted leak")
            self.assertTrue(ev["review_basis"], "review event lacks basis")


class TestMcpOutputStaysSafe(unittest.TestCase):
    def test_no_assertive_flag(self):
        for path, v in _jsonl("mcp_provision_views_*.jsonl"):
            self.assertFalse(v.get("assertive_output_allowed"), v.get("target"))

    def test_safe_summary_has_no_banned_verdict(self):
        for path, v in _jsonl("mcp_provision_views_*.jsonl"):
            for banned in ASSERTIVE_BANNED:
                self.assertNotIn(banned, v["safe_summary"], v.get("target"))

    def test_every_claim_attributed_and_cautious(self):
        seen = 0
        for path, v in _jsonl("mcp_provision_views_*.jsonl"):
            for c in v["claims"]:
                seen += 1
                self.assertTrue(c.get("source"))
                self.assertTrue(c.get("stance"))
                # assembler never grants claim_support -> never the relied-upon label
                self.assertNotEqual(c.get("usage"), "参考提示可", v.get("target"))
        self.assertGreater(seen, 0, "expected committed mcp views")


if __name__ == "__main__":
    unittest.main()
