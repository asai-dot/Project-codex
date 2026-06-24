"""alo-workflow-event CLI — workflow event envelope を stdlib のみで検証する。

  alo-workflow-event validate --schema <schema.json> <data.json|data.jsonl> ...

  * .jsonl は 1 行 1 イベントとして全行を検証。
  * .json は単一オブジェクト、又は配列(各要素を検証)。
  * 全件 green で exit 0、1 件でも失敗で exit 1。

外部 pip 依存なし(python3 標準ライブラリのみ)。
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple

from . import __version__
from .validator import iter_errors


def _load_schema(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _iter_instances(path: str) -> List[Tuple[str, Any]]:
    """(label, instance) のリストを返す。jsonl は行ごと、json は単体/配列。"""
    out: List[Tuple[str, Any]] = []
    if path.endswith(".jsonl"):
        with open(path, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                out.append(("{}:{}".format(path, lineno), json.loads(line)))
    else:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            for i, item in enumerate(data):
                out.append(("{}[{}]".format(path, i), item))
        else:
            out.append((path, data))
    return out


def _cmd_validate(args: argparse.Namespace) -> int:
    schema = _load_schema(args.schema)
    total = 0
    failed = 0
    for data_path in args.data:
        try:
            instances = _iter_instances(data_path)
        except (OSError, ValueError) as exc:
            print("ERROR {}: {}".format(data_path, exc), file=sys.stderr)
            failed += 1
            continue
        for label, instance in instances:
            total += 1
            errors = iter_errors(instance, schema)
            if errors:
                failed += 1
                print("FAIL {}".format(label))
                for err in errors:
                    print("    - {}".format(err))
            elif args.verbose:
                print("ok   {}".format(label))

    passed = total - failed
    print("{} checked, {} passed, {} failed".format(total, passed, failed))
    return 0 if failed == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alo-workflow-event",
        description="ALO workflow event envelope を stdlib のみで検証する。",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser(
        "validate", help="schema に対してデータ(.json/.jsonl)を検証する"
    )
    p_validate.add_argument(
        "--schema", required=True, help="JSON Schema ファイルへのパス"
    )
    p_validate.add_argument(
        "data", nargs="+", help="検証対象の .json / .jsonl ファイル"
    )
    p_validate.add_argument(
        "-v", "--verbose", action="store_true", help="green 行も表示する"
    )
    p_validate.set_defaults(func=_cmd_validate)
    return parser


def main(argv: List[str] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
