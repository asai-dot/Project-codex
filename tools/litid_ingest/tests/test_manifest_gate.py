"""manifest_gate.py の検証則テスト (§7-A 契約ゲート)."""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import manifest_gate as mg  # noqa: E402

GOOD = {
    "source": "bengo4",
    "source_system": "bengo4.com",
    "fetched_at": "2026-06-10T05:00:00+09:00",
    "account": "owner",
    "fetch_method": "scrape",
    "acquisition_path": "authenticated_scrape",
    "source_location": "https://example.com",
    "rights_class": "subscription_access",
    "medium_origin": "digital",
    "route_local_id": "content_id",
    "key_field": "content_id",
    "toc_origin": "publisher_html",
    "extractor_version": "bengo4_catalog.py@abc123",
    "record_count": 4490,
    "files": [{"name": "catalog.jsonl", "sha256": "a" * 64, "bytes": 1}],
    "evidence_locator": "box://123#row",
}


def test_good_manifest_passes():
    assert mg.validate(GOOD) == []


def test_missing_field_blocks():
    m = copy.deepcopy(GOOD)
    del m["evidence_locator"]
    errs = mg.validate(m)
    assert any("evidence_locator" in e for e in errs)


def test_todo_left_blocks():
    m = copy.deepcopy(GOOD)
    m["source_location"] = "TODO_url_or_box_or_local"
    errs = mg.validate(m)
    assert any("TODO" in e and "source_location" in e for e in errs)


def test_enum_violation_blocks():
    m = copy.deepcopy(GOOD)
    m["rights_class"] = "rented"
    assert any("rights_class" in e for e in mg.validate(m))


def test_bad_sha256_blocks():
    m = copy.deepcopy(GOOD)
    m["files"] = [{"name": "x", "sha256": "deadbeef"}]
    assert any("sha256" in e for e in mg.validate(m))


def test_empty_files_blocks():
    m = copy.deepcopy(GOOD)
    m["files"] = []
    assert any("files" in e for e in mg.validate(m))


def test_record_count_must_be_positive_int():
    m = copy.deepcopy(GOOD)
    m["record_count"] = 0
    assert any("record_count" in e for e in mg.validate(m))
    m["record_count"] = "4490"
    assert any("record_count" in e for e in mg.validate(m))


def test_bad_fetched_at_blocks():
    m = copy.deepcopy(GOOD)
    m["fetched_at"] = "last tuesday"
    assert any("fetched_at" in e for e in mg.validate(m))


def test_stub_with_todos_fails_as_whole():
    """field_profile の stub をそのまま投入しようとしたら必ず止まること."""
    stub = {
        "source": "bengo4", "source_system": "TODO", "fetched_at": "TODO_capture_timestamp",
        "account": "TODO_owner_account", "fetch_method": "TODO_api|scrape|colophon_ocr",
        "acquisition_path": "TODO", "source_location": "TODO", "rights_class": "TODO",
        "medium_origin": "TODO", "route_local_id": "content_id", "key_field": "content_id",
        "toc_origin": "publisher_html", "extractor_version": "TODO", "record_count": 50,
        "files": [{"name": "x.jsonl", "sha256": "b" * 64, "bytes": None}],
        "evidence_locator": "TODO",
    }
    assert len(mg.validate(stub)) >= 5
