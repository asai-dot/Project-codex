"""indep_lineage — DD-INDEP-LINEAGE-001 v0.1（独立性 lineage 正本・反こたつ記事の核）。

依存ゼロ・read-only 純関数。両監査（DDRECONCILE/DDXMODAL）の B1-B4 を反映：
独立票は object_id/record_id/scan_id では数えない。
- content: policy が upstream_lineage / collapse_key から算定する content_independence_group の DISTINCT。
- observation: raw_input_hash 由来の acquisition lineage root の DISTINCT（OCR/parser は子）。

参照: docs/dd_candidates/DD-INDEP-LINEAGE-001_..._v0.1_20260625.md
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Set

BINDING_ACTIVE = "active"
BINDING_STALE = "stale"
BINDING_SUPERSEDED = "superseded"


class IndepValidationError(ValueError):
    pass


# ---- content lineage binding（§2） --------------------------------------------------
@dataclass(frozen=True)
class ContentLineageBinding:
    binding_id: str
    source_artifact_ref: str          # どの book/record からの観測か
    content_object_id: str            # 条文/判例/版/passage（独立票の単位ではない）
    upstream_lineage_id: str          # 上流原稿/authority/editorial 系譜
    same_origin_collapse_key: Optional[str]  # 転載/派生 record を畳む key（無ければ None）
    independence_policy_version: str
    binding_status: str = BINDING_ACTIVE

    def __post_init__(self):
        if self.binding_status not in (BINDING_ACTIVE, BINDING_STALE, BINDING_SUPERSEDED):
            raise IndepValidationError(f"未知 binding_status: {self.binding_status}")


GROUP_UNKNOWN = "__unknown_lineage__"   # note5: 不明系譜は independent に格上げしない


def content_independence_group(b: ContentLineageBinding) -> str:
    """policy 算定: 独立群 = collapse_key 優先、無ければ upstream_lineage_id。

    object_id では数えない（B1/B4）。転載/同一上流は同一群へ collapse。
    upstream も collapse も不明（falsy）なら GROUP_UNKNOWN（note5: 既定で独立にしない）。
    """
    key = b.same_origin_collapse_key or b.upstream_lineage_id
    return key if key else GROUP_UNKNOWN


def content_independent(bindings: Iterable[ContentLineageBinding]) -> bool:
    """active binding の **既知** content_independence_group の DISTINCT ≥ 2。

    note5（保守化）: GROUP_UNKNOWN は数えない。不明系譜だけでは独立を立てない。
    """
    groups: Set[str] = {
        content_independence_group(b) for b in bindings if b.binding_status == BINDING_ACTIVE
    }
    groups.discard(GROUP_UNKNOWN)
    return len(groups) >= 2


# ---- observation acquisition lineage（§3） -----------------------------------------
@dataclass(frozen=True)
class ObservationRun:
    run_id: str
    raw_input_hash: str               # raw bytes の同一性（複製 scan を畳む・root の素）
    acquisition_event_id: str
    ocr_engine: str                   # 子（独立票でない）
    parser: str
    normalization_profile: str
    scan_source_id: str = ""          # 参考。root には使わない（複製で増やせるため）


def observation_lineage_root(r: ObservationRun) -> str:
    """root は raw_input_hash 由来（scan_source_id ではない・B3）。"""
    return r.raw_input_hash


def observation_independent(runs: Iterable[ObservationRun]) -> bool:
    """observation lineage root の DISTINCT ≥ 2（同一 raw bytes の別 run は1系統）。"""
    roots: Set[str] = {observation_lineage_root(r) for r in runs}
    return len(roots) >= 2


# ---- consumer 規約（§5） -----------------------------------------------------------
def xmodal_confirmed_independent(content_bindings: Iterable[ContentLineageBinding]) -> bool:
    """XMODAL confirmed: content group DISTINCT ≥ 2。observation は数えない。"""
    return content_independent(content_bindings)


def binding_change_invalidates(old: ContentLineageBinding,
                               new: ContentLineageBinding) -> bool:
    """B2: binding 変更（独立群が変わる）→ 既存 assessment を stale/re-eval すべきか。"""
    return content_independence_group(old) != content_independence_group(new)
