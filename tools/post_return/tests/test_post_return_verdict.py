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
        # work遅延超過 + サンプル下限未達 → ハードゲートは全通過、ソフトが WARN
        v = prv.evaluate(load("metrics_CONDITIONAL.json"))
        self.assertEqual(v.verdict, "CONDITIONAL")
        self.assertFalse(any(c.hard and c.status == prv.FAIL for c in v.checks))
        self.assertTrue(any(c.status == prv.WARN for c in v.checks))

    def test_nogo_hard_fail(self):
        v = prv.evaluate(load("metrics_NOGO.json"))
        self.assertEqual(v.verdict, "NO-GO")
        gates_failed = {c.gate for c in v.checks if c.hard and c.status == prv.FAIL}
        # 接地/false-merge/provenance/決定性/rights/HOLD すべて踏む
        for g in ("G1", "G2", "G3", "G4", "G5", "G7"):
            self.assertIn(g, gates_failed)

    def test_fail_closed_missing_metrics(self):
        # 必須キー欠落は GO にしない (fail-closed)
        v = prv.evaluate({})
        self.assertEqual(v.verdict, "NO-GO")
        self.assertTrue(any(c.status == prv.FAIL for c in v.checks))

    def test_fail_closed_empty_grounding(self):
        # total==0 は「接地対象が空＝判定不能」で FAIL
        m = load("metrics_GO.json")
        m["grounding"] = {"total": 0, "grounded": 0, "ungrounded_ids": []}
        v = prv.evaluate(m)
        self.assertEqual(v.verdict, "NO-GO")

    def test_determinism_drift_is_nogo(self):
        m = load("metrics_GO.json")
        m["determinism"]["run_b_hash"] = "sha256:deadbeef0000"
        v = prv.evaluate(m)
        self.assertEqual(v.verdict, "NO-GO")
        self.assertTrue(any(c.gate == "G4" and c.status == prv.FAIL for c in v.checks))

    def test_hold_flag_blocks(self):
        m = load("metrics_GO.json")
        m["hold"]["flags"] = ["manual-hold"]
        v = prv.evaluate(m)
        self.assertEqual(v.verdict, "NO-GO")

    def test_provenance_double_count_blocks(self):
        m = load("metrics_GO.json")
        m["provenance"]["double_counted_ids"] = ["src-1"]
        v = prv.evaluate(m)
        self.assertEqual(v.verdict, "NO-GO")

    def test_sample_below_min_is_conditional(self):
        m = load("metrics_GO.json")
        m["false_merge"]["sampled"] = 10
        v = prv.evaluate(m)
        self.assertEqual(v.verdict, "CONDITIONAL")

    def test_deterministic_verdict(self):
        # 同じ入力 → 同じ verdict / 同じ理由 (決定性)
        m = load("metrics_NOGO.json")
        a = prv.evaluate(m).to_dict()
        b = prv.evaluate(m).to_dict()
        self.assertEqual(a, b)

    def test_plan_only_on_go(self):
        go = prv.evaluate(load("metrics_GO.json"))
        plan = prv.render_plan("501", go)
        self.assertIn("DDL", plan)
        self.assertIn("owner-gated", plan)

    def test_exit_codes(self):
        # CLI exit: GO=0, CONDITIONAL=1, NO-GO=2
        self.assertEqual(prv.main(["--metrics", os.path.join(SAMPLES, "metrics_GO.json")]), 0)
        self.assertEqual(prv.main(["--metrics", os.path.join(SAMPLES, "metrics_CONDITIONAL.json")]), 1)
        self.assertEqual(prv.main(["--metrics", os.path.join(SAMPLES, "metrics_NOGO.json")]), 2)


if __name__ == "__main__":
    unittest.main()
