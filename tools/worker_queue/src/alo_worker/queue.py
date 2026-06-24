"""Worker Queue レーンの走査・分類・状態遷移 (side-effects は transition 系のみ)。

フォルダ構成 (root = ``docs/worker_queue/`` の実パス):

    <root>/inbox/      … queued task = まだ着手していない作業票 (W-*.md)
    <root>/doing/      … 1 件だけ着手中 (claim 済み)。中断はここに残る = 復旧対象
    <root>/done/       … 完了 task + WORKER_PASS 系 RESULT
    <root>/blocked/    … BLOCKED/FAIL で畳んだ task + RESULT

SoT は「フォルダ位置 + RESULT ラベル」。台帳 (registry) はそこから派生する控え。
台帳だけ更新してファイルを動かさない運用は禁止 (gpt_audit と同じ規律)。
"""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .task import (
    LABEL_BLOCKED,
    LABEL_PASS,
    Task,
    first_label,
    is_task_file,
    parse_task,
)

LANES = ("inbox", "doing", "done", "blocked")

# lane_status (= 三点照合の結果)
QUEUED = "queued"                       # inbox / status queued (正常な待ち)
HELD = "held"                           # inbox / status hold|blocked (着手保留)
IN_PROGRESS = "in_progress"             # doing にある = 着手中 or 中断 (復旧対象)
DONE = "done"                           # done にあり PASS 系 RESULT あり
BLOCKED = "blocked"                     # blocked にあり BLOCKED/FAIL RESULT あり
# accident 系: 自動処理せず人間/GPT 確認
TERMINAL_NO_RESULT = "terminal_without_result"   # done|blocked にあるのに RESULT 不在
TERMINAL_BAD_LABEL = "terminal_bad_label"        # RESULT ラベルがレーンと不整合


def lane_dirs(root: str) -> Dict[str, str]:
    return {lane: os.path.join(root, lane) for lane in LANES}


@dataclass
class Queue:
    root: str
    tasks: List[Task]

    def by_lane_status(self, lane_status: str) -> List[Task]:
        return [t for t in self.tasks if t.lane_status == lane_status]

    def by_lane(self, lane: str) -> List[Task]:
        return [t for t in self.tasks if t.lane == lane]

    def counts(self) -> Dict[str, int]:
        c = {k: 0 for k in (QUEUED, HELD, IN_PROGRESS, DONE, BLOCKED,
                            TERMINAL_NO_RESULT, TERMINAL_BAD_LABEL)}
        for t in self.tasks:
            c[t.lane_status] = c.get(t.lane_status, 0) + 1
        c["total"] = len(self.tasks)
        return c


# --- low-level -------------------------------------------------------------
def _list_task_paths(dirpath: str) -> List[str]:
    if not os.path.isdir(dirpath):
        return []
    out = []
    for name in sorted(os.listdir(dirpath)):
        full = os.path.join(dirpath, name)
        if is_task_file(name) and os.path.isfile(full):
            out.append(full)
    return out


def _result_path(root: str, lane: str, task: Task) -> str:
    return os.path.join(root, lane, task.expected_result)


