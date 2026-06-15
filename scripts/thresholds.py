"""thresholds — 調整可能パラメータの単一ソース (legallibjoin v0.3.1)。

検知ロジックに散らばっていた閾値 (coverage 比 / page tolerance / PDF 品質条件 等) を
`config/thresholds.json` に集約し、実データ調整を「コード変更なし」にする。

- 既定値はコード内 `DEFAULTS` に持ち (config が無くても動く)、
- `config/thresholds.json` があればその値で上書きし、
- 呼び出し側からの明示 override が最優先。

report-only。閾値は検知/分類の判定にのみ効き、本番書き込みは apply_guard が別途制御する。
stdlib のみ・決定的。
"""

from __future__ import annotations

import json
from pathlib import Path

THRESHOLDS_VERSION = "0.3.1"

# 現行コードの既定値を忠実に複製したもの (config 不在でも挙動不変)。
DEFAULTS: dict = {
    "coverage_mismatch_ratio": 3.0,      # conflict_detector._coverage_mismatch
    "edition_page_tolerance": 0.1,       # edition_identity.classify_edition_identity
    "pdf_required_confidence": "high",   # page_basis.qualify_pdf_observation
    "pdf_required_coverage": "full_toc",
    "appendix_misclassified_min": 2,     # conflict_detector._appendix_misclassified
    "health": {
        "weight_l1_bib": 30,
        "weight_l2_toc": 40,
        "weight_l3_body": 30,
        "l2_rich_min_depth": 2,
        "l2_rich_min_nodes": 5,
    },
}

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "thresholds.json"


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if k.startswith("_"):
            continue  # _comment / _version 等のメタは無視。
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_thresholds(path: str | Path | None = None,
                    *, override: dict | None = None) -> dict:
    """既定値 ← config ファイル ← override の優先順位でマージした閾値 dict を返す。

    Args:
        path: 明示パス。None なら config/thresholds.json を探し、無ければ既定のみ。
        override: 呼び出し側の最優先上書き (CLI 引数など)。

    Returns:
        DEFAULTS と同じ形の dict。
    """
    merged = dict(DEFAULTS)
    merged["health"] = dict(DEFAULTS["health"])

    cfg_path = Path(path) if path is not None else _DEFAULT_CONFIG_PATH
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                merged = _deep_merge(merged, data)
        except (json.JSONDecodeError, OSError):
            # 壊れた config は無視して既定で動く (汚い config がパイプを止めない)。
            pass

    if override:
        merged = _deep_merge(merged, override)
    return merged


__all__ = ["THRESHOLDS_VERSION", "DEFAULTS", "load_thresholds"]
