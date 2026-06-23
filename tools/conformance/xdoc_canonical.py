"""xdoc_canonical — DD-XDOC-001 v0.7 §5 の決定的 ID 正規化（依存ゼロ・read-only 純関数）

Phase 0 適合性ハーネス。production に一切触れない。DD 本文の canonicalization 規則を
そのまま実行可能コードにし、受入試験 9（symmetric side-swap → 同一 id）/ 10（companion set
変化 → id 変化）を機械証明する。GPT 監査が最も誤実装を警戒した箇所（B1/B3/B9/B13）。

参照: docs/dd_candidates/DD-XDOC-001_..._v0.7_20260622.md §5
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional


# ---- canonical JSON（normative）: NFC / key コードポイント昇順 / 余白なし --------------
def _nfc(obj):
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, list):
        return [_nfc(x) for x in obj]
    if isinstance(obj, dict):
        return {_nfc(k): _nfc(v) for k, v in obj.items()}
    return obj


def canonical_json(obj) -> str:
    """決定的直列化: NFC 正規化 + key 昇順 + 区切り最小 + 非ASCIIそのまま。"""
    return json.dumps(
        _nfc(obj), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---- member / side 正規化（§5） ------------------------------------------------------
@dataclass(frozen=True)
class MemberTuple:
    asset_id: str
    text_revision: str
    unit_id: str

    def canonical(self) -> str:
        # member_canonical(m) = canonical_json (asset_id, text_revision, unit_id)
        return canonical_json(
            {
                "asset_id": self.asset_id,
                "text_revision": self.text_revision,
                "unit_id": self.unit_id,
            }
        )


def side_canonical(members: List[MemberTuple]) -> List[str]:
    """side_canonical = sort_ascending([member_canonical(m) ...])（重複除去なし）。"""
    return sorted(m.canonical() for m in members)


def _has_intra_side_dup(members: List[MemberTuple]) -> bool:
    cans = [m.canonical() for m in members]
    return len(cans) != len(set(cans))


def _self_overlap(a: List[MemberTuple], b: List[MemberTuple]) -> bool:
    return bool(set(m.canonical() for m in a) & set(m.canonical() for m in b))


class XdocValidationError(ValueError):
    """DD-XDOC v0.7 の constraint/gate 違反。"""


# cardinality enum（§2）: 単一 enum。symmetric は n_one を作らない。
CARD_ONE_ONE = "one_one"
CARD_ONE_N = "one_n"
CARD_N_ONE = "n_one"
CARD_N_M = "n_m"


def determine_cardinality(direction: str, a: List[MemberTuple], b: List[MemberTuple]) -> str:
    """§5 cardinality 決定式（単一 field）。symmetric=unordered / directional=順序保持。"""
    la, lb = len(a), len(b)
    if direction == "symmetric":
        lo, hi = sorted((la, lb))
        if lo == 1 and hi == 1:
            return CARD_ONE_ONE
        if lo == 1 and hi > 1:
            return CARD_ONE_N
        return CARD_N_M  # n,m>1
    # directional (a_to_b / b_to_a): side 順序保持
    if la == 1 and lb == 1:
        return CARD_ONE_ONE
    if la == 1 and lb > 1:
        return CARD_ONE_N
    if la > 1 and lb == 1:
        return CARD_N_ONE
    return CARD_N_M


def _members_canonical(direction: str, a: List[MemberTuple], b: List[MemberTuple]) -> List[List[str]]:
    """ID 材料用 members_canonical。symmetric は side 入替不変、directional は順序保持。"""
    sa, sb = side_canonical(a), side_canonical(b)
    if direction == "symmetric":
        # side 正規化: side_canonical を文字列比較し小さい方を canonical_a
        lo, hi = sorted((canonical_json(sa), canonical_json(sb)))
        return [json.loads(lo), json.loads(hi)]
    return [sa, sb]  # directional: side 順序保持


# ---- alignment_observation_id（§5 canonical） --------------------------------------
@dataclass
class Alignment:
    schema_version: str
    facet: str
    comparison_intent: str
    direction: str  # a_to_b | b_to_a | symmetric
    members_a: List[MemberTuple]
    members_b: List[MemberTuple]
    primary_method_registry_id: str
    applied_companion_method_registry_ids: List[str]
    parameter_profile_hash: str
    normalization_profile_id: str
    normalization_profile_version: str
    tokenization_profile_id: str
    tokenization_profile_version: str
    corpus_snapshot_id: str
    release_id: str
    result_payload_digest: Optional[str] = None  # nondeterministic method のみ
    cardinality: str = field(default="", init=False)

    def __post_init__(self):
        # side non-empty（B13）
        if not self.members_a or not self.members_b:
            raise XdocValidationError("members_a / members_b は minItems=1")
        # 同一 side 内 duplicate（§5）
        if _has_intra_side_dup(self.members_a) or _has_intra_side_dup(self.members_b):
            raise XdocValidationError("G_XDOC_NO_SELF_LOOP: 同一 side 内 duplicate member")
        # self overlap（§5）
        if _self_overlap(self.members_a, self.members_b):
            raise XdocValidationError("G_XDOC_NO_SELF_LOOP: 両 side に同一 member（self overlap）")
        self.cardinality = determine_cardinality(
            self.direction, self.members_a, self.members_b
        )
        # constraint: symmetric ⇒ n_one 禁止（§5）
        if self.direction == "symmetric" and self.cardinality == CARD_N_ONE:
            raise XdocValidationError("symmetric で n_one は不可")

    def observation_id(self) -> str:
        material = {
            "schema_version": self.schema_version,
            "facet": self.facet,
            "comparison_intent": self.comparison_intent,
            "direction": self.direction,
            "cardinality": self.cardinality,
            "members_canonical": _members_canonical(
                self.direction, self.members_a, self.members_b
            ),
            "primary_method_registry_id": self.primary_method_registry_id,
            # B9: companion set も ID 材料（canonical sort）
            "applied_companion_method_registry_ids": sorted(
                self.applied_companion_method_registry_ids
            ),
            "parameter_profile_hash": self.parameter_profile_hash,
            "normalization_profile_id": self.normalization_profile_id,
            "normalization_profile_version": self.normalization_profile_version,
            "tokenization_profile_id": self.tokenization_profile_id,
            "tokenization_profile_version": self.tokenization_profile_version,
            "result_payload_digest": self.result_payload_digest,  # NULL 可
            "corpus_snapshot_id": self.corpus_snapshot_id,
            "release_id": self.release_id,
        }
        return sha256_hex(canonical_json(material))
