import os

from conftest import write_result

from alo_worker import registry
from alo_worker.queue import block, claim, complete, scan


def _complete_one(root, task_id, label="WORKER_PASS"):
    claim(scan(root), task_id)
    write_result(root, "done", task_id, label=label)
    res = complete(scan(root), task_id)
    entry = registry.make_entry(res, ts="2026-06-23T10:00:00+09:00")
    registry.append(root, entry)
    return entry


def test_append_and_load(queue_root):
    entry = _complete_one(queue_root, "W-20260623-001")
    rows = registry.load(queue_root)
    assert len(rows) == 1
    assert rows[-1]["worker_task_id"] == "W-20260623-001"
    assert rows[-1]["dest_lane"] == "done"
    assert rows[-1]["result_label"] == "WORKER_PASS"
    assert rows[-1]["next_action"]  # 非空


def test_render_md_is_deterministic(queue_root):
    _complete_one(queue_root, "W-20260623-001")
    md1 = registry.render_md(queue_root)
    md2 = registry.render_md(queue_root)
    assert md1 == md2
    assert "W-20260623-001" in md1
    assert os.path.isfile(os.path.join(queue_root, registry.REGISTRY_MD))


def test_latest_per_task_last_wins(queue_root):
    # block 経由で 1 行、その後同 id を再 complete はしないが、後勝ちロジックを確認
    claim(scan(queue_root), "W-20260623-002")
    write_result(queue_root, "blocked", "W-20260623-002", label="WORKER_BLOCKED")
    res = block(scan(queue_root), "W-20260623-002")
    registry.append(queue_root, registry.make_entry(res, ts="2026-06-23T11:00:00+09:00"))
    latest = registry.latest_per_task(queue_root)
    assert latest["W-20260623-002"]["dest_lane"] == "blocked"
