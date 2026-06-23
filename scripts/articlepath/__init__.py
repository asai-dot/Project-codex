"""scripts.articlepath — canonical article identity (PLAN L4: 同定の地盤).

The connection axis (DD-LAWREF-001) and dispute grouping (assembler) both hang
on one thing: deciding that two references point at the *same* provision. e-Gov
gives article numbers three ways that must collapse to one canonical key:

  - XML ``Num`` attribute (arabic, ``_`` separator):  ``398_22`` = 第398条の22
  - house style (lawdelta / DD-LAWTIME tail):         ``art:398-22``
  - text references (kanji, in commentary/judgments):  第三百九十八条の二十二第二項

This package parses all three into ``ArticlePath`` and emits a canonical string
plus a *numeric* sort key (so ``art:398-2`` < ``art:398-22`` — string sorting
gets this wrong). It also builds an old↔new ``crosswalk`` from lawdelta output.

Reuses ``kanji_to_int`` from scripts.drafterintent (single source of truth for
kanji ordinals). Stdlib only, no DB.
"""
from .normalize import ArticlePath, parse, sort_key, ParseError

__all__ = ["ArticlePath", "parse", "sort_key", "ParseError"]
