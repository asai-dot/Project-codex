#!/usr/bin/env python3
"""run_conformance — 設計三部作 適合性ハーネスの単一エントリ（依存ゼロ）。

Phase 0 の「設計が機械的に通る」証明を1コマンドで回し、DD別カバレッジ要約を出す。
production/Box/DB/OCR には一切触れない。alo_gpt_audit.py と同じ single-writer・read-only 規律。

使い方:
  python3 tools/conformance/run_conformance.py            # 全テスト実行 + 要約
  python3 tools/conformance/run_conformance.py --summary  # 要約のみ（テスト名一覧）
  python3 tools/conformance/run_conformance.py --json     # 機械可読サマリ
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.join(HERE, "tests")

# DD → module/test の対応（owner 5行サマリ用）
DD_MAP = {
    "DD-LAYOUT-001": ["test_layout_projection", "test_layout_hashbundle"],
    "DD-TRILOGY-RECONCILE-001": ["test_reconcile_indep_registry"],
    "DD-XMODAL-001": ["test_xmodal_agreement"],
    "DD-XDOC-001": [
        "test_xdoc_canonical", "test_xdoc_eligibility",
        "test_xdoc_coverage", "test_xdoc_support", "test_xdoc_ranges", "test_xdoc_method",
        "test_xdoc_claim", "test_xdoc_scope_binding", "test_xdoc_support_revision",
    ],
}


def _discover():
    sys.path.insert(0, HERE)
    return unittest.defaultTestLoader.discover(TESTS, pattern="test_*.py")


def _count_by_module(suite, acc=None):
    acc = acc if acc is not None else {}
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            _count_by_module(t, acc)
        else:
            mod = type(t).__module__
            acc[mod] = acc.get(mod, 0) + 1
    return acc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true", help="要約のみ")
    ap.add_argument("--json", action="store_true", help="機械可読サマリ")
    args = ap.parse_args(argv)

    suite = _discover()
    by_mod = _count_by_module(suite)

    if args.summary and not args.json:
        for dd, mods in DD_MAP.items():
            n = sum(by_mod.get(m, 0) for m in mods)
            print(f"{dd}: {n} tests  ({', '.join(mods)})")
        print(f"TOTAL: {sum(by_mod.values())} tests")
        return 0

    runner = unittest.TextTestRunner(verbosity=1, stream=sys.stderr)
    result = runner.run(suite)

    dd_summary = {
        dd: sum(by_mod.get(m, 0) for m in mods) for dd, mods in DD_MAP.items()
    }
    summary = {
        "total": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "ok": result.wasSuccessful(),
        "by_dd": dd_summary,
        "production_touched": False,  # 不変条件: 純関数のみ
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("\n=== 適合性ハーネス要約（Phase 0・production 不変） ===", file=sys.stderr)
        for dd, n in dd_summary.items():
            print(f"  {dd}: {n} tests", file=sys.stderr)
        print(f"  TOTAL: {summary['total']}  ok={summary['ok']}"
              f"  fail={summary['failures']}  err={summary['errors']}", file=sys.stderr)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
