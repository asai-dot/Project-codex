"""owner-digest コマンド + 台帳 enrichment のテスト。"""

from alo_gpt_audit import ledger
from alo_gpt_audit.cli import main


def _close_all(root):
    main(["--root", root, "close-all", "--apply"])


def test_close_enriches_ledger(capsys, design_lane_root):
    _close_all(design_lane_root)
    capsys.readouterr()
    rows = ledger.load(design_lane_root)
    assert len(rows) == 4
    for r in rows:
        # enrichment フィールドが全行に存在
        assert r["event"] == "close"
        assert "ts" in r and r["ts"]
        assert "verdict" in r
        assert "loop_state" in r
        assert "owner_digest_5line" in r
        assert "claude_rethink_prompt" in r
        assert "queue" in r
        assert "approval_required_to_act" in r
        # 既存フィールドも保持
        assert "reflected" in r
        assert r["reflected"] is False
        assert "next_action_type" in r


def test_verdict_and_loop_state(capsys, design_lane_root):
    _close_all(design_lane_root)
    capsys.readouterr()
    by_id = {r["request_id"]: r for r in ledger.load(design_lane_root)}

    # MODIFY_REQUIRED -> patch / returned
    sr = by_id["20260605_statusregistry_v0.1_DDSTATUS"]
    assert sr["verdict"] == "MODIFY_REQUIRED"
    assert sr["next_action_type"] == "patch"
    assert sr["loop_state"] == "returned"
    assert sr["queue"] == "patch_queue"

    # PASS_WITH_NOTES + blocking -> ratify, returned (not ratify_wait)
    ch = by_id["20260605_claudehead_v1.1_DDCLAUDEHEAD"]
    assert ch["verdict"] == "PASS_WITH_NOTES"
    assert ch["next_action_type"] == "ratify"
    assert ch["loop_state"] == "returned"
    assert ch["approval_required_to_act"] is True


def test_owner_digest_default_vs_all(capsys, design_lane_root):
    _close_all(design_lane_root)
    capsys.readouterr()

    rc = main(["--root", design_lane_root, "owner-digest"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Owner 5行サマリ — 4 件" in out
    assert "結論: PASS_WITH_NOTES" in out

    # reflect 1 件 -> action_queue は 3 件、--all は 4 件のまま
    main(["--root", design_lane_root, "reflect",
          "20260605_statusregistry_v0.1_DDSTATUS", "--apply"])
    capsys.readouterr()

    rc = main(["--root", design_lane_root, "owner-digest"])
    assert rc == 0
    assert "Owner 5行サマリ — 3 件" in capsys.readouterr().out

    rc = main(["--root", design_lane_root, "owner-digest", "--all"])
    assert rc == 0
    assert "Owner 5行サマリ — 4 件" in capsys.readouterr().out
