import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import post_return_verdict as prv  # noqa: E402

SAMPLES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))


def load(name):
    with open(os.path.join(SAMPLES, name), encoding="utf-8") as f:
        return json.load(f)


class TestVerdict(unittest.TestCase):
    def test_go_all_pass(self):
        v = prv.evaluate(load("metrics_GO.json"))
        self.assertEqual(v.verdict, "GO")
        self.assertEqual(len(v.checks), 12)
        self.assertTrue(all(c.status == prv.PASS for c in v.checks))
        self.assertEqual(v.reasons, [])

    def test_conditional_soft_warn(self):
        # rights_blocked_rate 超過 + provenance_collapse_count==0 + coverage<0.95 → ハード全通過・ソフトWARN
        v = prv.evaluate(load("metrics_CONDITIONAL.json"))
        self.assertEqual(v.verdict, "CONDITIONAL")
        self.assertFalse(any(c.hard and c.status == prv.FAIL for c in v.checks))
        self.assertTrue(any(c.status == prv.WARN for c in v.checks))

    def test_nogo_hard_fail(self):
        v = prv.evaluate(load("metrics_NOGO.json"))
        self.assertEqual(v.verdict, "NO-GO")
        gates_failed = {c.gate for c in v.checks if c.hard and c.status == prv.FAIL}
        for g in ("G1", "G2", "G3", "G4", "G5", "G7"):
            self.assertIn(g, gates_failed)

    def test_fail_closed_missing_metrics(self):
        v = prv.evaluate({})
        self.assertEqual(v.verdict, "NO-GO")
        self.assertTrue(any(c.status == prv.FAIL for c in v.checks))

    def test_ungrounded_blocks(self):
        m = load("metrics_GO.json")
        m["ungrounded_value_count"] = 1
        self.assertEqual(prv.evaluate(m).verdict, "NO-GO")

    def test_cohort_shortfall_blocks(self):
        m = load("metrics_GO.json")
        m["cohort"]["processed"] = 500
        self.assertEqual(prv.evaluate(m).verdict, "NO-GO")

    def test_classification_collapse_is_false_merge_nogo(self):
        m = load("metrics_GO.json")
        m["classification_multi_preserved"] = False
        v = prv.evaluate(m)
        self.assertEqual(v.verdict, "NO-GO")
        self.assertTrue(any(c.gate == "G2" and c.status == prv.FAIL for c in v.checks))

    def test_provenance_family_collapse_required(self):
        m = load("metrics_GO.json")
        m["provenance_family_collapse_effective"] = False
        self.assertEqual(prv.evaluate(m).verdict, "NO-GO")

    def test_determinism_drift_is_nogo(self):
        m = load("metrics_GO.json")
        m["determinism"]["run_b_hash"] = "sha256:deadbeef0000"
        v = prv.evaluate(m)
        self.assertEqual(v.verdict, "NO-GO")
        self.assertTrue(any(c.gate == "G4" and c.status == prv.FAIL for c in v.checks))

    def test_rights_profile_coverage_required(self):
        m = load("metrics_GO.json")
        m["rights_profile_coverage"] = 0.99
        self.assertEqual(prv.evaluate(m).verdict, "NO-GO")

    def test_scope_write_violation_is_hold_nogo(self):
        # report-only 違反: DB 書込が出たら HOLD/NO-GO
        m = load("metrics_GO.json")
        m["write_evidence"]["db_writes"] = 1
        v = prv.evaluate(m)
        self.assertEqual(v.verdict, "NO-GO")
        self.assertTrue(any(c.gate == "G7" and c.status == prv.FAIL for c in v.checks))

    def test_access_mixed_into_consensus_is_nogo(self):
        m = load("metrics_GO.json")
        m["access_not_in_biblio_consensus"] = False
        self.assertEqual(prv.evaluate(m).verdict, "NO-GO")

    def test_rights_blocked_rate_high_is_conditional(self):
        m = load("metrics_GO.json")
        m["rights_blocked_rate"] = 0.5
        self.assertEqual(prv.evaluate(m).verdict, "CONDITIONAL")

    def test_deterministic_verdict(self):
        m = load("metrics_NOGO.json")
        self.assertEqual(prv.evaluate(m).to_dict(), prv.evaluate(m).to_dict())

    def test_plan_only_on_go(self):
        go = prv.evaluate(load("metrics_GO.json"))
        plan = prv.render_plan("attr_layer_501_dryrun_20260615", go)
        self.assertIn("owner-gated", plan)
        self.assertIn("backfill", plan)

    def test_exit_codes(self):
        self.assertEqual(prv.main(["--metrics", os.path.join(SAMPLES, "metrics_GO.json")]), 0)
        self.assertEqual(prv.main(["--metrics", os.path.join(SAMPLES, "metrics_CONDITIONAL.json")]), 1)
        self.assertEqual(prv.main(["--metrics", os.path.join(SAMPLES, "metrics_NOGO.json")]), 2)


if __name__ == "__main__":
    unittest.main()
