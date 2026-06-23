# -*- coding: utf-8 -*-
"""Tests for scripts.eval — per-label P/R/F1, confusion, empty-gold no-op,
and the lawdelta demo gold wiring smoke.
"""
import json
import os
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)  # runnable via `python tests/test_eval.py` or `-m unittest`

from scripts.eval.metrics import evaluate, load_labeled, ABSENT  # noqa: E402


class TestMetrics(unittest.TestCase):
    def test_perfect_match(self):
        gold = {"a": "repeal", "b": "no_change", "c": "split"}
        ev = evaluate(gold, dict(gold))
        self.assertEqual(ev.micro()["precision"], 1.0)
        self.assertEqual(ev.micro()["recall"], 1.0)
        self.assertEqual(ev.macro()["f1"], 1.0)

    def test_one_misclassification(self):
        gold = {"a": "repeal", "b": "no_change"}
        pred = {"a": "repeal", "b": "substitution"}  # b wrong
        ev = evaluate(gold, pred).to_dict()
        # micro: 1 tp, 1 fp (substitution), 1 fn (no_change)
        self.assertEqual(ev["micro"], {"precision": 0.5, "recall": 0.5,
                                       "f1": 0.5, "tp": 1, "fp": 1, "fn": 1})
        by = {s["label"]: s for s in ev["per_label"]}
        self.assertEqual(by["no_change"]["recall"], 0.0)        # missed
        self.assertEqual(by["substitution"]["precision"], 0.0)  # hallucinated

    def test_missing_prediction_is_false_negative(self):
        gold = {"a": "repeal", "b": "split"}
        pred = {"a": "repeal"}  # b not predicted at all
        by = {s["label"]: s for s in evaluate(gold, pred).to_dict()["per_label"]}
        self.assertEqual(by["split"]["fn"], 1)
        self.assertEqual(by["split"]["recall"], 0.0)

    def test_extra_prediction_is_false_positive(self):
        gold = {"a": "repeal"}
        pred = {"a": "repeal", "z": "insertion"}  # z hallucinated
        by = {s["label"]: s for s in evaluate(gold, pred).to_dict()["per_label"]}
        self.assertEqual(by["insertion"]["fp"], 1)
        self.assertEqual(by["insertion"]["precision"], 0.0)

    def test_absent_excluded_from_micro(self):
        # ABSENT must not appear as a scored label
        gold = {"a": "repeal"}
        pred = {"a": "repeal", "z": "insertion"}
        labels = {s["label"] for s in evaluate(gold, pred).to_dict()["per_label"]}
        self.assertNotIn(ABSENT, labels)

    def test_empty_gold_is_noop(self):
        ev = evaluate({}, {"a": "repeal"}).to_dict()
        self.assertTrue(ev["empty_gold"])
        self.assertIsNone(ev["micro"])

    def test_gold_is_subset_audit(self):
        # Audit mode: only 'a' is verified; producer also predicts on 'b' (unverified)
        gold = {"a": "repeal"}
        pred = {"a": "repeal", "b": "substitution"}
        ev = evaluate(gold, pred, gold_is_subset=True)
        m = ev.micro()
        self.assertEqual(m["precision"], 1.0)
        self.assertEqual(m["recall"], 1.0)
        # 'b' must NOT be counted as a substitution FP
        labels = {s["label"] for s in ev.to_dict()["per_label"]}
        self.assertNotIn("substitution", labels)


class TestLoad(unittest.TestCase):
    def test_load_skips_blank_and_missing_key(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.jsonl")
            with open(p, "w", encoding="utf-8") as f:
                f.write(json.dumps({"k": "1", "v": "a"}) + "\n")
                f.write("\n")  # blank
                f.write(json.dumps({"v": "b"}) + "\n")  # no key -> skipped
            got = load_labeled(p, "k", "v")
            self.assertEqual(got, {"1": "a"})

    def test_missing_file_returns_empty(self):
        self.assertEqual(load_labeled("/no/such/file.jsonl", "k", "v"), {})


class TestDemoGoldWiring(unittest.TestCase):
    """The committed demo gold must line up 1:1 with the committed demo pred."""

    def test_lawdelta_demo_gold_matches_pred(self):
        gold = load_labeled(os.path.join(REPO, "tests/gold/lawdelta_demo_minpo.gold.jsonl"),
                            "article_path", "delta_kind")
        pred = load_labeled(os.path.join(REPO, "out/law_textual_delta_demo_minpo.jsonl"),
                            "article_path", "delta_kind")
        self.assertTrue(gold, "demo gold should not be empty")
        self.assertTrue(pred, "demo pred artifact missing")
        ev = evaluate(gold, pred)
        self.assertEqual(ev.micro()["f1"], 1.0,
                         "demo gold is a self-consistency smoke; should be P/R=1.0")


if __name__ == "__main__":
    unittest.main()
