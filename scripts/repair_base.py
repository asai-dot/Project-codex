"""repair_base — 自己浄化 repair 層の基盤 (DDSELFHEAL Phase C0, dry-run only)。

GPT 監査 (DDSELFHEAL_PASS_WITH_NOTES) の must_fix を骨格にする:
  * #1 repair class 5分類 (書込権限の階層)。
  * #2 raw source snapshot を mutate しない (repairer は派生フィールドのみ plan する)。
  * #7 repair manifest schema (input_hashes / before / after / rollback / gate / decision_log / class)。

**本モジュールは plan (dry-run) を作るだけで、何も書き込まない。** 実書込は phase gate +
apply_guard + owner whitelist を全通過した後にのみ別途行う (現状は C0 = 実書込 HOLD)。
stdlib のみ・決定的。
"""

from __future__ import annotations

import hashlib
import json

REPAIR_BASE_VERSION = "0.3.1"

# must_fix #1: repair class (弱い→強い書込権限)。
REPORT_ONLY = "report_only"
QUARANTINE_ONLY = "quarantine_only"
DET_NO_CANONICAL = "deterministic_no_canonical_write"
DET_PROJECTION = "deterministic_projection_write"
SEMANTIC_IDENTITY = "semantic_or_identity_review_required"

REPAIR_CLASSES = (REPORT_ONLY, QUARANTINE_ONLY, DET_NO_CANONICAL,
                  DET_PROJECTION, SEMANTIC_IDENTITY)

# 各 phase で「実書込」を許す class (GPT 指定 C0→C1→C2)。C0 は実書込なし(dry-run のみ)。
_PHASE_WRITABLE = {
    "C0": frozenset(),  # 実書込なし。manifest を出すだけ。
    "C1": frozenset({REPORT_ONLY, QUARANTINE_ONLY, DET_NO_CANONICAL}),
    "C2": frozenset({REPORT_ONLY, QUARANTINE_ONLY, DET_NO_CANONICAL, DET_PROJECTION}),
}
# semantic/identity はどの phase でも自動書込しない (must_fix #8 / hard rule #3)。


def is_write_allowed_in_phase(repair_class: str, phase: str) -> bool:
    """その class が当該 phase で実書込を許されるか (semantic/identity は常に不可)。"""
    if repair_class == SEMANTIC_IDENTITY:
        return False
    return repair_class in _PHASE_WRITABLE.get(phase, frozenset())


def sha256_of(obj) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


class Repairer:
    """repairer の基底。サブクラスは決定的に detect/plan を実装する。

    不変条件 (must_fix #2): plan は **派生フィールドのみ**を before/after に載せ、
    raw source (生 title / 生 pdf_page / canonical identity) は対象にしない。
    """

    name = "base"
    repair_class = REPORT_ONLY
    version = "0.0.0"

    def detect(self, book: dict) -> bool:
        """この book に適用余地があるか (既に綺麗なら False = 冪等の素)。"""
        raise NotImplementedError

    def plan(self, book: dict) -> dict | None:
        """決定的な修復案を返す。書き込みはしない。

        Returns: {"target","changes":[{"locator","field","before","after"}],"basis"} or None。
        """
        raise NotImplementedError


_REGISTRY: list[Repairer] = []


def register(repairer: Repairer) -> Repairer:
    _REGISTRY.append(repairer)
    return repairer


def registry() -> list[Repairer]:
    return list(_REGISTRY)


def build_manifest(book: dict, repairer: Repairer, plan: dict, *,
                   gate_result: dict, rollback_bundle: dict | None,
                   decision_log_hash: str | None,
                   owner_or_whitelist_ref: str | None) -> dict:
    """must_fix #7 の repair manifest を組み立てる (純データ・書込なし)。"""
    isbn = book.get("isbn", "")
    input_hashes = {
        "source_meta": sha256_of(book.get("source_meta", {})),
        "sources": sha256_of(book.get("sources", {})),
    }
    repair_id = sha256_of([isbn, repairer.name, repairer.version, plan])[:23]
    return {
        "repair_id": repair_id,
        "isbn": isbn,
        "repairer": repairer.name,
        "repairer_version": repairer.version,
        "repair_class": repairer.repair_class,
        "input_hashes": input_hashes,
        "target": plan.get("target"),
        "changes": plan.get("changes", []),
        "basis": plan.get("basis", ""),
        "rollback_bundle": rollback_bundle,
        "decision_log_hash": decision_log_hash,
        "gate_result": gate_result,        # apply_guard の allowed/refusals
        "owner_or_whitelist_ref": owner_or_whitelist_ref,
        "write_executed": False,           # C0: 常に False (dry-run)
    }


__all__ = [
    "REPAIR_BASE_VERSION", "REPORT_ONLY", "QUARANTINE_ONLY", "DET_NO_CANONICAL",
    "DET_PROJECTION", "SEMANTIC_IDENTITY", "REPAIR_CLASSES",
    "is_write_allowed_in_phase", "sha256_of", "Repairer",
    "register", "registry", "build_manifest",
]
