#!/usr/bin/env python3
"""Operational handoff-lane tests for alo_gpt_audit (non_mutating only).

Locks the v0.1 operational-impl audit must_fix:
  #1 blocked -> no route card
  #2 blocked reason appended append-only to ledger
  #4 feature flag default off (no writes unless enabled)

依存ゼロ。実行: python3 -m unittest discover -s tools/gpt_audit/tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import alo_gpt_audit as A  # noqa: E402


def _lane(tmp: str) -> "A.Lane":
    return A.Lane(Path(tmp))


def _logs():
    out = []
    return out, out.append


NON_MUTATING = {
    "packet_id": "DISP_t_001",
    "next_action_type": "doc_patch",
    "assignee": "worker_cc",
    "execution_role": "worker",
    "data_access_class": "internal",
    "side_effect_flags": [],
}
MUTATING = {
    "packet_id": "DISP_t_002",
    "next_action_type": "code_patch",
    "assignee": "local",
    "execution_role": "deterministic",
    "data_access_class": "internal",
    "side_effect_flags": ["file_move"],
}


class TestHandoffLane(unittest.TestCase):
    def setUp(self):
        self.assertTrue(A.HANDOFF_VALIDATOR_AVAILABLE, "validator import must work")
        self._flag = A.HANDOFF_LANE_ENABLED

    def tearDown(self):
        A.HANDOFF_LANE_ENABLED = self._flag

    def test_blocked_no_card_and_ledger_appended(self):
        # mutating + default env -> blocked; flag on + apply -> ledger, no card.
        A.HANDOFF_LANE_ENABLED = True
        with tempfile.TemporaryDirectory() as tmp:
            lane = _lane(tmp)
            logs, log = _logs()
            rc = A.handoff_validate_packet(lane, MUTATING, apply=True, log=log)
            self.assertEqual(rc, 0)
            # #1 no card written
            self.assertFalse((Path(tmp) / A.HANDOFF_QUEUE).exists())
            # #2 blocked reason appended append-only
            entries = lane.read_ledger()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["event"], "handoff_blocked")
            self.assertEqual(entries[0]["block_reason"],
                             "lease_required_but_unavailable")

    def test_flag_off_no_writes(self):
        # #4 default off: even with --apply, no card and no ledger writes.
        A.HANDOFF_LANE_ENABLED = False
        with tempfile.TemporaryDirectory() as tmp:
            lane = _lane(tmp)
            logs, log = _logs()
            A.handoff_validate_packet(lane, MUTATING, apply=True, log=log)
            A.handoff_validate_packet(lane, NON_MUTATING, apply=True, log=log)
            self.assertFalse((Path(tmp) / A.HANDOFF_QUEUE).exists())
            self.assertEqual(lane.read_ledger(), [])

    def test_non_mutating_card_when_enabled(self):
        A.HANDOFF_LANE_ENABLED = True
        with tempfile.TemporaryDirectory() as tmp:
            lane = _lane(tmp)
            logs, log = _logs()
            rc = A.handoff_validate_packet(lane, NON_MUTATING, apply=True, log=log)
            self.assertEqual(rc, 0)
            card = Path(tmp) / A.HANDOFF_QUEUE / "DISP_t_001_DISPATCH_CARD.md"
            self.assertTrue(card.exists())
            self.assertIn("mutation_class: non_mutating", card.read_text())

    def test_parser_has_handoff_validate(self):
        parser = A.build_parser()
        ns = parser.parse_args(["handoff-validate", "x.json"])
        self.assertIs(ns.func, A.cmd_handoff_validate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
