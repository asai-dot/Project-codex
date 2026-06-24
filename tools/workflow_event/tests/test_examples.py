"""同梱の v0.2 examples が schema_v0.2 で全件 green であること、及び
ネガティブ例が確実に弾かれることを固定する受け入れテスト。"""

import copy

from conftest import EXAMPLES_PATH, SCHEMA_PATH

from alo_workflow_event.validator import iter_errors


def test_all_examples_validate_green(schema, examples):
    assert len(examples) >= 4
    for i, ev in enumerate(examples):
        errs = iter_errors(ev, schema)
        assert errs == [], "example #{} failed: {}".format(i, errs)


def test_examples_use_v02_schema_version(examples):
    for ev in examples:
        assert ev["schema_version"] == "alo-workflow-event-0.2"


def test_x_prefixed_event_type_allowed(examples):
    # 緩衝帯: x- 接頭辞のイベントが少なくとも 1 件含まれ green であること。
    assert any(ev["event_type"].startswith("x-") for ev in examples)


def _base(examples):
    return copy.deepcopy(examples[0])


def test_negative_wrong_schema_version(schema, examples):
    ev = _base(examples)
    ev["schema_version"] = "alo-workflow-event-0.1"
    assert iter_errors(ev, schema)


def test_negative_missing_required(schema, examples):
    ev = _base(examples)
    del ev["event_id"]
    assert iter_errors(ev, schema)


def test_negative_unknown_event_type(schema, examples):
    ev = _base(examples)
    ev["event_type"] = "totally_unknown_event"  # enum 外かつ x- 接頭辞でない
    assert iter_errors(ev, schema)


def test_negative_bad_x_prefix(schema, examples):
    ev = _base(examples)
    ev["event_type"] = "x-BadCase"  # 大文字は pattern ^x-[a-z0-9_]+$ 不適合
    assert iter_errors(ev, schema)


def test_negative_additional_property(schema, examples):
    ev = _base(examples)
    ev["surprise"] = "nope"  # トップレベル additionalProperties:false
    assert iter_errors(ev, schema)


def test_negative_bad_event_id_pattern(schema, examples):
    ev = _base(examples)
    ev["event_id"] = "not-an-alo-id"
    assert iter_errors(ev, schema)


def test_negative_bad_datetime(schema, examples):
    ev = _base(examples)
    ev["occurred_at"] = "yesterday"
    assert iter_errors(ev, schema)


def test_negative_enum_violation_nested(schema, examples):
    ev = _base(examples)
    ev["source"]["source_kind"] = "carrier_pigeon"  # SourceRef.source_kind enum 外
    assert iter_errors(ev, schema)


def test_negative_confidence_out_of_range(schema, examples):
    ev = _base(examples)
    ev["confidence"] = 1.5
    assert iter_errors(ev, schema)


def test_paths_exist():
    import os
    assert os.path.isfile(SCHEMA_PATH)
    assert os.path.isfile(EXAMPLES_PATH)
