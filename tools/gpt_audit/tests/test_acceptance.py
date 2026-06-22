"""検収テスト (Mac CC 実装の受け入れ) — 設計書 §13 の理想シナリオ。

TEST-1 status / TEST-2 dry-run / TEST-3 execute / TEST-4 idempotency /
TEST-5 missing-result / TEST-6 bad-label。特に idempotency が要。
"""

import json
import os

from alo_gpt_audit.cli import main
from conftest import write_request, write_result


def _to_gpt_requests(root):
    d = os.path.join(root, "to_gpt")
    return sorted(n for n in os.listdir(d) if n.endswith("_REQUEST.md"))


def _processed_requests(root):
    d = os.path.join(root, "to_gpt", "processed")
    if not os.path.isdir(d):
        return []
    return sorted(n for n in os.listdir(d) if n.endswith("_REQUEST.md"))


def _results(root):
    d = os.path.join(root, "from_gpt")
    return sorted(n for n in os.listdir(d) if n.endswith("_RESULT.md"))


def test_1_status_reports_four_answered(capsys, design_lane_root):
    main(["--root", design_lane_root, "status", "--json"])
    counts = json.loads(capsys.readouterr().out)["counts"]
    assert counts["active_requests"] == 4
    assert counts["results"] == 4
    assert counts["answered_not_processed"] == 4


def test_2_close_all_dry_run_moves_nothing(capsys, design_lane_root):
    rc = main(["--root", design_lane_root, "close-all"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "DRY-RUN" in out
    # 4 件すべて表示され、NEED_MORE / MODIFY_REQUIRED も退避対象
    assert out.count("- ") >= 4
    assert "DDCASESOURCE_NEED_MORE" in out
    assert "DDSTATUS_MODIFY_REQUIRED" in out
    # 何も動いていない
    assert len(_to_gpt_requests(design_lane_root)) == 4
    assert _processed_requests(design_lane_root) == []


def test_3_close_all_execute_moves_four(capsys, design_lane_root):
    rc = main(["--root", design_lane_root, "close-all", "--apply"])
    assert rc == 0
    # to_gpt 直下は 0、processed に 4、from_gpt RESULT は残る
    assert _to_gpt_requests(design_lane_root) == []
    assert len(_processed_requests(design_lane_root)) == 4
    assert len(_results(design_lane_root)) == 4
    # 台帳に 4 行、next_action_type が載っている
    from alo_gpt_audit import ledger

    rows = ledger.load(design_lane_root)
    assert len(rows) == 4
    assert all("next_action_type" in r for r in rows)


def test_4_idempotency_second_run_is_noop(capsys, design_lane_root):
    from alo_gpt_audit import ledger

    main(["--root", design_lane_root, "close-all", "--apply"])
    capsys.readouterr()
    rows_after_first = len(ledger.load(design_lane_root))
    processed_after_first = _processed_requests(design_lane_root)

    # 再実行: 何も移動せず、台帳も増えない (二重移動・二重追記なし)
    rc = main(["--root", design_lane_root, "close-all", "--apply"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "0 件" in out or "退避するものはありません" in out
    assert _processed_requests(design_lane_root) == processed_after_first
    assert len(ledger.load(design_lane_root)) == rows_after_first


def test_5_missing_result_is_not_moved(capsys, design_lane_root):
    # RESULT のないダミー REQUEST を追加
    write_request(
        design_lane_root, "to_gpt", "20260606_noresult_v0.1_GATE_REQUEST.md",
        "20260606_noresult_v0.1_GATE", "GATE",
    )
    main(["--root", design_lane_root, "close-all", "--apply"])
    capsys.readouterr()
    # answered 4 件は退避、noresult は to_gpt に残る
    remaining = _to_gpt_requests(design_lane_root)
    assert remaining == ["20260606_noresult_v0.1_GATE_REQUEST.md"]

    # 明示 close も拒否される
    rc = main(["--root", design_lane_root, "close", "20260606_noresult_v0.1_GATE"])
    assert rc == 2


def test_6_bad_label_is_not_moved(capsys, design_lane_root):
    write_request(
        design_lane_root, "to_gpt", "20260606_badlabel_v0.1_GBAD_REQUEST.md",
        "20260606_badlabel_v0.1_GBAD", "GBAD",
    )
    write_result(
        design_lane_root, "20260606_badlabel_v0.1_GBAD_RESULT.md",
        "NOT_A_VALID_LABEL", "20260606_badlabel_v0.1_GBAD",
    )
    rc = main(["--root", design_lane_root, "close", "20260606_badlabel_v0.1_GBAD"])
    assert rc == 2  # REFUSED invalid_label
    assert "20260606_badlabel_v0.1_GBAD_REQUEST.md" in _to_gpt_requests(design_lane_root)
