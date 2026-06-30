"""field_profile.py の最小テスト (read-only プロファイラの不変則)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import field_profile as fp  # noqa: E402


def _write(tmp_path, name, rows):
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return str(p)


def test_isbn13_checksum():
    assert fp.isbn13_checksum_ok("9784335357114")
    assert not fp.isbn13_checksum_ok("9784335357115")
    assert not fp.isbn13_checksum_ok("123")


def test_isbn10_checksum():
    assert fp.isbn10_checksum_ok("4335357117") or fp.isbn10_checksum_ok("030640615X")
    assert not fp.isbn10_checksum_ok("4335357110")


def test_normalize_isbn_rejects_nonscalar():
    assert fp.normalize_isbn({"a": 1}) is None
    assert fp.normalize_isbn(None) is None
    assert fp.normalize_isbn("978-4-335-35711-4") == "9784335357114"


def test_bengo4_has_no_isbn_autodetected(tmp_path):
    """監査の核: bengo4 は無ISBN. 自動推定で isbn_field=None になること."""
    path = _write(tmp_path, "bengo4.jsonl", [
        {"content_id": f"c{i}", "title": {"main": "x"}, "toc": ["a", "b"]} for i in range(5)
    ])
    p = fp.profile(path, key=None, isbn_field=None, toc_field=None)
    assert p["isbn_field"] is None
    assert p["key_field"] == "content_id"
    assert p["key_unique_pct"] == 100.0
    assert p["toc_coverage_pct"] == 100.0


def test_isbn_route_coverage_and_validity(tmp_path):
    path = _write(tmp_path, "lb.jsonl", [
        {"book_id": "b1", "isbn": "9784335357114"},
        {"book_id": "b2", "isbn": "9784335357114"},  # dup
        {"book_id": "b3", "isbn": ""},               # empty -> not counted
        {"book_id": "b4", "isbn": "9784335357115"},  # present but invalid checksum
    ])
    p = fp.profile(path, key="book_id", isbn_field="isbn", toc_field=None)
    assert p["record_count"] == 4
    assert p["isbn_coverage_pct"] == 75.0          # 3 of 4 present
    assert p["isbn_duplicate_rows"] == 1
    assert 60.0 <= p["isbn_valid_pct_of_present"] <= 70.0  # 2 of 3 valid


def test_bad_json_counted(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"a":1}\nnot json\n{"a":2}\n', encoding="utf-8")
    r = fp.profile(str(p), key="a", isbn_field=None, toc_field=None)
    assert r["record_count"] == 3
    assert r["bad_json_lines"] == 1
