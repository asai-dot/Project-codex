"""workflow_event テスト用フィクスチャ。

リポジトリ同梱の v0.2 schema / examples の実パスを解決して提供する。
(tools/workflow_event/tests/ から 3 つ上が repo root)。
"""

import json
import os

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
_V02_DIR = os.path.join(_REPO_ROOT, "docs", "workflow_model", "v0.2")

SCHEMA_PATH = os.path.join(_V02_DIR, "alo_workflow_event_schema_v0.2.json")
EXAMPLES_PATH = os.path.join(_V02_DIR, "alo_workflow_event_examples_v0.2.jsonl")


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_jsonl(path):
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


@pytest.fixture
def schema():
    return load_json(SCHEMA_PATH)


@pytest.fixture
def examples():
    return load_jsonl(EXAMPLES_PATH)
