"""Parse e-Gov Num / house path / kanji text-ref into a canonical ArticlePath."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from scripts.drafterintent.patterns import kanji_to_int, ARTICLE_RE


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class ArticlePath:
    """A provision locator. ``branch`` = 枝番 (第N条の*M*); para/item optional."""
    main: int
    branch: Optional[int] = None
    paragraph: Optional[int] = None
    item: Optional[int] = None

    def canonical(self) -> str:
        s = f"art:{self.main}"
        if self.branch is not None:
            s += f"-{self.branch}"
        if self.paragraph is not None:
            s += f":para:{self.paragraph}"
        if self.item is not None:
            s += f":item:{self.item}"
        return s

    def root(self) -> "ArticlePath":
        """条 root: drop paragraph/item (keeps 枝番). Used for dispute grouping."""
        return ArticlePath(self.main, self.branch)

    def sort_key(self) -> tuple:
        """Numeric ordering. Absent components sort *before* present ones so the
        bare article precedes its paragraphs (art:5 < art:5:para:1)."""
        def k(v: Optional[int]) -> tuple:
            return (0, 0) if v is None else (1, v)
        return (self.main, *k(self.branch), *k(self.paragraph), *k(self.item))

    def __str__(self) -> str:  # canonical is the string form
        return self.canonical()


def _to_int(tok: str) -> int:
    v = kanji_to_int(tok)
    if v is None:
        raise ParseError(f"not an ordinal: {tok!r}")
    return int(v)


_HOUSE_RE = re.compile(
    r"^art:(?P<main>[0-9]+)(?:-(?P<branch>[0-9]+))?"
    r"(?::para:(?P<para>[0-9]+))?(?::item:(?P<item>[0-9]+))?$"
)
# e-Gov Num: arabic (possibly zenkaku/kanji) tokens joined by '_' (398_22).
_EGOV_RE = re.compile(r"^[0-9０-９一二三四五六七八九十百千〇零]+(?:_[0-9０-９一二三四五六七八九十百千〇零]+)*$")


def from_house(s: str) -> ArticlePath:
    m = _HOUSE_RE.match(s.strip())
    if not m:
        raise ParseError(f"not a house path: {s!r}")
    g = m.groupdict()
    return ArticlePath(
        main=int(g["main"]),
        branch=int(g["branch"]) if g["branch"] else None,
        paragraph=int(g["para"]) if g["para"] else None,
        item=int(g["item"]) if g["item"] else None,
    )


def from_egov_num(num: str) -> ArticlePath:
    """e-Gov ``Article/@Num`` -> ArticlePath. ``398_22`` -> 第398条の22.

    e-Gov uses one ``_`` for a 枝番 (第N条の M). Deeper nesting (の M の K) would
    appear as a second ``_``; 民法 has none but we keep the first as branch and
    fold any extra into the branch via dotted notation to avoid data loss.
    """
    toks = [t for t in num.strip().split("_") if t != ""]
    if not toks:
        raise ParseError(f"empty egov num: {num!r}")
    main = _to_int(toks[0])
    branch = _to_int(toks[1]) if len(toks) > 1 else None
    if len(toks) > 2:
        # rare deep 枝番: keep readable, flag via branch string is not int-safe,
        # so encode as main with a composite branch is impossible in int; raise
        # so the caller logs it rather than silently mis-identifying.
        raise ParseError(f"deep 枝番 (>1 underscore) not yet modelled: {num!r}")
    return ArticlePath(main=main, branch=branch)


def from_text_ref(s: str) -> ArticlePath:
    """First 第N条… reference inside free text (kanji or arabic)."""
    m = ARTICLE_RE.search(s)
    if not m:
        raise ParseError(f"no article reference in text: {s!r}")
    main = _to_int(m.group("article"))
    branch = _to_int(m.group("branch")) if m.group("branch") else None
    para = _to_int(m.group("para")) if m.group("para") else None
    item = _to_int(m.group("item")) if m.group("item") else None
    return ArticlePath(main, branch, para, item)


def parse(s: str) -> ArticlePath:
    """Dispatch on shape: house path, e-Gov Num, or kanji/arabic text ref."""
    s = (s or "").strip()
    if not s:
        raise ParseError("empty")
    if s.startswith("art:"):
        return from_house(s)
    if "条" in s:
        return from_text_ref(s)
    if _EGOV_RE.match(s):
        return from_egov_num(s)
    # bare "398-22" house tail without prefix
    if re.match(r"^[0-9]+(-[0-9]+)?$", s):
        return from_house("art:" + s)
    raise ParseError(f"unrecognized article reference: {s!r}")


def sort_key(s: str) -> tuple:
    """Convenience: numeric sort key from any accepted form."""
    return parse(s).sort_key()
