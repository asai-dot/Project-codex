"""監査レーンの走査・分類・close 処理 (pure core, side-effects は close_request のみ)。

フォルダ構成 (root = Box folder ``gpt_ometsuke/`` を Box Drive で同期した実パス):

    <root>/to_gpt/              … ACTIVE REQUEST = 未回答 (*_REQUEST.md)
    <root>/to_gpt/processed/    … 退避済み REQUEST の控え
    <root>/from_gpt/            … RESULT 正本アーカイブ (*_RESULT.md)
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .frontmatter import split_frontmatter

REQUEST_SUFFIX = "_REQUEST.md"
RESULT_SUFFIX = "_RESULT.md"

# allowed_labels は front-matter に列挙されないことが多いので gate から導出する。
LABEL_SUFFIXES = ("PASS", "PASS_WITH_NOTES", "MODIFY_REQUIRED", "FAIL", "NEED_MORE")

# --- lane status -----------------------------------------------------------
ACTIVE = "active"                                      # queued, GPT 未回答 (正常な待ち)
BLOCKED_ACTIVE = "blocked_active"                      # blocked/superseded/cancelled で待ち
ANSWERED_NOT_PROCESSED = "answered_not_processed"      # RESULT あり / 未退避 → close 対象
DUPLICATE = "duplicate_in_processed"                   # to_gpt と processed の両方に存在
PROCESSED_WITHOUT_RESULT = "processed_without_result"  # 事故: 退避済なのに RESULT 不在

_REQUEST_ID_RE = re.compile(r"^\s*request_id:\s*(\S+)", re.MULTILINE)


def lane_dirs(root: str) -> Dict[str, str]:
    return {
        "to_gpt": os.path.join(root, "to_gpt"),
        "from_gpt": os.path.join(root, "from_gpt"),
        "processed": os.path.join(root, "to_gpt", "processed"),
    }


def default_result_name(request_filename: str) -> str:
    """``*_REQUEST.md`` -> ``*_RESULT.md`` (front-matter 欠落時のフォールバック)。"""
    if request_filename.endswith(REQUEST_SUFFIX):
        return request_filename[: -len(REQUEST_SUFFIX)] + RESULT_SUFFIX
    return request_filename


@dataclass
class Request:
    path: str
    filename: str
    request_id: Optional[str]
    gate: Optional[str]
    topic: Optional[str]
    status: str                       # queued|blocked|superseded|cancelled
    expected_result: str              # result_expected_filename (front-matter 正本)
    supersedes: Optional[str]
    lane_status: str = ""
    result_path: Optional[str] = None
    result_label: Optional[str] = None

    @property
    def allowed_labels(self) -> set:
        if not self.gate:
            return set()
        return {"{}_{}".format(self.gate, s) for s in LABEL_SUFFIXES}


@dataclass
class Lane:
    root: str
    requests: List[Request]
    result_names: set
    processed_by_name: Dict[str, str]
    processed_by_reqid: Dict[str, str]

    def by_status(self, status: str) -> List[Request]:
        return [r for r in self.requests if r.lane_status == status]

    def counts(self) -> Dict[str, int]:
        c = {
            "active": 0,
            "blocked_active": 0,
            "answered_not_processed": 0,
            "duplicate_in_processed": 0,
            "processed_without_result": 0,
        }
        for r in self.requests:
            c[r.lane_status] = c.get(r.lane_status, 0) + 1
        c["active_requests"] = len(self.requests)
        c["processed"] = len(self.processed_by_name)
        c["results"] = len(self.result_names)
        return c


# --- low-level file helpers ------------------------------------------------
def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def parse_request(path: str) -> Request:
    meta, _body = split_frontmatter(_read_text(path))
    filename = os.path.basename(path)
    expected = meta.get("result_expected_filename") or default_result_name(filename)
    return Request(
        path=path,
        filename=filename,
        request_id=meta.get("request_id"),
        gate=meta.get("gate"),
        topic=meta.get("topic"),
        status=(meta.get("status") or "queued").strip(),
        expected_result=expected,
        supersedes=meta.get("supersedes"),
    )


def first_label(result_path: str) -> str:
    """RESULT 先頭の非空行 (= ラベル単独行) を返す。"""
    with open(result_path, "r", encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if s:
                return s
    return ""


def result_body_request_id(result_path: str) -> Optional[str]:
    m = _REQUEST_ID_RE.search(_read_text(result_path))
    return m.group(1) if m else None


def sha1_of(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _list_request_paths(dirpath: str) -> List[str]:
    if not os.path.isdir(dirpath):
        return []
    out = []
    for name in sorted(os.listdir(dirpath)):
        full = os.path.join(dirpath, name)
        if name.endswith(REQUEST_SUFFIX) and os.path.isfile(full):
            out.append(full)
    return out


def _list_result_names(dirpath: str) -> set:
    if not os.path.isdir(dirpath):
        return set()
    return {
        n
        for n in os.listdir(dirpath)
        if n.endswith(RESULT_SUFFIX) and os.path.isfile(os.path.join(dirpath, n))
    }


# --- scan / classify -------------------------------------------------------
def scan(root: str) -> Lane:
    dirs = lane_dirs(root)
    result_names = _list_result_names(dirs["from_gpt"])

    processed_paths = _list_request_paths(dirs["processed"])
    processed_by_name = {os.path.basename(p): p for p in processed_paths}
    processed_by_reqid: Dict[str, str] = {}
    for p in processed_paths:
        rid = parse_request(p).request_id
        if rid:
            processed_by_reqid[rid] = p

    requests: List[Request] = []
    for path in _list_request_paths(dirs["to_gpt"]):
        req = parse_request(path)
        has_result = req.expected_result in result_names
        in_processed = req.filename in processed_by_name or (
            bool(req.request_id) and req.request_id in processed_by_reqid
        )
        if has_result:
            req.result_path = os.path.join(dirs["from_gpt"], req.expected_result)
            req.result_label = first_label(req.result_path)
        req.lane_status = _classify(req.status, has_result, in_processed)
        requests.append(req)

    return Lane(root, requests, result_names, processed_by_name, processed_by_reqid)


def _classify(status: str, has_result: bool, in_processed: bool) -> str:
    # §6 三点照合: A(=to_gpt直下にある, 自明) / B(=RESULTあり) / C(=processedにある)
    if has_result and in_processed:
        return DUPLICATE
    if has_result and not in_processed:
        return ANSWERED_NOT_PROCESSED
    if not has_result and in_processed:
        return PROCESSED_WITHOUT_RESULT
    if status in ("blocked", "superseded", "cancelled"):
        return BLOCKED_ACTIVE
    return ACTIVE


# --- close -----------------------------------------------------------------
class CloseError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class CloseResult:
    request: Request
    result_filename: str
    result_label: str
    action: str          # moved | consolidated | moved_overwrite
    dest_path: str
    warnings: List[str] = field(default_factory=list)


def find_request(lane: Lane, ident: str) -> Optional[Request]:
    for r in lane.requests:
        if r.request_id == ident:
            return r
    for r in lane.requests:
        if r.filename == ident or r.filename == ident + REQUEST_SUFFIX:
            return r
    return None


def close_request(lane: Lane, ident: str, force: bool = False) -> CloseResult:
    """1件の REQUEST を検証して processed/ へ退避する (実ファイル移動)。"""
    req = find_request(lane, ident)
    if req is None:
        if (
            ident in lane.processed_by_reqid
            or ident in lane.processed_by_name
            or (ident + REQUEST_SUFFIX) in lane.processed_by_name
        ):
            raise CloseError("already_processed", "{} は既に processed 退避済みです".format(ident))
        raise CloseError("not_found", "to_gpt/ 直下に {} の REQUEST が見つかりません".format(ident))

    if req.lane_status == PROCESSED_WITHOUT_RESULT:
        raise CloseError(
            "processed_without_result",
            "{}: processed 済なのに RESULT 不在。自動処理せず人間確認が必要です".format(req.request_id),
        )

    dirs = lane_dirs(lane.root)
    result_path = os.path.join(dirs["from_gpt"], req.expected_result)
    if not os.path.isfile(result_path):
        raise CloseError(
            "missing_result",
            "{}: from_gpt/{} が存在しません (未回答)".format(req.request_id, req.expected_result),
        )

    label = first_label(result_path)
    if req.allowed_labels and label not in req.allowed_labels and not force:
        raise CloseError(
            "invalid_label",
            "{}: RESULT 先頭行 '{}' が allowed_labels {} に含まれません (--force で強制可)".format(
                req.request_id, label, sorted(req.allowed_labels)
            ),
        )

    warnings: List[str] = []
    body_reqid = result_body_request_id(result_path)
    if body_reqid and req.request_id and body_reqid != req.request_id:
        raise CloseError(
            "request_id_mismatch",
            "RESULT 本文の request_id '{}' が REQUEST '{}' と不一致".format(body_reqid, req.request_id),
        )
    if not body_reqid:
        warnings.append("RESULT 本文に request_id 行が無い (§5.3 推奨項目)")

    os.makedirs(dirs["processed"], exist_ok=True)
    dest = os.path.join(dirs["processed"], req.filename)
    action = "moved"
    if os.path.exists(dest):
        if sha1_of(dest) == sha1_of(req.path):
            # §6: 重複は削除でなく processed へ集約。控えは残し、to_gpt の余分を消す。
            os.remove(req.path)
            action = "consolidated"
        elif force:
            os.replace(req.path, dest)
            action = "moved_overwrite"
        else:
            raise CloseError(
                "duplicate_conflict",
                "processed/ に同名の異なる REQUEST が既存。--force で上書き可、要人間確認",
            )
    else:
        shutil.move(req.path, dest)

    return CloseResult(
        request=req,
        result_filename=req.expected_result,
        result_label=label,
        action=action,
        dest_path=dest,
        warnings=warnings,
    )
