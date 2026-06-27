#!/usr/bin/env python3
"""alo-gpt-audit 検収テスト (DESIGN v0.3 §H TEST-1..6 + LOOP_RULE §8 反映キュー)。

依存ゼロ (標準 unittest)。各テストは tempdir に gpt_ometsuke レーンを構築する。
実行: python3 -m unittest discover -s tools/gpt_audit/tests
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import alo_gpt_audit as A  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_request(req_dir: Path, *, rid: str, gate: str, topic: str,
                 status: str = "queued", result_expected: str | None = None,
                 extra_fm: str = "") -> Path:
    ef = result_expected or f"{rid}_RESULT.md"
    fm = (
        "---\n"
        f"request_id: {rid}\n"
        f"topic: {topic}\n"
        f"gate: {gate}\n"
        f"status: {status}\n"
        f"result_expected_filename: {ef}\n"
        f"{extra_fm}"
        "---\n"
        f"# REQUEST {rid}\n\n本文。\n"
    )
    p = req_dir / f"{rid}_REQUEST.md"
    write(p, fm)
    return p


def make_result(from_dir: Path, *, rid: str, label: str, filename: str | None = None,
                body: str = "") -> Path:
    name = filename or f"{rid}_RESULT.md"
    text = f"{label}\n\nrequest_id: {rid}\n\n{body}\n"
    p = from_dir / name
    write(p, text)
    return p


class LaneFixture:
    """answered(PASS), answered(MODIFY), answered(NEED_MORE), missing, bad-label を持つ標準レーン。"""

    def __init__(self, root: Path):
        self.root = root
        self.to_gpt = root / "to_gpt"
        self.from_gpt = root / "from_gpt"
        self.to_gpt.mkdir(parents=True)
        self.from_gpt.mkdir(parents=True)

        # 1) answered PASS
        make_request(self.to_gpt, rid="20260607_alpha_v1_DDA", gate="DDA", topic="alpha")
        make_result(self.from_gpt, rid="20260607_alpha_v1_DDA", label="DDA_PASS")

        # 2) answered MODIFY_REQUIRED
        make_request(self.to_gpt, rid="20260607_beta_v1_DDB", gate="DDB", topic="beta")
        make_result(self.from_gpt, rid="20260607_beta_v1_DDB",
                    label="DDB_MODIFY_REQUIRED",
                    body="required_patches:\n  - fix X\n  - fix Y\n")

        # 3) answered NEED_MORE (material_absent)
        make_request(self.to_gpt, rid="20260607_gamma_v1_DDC", gate="DDC", topic="gamma")
        make_result(self.from_gpt, rid="20260607_gamma_v1_DDC",
                    label="DDC_NEED_MORE",
                    body="need_more_type: material_absent\n"
                         "missing_materials:\n  - file_a.md\n  - file_b.md\n")

        # 4) missing result (GPT 未回答)
        make_request(self.to_gpt, rid="20260607_delta_v1_DDD", gate="DDD", topic="delta")

        # 5) bad label result (移動しない)
        make_request(self.to_gpt, rid="20260607_eps_v1_DDE", gate="DDE", topic="eps")
        make_result(self.from_gpt, rid="20260607_eps_v1_DDE",
                    label="not a valid label line")

    def lane(self) -> A.Lane:
        return A.Lane(self.root)


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "gpt_ometsuke"
        self.fx = LaneFixture(self.root)
        self.lane = self.fx.lane()

    def tearDown(self):
        self.tmp.cleanup()

    def capture(self, fn, *a, **k):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = fn(*a, **k)
        return rc, buf.getvalue()


class Test1Status(BaseCase):
    """TEST-1: status が answered_not_processed を正しく数える。"""

    def test_counts(self):
        matches = self.lane.matches()
        counts = {}
        for m in matches:
            counts[m.lane_status] = counts.get(m.lane_status, 0) + 1
        self.assertEqual(counts.get("answered_not_processed"), 3)
        self.assertEqual(counts.get("missing_result"), 1)
        self.assertEqual(counts.get("bad_label"), 1)


class Test2DryRun(BaseCase):
    """TEST-2: dry-run は何も動かさない & NEED_MORE/MODIFY も対象。"""

    def test_dry_run_no_mutation(self):
        before = sorted(p.name for p in self.lane.to_gpt.iterdir())
        args = type("A", (), {"apply": False})()
        rc, out = self.capture(A.cmd_close_all, self.lane, args)
        after = sorted(p.name for p in self.lane.to_gpt.iterdir())
        self.assertEqual(before, after)              # ファイル移動なし
        self.assertFalse(self.lane.ledger_path.exists())  # 台帳作成なし
        self.assertIn("beta", out)                   # MODIFY も対象
        self.assertIn("gamma", out)                  # NEED_MORE も対象


class Test3Execute(BaseCase):
    """TEST-3: execute で REQUEST->processed, to_gpt直下 answered=0, RESULT残置。"""

    def test_execute(self):
        args = type("A", (), {"apply": True})()
        self.capture(A.cmd_close_all, self.lane, args)
        # answered 3 件が processed へ
        processed = sorted(p.name for p in self.lane.processed.iterdir())
        self.assertIn("20260607_alpha_v1_DDA_REQUEST.md", processed)
        self.assertIn("20260607_beta_v1_DDB_REQUEST.md", processed)
        self.assertIn("20260607_gamma_v1_DDC_REQUEST.md", processed)
        # to_gpt 直下に answered は残らない (missing/bad は残る)
        remaining = {m.lane_status for m in self.lane.matches()}
        self.assertNotIn("answered_not_processed", remaining)
        # RESULT は from_gpt に残置
        results = {r.filename for r in self.lane.results()}
        self.assertIn("20260607_alpha_v1_DDA_RESULT.md", results)
        # 台帳 3 件
        self.assertEqual(len([e for e in self.lane.read_ledger()
                              if e["event"] == "close"]), 3)


class Test4Idempotency(BaseCase):
    """TEST-4: 再実行で二重移動・二重台帳・二重カードが起きない。"""

    def test_rerun(self):
        args = type("A", (), {"apply": True})()
        self.capture(A.cmd_close_all, self.lane, args)
        ledger1 = self.lane.read_ledger()
        cards1 = sorted((self.root / "patch_queue").glob("*.md"))
        # 2 回目
        self.capture(A.cmd_close_all, self.lane, args)
        ledger2 = self.lane.read_ledger()
        cards2 = sorted((self.root / "patch_queue").glob("*.md"))
        close1 = [e for e in ledger1 if e["event"] == "close"]
        close2 = [e for e in ledger2 if e["event"] == "close"]
        self.assertEqual(len(close1), len(close2))   # 二重追記なし
        self.assertEqual(cards1, cards2)             # 二重カードなし


class Test5MissingResult(BaseCase):
    """TEST-5: RESULT 無し REQUEST は移動しない。"""

    def test_missing(self):
        args = type("A", (), {"apply": True})()
        self.capture(A.cmd_close_all, self.lane, args)
        # delta は from_gpt に RESULT なし -> to_gpt 直下に残る
        active = {r.filename for r in self.lane.active_requests()}
        self.assertIn("20260607_delta_v1_DDD_REQUEST.md", active)


class Test6BadLabel(BaseCase):
    """TEST-6: 先頭行が不正な RESULT は移動しない。"""

    def test_bad_label(self):
        args = type("A", (), {"apply": True})()
        self.capture(A.cmd_close_all, self.lane, args)
        active = {r.filename for r in self.lane.active_requests()}
        self.assertIn("20260607_eps_v1_DDE_REQUEST.md", active)
        # ledger に eps は載らない
        rids = {e["request_id"] for e in self.lane.read_ledger()}
        self.assertNotIn("20260607_eps_v1_DDE", rids)


class TestActionQueue(BaseCase):
    """task #4: action-queue に reflected:false が出る。"""

    def test_reflected_false(self):
        args = type("A", (), {"apply": True})()
        self.capture(A.cmd_close_all, self.lane, args)
        q = A.action_queue(self.lane)
        rids = {e["request_id"] for e in q}
        # 3 件すべて未反映として出る
        self.assertEqual(rids, {
            "20260607_alpha_v1_DDA",
            "20260607_beta_v1_DDB",
            "20260607_gamma_v1_DDC",
        })
        for e in q:
            self.assertFalse(e["reflected"])

    def test_reflect_removes_from_queue(self):
        args = type("A", (), {"apply": True})()
        self.capture(A.cmd_close_all, self.lane, args)
        ref_args = type("A", (), {"request_id": "20260607_alpha_v1_DDA",
                                  "apply": True})()
        self.capture(A.cmd_reflect, self.lane, ref_args)
        q = A.action_queue(self.lane)
        rids = {e["request_id"] for e in q}
        self.assertNotIn("20260607_alpha_v1_DDA", rids)


