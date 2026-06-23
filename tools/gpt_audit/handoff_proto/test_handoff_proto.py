"""Offline test harness for the HEAD_HAND handoff fixture-bound prototype.

Run: python -m unittest tools.gpt_audit.handoff_proto.test_handoff_proto
or:  python tools/gpt_audit/handoff_proto/test_handoff_proto.py

Pure offline. No external calls, no writes, no queue/ledger/Box mutation.
"""

from __future__ import annotations

import json
import os
import unittest

from validator import (
    Env,
    compute_packet_hash,
    reconcile,
    validate_dispatch,
)

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_fixtures() -> dict:
    with open(os.path.join(HERE, "fixtures.json"), encoding="utf-8") as fh:
        return json.load(fh)


class TestDispatchFixtures(unittest.TestCase):
    def test_dispatch_table(self):
        fixtures = _load_fixtures()["dispatch"]
        self.assertGreaterEqual(len(fixtures), 15)
        for fx in fixtures:
            with self.subTest(fx["name"]):
                env = Env(**fx.get("env", {}))
                v = validate_dispatch(dict(fx["packet"]), env)
                exp = fx["expect"]
                self.assertEqual(v.dispatchable, exp["dispatchable"])
                if "block_reason" in exp:
                    self.assertEqual(v.block_reason, exp["block_reason"])
                for axis in ("mutation_class", "egress_decision", "resource_effect_class"):
                    if axis in exp:
                        self.assertEqual(getattr(v, axis), exp[axis], axis)


class TestHashJCS(unittest.TestCase):
    def _base(self):
        return {
            "packet_schema_version": "handoff-dispatch/0.5",
            "packet_id": "DISP_x_001",
            "assignee": "local",
            "objective": "café",  # NFC normalization target
        }

    def test_runtime_envelope_excluded(self):
        p = self._base()
        h1 = compute_packet_hash(p)
        p2 = dict(p)
        p2["runtime_envelope"] = {
            "attempt_id": "ATT-1",
            "runner_id": "r1",
            "session_id": "s1",
        }
        h2 = compute_packet_hash(p2)
        self.assertEqual(h1, h2, "runtime_envelope must not change packet_hash")

    def test_packet_hash_field_excluded(self):
        p = self._base()
        h1 = compute_packet_hash(p)
        p2 = dict(p)
        p2["packet_hash"] = "sha256:deadbeef"
        self.assertEqual(h1, compute_packet_hash(p2))

    def test_normative_field_change_changes_hash(self):
        p = self._base()
        h1 = compute_packet_hash(p)
        p2 = dict(p)
        p2["assignee"] = "codex"
        self.assertNotEqual(h1, compute_packet_hash(p2))

    def test_nfc_normalization_stable(self):
        # decomposed "café" must hash equal to composed form
        p = self._base()
        p_decomposed = dict(p)
        p_decomposed["objective"] = "café"
        self.assertEqual(compute_packet_hash(p), compute_packet_hash(p_decomposed))


def _att(aid, recorded, acc=True, out="h", complete=True, valid=True):
    return {
        "attempt_id": aid,
        "source_queue_item_id": "Q1",
        "packet_generation": 1,
        "packet_hash": "sha256:aaa",
        "acceptance_pass": acc,
        "evidence_complete": complete,
        "output_hash": out,
        "schema_valid": valid,
        "recorded_at": recorded,
    }


class TestReconcile(unittest.TestCase):
    def test_mixed_rep_dup_invalid(self):
        ev = reconcile([
            _att("A", 1, out="h"),
            _att("B", 2, out="h"),            # duplicate of A
            _att("C", 3, acc=False, valid=False),  # invalid
        ])
        rels = {r["attempt_id"]: r["relation"] for r in ev["attempt_relations"]}
        self.assertEqual(ev["representative_attempt_id"], "A")
        self.assertEqual(rels["A"], "representative")
        self.assertEqual(rels["B"], "duplicate")
        self.assertEqual(rels["C"], "invalid")
        self.assertFalse(ev["needs_head_resolution"])

    def test_conflict_no_representative(self):
        # two valid, divergent outputs, both complete → conflict
        ev = reconcile([
            _att("A", 1, out="h1", complete=True),
            _att("B", 2, out="h2", complete=True),
        ])
        self.assertIsNone(ev["representative_attempt_id"])
        self.assertTrue(ev["needs_head_resolution"])
        rels = {r["attempt_id"]: r["relation"] for r in ev["attempt_relations"]}
        self.assertEqual(set(rels.values()), {"conflict"})

    def test_all_invalid(self):
        ev = reconcile([
            _att("A", 1, acc=False, valid=False),
            _att("B", 2, acc=False, valid=False),
        ])
        self.assertIsNone(ev["representative_attempt_id"])
        self.assertTrue(ev["needs_head_resolution"])

    def test_completeness_breaks_divergence(self):
        # divergent outputs but only one is evidence_complete → it wins
        ev = reconcile([
            _att("A", 1, out="h1", complete=False),
            _att("B", 2, out="h2", complete=True),
        ])
        self.assertEqual(ev["representative_attempt_id"], "B")
        self.assertFalse(ev["needs_head_resolution"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
