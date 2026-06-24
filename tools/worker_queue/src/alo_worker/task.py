"""worker task ファイルのモデルと検査ルール (pure, no side-effects)。

task は front-matter で「1目的 / 1許可範囲 / 1禁止リスト / 1テスト / 1RESULT」を固定する。
ここでは parse と lint (preflight) だけを行い、ファイル移動は queue.py が担う。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .frontmatter import Value, as_list, split_frontmatter

TASK_SUFFIX = ".md"
RESULT_SUFFIX = "_RESULT.md"

# RESULT 先頭行ラベル (§5)。done 行きと blocked 行きを分ける。
LABEL_PASS = {"WORKER_PASS", "WORKER_PASS_WITH_NOTES"}
LABEL_BLOCKED = {"WORKER_BLOCKED", "WORKER_FAIL"}
ALL_LABELS = LABEL_PASS | LABEL_BLOCKED

VALID_PRIORITIES = {"P0", "P1", "P2"}
VALID_STATUSES = {"queued", "hold", "blocked", "doing", "done"}

# 既定で禁止 (owner / GPT 承認なしには越えられない) 破壊的アクション。
# task が forbidden_actions を省略しても、この既定セットは常に効く。
DEFAULT_FORBIDDEN = {
    "production_db_write",
    "canonical_promotion",
    "edit_accepted_dir",
    "destructive_delete",
    "external_api_bulk_call",
    "schema_migration",
}

# lint が要求する front-matter キー (これが「逃げ道のない作業票」の最低条件)。
REQUIRED_KEYS = [
    "worker_task_id",
    "status",
    "priority",
    "goal",
    "allowed_paths",
    "exit_criteria",
]


@dataclass
class Task:
    path: str
    filename: str
    worker_task_id: Optional[str]
    status: str
    priority: Optional[str]
    owner: Optional[str]
    goal: Optional[str]
    mode: Optional[str]
    allowed_paths: List[str]
    forbidden_actions: List[str]
    test_command: Optional[str]
    exit_criteria: List[str]
    max_attempts: Optional[str]
    expected_result: str
    lane: str = ""              # inbox|doing|done|blocked (= 現在位置)
    lane_status: str = ""       # queued|held|in_progress|done|blocked|accident_*
    result_path: Optional[str] = None
    result_label: Optional[str] = None
    meta: Dict[str, Value] = field(default_factory=dict)

    @property
    def effective_forbidden(self) -> set:
        return set(self.forbidden_actions) | DEFAULT_FORBIDDEN


def default_result_name(task_filename: str) -> str:
    """``W-...md`` -> ``W-..._RESULT.md`` (result_expected 省略時のフォールバック)。"""
    if task_filename.endswith(RESULT_SUFFIX):
        return task_filename
    base = task_filename[: -len(TASK_SUFFIX)] if task_filename.endswith(TASK_SUFFIX) else task_filename
    return base + RESULT_SUFFIX


def is_task_file(filename: str) -> bool:
    return filename.endswith(TASK_SUFFIX) and not filename.endswith(RESULT_SUFFIX)


def is_result_file(filename: str) -> bool:
    return filename.endswith(RESULT_SUFFIX)


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def parse_task(path: str) -> Task:
    meta, _body = split_frontmatter(_read_text(path))
    filename = os.path.basename(path)
    expected = meta.get("result_expected_filename") or default_result_name(filename)
    if isinstance(expected, list):  # 念のため正規化
        expected = expected[0] if expected else default_result_name(filename)
    status = (meta.get("status") or "queued")
    if isinstance(status, list):
        status = status[0] if status else "queued"
    return Task(
        path=path,
        filename=filename,
        worker_task_id=_scalar(meta.get("worker_task_id")),
        status=str(status).strip(),
        priority=_scalar(meta.get("priority")),
        owner=_scalar(meta.get("owner")),
        goal=_scalar(meta.get("goal")),
        mode=_scalar(meta.get("mode")),
        allowed_paths=as_list(meta.get("allowed_paths")),
        forbidden_actions=as_list(meta.get("forbidden_actions")),
        test_command=_scalar(meta.get("test_command")),
        exit_criteria=as_list(meta.get("exit_criteria")),
        max_attempts=_scalar(meta.get("max_attempts")),
        expected_result=str(expected),
        meta=meta,
    )


def _scalar(value: Value) -> Optional[str]:
    if value is None or value == "":
        return None
    if isinstance(value, list):
        return value[0] if value else None
    return value


def first_label(result_path: str) -> str:
    """RESULT 先頭の非空行 (= ラベル単独行) を返す。"""
    with open(result_path, "r", encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if s:
                return s
    return ""


# --- lint (preflight) ------------------------------------------------------
@dataclass
class LintFinding:
    task_filename: str
    level: str          # error | warn
    code: str
    message: str


def lint_task(task: Task, root: Optional[str] = None) -> List[LintFinding]:
    """1 task の front-matter 健全性を検査する (advisory; error は CLI で exit 1)。"""
    out: List[LintFinding] = []

    def err(code: str, msg: str) -> None:
        out.append(LintFinding(task.filename, "error", code, msg))

    def warn(code: str, msg: str) -> None:
        out.append(LintFinding(task.filename, "warn", code, msg))

    for key in REQUIRED_KEYS:
        present = task.meta.get(key)
        if present is None or present == "" or present == []:
            err("missing_key", "必須キー '{}' が無い".format(key))

    if task.worker_task_id:
        stem = task.filename[: -len(TASK_SUFFIX)] if task.filename.endswith(TASK_SUFFIX) else task.filename
        if not stem.startswith(task.worker_task_id):
            warn("id_filename_mismatch",
                 "worker_task_id '{}' がファイル名 '{}' の接頭辞と一致しない".format(
                     task.worker_task_id, task.filename))

    if task.priority and task.priority not in VALID_PRIORITIES:
        err("bad_priority", "priority '{}' は {} のいずれかにする".format(
            task.priority, sorted(VALID_PRIORITIES)))

    if task.status and task.status not in VALID_STATUSES:
        warn("unknown_status", "status '{}' は想定外 ({})".format(
            task.status, sorted(VALID_STATUSES)))

    if not task.test_command and not task.exit_criteria:
        err("no_exit", "test_command も exit_criteria も無い — 完了条件が固定されていない")

    if not task.allowed_paths:
        err("no_allowed_paths", "allowed_paths が空 — 触ってよい範囲が未定義 (止まる原因)")

    # allowed_paths が実在するかは advisory (他リポジトリ向け task もあり得る)
    if root and task.allowed_paths:
        repo_root = _repo_root_of(root)
        for p in task.allowed_paths:
            if os.path.isabs(p):
                warn("abs_path", "allowed_paths に絶対パス '{}' — リポジトリ相対にする".format(p))
                continue
            if repo_root and not os.path.exists(os.path.join(repo_root, p)):
                warn("path_absent", "allowed_paths '{}' が現リポジトリに存在しない (別repo task?)".format(p))

    return out


def _repo_root_of(queue_root: str) -> Optional[str]:
    """queue root が ``<repo>/docs/worker_queue`` のとき repo root を返す (best-effort)。"""
    parent = os.path.dirname(os.path.dirname(os.path.abspath(queue_root)))
    return parent if os.path.isdir(parent) else None