class TestClassification(BaseCase):
    """task #3: next_action_type 分類。"""

    def test_mapping(self):
        results = self.lane.results()
        by = {}
        for m in self.lane.matches():
            if m.result and m.result.verdict:
                rec = A.build_record(m, event="close")
                by[m.result.verdict] = rec["next_action_type"]
        self.assertEqual(by["PASS"], "ratify")
        self.assertEqual(by["MODIFY_REQUIRED"], "patch")
        self.assertEqual(by["NEED_MORE"], "required_materials")

    def test_pass_with_notes_blocking_downgrades_to_patch(self):
        # blocking_before_ratify があると ratify でなく patch
        make_request(self.lane.to_gpt, rid="20260607_zeta_v1_DDZ",
                     gate="DDZ", topic="zeta")
        make_result(self.lane.from_gpt, rid="20260607_zeta_v1_DDZ",
                    label="DDZ_PASS_WITH_NOTES",
                    body="blocking_before_ratify:\n  - must fix Z before ratify\n")
        m = [m for m in self.lane.matches()
             if m.request.request_id == "20260607_zeta_v1_DDZ"][0]
        rec = A.build_record(m, event="close")
        self.assertEqual(rec["next_action_type"], "patch")
        self.assertEqual(rec["blocking_before_ratify"], ["must fix Z before ratify"])


