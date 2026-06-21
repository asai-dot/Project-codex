"""Parsers producing ArticleUnit lists.

Two input forms:

1. e-Gov 法令標準XML (スキーマ v3.0) — ``Law/LawBody/MainProvision//Article``.
   Notes from 30_law_layer §4.4: ``Article[@Delete="true"]`` is a deleted
   shell; the XML has no enforcement-date field (revision metadata carries it).
2. Plain JSONL fixtures — one object per article:
   ``{"article_number": "709", "caption": "...", "text": "...", "deleted": false}``

Only MainProvision is diffed in v0.1 (附則 SupplProvision is out of scope for
article deltas; it is lawtime's domain).
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Iterable, List

from .model import ArticleUnit, nfc


def _article_number_from_num(num: str) -> str:
    """e-Gov ``Num="709_2"`` (第709条の2) -> ``709-2`` (house style)."""
    return (num or "").strip().replace("_", "-").replace(":", "-")


def _gather_text(elem: ET.Element) -> str:
    """Concatenate Sentence-level text under an element, depth-first.

    Keeps proviso (ただし書) and items (号) inline; structure recovery beyond
    article granularity is Phase-2.1 (paragraph/item paths).
    """
    parts: List[str] = []
    for sent in elem.iter():
        if sent.tag in ("Sentence", "Column") and sent.text:
            parts.append(sent.text)
        # ParagraphNum / ItemTitle markers keep ordinal context for similarity
        elif sent.tag in ("ParagraphNum", "ItemTitle") and sent.text:
            parts.append(sent.text)
    return nfc("".join(parts))


def parse_egov_xml(path: str) -> List[ArticleUnit]:
    tree = ET.parse(path)
    root = tree.getroot()
    units: List[ArticleUnit] = []
    main = root.find(".//MainProvision")
    if main is None:
        return units
    for idx, art in enumerate(main.iter("Article")):
        num = _article_number_from_num(art.get("Num", ""))
        caption_el = art.find("ArticleCaption")
        caption = nfc(caption_el.text) if caption_el is not None and caption_el.text else ""
        deleted = (art.get("Delete") == "true")
        # exclude caption/title from the diffed body: body = paragraphs only
        body_parts = [_gather_text(p) for p in art.findall("Paragraph")]
        text = "".join(body_parts)
        units.append(ArticleUnit(
            article_path=f"art:{num}",
            article_number=num,
            caption=caption,
            text=text,
            deleted=deleted,
            order_index=idx,
        ))
    return units


def parse_articles_jsonl(path: str) -> List[ArticleUnit]:
    units: List[ArticleUnit] = []
    with open(path, encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            num = _article_number_from_num(str(obj["article_number"]))
            units.append(ArticleUnit(
                article_path=f"art:{num}",
                article_number=num,
                caption=obj.get("caption", ""),
                text=obj.get("text", ""),
                deleted=bool(obj.get("deleted", False)),
                order_index=obj.get("order_index", idx),
            ))
    return units


def load_articles(path: str) -> List[ArticleUnit]:
    if path.endswith(".xml"):
        return parse_egov_xml(path)
    return parse_articles_jsonl(path)
