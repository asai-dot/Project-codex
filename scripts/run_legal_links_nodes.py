#!/usr/bin/env python3
"""任意の TOC ノード jsonl（`text` フィールドを持つ行）に法令/判例リンクを付与する.

`biblio.bib_toc` を SQL でエクスポートした実データ等、article schema でない
汎用ノード列に対して legal_links を適用するための薄いドライバ。

入力 jsonl の各行は最低限 `text` を持てばよい（bib_id/ordinal/title 等は透過）。

Usage:
    python scripts/run_legal_links_nodes.py --nodes nodes.jsonl --out out_real
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codex.egov_index import EgovIndex  # noqa: E402
from codex.legal_links import extract_links  # noqa: E402

PASSTHROUGH = ("bib_id", "journal_book_id", "ordinal", "page", "level",
               "bib_title", "journal_title", "title", "pub_year", "form_type")


def run(nodes_path: str, egov_path: str | None, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    index = EgovIndex.load(egov_path) if egov_path else EgovIndex.load()

    out_path = os.path.join(out_dir, "legal_links_nodes.jsonl")
    n_nodes = n_links = n_statute = n_case = n_egov = 0
    with open(nodes_path, encoding="utf-8") as fin, \
            open(out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            node = json.loads(line)
            n_nodes += 1
            text = node.get("text") or node.get("title") or node.get("raw_label") or ""
            meta = {k: node[k] for k in PASSTHROUGH if k in node}
            for lk in extract_links(text, index):
                n_links += 1
                if lk["scheme"] == "jp_statute_ref":
                    n_statute += 1
                    if lk.get("article_in_egov"):
                        n_egov += 1
                else:
                    n_case += 1
                fout.write(json.dumps({**meta, "node_text": text, **lk},
                                      ensure_ascii=False) + "\n")

    return {"nodes": n_nodes, "links": n_links, "statute_refs": n_statute,
            "case_citations": n_case, "egov_confirmed_articles": n_egov,
            "out_path": out_path}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nodes", required=True, help="text フィールドを持つ jsonl")
    ap.add_argument("--egov", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    s = run(args.nodes, args.egov, args.out)
    print(f"nodes: {s['nodes']}  links: {s['links']} "
          f"(statute {s['statute_refs']}, egov-confirmed {s['egov_confirmed_articles']}, "
          f"case {s['case_citations']})")
    print("out:", s["out_path"])


if __name__ == "__main__":
    main()
