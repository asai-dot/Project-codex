"""ALO workflow event envelope の stdlib-only 検証ツール。

JSON Schema draft 2020-12 の必要十分なサブセット(type / required / enum /
const / additionalProperties:false / $ref(#/$defs) / oneOf / pattern /
items / format:date-time の緩い解釈)を解釈する検証器を提供する。
外部 pip 依存(jsonschema 等)は使わない。
"""

from __future__ import annotations

__version__ = "0.2.0"

from .validator import ValidationError, validate

__all__ = ["__version__", "ValidationError", "validate"]
