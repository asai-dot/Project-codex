"""gate-check コマンドのテスト (承認要否)。"""

from alo_gpt_audit.cli import main


def test_approval_free_op_returns_0(capsys, lane_root):
    rc = main(["--root", lane_root, "gate-check", "status"])
    assert rc == 0
    assert "承認不要" in capsys.readouterr().out


def test_owner_gated_op_returns_2(capsys, lane_root):
    rc = main(["--root", lane_root, "gate-check", "production_db"])
    assert rc == 2
    assert "承認必要" in capsys.readouterr().out


def test_unknown_op_is_gated(capsys, lane_root):
    rc = main(["--root", lane_root, "gate-check", "frobnicate"])
    assert rc == 2
    assert "未知" in capsys.readouterr().out
