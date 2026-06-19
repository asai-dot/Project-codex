#!/usr/bin/env python3
"""silver_resolve デモ: synthetic fixture を生成し silver-1/silver-2 を回して artifacts/ へ.

実データ無しでツールの動作を検証する (gpt_audit/demo_run.py と同流儀).
本物の Box 同期データへ向ける手順は RUNBOOK.md を参照.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import silver_cite_id as s1
import silver_toc_section as s2

REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "artifacts"


def _w(path: Path, rows):
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    ARTIFACTS.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # --- silver-1 fixture (掲載位置→判例ID) ---
        pub = [
            {"hanrei_id": "27824765", "journal": "労働判例", "issue": "1060", "page": "5"},
            {"hanrei_id": "27000001", "journal": "民集", "issue": "48-5", "page": "1165"},
            {"hanrei_id": "28011518", "journal": "判例タイムズ", "issue": "850", "page": "100"},
            {"hanrei_id": "28011519", "journal": "判例タイムズ", "issue": "850", "page": "100"},  # 同頁複数
        ]
        lic = [
            {"edge_id": "lic:1", "edge_type": "cites_judgment_via_journal",
             "source_locator": "journal_article:労判:1060:5"},            # 正規化要 -> exact strong
            {"edge_id": "lic:2", "edge_type": "cites_judgment_via_journal",
             "source_locator": "journal_article:民集:48-5:1165"},         # exact strong
            {"edge_id": "lic:3", "edge_type": "cites_judgment_via_journal",
             "source_locator": "journal_article:判例タイムズ:850:100"},   # 多候補 -> review
            {"edge_id": "lic:4", "edge_type": "cites_judgment_via_journal",
             "source_locator": "journal_article:労働判例:1060:"},         # 頁欠 -> 号fallback review
            {"edge_id": "lic:5", "edge_type": "cites_judgment_via_journal",
             "source_locator": "こわれた文字列"},                          # parse 不能 -> locator_unresolvable
            {"edge_id": "lic:6", "edge_type": "cites_judgment_via_journal",
             "source_locator": "journal_article:金融商事判例:9999:1"},     # 索引に無 -> db_unbuilt
            {"edge_id": "lic:7", "edge_type": "cites_judgment_by_date",
             "court": "最高裁", "date": "1994-07-18"},                     # court+date -> review
        ]
        canon = [{"hanrei_id": "27824765", "court": "最高裁", "date": "1994-07-18"}]
        norm = {"労判": "労働判例"}
        authority = {"authority_dataset_version": "periodical_20260611_demo",
                     "authority_hash": "demohash", "rule_version": "v0.1"}
        _w(d / "lic.jsonl", lic)
        _w(d / "pub.jsonl", pub)
        _w(d / "canon.jsonl", canon)
        (d / "norm.json").write_text(json.dumps(norm, ensure_ascii=False), encoding="utf-8")
        (d / "authority.json").write_text(json.dumps(authority, ensure_ascii=False), encoding="utf-8")

        s1.main(["--lic-edges", str(d / "lic.jsonl"), "--pub-index", str(d / "pub.jsonl"),
                 "--canon-index", str(d / "canon.jsonl"), "--norm-dict", str(d / "norm.json"),
                 "--authority-snapshot", str(d / "authority.json"),
                 "--out", str(d / "out1")])
        (ARTIFACTS / "DEMO_silver_cite_resolution_report.md").write_text(
            (d / "out1" / "silver_cite_resolution_report.md").read_text(encoding="utf-8"),
            encoding="utf-8")

        # --- silver-2 fixture (TOC→論点section) ---
        nodes = [
            {"toc_node_id": "t1", "parent_id": None, "book_id": "b1",
             "heading": "第3章 賃貸借", "kind": "heading"},
            {"toc_node_id": "t2", "parent_id": "t1", "book_id": "b1",
             "heading": "賃料不払を理由とする解除と信頼関係破壊", "kind": "heading"},
            {"toc_node_id": "r1", "parent_id": "t2", "book_id": "b1", "kind": "row"},
            {"toc_node_id": "r2", "parent_id": "t2", "book_id": "b1", "kind": "row"},
            {"toc_node_id": "t3", "parent_id": "t1", "book_id": "b1",
             "heading": "転借人への代払の機会", "kind": "heading"},
            {"toc_node_id": "r3", "parent_id": "t3", "book_id": "b1", "kind": "row"},
        ]
        edges = [
            {"toc_node_id": "r1", "hanrei_id": "27824765", "book_id": "b1"},
            {"toc_node_id": "r2", "hanrei_id": "27000001", "book_id": "b1"},  # t2 で 27824765 と共起
            {"toc_node_id": "r3", "hanrei_id": "28011518", "book_id": "b1"},  # 別section
        ]
        hyo = [{"hanrei_id": "27824765", "hyoshaku_count": 11},
               {"hanrei_id": "27000001", "hyoshaku_count": 11}]
        _w(d / "nodes.jsonl", nodes)
        _w(d / "edges.jsonl", edges)
        _w(d / "hyo.jsonl", hyo)

        s2.main(["--toc-nodes", str(d / "nodes.jsonl"), "--toc-edges", str(d / "edges.jsonl"),
                 "--hyoshaku", str(d / "hyo.jsonl"), "--out", str(d / "out2")])
        (ARTIFACTS / "DEMO_silver_toc_section_report.md").write_text(
            (d / "out2" / "silver_toc_section_report.md").read_text(encoding="utf-8"),
            encoding="utf-8")

    print(f"[demo] reports -> {ARTIFACTS}/DEMO_silver_*.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
