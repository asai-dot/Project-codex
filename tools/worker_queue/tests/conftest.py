"""Worker Queue テスト用フィクスチャ (合成データ・実 Box 不要)。

inbox に P0/P1/P2 の task を 3 件置いた最小キューを組む。各テストは tmp_path 上で
claim/complete/block を実行して「フォルダ位置=状態」が守られるか確かめる。
"""

import os

import pytest

LANES = ("inbox", "doing", "done", "blocked")


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_task(root, lane, task_id, priority="P0", status="queued",
               goal="failing test を green にする",
               allowed_paths=("src/", "tests/", "docs/worker_queue/"),
               forbidden=("schema_migration", "destructive_delete"),
               test_command="pytest -q",
               exit_criteria=("pytest -q exits 0", "WORKER_RESULT written"),
               extra_keys=None, body="# Task\n最小差分で直す。\n"):
    filename = "{}.md".format(task_id)
    fm = ["---",
          "worker_task_id: {}".format(task_id),
          "status: {}".format(status),
          "priority: {}".format(priority),
          "owner: claude-code-worker",
          "goal: {}".format(goal),
          "mode: implementation"]
    fm.append("allowed_paths:")
    for p in allowed_paths:
        fm.append("  - {}".format(p))
    fm.append("forbidden_actions:")
    for f in forbidden:
        fm.append("  - {}".format(f))
    if test_command:
        fm.append("test_command: {}".format(test_command))
    fm.append("exit_criteria:")
    for c in exit_criteria:
        fm.append("  - {}".format(c))
    fm.append("max_attempts: 2")
    fm.append("result_expected_filename: {}_RESULT.md".format(task_id))
    if extra_keys:
        for k, v in extra_keys.items():
            fm.append("{}: {}".format(k, v))
    fm.append("---")
    fm.append("")
    fm.append(body)
    _write(os.path.join(root, lane, filename), "\n".join(fm) + "\n")
    return filename


def write_result(root, lane, task_id, label="WORKER_PASS",
                 body="## Summary\ngreen.\n"):
    text = "{}\n# Worker Result\nworker_task_id: {}\nlabel: {}\n\n{}".format(
        label, task_id, label, body)
    _write(os.path.join(root, lane, "{}_RESULT.md".format(task_id)), text)


def build_queue(root):
    for lane in LANES:
        os.makedirs(os.path.join(root, lane), exist_ok=True)
    write_task(root, "inbox", "W-20260623-001", priority="P0")
    write_task(root, "inbox", "W-20260623-002", priority="P1")
    write_task(root, "inbox", "W-20260623-003", priority="P2", status="hold")
    return root


@pytest.fixture
def queue_root(tmp_path):
    return build_queue(str(tmp_path / "worker_queue"))
