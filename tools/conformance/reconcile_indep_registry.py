"""reconcile_indep_registry — RECONCILE §1 の family_kind→axis 語彙写像のみ。

独立性の**カウント**は DD-INDEP-LINEAGE-001（indep_lineage.py）が正本。
本モジュールは family_kind を content_origin / observation_pipeline のどちらの軸の
**分類語彙**かに写像するだけ（カウント単位ではない・監査 B1/B4 反映）。
"""
from __future__ import annotations

AXIS_CONTENT = "content_origin"
AXIS_OBSERVATION = "observation_pipeline"

FAMILY_KIND_TO_AXIS = {
    "statute_text": AXIS_CONTENT, "case_law": AXIS_CONTENT, "legal_dictionary": AXIS_CONTENT,
    "classification_scheme": AXIS_CONTENT, "commentary_publisher": AXIS_CONTENT,
    "editorial_source": AXIS_CONTENT, "court_db": AXIS_CONTENT,
    "ocr_engine": AXIS_OBSERVATION, "parser": AXIS_OBSERVATION,
    "normalization_profile": AXIS_OBSERVATION, "scan_source": AXIS_OBSERVATION,
}


class ReconcileValidationError(ValueError):
    pass


def axis_for_kind(family_kind: str) -> str:
    if family_kind not in FAMILY_KIND_TO_AXIS:
        raise ReconcileValidationError(f"未写像の family_kind: {family_kind}")
    return FAMILY_KIND_TO_AXIS[family_kind]
