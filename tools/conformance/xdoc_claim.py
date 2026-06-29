"""xdoc_claim — DD-XDOC-001 v0.9 §6（claim member selector・過少申告封じ）。

依存ゼロ・read-only 純関数。受入試験6a（claimed_side=both で1 member だけ列挙を封じる）。
- all_on_side: claimed_member_refs = expected_member_set（完全一致必須）
- explicit_subset: subset_selector_id = hash 固定・claimed ⊆ expected（自由省略を記録として残す）

参照: docs/dd_candidates/DD-XDOC-001_..._v0.9_20260623.md §6
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Set

try:
    from . import xdoc_canonical as _xc
except ImportError:  # pragma: no cover
    import xdoc_canonical as _xc

MODE_ALL_ON_SIDE = "all_on_side"
MODE_EXPLICIT_SUBSET = "explicit_subset"


class ClaimValidationError(ValueError):
    pass


def subset_selector_id(claimed_member_refs: List[str], claimed_side: str) -> str:
    return _xc.sha256_hex(_xc.canonical_json({
        "claimed_member_refs": sorted(claimed_member_refs),
        "claimed_side": claimed_side,
    }))


@dataclass
class ClaimMemberSelector:
    use_assessment_key_id: str
    mode: str  # all_on_side | explicit_subset
    claimed_side: str  # a | b | both
    claimed_member_refs: List[str]  # minItems=1
    subset_selector_id_value: str = ""  # explicit_subset のとき必須

    def __post_init__(self):
        if not self.claimed_member_refs:
            raise ClaimValidationError("claimed_member_refs は minItems=1")
        if self.mode not in (MODE_ALL_ON_SIDE, MODE_EXPLICIT_SUBSET):
            raise ClaimValidationError(f"未知の mode: {self.mode}")


def expected_member_set(members_a: List[str], members_b: List[str], claimed_side: str) -> Set[str]:
    if claimed_side == "a":
        return set(members_a)
    if claimed_side == "b":
        return set(members_b)
    if claimed_side == "both":
        return set(members_a) | set(members_b)
    raise ClaimValidationError(f"未知の claimed_side: {claimed_side}")


def claim_member_complete(selector: ClaimMemberSelector,
                          members_a: List[str], members_b: List[str]) -> bool:
    """G_XDOC_CLAIM_MEMBER_COMPLETE（B19）。absence/difference claim の完全性。"""
    expected = expected_member_set(members_a, members_b, selector.claimed_side)
    claimed = set(selector.claimed_member_refs)
    if selector.mode == MODE_ALL_ON_SIDE:
        return claimed == expected  # 完全一致必須（過少申告を reject）
    # explicit_subset: subset_selector_id 必須・hash 一致・claimed ⊆ expected
    if not selector.subset_selector_id_value:
        return False
    if selector.subset_selector_id_value != subset_selector_id(selector.claimed_member_refs, selector.claimed_side):
        return False
    return claimed <= expected
