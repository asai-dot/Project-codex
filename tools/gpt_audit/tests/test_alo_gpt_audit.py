#!/usr/bin/env python3
"""alo-gpt-audit 検収テスト（GPT_PRO_AUDIT_LANE_DESIGN v0.3 §H, TEST-1〜6）。

実行: python -m pytest tools/gpt_audit/tests   または   python tools/gpt_audit/tests/test_alo_gpt_audit.py
依存ゼロ（unittest のみ）。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import alo_gpt_audit as a  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_lane(tmp: Path) -> a.Lane:
    lane = a.Lane(tmp)
    lane.to_gpt.mkdir(parents=True, exist_ok=True)
    lane.processed.mkdir(parents=True, exist_ok=True)
    lane.from_gpt.mkdir(parents=True, exist_ok=True)
    return lane


def seed_basic(lane: a.Lane) -> None:
    # answered: REQUEST in to_gpt + valid RESULT in from_gpt
    _write(lane.to_gpt / "20260607_lawtime_v0.2_DDLAWTIME_REQUEST.md",
           "request_id: 20260607_lawtime_v0.2_DDLAWTIME\n")
    _write(lane.from_gpt / "20260607_lawtime_v0.2_DDLAWTIME_RESULT.md",
           "DDLAWTIME_MODIFY_REQUIRED\n\nbody\n")
    # answered via interim .processed.md naming
    _write(lane.to_gpt / "20260607_toclegalref_v0.2_DDTOCLEGALREF_REQUEST.processed.md",
           "request_id: 20260607_toclegalref_v0.2_DDTOCLEGALREF\n")
    _write(lane.from_gpt / "20260607_toclegalref_v0.2_DDTOCLEGALREF_RESULT.md",
           "DDTOCLEGALREF_PASS_WITH_NOTES\n")
    # genuinely unanswered (no RESULT)
    _write(lane.to_gpt / "20260607_legaldb_v0.6_DESIGN_REQUEST.md",
           "request_id: 20260607_legaldb_v0.6_DESIGN\n")


class TestStem(unittest.TestCase):
    def test_stem_variants(self):
        self.assertEqual(a.stem_of("x_REQUEST.md"), "x")
        self.assertEqual(a.stem_of("x_REQUEST.processed.md"), "x")
        self.assertEqual(a.stem_of("x_RESULT.md"), "x")
        self.assertIsNone(a.stem_of("random.txt"))

    def test_strip_gate(self):
        self.assertEqual(a.strip_gate("DDLAWTIME_MODIFY_REQUIRED"), "MODIFY_REQUIRED")
        self.assertEqual(a.strip_gate("G0_PASS_WITH_NOTES"), "PASS_WITH_NOTES")
        self.assertEqual(a.strip_gate("nonsense"), "")

    def test_next_action_mapping(self):
        e = a.LedgerEntry(request_id="x", result_label="DD_MODIFY_REQUIRED").enrich_from_label()
        self.assertEqual(e.next_action_type, "patch")
        self.assertFalse(e.ratify_required)
        self.assertTrue(e.requeue_expected)
        self.assertEqual(e.target_queue, "patch_queue")
        e2 = a.LedgerEntry(request_id="y", result_label="DD_PASS_WITH_NOTES").enrich_from_label()
        self.assertEqual(e2.next_action_type, "ratify")
        self.assertTrue(e2.ratify_required)
        self.assertEqual(e2.target_queue, "approval_queue")


class TestLaneOps(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.lane = make_lane(self.tmp)
        seed_basic(self.lane)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_status_counts_answered(self):
        """TEST-1 status: answered_not_processed を正しく数える。"""
        rows = {r.stem: r for r in a.compute_status(self.lane)}
        self.assertEqual(rows["20260607_lawtime_v0.2_DDLAWTIME"].lane_status,
                         "answered_not_processed")
        self.assertEqual(rows["20260607_toclegalref_v0.2_DDTOCLEGALREF"].lane_status,
                         "answered_not_processed")
        self.assertEqual(rows["20260607_legaldb_v0.6_DESIGN"].lane_status, "active")

    def test_2_dry_run_moves_nothing(self):
        """TEST-2 dry-run: 退避予定を出すが何も動かさない。"""
        before = sorted(p.name for p in self.lane.to_gpt.iterdir() if p.is_file())
        plans = a.plan_close(self.lane)
        movable = [p for p in plans if p.actionable]
        self.assertEqual(len(movable), 2)  # lawtime + toclegalref
        after = sorted(p.name for p in self.lane.to_gpt.iterdir() if p.is_file())
        self.assertEqual(before, after)  # 何も動いていない

    def test_3_execute_retreats(self):
        """TEST-3 execute: REQUEST->processed, to_gpt直下から消える, RESULT残置。"""
        plans = [p for p in a.plan_close(self.lane) if p.actionable]
        a.execute_plan(self.lane, plans)
        direct = [p.name for p in self.lane.to_gpt.iterdir() if p.is_file()]
        # 未回答の legaldb v0.6 だけ直下に残る
        self.assertEqual(direct, ["20260607_legaldb_v0.6_DESIGN_REQUEST.md"])
        # 退避先はサフィックスを剥がした正規名
        proc = sorted(p.name for p in self.lane.processed.iterdir() if p.is_file())
        self.assertIn("20260607_lawtime_v0.2_DDLAWTIME_REQUEST.md", proc)
        self.assertIn("20260607_toclegalref_v0.2_DDTOCLEGALREF_REQUEST.md", proc)
        # RESULT は from_gpt に残る
        self.assertTrue((self.lane.from_gpt /
                         "20260607_lawtime_v0.2_DDLAWTIME_RESULT.md").exists())

    def test_4_idempotency(self):
        """TEST-4 idempotency: 再実行で二重移動・二重台帳追記しない。"""
        plans = [p for p in a.plan_close(self.lane) if p.actionable]
        a.execute_plan(self.lane, plans)
        ledger_after_1 = a.load_ledger(self.lane.ledger_path)
        # 2 回目: もう answered_not_processed は無い → 退避予定 0
        plans2 = [p for p in a.plan_close(self.lane) if p.actionable]
        self.assertEqual(plans2, [])
        a.execute_plan(self.lane, plans2)
        ledger_after_2 = a.load_ledger(self.lane.ledger_path)
        self.assertEqual(set(ledger_after_1), set(ledger_after_2))
        # processed に重複ファイルが生まれていない
        proc = [p.name for p in self.lane.processed.iterdir() if p.is_file()]
        self.assertEqual(len(proc), len(set(proc)))

    def test_5_missing_result_not_moved(self):
        """TEST-5 missing-result: RESULT 無し REQUEST は移動しない。"""
        plans = a.plan_close(self.lane)
        stems_moving = {p.stem for p in plans if p.actionable}
        self.assertNotIn("20260607_legaldb_v0.6_DESIGN", stems_moving)

    def test_6_bad_label_not_moved(self):
        """TEST-6 bad-label: 先頭行が不正な RESULT は移動しない。"""
        _write(self.lane.to_gpt / "20260607_badcase_v0.1_DDBAD_REQUEST.md", "x\n")
        _write(self.lane.from_gpt / "20260607_badcase_v0.1_DDBAD_RESULT.md",
               "this is not a label\n")
        rows = {r.stem: r for r in a.compute_status(self.lane)}
        self.assertEqual(rows["20260607_badcase_v0.1_DDBAD"].lane_status, "bad_label")
        plans = a.plan_close(self.lane)
        moving = {p.stem for p in plans if p.actionable}
        self.assertNotIn("20260607_badcase_v0.1_DDBAD", moving)

    def test_build_ledger_and_action_queue(self):
        """build-ledger が RESULT 全件を台帳化し、action-queue が reflected:false を返す。"""
        merged = a.build_ledger(self.lane)
        a.save_ledger(self.lane.ledger_path, merged)
        q = a.action_queue(self.lane)
        ids = {e.request_id for e in q}
        self.assertIn("20260607_lawtime_v0.2_DDLAWTIME", ids)
        self.assertIn("20260607_toclegalref_v0.2_DDTOCLEGALREF", ids)
        # patch(MODIFY) が ratify(PASS_WITH_NOTES) より前に並ぶ
        self.assertEqual(q[0].next_action_type, "patch")

    def test_build_ledger_preserves_enrichment(self):
        """build-ledger は人手エンリッチ（reflected等）を request_id で引き継ぐ。"""
        merged = a.build_ledger(self.lane)
        merged["20260607_lawtime_v0.2_DDLAWTIME"].reflected = True
        merged["20260607_lawtime_v0.2_DDLAWTIME"].claude_rethink_prompt = "keep me"
        a.save_ledger(self.lane.ledger_path, merged)
        merged2 = a.build_ledger(self.lane)
        self.assertTrue(merged2["20260607_lawtime_v0.2_DDLAWTIME"].reflected)
        self.assertEqual(merged2["20260607_lawtime_v0.2_DDLAWTIME"].claude_rethink_prompt,
                         "keep me")


class TestLint(unittest.TestCase):
    def test_lint_missing_fields(self):
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        lane = make_lane(tmp)
        _write(lane.to_gpt / "20260607_x_v0.1_DDX_REQUEST.md",
               "request_id: x\ntopic: x\n")
        missing = a.lint_request(lane.to_gpt / "20260607_x_v0.1_DDX_REQUEST.md")
        self.assertIn("review_scope", missing)
        self.assertIn("source_hash", missing)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
