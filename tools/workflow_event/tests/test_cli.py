"""CLI (validate サブコマンド) の終了コードと出力を固定する。"""

import json
import os

from conftest import EXAMPLES_PATH, SCHEMA_PATH

from alo_workflow_event.cli import main


def test_validate_examples_exit_zero(capsys):
    rc = main(["validate", "--schema", SCHEMA_PATH, EXAMPLES_PATH])
    out = capsys.readouterr().out
    assert rc == 0
    assert "0 failed" in out


def test_validate_bad_file_exit_one(tmp_path, capsys):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"schema_version": "wrong"}) + "\n", encoding="utf-8")
    rc = main(["validate", "--schema", SCHEMA_PATH, str(bad)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAIL" in out


def test_validate_single_json(tmp_path, capsys):
    # examples の 1 行目を単体 .json として書き出し、green を確認。
    with open(EXAMPLES_PATH, "r", encoding="utf-8") as fh:
        first = json.loads(fh.readline())
    single = tmp_path / "one.json"
    single.write_text(json.dumps(first), encoding="utf-8")
    rc = main(["validate", "--schema", SCHEMA_PATH, str(single)])
    assert rc == 0


def test_validate_json_array(tmp_path, capsys):
    with open(EXAMPLES_PATH, "r", encoding="utf-8") as fh:
        events = [json.loads(l) for l in fh if l.strip()]
    arr = tmp_path / "arr.json"
    arr.write_text(json.dumps(events), encoding="utf-8")
    rc = main(["validate", "--schema", SCHEMA_PATH, str(arr)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "{} checked".format(len(events)) in out
