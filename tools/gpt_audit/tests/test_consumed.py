"""consumed モジュール + コマンドのテスト。"""

import os

import pytest

from alo_gpt_audit import consumed
from alo_gpt_audit.cli import main


def _close_all(root):
    main(["--root", root, "close-all", "--apply"])


def test_consumption_state():
    assert consumed.consumption_state({"reflected": False}) == "未反映"
    assert consumed.consumption_state(
        {"reflected": False, "loop_state": "ratify_wait"}) == "ratify待ち"
    assert consumed.consumption_state(
        {"reflected": True, "loop_state": "requeued"}) == "反映済(後続へ)"
    assert consumed.consumption_state(
        {"reflected": True, "loop_state": "closed"}) == "closed"
    assert consumed.consumption_state(
        {"reflected": True, "loop_state": "reflected"}) == "反映済"


def test_load_ledger_skips_comments_and_blank(tmp_path):
    p = tmp_path / "led.jsonl"
    p.write_text(
        '\n'
        '{"_comment": "header"}\n'
        '{"request_id": "r1", "next_action_type": "patch"}\n'
        '\n',
        encoding="utf-8",
    )
    rows = consumed.load_ledger(str(p))
    assert len(rows) == 1
    assert rows[0]["request_id"] == "r1"


def test_load_ledger_requires_request_id(tmp_path):
    p = tmp_path / "led.jsonl"
    p.write_text('{"next_action_type": "patch"}\n', encoding="utf-8")
    with pytest.raises(ValueError):
        consumed.load_ledger(str(p))


def test_render_escapes_pipe_and_newline():
    rows = [{
        "request_id": "r|1",
        "result_label": "G_PASS",
        "next_action_type": "ratify",
        "owner_digest_5line": "line1\nline2",
        "claude_rethink_prompt": "do | this",
    }]
    md = consumed.render(rows, "src.jsonl", generated_at="FIXED")
    assert "r\\|1" in md
    assert "line1 line2" in md
    assert "do \\| this" in md
    # generated_at が反映される
    assert "- generated_at: FIXED" in md


def test_build_writes_consumed_at_lane_root(capsys, design_lane_root):
    _close_all(design_lane_root)
    capsys.readouterr()
    rc = main(["--root", design_lane_root, "consumed", "build",
               "--generated-at", "FIXED"])
    assert rc == 0
    out_path = os.path.join(design_lane_root, "CONSUMED.md")
    assert os.path.isfile(out_path)
    text = open(out_path, encoding="utf-8").read()
    assert "CONSUMED — 監査結果の消化ビュー" in text
    assert "20260605_statusregistry_v0.1_DDSTATUS" in text
    # default ledger path = <root>/_AUDIT_LEDGER.jsonl
    assert os.path.join(design_lane_root, "_AUDIT_LEDGER.jsonl") in text


def test_check_detects_drift(capsys, design_lane_root):
    _close_all(design_lane_root)
    capsys.readouterr()
    main(["--root", design_lane_root, "consumed", "build", "--generated-at", "X"])
    capsys.readouterr()

    # generated_at が違っても check は一致 (その行は無視)
    rc = main(["--root", design_lane_root, "consumed", "check",
               "--generated-at", "Y"])
    assert rc == 0
    assert "ドリフトなし" in capsys.readouterr().out

    # reflect で内容が変われば drift
    main(["--root", design_lane_root, "reflect",
          "20260605_statusregistry_v0.1_DDSTATUS", "--apply"])
    capsys.readouterr()
    rc = main(["--root", design_lane_root, "consumed", "check",
               "--generated-at", "Y"])
    assert rc == 1
    assert "ドリフト" in capsys.readouterr().out


def test_check_missing_file_is_drift(capsys, design_lane_root):
    _close_all(design_lane_root)
    capsys.readouterr()
    rc = main(["--root", design_lane_root, "consumed", "check"])
    assert rc == 1
