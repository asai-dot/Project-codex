"""Map 改め文 (amendment sentences) to (article_path, delta_kind).

Conservative by design: only well-formed, unambiguous operations are typed;
anything else is ``unknown`` (never guessed). delta_kind values match
``scripts.lawdelta.model.DeltaRecord.DELTA_KIND_DOMAIN``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from scripts.articlepath import parse as parse_path, ParseError

_NUM = r"[0-9０-９一二三四五六七八九十百千〇零]+"
# an article token in 改め文: 第N条[のM]
_ART = rf"第(?P<art>{_NUM})条(?:の(?P<br>{_NUM}))?"
_ART_RE = re.compile(_ART)


@dataclass
class Amendment:
    article_path: Optional[str]   # canonical target (None if unresolved)
    delta_kind: str               # lawdelta domain
    operation: str                # short label of the matched 改め文 form
    new_path: Optional[str]       # for renumber/relocate (第X条を第Y条とする)
    snippet: str                  # the source sentence (provenance)

    def to_dict(self) -> dict:
        return {"article_path": self.article_path, "delta_kind": self.delta_kind,
                "operation": self.operation, "new_path": self.new_path,
                "snippet": self.snippet}


def _path(m: re.Match) -> Optional[str]:
    tok = "第" + m.group("art") + "条" + ("の" + m.group("br") if m.group("br") else "")
    try:
        return parse_path(tok).canonical()
    except ParseError:
        return None


def _all_paths(s: str) -> List[str]:
    out = []
    for m in _ART_RE.finditer(s):
        p = _path(m)
        if p:
            out.append(p)
    return out


def _expand_range(s: str) -> List[str]:
    """「第X条から第Y条まで」を [art:X..art:Y] に展開。枝番混在は安全側で空。"""
    paths = _all_paths(s)
    if len(paths) < 2 or "まで" not in s:
        return []
    a, b = paths[0], paths[1]
    # Both must be plain articles (no 枝番) for a numeric range to be safe.
    try:
        from scripts.articlepath import parse as parse_path
        pa, pb = parse_path(a), parse_path(b)
    except Exception:
        return []
    if pa.branch is not None or pb.branch is not None or pa.main > pb.main:
        return []
    return [f"art:{n}" for n in range(pa.main, pb.main + 1)]


def _split_sentences(text: str) -> List[str]:
    # 改め文 sentences end in 。; keep nonempty trimmed parts.
    return [s.strip() for s in re.split(r"(?<=。)", text) if s.strip()]


def parse_amendment_sentence(s: str) -> List[Amendment]:
    """Return zero or more operations expressed by a single 改め文 sentence."""
    first = _ART_RE.search(s)
    if not first:
        return []
    target = _path(first)

    # --- renumber/relocate: 第X条を第Y条とする / …に移す ---
    if "とする" in s:
        paths = _all_paths(s)
        if "条とする" in s and len(paths) >= 2:
            return [Amendment(paths[0], "renumber", "条とする(繰替)", paths[1], s)]
    if "に移す" in s or "へ移す" in s:
        paths = _all_paths(s)
        new = paths[1] if len(paths) >= 2 else None
        return [Amendment(target, "relocate", "移す", new, s)]

    # --- insertion: 第X条の次に次の(一|二|…)条を加える ---
    if re.search(r"の次に.*条を加える", s):
        paths = _all_paths(s)
        # If the added article number is spelled out in the same sentence it is
        # the token after the anchor; otherwise it appears in the FOLLOWING
        # sentence and is resolved by parse_amendments via lookahead (None here).
        added = paths[1] if len(paths) >= 2 else None
        return [Amendment(added, "insertion", "次に条を加える", None, s)]

    # --- substitution variants (article still exists, content changes) ---
    if "の見出しを" in s and "に改める" in s:
        return [Amendment(target, "substitution", "見出し改め", None, s)]
    if re.search(r"中「.*」を「.*」に改める", s):
        return [Amendment(target, "substitution", "中「」を「」に改める", None, s)]
    if "を次のように改める" in s:
        # range form: 第X条から第Y条までを次のように改める → 全条 substitution
        if "まで" in s:
            r = _expand_range(s)
            if r:
                return [Amendment(p, "substitution", "範囲を次のように改める", None, s)
                        for p in r]
        return [Amendment(target, "substitution", "次のように改める", None, s)]
    if re.search(r"に次の.*(項|号)を加える", s):
        return [Amendment(target, "substitution", "項/号を加える", None, s)]
    if re.search(r"(項|号)を削る", s):
        return [Amendment(target, "substitution", "項/号を削る", None, s)]
    if re.search(r"中「.*」を削る", s):  # phrase deletion within an article
        return [Amendment(target, "substitution", "中「」を削る", None, s)]

    # --- repeal: 第X条[及び第Y条][の枝番]を削る (article-level deletion) ---
    if "を削る" in s and _all_paths(s):
        return [Amendment(p, "repeal", "条を削る", None, s) for p in _all_paths(s)]

    # recognized an article but not a known operation form
    return [Amendment(target, "unknown", "未分類", None, s)]


def _leading_article(s: str) -> Optional[str]:
    """Article path if the sentence *begins* with an article token (the added
    article block of an insertion: 「第778条の2　…」)."""
    m = _ART_RE.match(s.lstrip())
    return _path(m) if m else None


def parse_amendments(text: str) -> List[Amendment]:
    sents = _split_sentences(text)
    out: List[Amendment] = []
    skip = set()
    for i, s in enumerate(sents):
        if i in skip:
            continue
        for a in parse_amendment_sentence(s):
            if a.delta_kind == "insertion" and a.article_path is None:
                # added article number is in the following sentence block
                if i + 1 < len(sents):
                    added = _leading_article(sents[i + 1])
                    if added:
                        a = Amendment(added, "insertion", a.operation, None, s)
                        skip.add(i + 1)  # consumed as the added article, not its own op
            out.append(a)
    return out
