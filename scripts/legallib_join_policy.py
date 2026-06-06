"""toc_source 優先順位ポリシー + legallib 上書きゲート (Fork 1 / 最初の一歩 ②).

検収条件「既存の人手/NDL TOC を1件も劣化させない」を **コードで保証** する層。

確定ポリシー (浅井さん指示):
  * 人手 (manual) / NDL > legallib。これらは legallib で **絶対に上書きしない**。
  * legallib の auto_accept が既存ファイルを上書きできるのは
    **既存が「simple のみ」の場合に限る** (= 昇格上書き)。

generic な ``merge_toc_updates.py`` は rank ベースで replace_if_higher_source
する (openbd が simple でなくても rank が上なら置換しうる)。legallib はそれより
**厳しい simple-only ゲート** を独自に課す。理由: legallib は外部由来で
誤接合リスクがあり、人手/NDL/出版社/PDF目次のような「人が触った/精度の高い」
既存 TOC を 1 件も劣化させてはならないため (検収・誤マージ0ガード)。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# --- ソース優先順位 (小さいほど上位) ---------------------------------------
# 既存 toc_merge_policy.json を踏襲しつつ ``ndl`` と ``legallib`` を追加。
DEFAULT_PRIORITY = [
    "manual",       # 人手
    "ndl",          # NDL 正本
    "publisher",    # 出版社公式
    "toc_pdf",      # 目次PDF (人が用意)
    "legallib",     # ★ 今回追加: 詳細・階層あり
    "openbd",
    "books_or_jp",
    "bencom",
    "codex_ocr",
    "unknown",
]

# legallib では絶対に上書きしない既存ソース (人が触った/高精度なもの)。
# simple-only ゲートに加えた二重の安全弁。
PROTECTED_SOURCES = frozenset({"manual", "ndl", "publisher", "toc_pdf"})

# legallib 自身の status / source 名。
LEGALLIB_SOURCE = "legallib"
LEGALLIB_STATUS = "legallib"

# 上書き可能な唯一の status。
OVERWRITABLE_STATUS = "simple"


def load_policy(path: str | Path | None = None) -> dict[str, Any]:
    """policy JSON を読む。無ければ既定 (DEFAULT_PRIORITY) を返す。"""
    if path is not None:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return {
        "priority": list(DEFAULT_PRIORITY),
        "protected_sources": sorted(PROTECTED_SOURCES),
        "legallib": {
            "source": LEGALLIB_SOURCE,
            "status": LEGALLIB_STATUS,
            "overwrite_gate": "simple_only",
            "rules": {
                "overwrite_only_if_all_simple": True,
                "never_overwrite_protected_sources": True,
                "skip_if_existing_already_legallib": True,
            },
        },
    }


def source_rank(priority: list[str], src: str | None) -> int:
    if src and src in priority:
        return priority.index(src)
    return len(priority) + 1


def existing_primary_source(existing_nodes: list[dict], priority: list[str]) -> str:
    """既存ノード群の代表ソース (最上位 rank のソース)。"""
    if not existing_nodes:
        return "unknown"
    sources = [n.get("toc_source") or "unknown" for n in existing_nodes]
    return min(sources, key=lambda s: source_rank(priority, s))


def is_all_simple(existing_nodes: list[dict]) -> bool:
    """全ノードが toc_status == 'simple' か。空は simple 扱いしない (False)。"""
    if not existing_nodes:
        return False
    return all(n.get("toc_status") == OVERWRITABLE_STATUS for n in existing_nodes)


def is_already_legallib(existing_nodes: list[dict]) -> bool:
    """既に legallib 由来か (冪等スキップ判定 / 既merge 344 件想定)。"""
    if not existing_nodes:
        return False
    return any(n.get("toc_source") == LEGALLIB_SOURCE for n in existing_nodes)


def existing_is_protected(
    existing_nodes: list[dict],
    *,
    protected_sources: frozenset[str] = PROTECTED_SOURCES,
) -> bool:
    """既存 TOC が「保護対象」か。

    保護対象 = 非 simple ノードを 1 つでも含む、または保護ソースを含む。
    保護対象なら legallib は **絶対に上書きしない** (→ human_review へ)。
    """
    if not existing_nodes:
        return False
    if not is_all_simple(existing_nodes):
        return True
    srcs = {n.get("toc_source") for n in existing_nodes}
    return bool(srcs & set(protected_sources))


# --- 接合判定 (1 件分) -------------------------------------------------------

def decide_join_action(
    existing_nodes: list[dict] | None,
    *,
    protected_sources: frozenset[str] = PROTECTED_SOURCES,
) -> str:
    """既存ファイル状態から legallib auto_accept の動作を決める。

    返り値 (action コード):
        ``create``                : 既存 TOC 無し → 新規作成。
        ``overwrite_simple``      : 既存が simple のみ・非保護 → 昇格上書き。
        ``skip_idempotent``       : 既に legallib → 何もしない (冪等)。
        ``route_human_review``    : 既存が保護対象 → 上書き禁止、人手レビューへ。

    この関数だけで検収「非simple は diff 0」を担保する:
    保護対象 (非simple または保護ソース) は必ず ``route_human_review`` になり、
    書き込み系 action (``create`` / ``overwrite_simple``) には決して入らない。
    """
    if not existing_nodes:
        return "create"
    if is_already_legallib(existing_nodes):
        return "skip_idempotent"
    if existing_is_protected(existing_nodes, protected_sources=protected_sources):
        return "route_human_review"
    if is_all_simple(existing_nodes):
        return "overwrite_simple"
    # ここに来るのは「非legallib・非simple・非保護ソース」= 念のため保護側へ。
    return "route_human_review"


WRITE_ACTIONS = frozenset({"create", "overwrite_simple"})
NO_WRITE_ACTIONS = frozenset({"skip_idempotent", "route_human_review"})


__all__ = [
    "DEFAULT_PRIORITY",
    "PROTECTED_SOURCES",
    "LEGALLIB_SOURCE",
    "LEGALLIB_STATUS",
    "OVERWRITABLE_STATUS",
    "WRITE_ACTIONS",
    "NO_WRITE_ACTIONS",
    "load_policy",
    "source_rank",
    "existing_primary_source",
    "is_all_simple",
    "is_already_legallib",
    "existing_is_protected",
    "decide_join_action",
]
