import json
import os

from alo_gpt_audit.cli import main


def test_status_text(capsys, lane_root):
    rc = main(["--root", lane_root, "status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "answered_not_processed: 1" in out
    assert "20260605_quasijudicial_v0.4_DDCASESOURCE_REQUEST.md" in out


def test_status_json(capsys, lane_root):
    rc = main(["--root", lane_root, "status", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"]["answered_not_processed"] == 1
    assert payload["counts"]["active"] == 5


def test_close_all_dry_run_then_apply(capsys, lane_root):
    # dry-run: 何も動かさない
    rc = main(["--root", lane_root, "close-all"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "20260605_quasijudicial_v0.4_DDCASESOURCE_REQUEST.md" in out
    assert os.path.exists(
        os.path.join(lane_root, "to_gpt", "20260605_quasijudicial_v0.4_DDCASESOURCE_REQUEST.md")
    )

    # apply: 退避され、台帳が生成される
    rc = main(["--root", lane_root, "close-all", "--apply"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "CLOSED" in out
    assert os.path.exists(os.path.join(lane_root, "_AUDIT_LEDGER.jsonl"))
    assert os.path.exists(os.path.join(lane_root, "_AUDIT_LEDGER.md"))

    # active queue の answered_not_processed はゼロに
    rc = main(["--root", lane_root, "status", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"]["answered_not_processed"] == 0


def test_root_from_env(capsys, lane_root, monkeypatch):
    monkeypatch.setenv("ALO_GPT_OMETSUKE_ROOT", lane_root)
    rc = main(["status"])
    assert rc == 0
    assert "answered_not_processed: 1" in capsys.readouterr().out


def test_close_single_request_id(capsys, lane_root):
    rc = main(["--root", lane_root, "close", "20260605_quasijudicial_v0.4_DDCASESOURCE"])
    assert rc == 0
    assert "CLOSED" in capsys.readouterr().out
