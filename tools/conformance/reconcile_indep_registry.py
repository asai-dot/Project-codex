"""reconcile_indep_registry — DD-TRILOGY-RECONCILE-001 v0.1 §1（独立性 共有 registry・2軸）。

依存ゼロ・read-only 純関数。XMODAL の単一 registry と XDOC の 2軸を1つの
shared_external_source_family に統合し、independence_axis タグで content_origin /
observation_pipeline を分ける。consumer 規約（XMODAL confirmed は content_origin の
DISTINCT のみ数える／XDOC は軸別）を機械証明する。

参照: docs/dd_candidates/DD-TRILOGY-RECONCILE-001_..._v0.1_20260624.md §1
"""
from __future__ import annotations

from typing import Dict, Iterable, Set

AXIS_CONTENT = "content_origin"
AXIS_OBSERVATION = "observation_pipeline"

# §1 family_kind → independence_axis 写像（normative・網羅）
FAMILY_KIND_TO_AXIS: Dict[str, str] = {
    # content_origin
    "statute_text": AXIS_CONTENT,
    "case_law": AXIS_CONTENT,
    "legal_dictionary": AXIS_CONTENT,
    "classification_scheme": AXIS_CONTENT,
    "commentary_publisher": AXIS_CONTENT,
    "editorial_source": AXIS_CONTENT,
    "court_db": AXIS_CONTENT,
    # observation_pipeline
    "ocr_engine": AXIS_OBSERVATION,
    "parser": AXIS_OBSERVATION,
    "normalization_profile": AXIS_OBSERVATION,
    "scan_source": AXIS_OBSERVATION,
}


class ReconcileValidationError(ValueError):
    pass


class SharedExternalSourceFamilyRegistry:
    """両 DD（XMODAL/XDOC）が consume する唯一の正本 registry。"""

    def __init__(self):
        self._kind: Dict[str, str] = {}  # family_id -> family_kind

    def register(self, family_id: str, family_kind: str) -> None:
        if family_kind not in FAMILY_KIND_TO_AXIS:
            raise ReconcileValidationError(f"未写像の family_kind: {family_kind}")
        self._kind[family_id] = family_kind

    def is_registered(self, family_id: str) -> bool:
        return family_id in self._kind

    def axis_of(self, family_id: str) -> str:
        """family_id の independence_axis（未登録は error）。"""
        if family_id not in self._kind:
            raise ReconcileValidationError(f"未登録 family: {family_id}")
        return FAMILY_KIND_TO_AXIS[self._kind[family_id]]

    def distinct_on_axis(self, family_ids: Iterable[str], axis: str) -> int:
        """指定 axis の DISTINCT registered family 数（未登録/別 axis は数えない）。"""
        fams: Set[str] = set()
        for fid in family_ids:
            if self.is_registered(fid) and self.axis_of(fid) == axis:
                fams.add(fid)
        return len(fams)

    # --- consumer 規約（§1） ---
    def xmodal_confirmed_independent(self, d2_family_ids: Iterable[str]) -> bool:
        """XMODAL confirmed: content_origin の DISTINCT family ≥ 2（observation は数えない）。"""
        return self.distinct_on_axis(d2_family_ids, AXIS_CONTENT) >= 2

    def xdoc_content_independent(self, family_ids: Iterable[str]) -> bool:
        return self.distinct_on_axis(family_ids, AXIS_CONTENT) >= 2

    def xdoc_observation_independent(self, family_ids: Iterable[str]) -> bool:
        return self.distinct_on_axis(family_ids, AXIS_OBSERVATION) >= 2


def axis_for_kind(family_kind: str) -> str:
    if family_kind not in FAMILY_KIND_TO_AXIS:
        raise ReconcileValidationError(f"未写像の family_kind: {family_kind}")
    return FAMILY_KIND_TO_AXIS[family_kind]
