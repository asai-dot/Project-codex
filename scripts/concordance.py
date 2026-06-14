"""concordance — 複数ソース TOC の対応付け (DDLEGALLIBCONCORD v0.3.1, report-only)。

各ソース(legallib/lion/bencom/pdf)の正規化ノードを横断クラスタ化し、各入力ノードを
matched / orphan のいずれかに必ず分類する (all_nodes_accounted_for; silent discard 無し)。
merge も final_toc 生成もしない。本番書き込みなし。stdlib のみ・決定的。
"""


from __future__ import annotations

CONCORDANCE_VERSION = "0.3.1"

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _toc_text import normalize_title  # noqa: E402

# 章番号体系の検出 (numbering_scheme_changed 用)。
_NUM_SCHEMES = {
    "kanji_chapter": re.compile(r"第[0-9０-９]+[章編節]"),
    "kanji_num": re.compile(r"第[一二三四五六七八九十百]+[章編節]"),
    "roman": re.compile(r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]"),
    "article": re.compile(r"(article|art\.)\s*\d+", re.IGNORECASE),
    "arabic": re.compile(r"^[0-9０-９]+[\.\s　]"),
}


def numbering_scheme(title: str) -> str | None:
    for name, rx in _NUM_SCHEMES.items():
        if rx.search(title or ""):
            return name
    return None


def normalize_source_nodes(source: str, nodes: list[dict]) -> list[dict]:
    """1 ソースの生ノード列 → 正規化ノード列 (title_norm/depth/page を共通形に)。"""
    out = []
    for i, n in enumerate(nodes):
        if not isinstance(n, dict):
            continue
        title = n.get("t") or n.get("label") or n.get("title") or ""
        tnorm = normalize_title(title)
        if not tnorm:
            continue
        depth = n.get("depth") or n.get("l") or n.get("level") or 1
        try:
            depth = int(depth)
        except (TypeError, ValueError):
            depth = 1
        page = n.get("page_start")
        if page is None:
            page = n.get("p") or n.get("pdf_page") or n.get("print_page")
        out.append({
            "source": source, "idx": i, "title": title, "title_norm": tnorm,
            "depth": depth, "page": page, "scheme": numbering_scheme(title),
        })
    return out


def build_concordance(sources_nodes: dict[str, list[dict]]) -> dict:
    """{source: 生ノード列} → concordance。

    Returns:
        {
          "normalized": {source: [正規化ノード...]},
          "clusters": [{title_norm, depths, sources, members, kind}],   # kind=matched|orphan
          "accounting": {total_nodes, matched, orphan, accounted},
          "all_nodes_accounted_for": bool,
          "repeated_headings": {source: {title_norm: count>1}},
        }
    """
    normalized = {s: normalize_source_nodes(s, ns) for s, ns in sources_nodes.items()}

    # title_norm でクラスタ化。各ソース内の出現回数も数える。
    clusters: dict[str, dict] = {}
    repeated: dict[str, dict[str, int]] = {}
    for source, nodes in normalized.items():
        seen_in_source: dict[str, int] = {}
        for n in nodes:
            key = n["title_norm"]
            seen_in_source[key] = seen_in_source.get(key, 0) + 1
            c = clusters.setdefault(key, {"title_norm": key, "members": [],
                                          "sources": set(), "depths": set()})
            c["members"].append(n)
            c["sources"].add(source)
            c["depths"].add(n["depth"])
        for key, cnt in seen_in_source.items():
            if cnt > 1:
                repeated.setdefault(source, {})[key] = cnt

    total = sum(len(v) for v in normalized.values())
    matched = orphan = 0
    cluster_list = []
    for key, c in clusters.items():
        kind = "matched" if len(c["sources"]) >= 2 else "orphan"
        member_count = len(c["members"])
        if kind == "matched":
            matched += member_count
        else:
            orphan += member_count
        cluster_list.append({
            "title_norm": key, "kind": kind,
            "sources": sorted(c["sources"]), "depths": sorted(c["depths"]),
            "member_count": member_count,
        })

    accounted = matched + orphan
    return {
        "normalized": normalized,
        "clusters": cluster_list,
        "accounting": {"total_nodes": total, "matched": matched, "orphan": orphan,
                       "accounted": accounted},
        # 全ノードが matched/orphan のどちらかに入っている (silent discard 無し)。
        "all_nodes_accounted_for": accounted == total,
        "repeated_headings": repeated,
    }


__all__ = ["numbering_scheme", "normalize_source_nodes", "build_concordance"]
