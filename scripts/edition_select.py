"""edition_select — edition 同定 classifier の版選択ディスパッチャ (report-only)。

共有 `classify_edition_identity` (v1) と強化版 `classify_edition_identity_v2` を
**設定で切替**えるための薄い選択層。既定は "v1" (現行挙動不変)。

DD-EDIDENT-001 が GPT 再監査 + owner ratify されたら、`config/thresholds.json` の
`edition_classifier_version` を "v2" にする **1フリップ**だけで concordance/data_health
全体の edition 判定が強化版に切り替わる (コード変更不要)。それまでは v1 のまま。

返り値は両版とも {"status", "reason", ...} で status は共通4ラベル。report-only・決定的。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edition_identity import classify_edition_identity  # noqa: E402
from edition_identity_v2 import classify_edition_identity_v2  # noqa: E402

EDITION_SELECT_VERSION = "0.3.1"


def classify_edition(bib: list[dict], *, version: str = "v1",
                     page_tolerance: float = 0.1,
                     year_tolerance: int = 1,
                     manual_override: str | None = None) -> dict:
    """version="v1"|"v2" で classifier を選び、共通形 {status, reason, ...} を返す。

    未知 version は安全側に v1 を使う (未承認の版へ勝手に倒れない)。
    """
    if version == "v2":
        return classify_edition_identity_v2(
            bib, page_tolerance=page_tolerance, year_tolerance=year_tolerance,
            manual_override=manual_override)
    return classify_edition_identity(
        bib, page_tolerance=page_tolerance, manual_override=manual_override)


def classify_edition_with_thresholds(bib: list[dict], thresholds: dict | None = None,
                                     *, manual_override: str | None = None) -> dict:
    """thresholds dict から version/tolerance を読んで分類する糖衣。"""
    t = thresholds or {}
    return classify_edition(
        bib,
        version=t.get("edition_classifier_version", "v1"),
        page_tolerance=t.get("edition_page_tolerance", 0.1),
        year_tolerance=t.get("edition_year_tolerance", 1),
        manual_override=manual_override,
    )


__all__ = ["EDITION_SELECT_VERSION", "classify_edition",
           "classify_edition_with_thresholds"]
