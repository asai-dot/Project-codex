"""JSON Schema draft 2020-12 の必要十分なサブセットを stdlib のみで検証する。

サポートするキーワード:
  type / required / enum / const / additionalProperties:false /
  properties / $ref(#/$defs/... のみ) / oneOf / pattern / items /
  minItems / minLength / maxLength / minimum / maximum / format:date-time(緩め)

非対応のキーワードは「無視(=制約なし)」として扱う。これは検証器を
保守的(false negative を出さない方向)に倒すための意図的な設計。
jsonschema 等の外部 pip 依存は使わない。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# JSON の型名 → Python 型のマッピング。"integer" は bool を除外する点に注意。
_JSON_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
}

# date-time の緩い検証: RFC3339 風 (日付 T 時刻 [秒小数] (Z|±hh:mm))。
# 厳密なカレンダー妥当性(うるう年等)までは見ない=「緩め」。
_DATE_TIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$"
)
# date の緩い検証。
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ValidationError(Exception):
    """検証失敗。``errors`` に "path: message" 形式の理由を保持する。"""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors) if errors else "validation failed")


def validate(instance: Any, schema: Dict[str, Any]) -> None:
    """``instance`` を ``schema`` で検証する。失敗時は ValidationError を送出。"""
    errors: List[str] = []
    _validate(instance, schema, schema, "$", errors)
    if errors:
        raise ValidationError(errors)


def iter_errors(instance: Any, schema: Dict[str, Any]) -> List[str]:
    """検証エラーのリストを返す(送出しない)。green なら空リスト。"""
    errors: List[str] = []
    _validate(instance, schema, schema, "$", errors)
    return errors


def _resolve_ref(ref: str, root: Dict[str, Any]) -> Dict[str, Any]:
    """``#/$defs/Name`` 形式の局所 $ref を解決する。"""
    if not ref.startswith("#/"):
        raise ValueError("unsupported $ref (local '#/...' only): {}".format(ref))
    node: Any = root
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or token not in node:
            raise ValueError("unresolvable $ref: {}".format(ref))
        node = node[token]
    if not isinstance(node, dict):
        raise ValueError("$ref target is not a schema object: {}".format(ref))
    return node


def _validate(
    instance: Any,
    schema: Dict[str, Any],
    root: Dict[str, Any],
    path: str,
    errors: List[str],
) -> None:
    # $ref は他のキーワードに先立って解決し、対象スキーマで再帰検証する。
    if "$ref" in schema:
        try:
            target = _resolve_ref(schema["$ref"], root)
        except ValueError as exc:
            errors.append("{}: {}".format(path, exc))
            return
        _validate(instance, target, root, path, errors)
        # draft 2020-12 では $ref と兄弟キーワードの両立も可能だが、本サブセット
        # では $ref のみのスキーマを前提とし、他キーワードがあれば併せて評価する。

    # const
    if "const" in schema and instance != schema["const"]:
        errors.append(
            "{}: const mismatch (expected {!r})".format(path, schema["const"])
        )

    # enum
    if "enum" in schema and instance not in schema["enum"]:
        errors.append("{}: value {!r} not in enum".format(path, instance))

    # type (単一 or 配列)
    if "type" in schema:
        if not _check_type(instance, schema["type"]):
            errors.append(
                "{}: type mismatch (expected {}, got {})".format(
                    path, schema["type"], _typename(instance)
                )
            )

    # oneOf: ちょうど 1 件にマッチすること。
    if "oneOf" in schema:
        matched = 0
        for sub in schema["oneOf"]:
            sub_errs: List[str] = []
            _validate(instance, sub, root, path, sub_errs)
            if not sub_errs:
                matched += 1
        if matched != 1:
            errors.append(
                "{}: oneOf matched {} subschemas (expected exactly 1)".format(
                    path, matched
                )
            )

    # 文字列系
    if isinstance(instance, str):
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(
                "{}: string does not match pattern {!r}".format(
                    path, schema["pattern"]
                )
            )
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append("{}: shorter than minLength".format(path))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append("{}: longer than maxLength".format(path))
        if schema.get("format") == "date-time" and not _DATE_TIME_RE.match(instance):
            errors.append("{}: not a valid date-time".format(path))
        if schema.get("format") == "date" and not _DATE_RE.match(instance):
            errors.append("{}: not a valid date".format(path))

    # 数値系 (bool は number 扱いしない)
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append("{}: below minimum".format(path))
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append("{}: above maximum".format(path))

    # オブジェクト系
    if isinstance(instance, dict):
        _validate_object(instance, schema, root, path, errors)

    # 配列系
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append("{}: fewer than minItems".format(path))
        if "items" in schema:
            item_schema = schema["items"]
            for i, item in enumerate(instance):
                _validate(item, item_schema, root, "{}[{}]".format(path, i), errors)


def _validate_object(
    instance: Dict[str, Any],
    schema: Dict[str, Any],
    root: Dict[str, Any],
    path: str,
    errors: List[str],
) -> None:
    # required
    for key in schema.get("required", []):
        if key not in instance:
            errors.append("{}: missing required property {!r}".format(path, key))

    props = schema.get("properties", {})
    for key, value in instance.items():
        child_path = "{}.{}".format(path, key)
        if key in props:
            _validate(value, props[key], root, child_path, errors)
        else:
            # additionalProperties:false なら未知キーはエラー。
            # additionalProperties がスキーマなら、そのスキーマで検証。
            ap = schema.get("additionalProperties", True)
            if ap is False:
                errors.append(
                    "{}: additional property {!r} not allowed".format(path, key)
                )
            elif isinstance(ap, dict):
                _validate(value, ap, root, child_path, errors)


def _check_type(instance: Any, type_spec: Any) -> bool:
    if isinstance(type_spec, list):
        return any(_check_one_type(instance, t) for t in type_spec)
    return _check_one_type(instance, type_spec)


def _check_one_type(instance: Any, type_name: str) -> bool:
    check = _JSON_TYPE_CHECKS.get(type_name)
    if check is None:
        # 未知の型名は制約なし扱い(保守的)。
        return True
    return check(instance)


def _typename(instance: Any) -> str:
    if instance is None:
        return "null"
    if isinstance(instance, bool):
        return "boolean"
    if isinstance(instance, str):
        return "string"
    if isinstance(instance, float):
        return "number"
    if isinstance(instance, int):
        return "integer"
    if isinstance(instance, list):
        return "array"
    if isinstance(instance, dict):
        return "object"
    return type(instance).__name__
