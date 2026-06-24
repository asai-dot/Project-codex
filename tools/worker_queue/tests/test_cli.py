import json
import os

from conftest import write_result, write_task

from alo_worker import registry
from alo_worker.cli import main


def run(root, *argv):
    return main(["--root", root, *argv])


def test_status_json(queue_root, capsys):
    rc = run(queue_root, "status", "--json")
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"]["total"] == 3
    assert payload["counts"]["queued"] == 2


def test_next_picks_p0(queue_root, capsys):
    rc = run(queue_root, "next")
    assert rc == 0
    out = capsys.readouterr().out
    assert "W-20260623-001" in out          # P0 が先頭


def test_next_blocks_when_wip(queue_root, capsys):
    run(queue_root, "claim", "W-20260623-001")
    capsys.readouterr()
    rc = run(queue_root, "next")
    assert rc == 2                            # doing に着手中 -> 先に畳め
    assert "着手中" in capsys.readouterr().out


def test_lint_clean(queue_root):
    assert run(queue_root, "lint") == 0


def test_claim_then_complete_writes_ledger(queue_root, capsys):
    assert run(queue_root, "claim", "W-20260623-001") == 0
    write_result(queue_root, "done", "W-20260623-001", label="WORKER_PASS")
    capsys.readouterr()
    assert run(queue_root, "complete", "W-20260623-001") == 0
    out = capsys.readouterr().out
    assert "台帳追記" in out
    rows = registry.load(queue_root)
    assert rows[-1]["worker_task_id"] == "W-20260623-001"
    assert os.path.isfile(os.path.join(queue_root, registry.REGISTRY_MD))


def test_complete_missing_result_returns_2(queue_root, capsys):
    run(queue_root, "claim", "W-20260623-002")
    capsys.readouterr()
    rc = run(queue_root, "complete", "W-20260623-002")
    assert rc == 2
    assert "missing_result" in capsys.readouterr().err


def test_recover_clean(queue_root, capsys):
    rc = run(queue_root, "recover")
    assert rc == 0
    assert "クリーン" in capsys.readouterr().out


def test_recover_suggests_complete(queue_root, capsys):
    run(queue_root, "claim", "W-20260623-001")
    write_result(queue_root, "done", "W-20260623-001", label="WORKER_PASS")
    capsys.readouterr()
    rc = run(queue_root, "recover")
    assert rc == 0
    out = capsys.readouterr().out
    assert "complete" in out                  # done RESULT あり -> complete を提案


def test_recover_flags_accident(queue_root, capsys):
    write_task(queue_root, "done", "W-20260623-009")   # RESULT 無し
    rc = run(queue_root, "recover")
    assert rc == 1
    assert "accident" in capsys.readouterr().out


def test_registry_build(queue_root, capsys):
    run(queue_root, "claim", "W-20260623-001")
    write_result(queue_root, "done", "W-20260623-001", label="WORKER_PASS")
    run(queue_root, "complete", "W-20260623-001")
    capsys.readouterr()
    assert run(queue_root, "registry", "build") == 0
    assert "台帳再生成" in capsys.readouterr().out
