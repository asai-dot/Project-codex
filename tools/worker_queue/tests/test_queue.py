import os

import pytest
from conftest import write_result, write_task

from alo_worker import registry
from alo_worker.queue import (
    BLOCKED,
    DONE,
    HELD,
    IN_PROGRESS,
    QUEUED,
    TERMINAL_BAD_LABEL,
    TERMINAL_NO_RESULT,
    TransitionError,
    block,
    claim,
    complete,
    find_task,
    scan,
)


def test_scan_classifies_inbox(queue_root):
    q = scan(queue_root)
    c = q.counts()
    assert c["total"] == 3
    assert c[QUEUED] == 2          # P0, P1
    assert c[HELD] == 1            # P2 status=hold
    assert c[IN_PROGRESS] == 0


def test_claim_moves_inbox_to_doing(queue_root):
    q = scan(queue_root)
    res = claim(q, "W-20260623-001")
    assert res.action == "moved"
    assert res.dest_lane == "doing"
    assert not os.path.exists(os.path.join(queue_root, "inbox", "W-20260623-001.md"))
    assert os.path.exists(os.path.join(queue_root, "doing", "W-20260623-001.md"))
    assert scan(queue_root).counts()[IN_PROGRESS] == 1


def test_claim_held_is_refused(queue_root):
    q = scan(queue_root)
    with pytest.raises(TransitionError) as e:
        claim(q, "W-20260623-003")
    assert e.value.code == "held"


def test_claim_idempotent(queue_root):
    claim(scan(queue_root), "W-20260623-001")
    res = claim(scan(queue_root), "W-20260623-001")
    assert res.action == "already"


def test_complete_requires_pass_result(queue_root):
    claim(scan(queue_root), "W-20260623-001")
    # RESULT 未作成 -> missing_result
    with pytest.raises(TransitionError) as e:
        complete(scan(queue_root), "W-20260623-001")
    assert e.value.code == "missing_result"

    # 誤ラベル (BLOCKED を done に) -> invalid_label
    write_result(queue_root, "done", "W-20260623-001", label="WORKER_BLOCKED")
    with pytest.raises(TransitionError) as e:
        complete(scan(queue_root), "W-20260623-001")
    assert e.value.code == "invalid_label"


def test_complete_happy_path(queue_root):
    claim(scan(queue_root), "W-20260623-001")
    write_result(queue_root, "done", "W-20260623-001", label="WORKER_PASS")
    res = complete(scan(queue_root), "W-20260623-001")
    assert res.dest_lane == "done"
    assert res.result_label == "WORKER_PASS"
    after = scan(queue_root)
    assert after.counts()[DONE] == 1
    assert after.counts()[IN_PROGRESS] == 0
    t = find_task(after, "W-20260623-001")
    assert t.lane_status == DONE


def test_block_requires_blocked_label(queue_root):
    claim(scan(queue_root), "W-20260623-002")
    write_result(queue_root, "blocked", "W-20260623-002", label="WORKER_PASS")
    with pytest.raises(TransitionError) as e:
        block(scan(queue_root), "W-20260623-002")
    assert e.value.code == "invalid_label"

    write_result(queue_root, "blocked", "W-20260623-002", label="WORKER_BLOCKED")
    res = block(scan(queue_root), "W-20260623-002")
    assert res.dest_lane == "blocked"
    assert scan(queue_root).counts()[BLOCKED] == 1


def test_complete_from_inbox_refused(queue_root):
    with pytest.raises(TransitionError) as e:
        complete(scan(queue_root), "W-20260623-001")
    assert e.value.code == "not_claimed"


def test_terminal_without_result_is_accident(queue_root):
    # done に task だけ置く (RESULT 無し) -> accident
    write_task(queue_root, "done", "W-20260623-009")
    q = scan(queue_root)
    t = find_task(q, "W-20260623-009")
    assert t.lane_status == TERMINAL_NO_RESULT


def test_complete_idempotent_after_done(queue_root):
    claim(scan(queue_root), "W-20260623-001")
    write_result(queue_root, "done", "W-20260623-001", label="WORKER_PASS")
    complete(scan(queue_root), "W-20260623-001")
    res = complete(scan(queue_root), "W-20260623-001")
    assert res.action == "already"


def test_wrong_terminal_guard(queue_root):
    # done 済みの task を block しようとする -> wrong_terminal
    claim(scan(queue_root), "W-20260623-001")
    write_result(queue_root, "done", "W-20260623-001", label="WORKER_PASS")
    complete(scan(queue_root), "W-20260623-001")
    with pytest.raises(TransitionError) as e:
        block(scan(queue_root), "W-20260623-001")
    assert e.value.code == "wrong_terminal"


def test_force_overrides_bad_label(queue_root):
    claim(scan(queue_root), "W-20260623-001")
    write_result(queue_root, "done", "W-20260623-001", label="WORKER_BLOCKED")
    res = complete(scan(queue_root), "W-20260623-001", force=True)
    assert res.dest_lane == "done"
    assert res.warnings
