"""Build an old↔new article crosswalk from lawdelta output (PLAN L4).

lawdelta emits one row per (article) with a ``delta_kind`` and, for moves,
``counterpart_paths``. The crosswalk turns that into queryable mappings so the
identity layer can answer "what is old art:X now?" across a revision — the
prerequisite for hanging references / 委任 edges and for not mis-grouping
disputes when articles are renumbered.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .normalize import parse, ArticlePath, ParseError

# delta_kind -> how identity flows old->new
_MOVE_KINDS = {"renumber", "relocate", "split", "join", "substitution"}


@dataclass
class CrosswalkEntry:
    relation: str                  # delta_kind
    old_path: Optional[str]        # canonical; None for insertion
    new_paths: List[str]           # canonical; [] for repeal, >1 for split
    text_changed: bool

    def to_dict(self) -> dict:
        return {"relation": self.relation, "old_path": self.old_path,
                "new_paths": self.new_paths, "text_changed": self.text_changed}


def _canon(p: str) -> str:
    try:
        return parse(p).canonical()
    except ParseError:
        return p  # keep raw if unparseable (and let the report flag it)


def build_crosswalk(delta_rows: List[dict]) -> List[CrosswalkEntry]:
    """delta_rows = parsed lawdelta JSONL objects."""
    out: List[CrosswalkEntry] = []
    for r in delta_rows:
        kind = r["delta_kind"]
        if kind == "no_change":
            continue
        path = r.get("article_path")
        counterparts = [c for c in (r.get("counterpart_paths") or [])]
        if kind == "insertion":
            out.append(CrosswalkEntry(kind, None, [_canon(path)], r.get("text_changed", True)))
        elif kind == "repeal":
            out.append(CrosswalkEntry(kind, _canon(path), [], r.get("text_changed", True)))
        elif kind in ("split",):
            out.append(CrosswalkEntry(kind, _canon(path),
                                      [_canon(c) for c in counterparts] or [_canon(path)],
                                      True))
        elif kind in ("join",):
            # several old -> this new; row is keyed on the surviving article
            out.append(CrosswalkEntry(kind, _canon(path),
                                      [_canon(c) for c in counterparts] or [_canon(path)],
                                      True))
        else:  # substitution / renumber / relocate: same identity, maybe moved
            new = [_canon(c) for c in counterparts] if counterparts else [_canon(path)]
            out.append(CrosswalkEntry(kind, _canon(path), new, r.get("text_changed", True)))
    return out


def old_to_new_index(entries: List[CrosswalkEntry]) -> Dict[str, List[str]]:
    idx: Dict[str, List[str]] = {}
    for e in entries:
        if e.old_path is not None:
            idx.setdefault(e.old_path, [])
            idx[e.old_path].extend(e.new_paths)
    return idx
