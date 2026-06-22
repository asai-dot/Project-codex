import os

import pytest

from alo_gpt_audit import ledger
from alo_gpt_audit.lane import (
    ANSWERED_NOT_PROCESSED,
    CloseError,
    close_request,
    scan,
)
from conftest import write_request, write_result


def test_scan_matches_real_box_state(lane_root):
    lane = scan(lane_root)
    counts = lane.counts()
    assert counts["active_requests"] == 6
    assert counts["results"] == 7
    assert counts["processed"] == 6
    # 唯一の真の answered_not_processed = quasijudicial
    assert counts["answered_not_processed"] == 1
    # 再投函済み (statusregistry v0.2 / legaldb v0.5.1) は active のまま
    assert counts["active"] == 5
    assert counts["blocked_active"] == 0
    assert counts["duplicate_in_processed"] == 0
    assert counts["processed_without_result"] == 0

    answered = lane.by_status(ANSWERED_NOT_PROCESSED)[0]
    assert answered.request_id == "20260605_quasijudicial_v0.4_DDCASESOURCE"
    assert answered.result_label == "DDCASESOURCE_NEED_MORE"


def test_close_moves_request_and_writes_ledger(lane_root):
    lane = scan(lane_root)
    result = close_request(lane, "20260605_quasijudicial_v0.4_DDCASESOURCE")
    assert result.action == "moved"
    assert result.result_label == "DDCASESOURCE_NEED_MORE"

    # 物理移動: to_gpt から消え、processed に出現
    assert not os.path.exists(
        os.path.join(lane_root, "to_gpt", "20260605_quasijudicial_v0.4_DDCASESOURCE_REQUEST.md")
    )
    assert os.path.exists(
        os.path.join(
            lane_root, "to_gpt", "processed",
            "20260605_quasijudicial_v0.4_DDCASESOURCE_REQUEST.md",
        )
    )

    # 再走査で answered_not_processed は 0、processed は 7 に
    after = scan(lane_root)
    assert after.counts()["answered_not_processed"] == 0
    assert after.counts()["processed"] == 7

    # 台帳追記
    ledger.append(lane_root, ledger.make_entry(result))
    rows = ledger.load(lane_root)
    assert rows[-1]["request_id"] == "20260605_quasijudicial_v0.4_DDCASESOURCE"
    assert rows[-1]["result_label"] == "DDCASESOURCE_NEED_MORE"
    assert rows[-1]["next_action"] == "資料補充 → 再投函"


def test_close_refuses_missing_result(lane_root):
    lane = scan(lane_root)
    with pytest.raises(CloseError) as exc:
        close_request(lane, "20260606_caselink_CASELINK")
    assert exc.value.code == "missing_result"


def test_close_refuses_invalid_label(lane_root):
    # gate と一致しないラベルの RESULT を持つ REQUEST を追加
    write_request(
        lane_root, "to_gpt",
        "20260606_badlabel_v0.1_GBAD_REQUEST.md",
        "20260606_badlabel_v0.1_GBAD", "GBAD",
    )
    write_result(
        lane_root, "20260606_badlabel_v0.1_GBAD_RESULT.md",
        "TOTALLY_WRONG_LABEL", "20260606_badlabel_v0.1_GBAD",
    )
    lane = scan(lane_root)
    with pytest.raises(CloseError) as exc:
        close_request(lane, "20260606_badlabel_v0.1_GBAD")
    assert exc.value.code == "invalid_label"

    # --force で通る
    lane = scan(lane_root)
    result = close_request(lane, "20260606_badlabel_v0.1_GBAD", force=True)
    assert result.action == "moved"


def test_close_refuses_request_id_mismatch(lane_root):
    write_request(
        lane_root, "to_gpt",
        "20260606_mism_v0.1_GMIS_REQUEST.md",
        "20260606_mism_v0.1_GMIS", "GMIS",
    )
    write_result(
        lane_root, "20260606_mism_v0.1_GMIS_RESULT.md",
        "GMIS_PASS", "SOMEONE_ELSE",
    )
    lane = scan(lane_root)
    with pytest.raises(CloseError) as exc:
        close_request(lane, "20260606_mism_v0.1_GMIS")
    assert exc.value.code == "request_id_mismatch"


def test_close_already_processed(lane_root):
    lane = scan(lane_root)
    with pytest.raises(CloseError) as exc:
        close_request(lane, "20260605_claudehead_v1.1_DDCLAUDEHEAD")
    assert exc.value.code == "already_processed"


def test_close_consolidates_duplicate(lane_root):
    # processed に同名同内容を先に置く -> close は consolidated になる
    lane = scan(lane_root)
    req = lane.by_status(ANSWERED_NOT_PROCESSED)[0]
    import shutil

    dst = os.path.join(lane_root, "to_gpt", "processed", req.filename)
    shutil.copyfile(req.path, dst)

    lane = scan(lane_root)
    # 同名が processed にあるので duplicate 判定
    assert lane.by_status("duplicate_in_processed")
    result = close_request(lane, req.request_id)
    assert result.action == "consolidated"
    assert not os.path.exists(req.path)
