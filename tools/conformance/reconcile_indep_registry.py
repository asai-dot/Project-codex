"""reconcile_indep_registry — DD-TRILOGY-RECONCILE-001 §1（独立性・lineage 正本）。

依存ゼロ・read-only 純関数。**v0.1 監査の R1 指摘を反映した修正版**：
- 独立観測数は「pipeline 部品（ocr_engine/parser…）の DISTINCT 数」ではなく、
  **observation run lineage の根（同一 raw scan か）の DISTINCT 数**で数える。
  → 同一 raw scan に2エンジン掛けても独立1源（部品違いは独立でない）。
- content 独立は **same-origin collapse**：同一 origin object（同一条文/同一版元転載）は1源。

参照: DD-TRILOGY-RECONCILE-001 v0.2 §1（監査 RESULT Box 2306465882050 反映）
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Set

AXIS_CONTENT = "content_origin"
AXIS_OBSERVATION = "observation_pipeline"


class ReconcileValidationError(ValueError):
    pass


# ---- content 独立（same-origin collapse・R1 fixture 1） ------------------------------
@dataclass(frozen=True)
class ContentOrigin:
    """内容起源。同一 origin_object_id は同一源（複数本が同一条文を引く＝1源）。
    同一 editorial_source の転載（同一版元 provider 転載）も同一源に collapse。"""
    origin_object_id: str          # 例 statute:民法541 / case:最判… / edition:…
    editorial_source: str          # 版元/編集源（provider 転載の同一性）

    def origin_root(self) -> str:
        # collapse 規則: origin_object_id を根とする（同一条文＝1）。
        # 同一 editorial_source の異 object は別根だが、同一 object の別版元転載は同根。
        return self.origin_object_id


def content_independent(origins: Iterable[ContentOrigin]) -> bool:
    """DISTINCT origin_root ≥ 2。同一条文/同一版元転載は1源に collapse。"""
    roots: Set[str] = {o.origin_root() for o in origins}
    return len(roots) >= 2


# ---- observation 独立（lineage 根・R1 fixture 2） ----------------------------------
@dataclass(frozen=True)
class ObservationRun:
    """観測 run。lineage の根は raw scan（scan_source_id）。
    同一 raw scan の OCR/parser 違いは独立でない（部品違いは別観測でない）。"""
    scan_source_id: str            # raw scan の同一性（lineage 根）
    ocr_engine: str                # 部品（独立カウントには使わない）
    parser: str
    normalization_profile: str

    def lineage_root(self) -> str:
        return self.scan_source_id


def observation_independent(runs: Iterable[ObservationRun]) -> bool:
    """DISTINCT lineage 根（scan_source_id）≥ 2。部品違いは数えない。"""
    roots: Set[str] = {r.lineage_root() for r in runs}
    return len(roots) >= 2


# ---- XMODAL confirmed（content 独立のみ・observation は数えない・§1 consumer 規約） ----
def xmodal_confirmed_independent(content_origins: Iterable[ContentOrigin]) -> bool:
    """confirmed の D2 独立は content 起源の独立（same-origin collapse 後 ≥ 2）。
    observation pipeline は confirmed の独立票に数えない（R1）。"""
    return content_independent(content_origins)


# ---- family_kind → axis（語彙整合は維持・カウントには lineage を使う） ---------------
FAMILY_KIND_TO_AXIS = {
    "statute_text": AXIS_CONTENT, "case_law": AXIS_CONTENT, "legal_dictionary": AXIS_CONTENT,
    "classification_scheme": AXIS_CONTENT, "commentary_publisher": AXIS_CONTENT,
    "editorial_source": AXIS_CONTENT, "court_db": AXIS_CONTENT,
    "ocr_engine": AXIS_OBSERVATION, "parser": AXIS_OBSERVATION,
    "normalization_profile": AXIS_OBSERVATION, "scan_source": AXIS_OBSERVATION,
}


def axis_for_kind(family_kind: str) -> str:
    if family_kind not in FAMILY_KIND_TO_AXIS:
        raise ReconcileValidationError(f"未写像の family_kind: {family_kind}")
    return FAMILY_KIND_TO_AXIS[family_kind]
