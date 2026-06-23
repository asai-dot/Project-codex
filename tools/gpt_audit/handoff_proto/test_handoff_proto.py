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
    migrate_next_action_type,
    reconcile,
    select_active_generation,
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

    def test_weak_equivalence_tagged(self):
        # divergent output_hash but same acceptance + outputs set → weak equiv,
        # and the representative relation must carry basis_code weak_equivalence.
        a = _att("A", 1, out="h1")
        b = _att("B", 2, out="h2")
        for x in (a, b):
            x["acceptance_set"] = ["c1", "c2"]
            x["outputs_set"] = ["out.md"]
        ev = reconcile([a, b])
        self.assertEqual(ev["representative_attempt_id"], "A")
        rep = next(r for r in ev["attempt_relations"] if r["attempt_id"] == "A")
        self.assertIn("weak_equivalence", rep["basis_codes"])

    def test_stale_generation_distinct_from_stale_packet(self):
        # stale_generation is a reconciliation (cross-generation) outcome, NOT
        # the stale_packet dispatch block (digest failure, see F13).
        gen1 = _att("A", 1)
        gen1["packet_generation"] = 1
        gen2 = _att("B", 2)
        gen2["packet_generation"] = 2
        split = select_active_generation([gen1, gen2])
        self.assertEqual([a["attempt_id"] for a in split["active"]], ["B"])
        self.assertEqual([a["attempt_id"] for a in split["stale_generation"]], ["A"])


class TestEgressRedirect(unittest.TestCase):
    def test_redirect_in_and_out(self):
        fixtures = {f["name"]: f for f in _load_fixtures()["dispatch"]}
        for name, expect_block in (
            ("F16_redirect_into_allowlist_ok", None),
            ("F17_redirect_out_of_allowlist_blocked", "egress_forbidden"),
        ):
            with self.subTest(name):
                fx = fixtures[name]
                v = validate_dispatch(dict(fx["packet"]), Env(**fx.get("env", {})))
                self.assertEqual(v.block_reason, expect_block)


class TestPatchMigration(unittest.TestCase):
    def test_old_patch_maps(self):
        self.assertEqual(migrate_next_action_type("patch"), "design_patch")
        self.assertEqual(migrate_next_action_type("patch", code_like=True), "code_patch")
        self.assertEqual(migrate_next_action_type("refactor"), "refactor")


class TestOperationalDefaultLane(unittest.TestCase):
    """must_fix #3: while lease/permit subsystems are unimplemented (the default),
    only the non_mutating + non-permit + non-confidential lane may dispatch.
    This locks the operational rollout boundary as code."""

    def test_default_env_blocks_mutating_and_permit(self):
        env = Env()  # all subsystems unavailable — the real current state
        mutating = {
            "next_action_type": "code_patch", "assignee": "local",
            "execution_role": "deterministic", "data_access_class": "internal",
            "side_effect_flags": ["file_move"],
        }
        paid = {
            "next_action_type": "required_materials", "assignee": "codex",
            "execution_role": "worker", "data_access_class": "public",
            "egress_descriptor": {"destination_class": "public_query", "outbound_payload_class": "public"},
            "resource_descriptor": {"resource_effect_class": "paid"},
        }
        self.assertEqual(validate_dispatch(mutating, env).block_reason,
                         "lease_required_but_unavailable")
        self.assertEqual(validate_dispatch(paid, env).block_reason,
                         "resource_permit_unavailable")

    def test_default_env_allows_non_mutating_lane(self):
        env = Env()
        ok = {
            "next_action_type": "doc_patch", "assignee": "worker_cc",
            "execution_role": "worker", "data_access_class": "internal",
            "side_effect_flags": [],
        }
        self.assertTrue(validate_dispatch(ok, env).dispatchable)


if __name__ == "__main__":
    unittest.main(verbosity=2)