def sha1_of(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --- scan / classify -------------------------------------------------------
def scan(root: str) -> Queue:
    dirs = lane_dirs(root)
    tasks: List[Task] = []
    for lane in LANES:
        for path in _list_task_paths(dirs[lane]):
            task = parse_task(path)
            task.lane = lane
            _classify(root, lane, task)
            tasks.append(task)
    return Queue(root, tasks)


def _classify(root: str, lane: str, task: Task) -> None:
    if lane == "inbox":
        task.lane_status = HELD if task.status in ("hold", "blocked") else QUEUED
        return
    if lane == "doing":
        task.lane_status = IN_PROGRESS
        return

    # done / blocked: RESULT 実体とラベルで三点照合する
    rpath = _result_path(root, lane, task)
    if not os.path.isfile(rpath):
        task.lane_status = TERMINAL_NO_RESULT
        return
    label = first_label(rpath)
    task.result_path = rpath
    task.result_label = label
    if lane == "done":
        task.lane_status = DONE if label in LABEL_PASS else TERMINAL_BAD_LABEL
    else:  # blocked
        task.lane_status = BLOCKED if label in LABEL_BLOCKED else TERMINAL_BAD_LABEL


def find_task(queue: Queue, ident: str) -> Optional[Task]:
    for t in queue.tasks:
        if t.worker_task_id == ident:
            return t
    for t in queue.tasks:
        if t.filename == ident or t.filename == ident + ".md":
            return t
    return None


# --- transitions -----------------------------------------------------------
class TransitionError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class TransitionResult:
    task: Task
    op: str                    # claim | complete | block
    src_lane: str
    dest_lane: str
    action: str                # moved | already | consolidated
    dest_path: str
    result_label: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


def _move_task(task: Task, src_lane: str, dest_lane: str, root: str,
               op: str, result_label: Optional[str], warnings: List[str]) -> TransitionResult:
    dirs = lane_dirs(root)
    os.makedirs(dirs[dest_lane], exist_ok=True)
    dest = os.path.join(dirs[dest_lane], task.filename)
    action = "moved"
    if os.path.exists(dest):
        if sha1_of(dest) == sha1_of(task.path):
            os.remove(task.path)   # 同内容の重複は集約 (削除でなく退避先へ寄せる)
            action = "consolidated"
        else:
            raise TransitionError(
                "dest_conflict",
                "{}/ に同名の異なる task が既存。要人間確認".format(dest_lane),
            )
    else:
        shutil.move(task.path, dest)
    return TransitionResult(task, op, src_lane, dest_lane, action, dest, result_label, warnings)


def claim(queue: Queue, ident: str) -> TransitionResult:
    """inbox の 1 件を doing へ移す (着手宣言)。status が hold/blocked のものは拒否。"""
    task = find_task(queue, ident)
    if task is None:
        raise TransitionError("not_found", "task '{}' が見つかりません".format(ident))
    if task.lane == "doing":
        return TransitionResult(task, "claim", "doing", "doing", "already",
                                task.path, warnings=["既に doing にあります (no-op)"])
    if task.lane in ("done", "blocked"):
        raise TransitionError("already_terminal",
                              "{} は既に {} で終了済みです".format(ident, task.lane))
    if task.lane_status == HELD:
        raise TransitionError("held",
                              "{} は status={} のため着手保留 (inbox に留め置き)".format(
                                  ident, task.status))
    return _move_task(task, "inbox", "doing", queue.root, "claim", None, [])


def _complete_or_block(queue: Queue, ident: str, dest_lane: str, op: str,
                       allowed_labels: set, force: bool) -> TransitionResult:
    task = find_task(queue, ident)
    if task is None:
        raise TransitionError("not_found", "task '{}' が見つかりません".format(ident))
    if task.lane == dest_lane:
        return TransitionResult(task, op, dest_lane, dest_lane, "already",
                                task.path, task.result_label,
                                ["既に {} です (no-op)".format(dest_lane)])
    if task.lane == "inbox":
        raise TransitionError("not_claimed",
                              "{} は未着手 (inbox)。先に claim してください".format(ident))
    other = "blocked" if dest_lane == "done" else "done"
    if task.lane == other:
        raise TransitionError("wrong_terminal",
                              "{} は既に {} で終了済みです".format(ident, other))

    rpath = _result_path(queue.root, dest_lane, task)
    if not os.path.isfile(rpath):
        raise TransitionError(
            "missing_result",
            "{}/{} が無い — RESULT を書いてから {} してください".format(
                dest_lane, task.expected_result, op),
        )
    label = first_label(rpath)
    warnings: List[str] = []
    if label not in allowed_labels and not force:
        raise TransitionError(
            "invalid_label",
            "RESULT 先頭行 '{}' が {} 行きラベル {} に含まれません (--force で強制可)".format(
                label, dest_lane, sorted(allowed_labels)),
        )
    if label not in allowed_labels:
        warnings.append("ラベル '{}' を --force で {} に通した".format(label, dest_lane))
    return _move_task(task, task.lane, dest_lane, queue.root, op, label, warnings)


def complete(queue: Queue, ident: str, force: bool = False) -> TransitionResult:
    """doing の 1 件を done へ畳む。done/<RESULT> が WORKER_PASS 系であること。"""
    return _complete_or_block(queue, ident, "done", "complete", LABEL_PASS, force)


def block(queue: Queue, ident: str, force: bool = False) -> TransitionResult:
    """doing の 1 件を blocked へ畳む。blocked/<RESULT> が WORKER_BLOCKED/FAIL であること。"""
    return _complete_or_block(queue, ident, "blocked", "block", LABEL_BLOCKED, force)
