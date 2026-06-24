"""TOC タイトル正規化 (接合・突合・トリアージで共有).

`sync_safe_codex_toc_into_app.py` の normalize_title と同方針 (NFKC + 記号除去)。
タイトル集合の重なり判定 (Jaccard 等) に使う。
"""

from __future__ import annotations

import re
import unicodedata

_STRIP_RE = re.compile(
    r"[\s　・･:：,_\-\(\)\[\]【】「」『』“”\"'./&＆ー―−‐‑‒–—]+"
)


def normalize_title(text: str) -> str:
    s = unicodedata.normalize("NFKC", text or "").lower()
    return _STRIP_RE.sub("", s)


def title_set(nodes: list[dict]) -> set[str]:
    out = set()
    for n in nodes:
        t = normalize_title(n.get("t") or n.get("label") or "")
        if t:
            out.add(t)
    return out


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


__all__ = ["normalize_title", "title_set", "jaccard"]
