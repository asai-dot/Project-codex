#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
egov_definition_extract.py — e-Gov法令JSONから「定義条項」を golden data として抽出

ゴールデンデータ（用語→法定定義）。authority_rank=100 / scheme=jp_statutory_definition。
ALO 法令レイヤ URI体系: egov:{law_id}:art:{article}[:item:{n}]。

抽出する2書式:
  (1) 号建て定義（会社法2条型）: Item の ItemSentence が Column を持ち、Column1=用語・
      Column2…=定義（末尾「をいう／をいい／という」）。
  (2) 文中定義: Paragraph 文の「『X』とは、…をいう」「Xとは、…をいう」。

生データ非改変。出力は jsonl（term, definition, law_id, law_name, article, item, uri,
scheme, authority_rank, source）。

使い方: python3 egov_definition_extract.py OUT.jsonl LAWNAME=egov.json [LAWNAME=egov.json ...]
"""
import argparse
import json
import re
import sys


def text(n):
    if isinstance(n, str):
        return n
    if isinstance(n, dict):
        return "".join(text(c) for c in n.get("children", []) or [])
    if isinstance(n, list):
        return "".join(text(c) for c in n)
    return ""


def children(n, tag):
    return [c for c in (n.get("children", []) or [])
            if isinstance(c, dict) and c.get("tag") == tag]


DEF_TAIL = re.compile(r"(をいう|をいい|という)。?$")
# 文中定義の3書式（号建てColumnは別処理）
P_TOHA = re.compile(r"「([^「」]{1,30})」とは[、，]?(.{2,80}?(?:をいう|をいい))。")   # 「X」とは、…をいう
P_PAREN = re.compile(r"(?<=[をはがにへとやもの、。「」）・　])([一-龥々ー]{2,15}[ぁ-ん]{0,3})（((?:[^（）]){4,90}?をいう)。")  # X（…をいう）
P_ABBR = re.compile(r"(?:^|[、。）])([^、。「」（）]{3,60}?)（以下(?:[^「）]{0,15})?「([^」]{1,20})」という。?）")  # …（以下「X」という）
_LEAD = re.compile(r"^(?:又は|若しくは|及び|並びに|かつ|が|は|を|に|の|で|と|から|より|、|。|・)+")


def law_meta(doc):
    law_id = (doc.get("law_info") or {}).get("law_id")
    name = ""
    def find_title(n):
        nonlocal name
        if name:
            return
        if isinstance(n, dict):
            if n.get("tag") == "LawTitle":
                name = text(n); return
            for c in n.get("children", []) or []:
                find_title(c)
        elif isinstance(n, list):
            for c in n:
                find_title(c)
    find_title(doc.get("law_full_text"))
    return law_id, name


def extract(doc, law_name_override=None):
    law_id, law_name = law_meta(doc)
    law_name = law_name_override or law_name
    out = []
    seen = set()

    def add(term, definition, article, item, dtype, confidence):
        term = term.strip(); definition = definition.strip()
        if not term or len(term) > 40 or not definition:
            return
        uri = f"egov:{law_id}:art:{article}" + (f":item:{item}" if item else "")
        key = (term, article)
        if key in seen:
            return
        seen.add(key)
        out.append({"term": term, "definition": definition, "law_id": law_id,
                    "law_name": law_name, "article": article, "item": item,
                    "uri": uri, "scheme": "jp_statutory_definition",
                    "authority_rank": 100, "source": "egov",
                    "definition_type": dtype, "confidence": confidence})

    def walk(n, article=None):
        if isinstance(n, dict):
            if n.get("tag") == "Article":
                article = (n.get("attr") or {}).get("Num")
            if n.get("tag") == "Item" and article:
                inum = (n.get("attr") or {}).get("Num")
                # (1) 号建てColumn定義（会社法2条型）= high
                isent = children(n, "ItemSentence")
                if isent:
                    cols = children(isent[0], "Column")
                    if len(cols) >= 2:
                        term = text(cols[0])
                        deftxt = "".join(text(c) for c in cols[1:])
                        for sub in n.get("children", []) or []:
                            if isinstance(sub, dict) and str(sub.get("tag", "")).startswith("Subitem"):
                                deftxt += text(sub)
                        if DEF_TAIL.search(deftxt):
                            add(term, deftxt, article, inum, "item_definition", "high")
            # (2) 文中・括弧書き定義（Sentence テキスト）
            if n.get("tag") == "Sentence":
                t = text(n)
                for m in P_TOHA.finditer(t):                       # 「X」とは…をいう = high
                    add(m.group(1), m.group(2) + "。", article, None, "inline_toha", "high")
                for m in P_PAREN.finditer(t):                      # X（…をいう）= high
                    add(m.group(1), m.group(2) + "。", article, None, "paren_definition", "high")
                for m in P_ABBR.finditer(t):                       # …（以下「X」という）= medium（定義句境界がfuzzy）
                    add(m.group(2), _LEAD.sub("", m.group(1)), article, None, "paren_abbreviation", "medium")
            for c in n.get("children", []) or []:
                walk(c, article)
        elif isinstance(n, list):
            for c in n:
                walk(c, article)

    walk(doc.get("law_full_text"))
    return law_id, law_name, out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("sources", nargs="+", help="LAWNAME=path.json")
    args = ap.parse_args(argv)
    allout = []
    print("=== e-Gov 定義条項抽出 ===", file=sys.stderr)
    for spec in args.sources:
        name, path = spec.split("=", 1)
        doc = json.loads(open(path, encoding="utf-8").read())
        lid, lname, defs = extract(doc, law_name_override=name)
        allout.extend(defs)
        print(f"  {name} ({lid}): {len(defs)} 定義", file=sys.stderr)
    with open(args.out, "w", encoding="utf-8") as f:
        for d in allout:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"計 {len(allout)} 定義 → {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
