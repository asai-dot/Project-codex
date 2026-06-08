#!/usr/bin/env python3
"""consumed_view.py の単体テスト。実行: python3 tools/gpt_audit/test_consumed_view.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import consumed_view as cv  # noqa: E402


class ConsumedViewTest(unittest.TestCase):
    def test_disposition_mapping(self):
        self.assertEqual(cv.DISPOSITION["patch"], "採用(要修正)")
        self.assertEqual(cv.DISPOSITION["required_materials"], "保留(資料補充)")
        self.assertEqual(cv.DISPOSITION["reject"], "不採用")

    def test_consumption_state_uses_reflected_as_primary(self):
        # reflected:false が残る限り「反映済」にしない (loop_state より優先)
        self.assertEqual(cv.consumption_state({"loop_state": "returned", "reflected": False}), "未反映")
        self.assertEqual(cv.consumption_state({"loop_state": "requeued", "reflected": False}), "未反映")
        self.assertEqual(cv.consumption_state({"loop_state": "ratify_wait", "reflected": False}), "ratify待ち")
        self.assertEqual(cv.consumption_state({"loop_state": "requeued", "reflected": True}), "反映済(後続へ)")
        self.assertEqual(cv.consumption_state({"loop_state": "reflected", "reflected": True}), "反映済")

    def test_snapshot_counts(self):
        rows = cv.load_ledger(cv.DEFAULT_LEDGER)
        self.assertEqual(len(rows), 25)
        unreflected = [r for r in rows if cv.consumption_state(r) == "未反映"]
        ratify_wait = [r for r in rows if cv.consumption_state(r) == "ratify待ち"]
        # 2026-06-08 スナップショット: 未反映6 / ratify待ち8 / closed相当11
        self.assertEqual(len(unreflected), 6)
        self.assertEqual(len(ratify_wait), 8)

    def test_comment_line_skipped(self):
        # _comment ヘッダ行は request_id 無しでもエラーにならない
        rows = cv.load_ledger(cv.DEFAULT_LEDGER)
        self.assertTrue(all("request_id" in r for r in rows))

    def test_render_marks_unreflected_first(self):
        rows = cv.load_ledger(cv.DEFAULT_LEDGER)
        md = cv.render(rows, "x", "X")
        self.assertIn("未反映", md)
        # 未反映セクションが ratify待ちより前に出る
        self.assertLess(md.index("読んだが反映"), md.index("浅井判断待ち"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
