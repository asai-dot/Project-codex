#!/usr/bin/env python3
"""queue.py の classify() / fold() の単体テスト (依存ゼロ, unittest)。

closed の厳格化 (RESULT だけでは closed にしない) を中心に検証する。
実行: python3 tools/gpt_audit/test_queue.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import queue as q  # noqa: E402


def fold_events(events):
    return q.fold(events)


def one(rid, events):
    return fold_events([dict(e, request_id=rid) for e in events])[rid]


class ClassifyTest(unittest.TestCase):
    def test_request_only_is_unaudited(self):
        st = one("r", [dict(event="REQUEST_CREATED", topic="t", gate="G")])
        self.assertEqual(st.classify(), q.UNAUDITED)

    def test_result_without_consume_is_unconsumed(self):
        st = one("r", [
            dict(event="REQUEST_CREATED"),
            dict(event="RESULT_RETURNED", label="G_PASS"),
        ])
        self.assertEqual(st.classify(), q.UNCONSUMED)

    def test_result_alone_never_closed(self):
        # v0.2 中核ルール: RESULT が返っただけでは closed にしない。
        st = one("r", [
            dict(event="REQUEST_CREATED"),
            dict(event="RESULT_RETURNED", label="G_PASS"),
        ])
        self.assertNotEqual(st.classify(), q.CLOSED)

    def test_consumed_modify_needs_reflect(self):
        st = one("r", [
            dict(event="REQUEST_CREATED"),
            dict(event="RESULT_RETURNED", label="G_MODIFY_REQUIRED"),
            dict(event="CONSUMED", disposition="adopt", requires_reflection=True),
        ])
        self.assertEqual(st.classify(), q.UNREFLECTED)

    def test_pass_with_notes_reflected_then_awaiting_owner(self):
        st = one("r", [
            dict(event="REQUEST_CREATED"),
            dict(event="RESULT_RETURNED", label="G_PASS_WITH_NOTES"),
            dict(event="CONSUMED", disposition="adopt",
                 requires_reflection=True, ratify_required=True),
            dict(event="REFLECTED"),
        ])
        self.assertEqual(st.classify(), q.AWAITING_OWNER)

    def test_full_chain_closes(self):
        st = one("r", [
            dict(event="REQUEST_CREATED"),
            dict(event="RESULT_RETURNED", label="G_PASS"),
            dict(event="CONSUMED", disposition="adopt",
                 requires_reflection=True, ratify_required=True),
            dict(event="REFLECTED"),
            dict(event="RATIFIED"),
        ])
        self.assertEqual(st.classify(), q.CLOSED)

    def test_pass_with_ratify_not_yet_reflected_is_unreflected(self):
        st = one("r", [
            dict(event="REQUEST_CREATED"),
            dict(event="RESULT_RETURNED", label="G_PASS_WITH_NOTES"),
            dict(event="CONSUMED", disposition="adopt",
                 requires_reflection=True, ratify_required=True),
        ])
        self.assertEqual(st.classify(), q.UNREFLECTED)

    def test_reject_without_ratify_closes(self):
        st = one("r", [
            dict(event="REQUEST_CREATED"),
            dict(event="RESULT_RETURNED", label="G_FAIL"),
            dict(event="CONSUMED", disposition="reject", requires_reflection=False),
        ])
        self.assertEqual(st.classify(), q.CLOSED)

    def test_superseded_closes(self):
        st = one("r", [
            dict(event="REQUEST_CREATED"),
            dict(event="RESULT_RETURNED", label="G_MODIFY_REQUIRED"),
            dict(event="CONSUMED", disposition="adopt", requires_reflection=True),
            dict(event="REQUEUED", superseded_by="r2"),
        ])
        self.assertEqual(st.classify(), q.CLOSED)

    def test_need_more_defer_is_unreflected(self):
        st = one("r", [
            dict(event="REQUEST_CREATED"),
            dict(event="RESULT_RETURNED", label="G_NEED_MORE", need_more_type="material_absent"),
            dict(event="CONSUMED", disposition="defer", requires_reflection=True),
        ])
        self.assertEqual(st.classify(), q.UNREFLECTED)

    def test_reopened_reverts_closed(self):
        st = one("r", [
            dict(event="REQUEST_CREATED"),
            dict(event="RESULT_RETURNED", label="G_PASS"),
            dict(event="CONSUMED", disposition="adopt", requires_reflection=False,
                 ratify_required=True),
            dict(event="RATIFIED"),
            dict(event="CLOSED", reason="done"),
            dict(event="REOPENED"),
        ])
        # reopen 後は ratify 済なので再び closed 相当に戻るが、closed_explicit は解除される。
        self.assertFalse(st.closed_explicit)

    def test_label_kind_parsing(self):
        st = q.RequestState("r", label="DDLAWTIME_PASS_WITH_NOTES")
        self.assertEqual(st.label_kind, "PASS_WITH_NOTES")
        st2 = q.RequestState("r", label="G0_PASS")
        self.assertEqual(st2.label_kind, "PASS")


class SeedSnapshotTest(unittest.TestCase):
    """シード済みファイルがあれば 2026-06-08 の件数を満たすことを確認する。"""

    def test_seed_counts(self):
        if not os.path.exists(q.EVENTS_PATH):
            self.skipTest("QUEUE_EVENTS.jsonl 未生成")
        states = q.fold(q.load_events())
        buckets = q.bucketize(states)
        self.assertEqual(len(states), 25)
        self.assertEqual(len(buckets[q.UNREFLECTED]), 6)
        self.assertEqual(len(buckets[q.AWAITING_OWNER]), 8)
        self.assertEqual(len(buckets[q.CLOSED]), 11)
        self.assertEqual(len(buckets[q.UNAUDITED]), 0)
        self.assertEqual(len(buckets[q.UNCONSUMED]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
