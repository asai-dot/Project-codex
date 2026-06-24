"""validator のサブセット挙動を固定する単体テスト。"""

from alo_workflow_event.validator import iter_errors, validate, ValidationError


def test_type_string_ok():
    assert iter_errors("hi", {"type": "string"}) == []


def test_type_mismatch():
    errs = iter_errors(123, {"type": "string"})
    assert errs and "type mismatch" in errs[0]


def test_integer_excludes_bool():
    assert iter_errors(True, {"type": "integer"})  # bool は integer ではない


def test_number_excludes_bool():
    assert iter_errors(True, {"type": "number"})


def test_null_type_in_union():
    assert iter_errors(None, {"type": ["string", "null"]}) == []
    assert iter_errors("x", {"type": ["string", "null"]}) == []


def test_const_ok_and_fail():
    assert iter_errors("a", {"const": "a"}) == []
    assert iter_errors("b", {"const": "a"})


def test_enum():
    assert iter_errors("a", {"enum": ["a", "b"]}) == []
    assert iter_errors("z", {"enum": ["a", "b"]})


def test_required_and_additional_properties_false():
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["x"],
        "properties": {"x": {"type": "string"}},
    }
    assert iter_errors({"x": "ok"}, schema) == []
    assert iter_errors({}, schema)  # missing required
    assert iter_errors({"x": "ok", "y": 1}, schema)  # additional prop


def test_additional_properties_schema():
    schema = {
        "type": "object",
        "properties": {},
        "additionalProperties": {"type": "string"},
    }
    assert iter_errors({"k": "v"}, schema) == []
    assert iter_errors({"k": 1}, schema)


def test_pattern():
    schema = {"type": "string", "pattern": "^x-[a-z0-9_]+$"}
    assert iter_errors("x-foo_1", schema) == []
    assert iter_errors("y-foo", schema)


def test_items_and_min_items():
    schema = {"type": "array", "items": {"type": "string"}, "minItems": 1}
    assert iter_errors(["a", "b"], schema) == []
    assert iter_errors([], schema)  # minItems
    assert iter_errors(["a", 2], schema)  # bad item


def test_ref_to_defs():
    root = {
        "$defs": {"S": {"type": "string"}},
        "type": "object",
        "properties": {"a": {"$ref": "#/$defs/S"}},
        "additionalProperties": False,
    }
    assert iter_errors({"a": "ok"}, root) == []
    assert iter_errors({"a": 1}, root)


def test_oneof_exactly_one():
    schema = {
        "oneOf": [
            {"type": "string", "enum": ["a"]},
            {"type": "string", "pattern": "^x-"},
        ]
    }
    assert iter_errors("a", schema) == []
    assert iter_errors("x-foo", schema) == []
    # マッチ 0 件
    assert iter_errors("zzz", schema)


def test_oneof_null_or_ref():
    root = {
        "$defs": {"R": {"type": "object", "required": ["k"],
                        "properties": {"k": {"type": "string"}},
                        "additionalProperties": False}},
        "oneOf": [{"$ref": "#/$defs/R"}, {"type": "null"}],
    }
    assert iter_errors(None, root) == []
    assert iter_errors({"k": "v"}, root) == []
    assert iter_errors({"k": 1}, root)


def test_format_date_time_loose():
    schema = {"type": "string", "format": "date-time"}
    assert iter_errors("2026-01-15T06:20:00Z", schema) == []
    assert iter_errors("2026-01-15T06:20:00+09:00", schema) == []
    assert iter_errors("2026-01-15T06:20:00.123Z", schema) == []
    assert iter_errors("not-a-date", schema)


def test_minimum_maximum():
    schema = {"type": "number", "minimum": 0, "maximum": 1}
    assert iter_errors(0.5, schema) == []
    assert iter_errors(-1, schema)
    assert iter_errors(2, schema)


def test_validate_raises():
    try:
        validate(1, {"type": "string"})
    except ValidationError as exc:
        assert exc.errors
    else:
        raise AssertionError("expected ValidationError")
