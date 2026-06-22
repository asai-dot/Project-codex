"""reflect コマンド + ledger.action_queue / latest_state_per_request のテスト。"""

from alo_gpt_audit import ledger
from alo_gpt_audit.cli import main


def _close_all(root):
    main(["--root", root, "close-all", "--apply"])


def test_reflect_unknown_request(capsys, design_lane_root):
    _close_all(design_lane_root)
    capsys.readouterr()
    rc = main(["--root", design_lane_root, "reflect", "nope", "--apply"])
    assert rc == 1
    assert "ありません" in capsys.readouterr().out


def test_reflect_dry_run_does_not_write(capsys, design_lane_root):
    _close_all(design_lane_root)
    capsys.readouterr()
    before = len(ledger.load(design_lane_root))
    rc = main(["--root", design_lane_root, "reflect",
               "20260605_statusregistry_v0.1_DDSTATUS"])
    assert rc == 0
    assert "WOULD REFLECT" in capsys.readouterr().out
    assert len(ledger.load(design_lane_root)) == before


def test_reflect_apply_appends_event_and_state(capsys, design_lane_root):
    _close_all(design_lane_root)
    capsys.readouterr()
    rid = "20260605_statusregistry_v0.1_DDSTATUS"  # patch -> reflected
    before = len(ledger.load(design_lane_root))
    rc = main(["--root", design_lane_root, "reflect", rid, "--apply"])
    assert rc == 0
    rows = ledger.load(design_lane_root)
    assert len(rows) == before + 1
    last = rows[-1]
    assert last["event"] == "reflect"
    assert last["reflected"] is True
    assert last["loop_state"] == "reflected"
    # action_queue から外れる
    aq_ids = {e["request_id"] for e in ledger.action_queue(design_lane_root)}
    assert rid not in aq_ids
    # latest_state は reflect 行が後勝ち
    latest = ledger.latest_state_per_request(design_lane_root)[rid]
    assert latest["reflected"] is True


def test_reflect_reject_goes_closed(capsys, design_lane_root):
    """next_action が reject/none なら reflect で loop_state=closed。"""
    # FAIL の RESULT を足して 1 件 close する
    from conftest import write_request, write_result
    write_request(design_lane_root, "to_gpt",
                  "20260606_fail_v0.1_FX_REQUEST.md",
                  "20260606_fail_v0.1_FX", "FX")
    write_result(design_lane_root, "20260606_fail_v0.1_FX_RESULT.md",
                 "FX_FAIL", "20260606_fail_v0.1_FX")
    main(["--root", design_lane_root, "close", "20260606_fail_v0.1_FX"])
    capsys.readouterr()

    rc = main(["--root", design_lane_root, "reflect",
               "20260606_fail_v0.1_FX", "--apply"])
    assert rc == 0
    latest = ledger.latest_state_per_request(design_lane_root)["20260606_fail_v0.1_FX"]
    assert latest["next_action_type"] == "reject"
    assert latest["loop_state"] == "closed"


def test_reflect_idempotent(capsys, design_lane_root):
    _close_all(design_lane_root)
    capsys.readouterr()
    rid = "20260605_statusregistry_v0.1_DDSTATUS"
    main(["--root", design_lane_root, "reflect", rid, "--apply"])
    capsys.readouterr()
    before = len(ledger.load(design_lane_root))
    rc = main(["--root", design_lane_root, "reflect", rid, "--apply"])
    assert rc == 0
    assert "既に reflected" in capsys.readouterr().out
    assert len(ledger.load(design_lane_root)) == before
