from conftest import _write, build_queue

from alo_worker.queue import scan
from alo_worker.task import lint_task


def test_clean_task_has_no_errors(queue_root):
    q = scan(queue_root)
    for t in q.tasks:
        findings = lint_task(t)
        assert not [f for f in findings if f.level == "error"], t.filename


def test_missing_keys_flagged(tmp_path):
    root = build_queue(str(tmp_path / "wq"))
    # 必須キーを欠いた task
    _write(root + "/inbox/W-bad.md",
           "---\nworker_task_id: W-bad\nstatus: queued\n---\nno goal/paths/exit\n")
    q = scan(root)
    t = [x for x in q.tasks if x.filename == "W-bad.md"][0]
    codes = {f.code for f in lint_task(t) if f.level == "error"}
    assert "missing_key" in codes
    assert "no_allowed_paths" in codes


def test_bad_priority_is_error(tmp_path):
    root = build_queue(str(tmp_path / "wq"))
    _write(root + "/inbox/W-pri.md",
           "---\nworker_task_id: W-pri\nstatus: queued\npriority: URGENT\n"
           "goal: x\nallowed_paths:\n  - src/\nexit_criteria:\n  - done\n"
           "test_command: pytest\n---\n")
    q = scan(root)
    t = [x for x in q.tasks if x.filename == "W-pri.md"][0]
    codes = {f.code for f in lint_task(t) if f.level == "error"}
    assert "bad_priority" in codes


def test_id_filename_mismatch_warns(tmp_path):
    root = build_queue(str(tmp_path / "wq"))
    _write(root + "/inbox/wrongname.md",
           "---\nworker_task_id: W-xyz\nstatus: queued\npriority: P1\n"
           "goal: x\nallowed_paths:\n  - src/\nexit_criteria:\n  - done\n"
           "test_command: pytest\n---\n")
    q = scan(root)
    t = [x for x in q.tasks if x.filename == "wrongname.md"][0]
    codes = {f.code for f in lint_task(t) if f.level == "warn"}
    assert "id_filename_mismatch" in codes