class TestApprovalSeparation(BaseCase):
    """task #6: 承認不要 / 承認必要 の分離。"""

    def test_owner_gated_not_executed(self):
        for op in A.OWNER_GATED_OPS:
            args = type("A", (), {"operation": op})()
            rc, out = self.capture(A.cmd_gate_check, self.lane, args)
            self.assertEqual(rc, 2)
            self.assertIn("承認必要", out)

    def test_approval_free(self):
        for op in A.APPROVAL_FREE_OPS:
            args = type("A", (), {"operation": op})()
            rc, out = self.capture(A.cmd_gate_check, self.lane, args)
            self.assertEqual(rc, 0)
            self.assertIn("承認不要", out)


class TestOwnerDigest(BaseCase):
    """task #5: Owner 5行サマリ 形式。"""

    def test_five_lines(self):
        m = [m for m in self.lane.matches()
             if m.request.request_id == "20260607_beta_v1_DDB"][0]
        rec = A.build_record(m, event="close")
        digest = rec["owner_digest_5line"]
        lines = digest.splitlines()
        self.assertEqual(len(lines), 5)
        self.assertTrue(lines[0].startswith("監査:"))
        self.assertTrue(lines[1].startswith("結論:"))
        self.assertTrue(lines[2].startswith("理由:"))
        self.assertTrue(lines[3].startswith("次アクション:"))
        self.assertTrue(lines[4].startswith("Owner確認:"))


class TestLedgerFields(BaseCase):
    """task #2: 台帳の必須項目がすべて存在する。"""

    REQUIRED = [
        "request_id", "request_filename", "result_filename", "result_label",
        "next_action_type", "reflected", "blocking_before_ratify",
        "missing_materials", "owner_digest_5line", "claude_rethink_prompt",
        "loop_state",
    ]

    def test_fields(self):
        m = [m for m in self.lane.matches()
             if m.request.request_id == "20260607_gamma_v1_DDC"][0]
        rec = A.build_record(m, event="close")
        for k in self.REQUIRED:
            self.assertIn(k, rec, f"台帳項目 {k} 欠落")
        self.assertEqual(rec["missing_materials"], ["file_a.md", "file_b.md"])
        self.assertEqual(rec["loop_state"], "returned")


class TestSupersededSkip(BaseCase):
    """request_status=superseded はレビューせずスキップ。"""

    def test_superseded(self):
        make_request(self.lane.to_gpt, rid="20260607_old_v1_DDO", gate="DDO",
                     topic="old", status="superseded")
        make_result(self.lane.from_gpt, rid="20260607_old_v1_DDO", label="DDO_PASS")
        m = [m for m in self.lane.matches()
             if m.request.request_id == "20260607_old_v1_DDO"][0]
        self.assertEqual(m.lane_status, "skipped")


class TestExpectedFilenameMatch(BaseCase):
    """result_expected_filename が RESULT 名と違っても照合できる (三点照合)。"""

    def test_alt_filename(self):
        make_request(self.lane.to_gpt, rid="20260607_eta_v1_DDH", gate="DDH",
                     topic="eta",
                     result_expected="20260607_eta_v1_DDH_CUSTOM_RESULT.md")
        make_result(self.lane.from_gpt, rid="20260607_eta_v1_DDH",
                    label="DDH_PASS",
                    filename="20260607_eta_v1_DDH_CUSTOM_RESULT.md")
        m = [m for m in self.lane.matches()
             if m.request.request_id == "20260607_eta_v1_DDH"][0]
        self.assertEqual(m.lane_status, "answered_not_processed")
        self.assertEqual(m.reason, "result_expected_filename")


if __name__ == "__main__":
    unittest.main(verbosity=2)
