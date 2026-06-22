"""health コマンドのテスト。"""

import json

from alo_gpt_audit.cli import main


def test_health_text(capsys, design_lane_root):
    rc = main(["--root", design_lane_root, "health"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "監査レーン health report" in out
    assert "to_gpt 直下 active REQUEST: 4" in out
    assert "from_gpt RESULT 総数: 4" in out
    # 未反映 action item が無い (台帳がまだ空) -> GREEN
    assert "health: GREEN" in out


def test_health_json_after_close(capsys, design_lane_root):
    main(["--root", design_lane_root, "close-all", "--apply"])
    capsys.readouterr()
    rc = main(["--root", design_lane_root, "health", "--json"])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["processed_requests"] == 4
    assert report["results_total"] == 4
    assert report["active_requests"] == 0
    assert report["ledger_events"] == 4
    assert report["unreflected_action_items"] == 4
    # next_action 内訳: patch x2, required_materials x1, ratify x1
    assert report["action_queue_by_type"]["patch"] == 2
    assert report["action_queue_by_type"]["required_materials"] == 1
    assert report["action_queue_by_type"]["ratify"] == 1
    assert set(report["route_queue_sizes"]) == {
        "approval_queue", "patch_queue", "material_queue", "rejected_queue"}
    assert report["inplace_processed_pending_relocate"] == 0


def test_health_yellow_when_unreflected(capsys, design_lane_root):
    main(["--root", design_lane_root, "close-all", "--apply"])
    capsys.readouterr()
    rc = main(["--root", design_lane_root, "health"])
    assert rc == 0
    assert "health: YELLOW" in capsys.readouterr().out
