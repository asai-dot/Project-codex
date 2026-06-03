#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
assemble_term_card.py — golden term card 生成（用語ノード＝語彙レイヤ Hub の最終形）

e-Gov法定定義（錨・authority_rank=100）＋ 有斐閣/学陽 gloss ＋ JLT英訳・読み を、綺麗なキー
（見出し語）で join して1ノードに集約。錨に各源を刺し、多源で検証（読み一致・gloss相互確認）。

入力:
  --gold     egov_statutory_definitions*.jsonl（term, definition, law_name, uri, ...）
  --yuhikaku 有斐閣 all_entries（jsonl/txt: headword, definition, reading）  [任意]
  --gakuyo   学陽 all_entries.jsonl                                          [任意]
  --jlt-csv  JLT v19 CSV（用語,読み,…,訳語候補,…）                           [任意]
  --out-dir  カード出力先（既定 data/cards）
  terms...   対象見出し語（複数）
"""
import argparse
import csv
import json
import os
import sys
import unicodedata


def nf(s):
    return unicodedata.normalize("NFKC", (s or "")).strip()


def load_jsonl_map(path):
    d = {}
    if not path or not os.path.exists(path):
        return d
    for l in open(path, encoding="utf-8"):
        l = l.strip()
        if l[:1] != "{":
            continue
        try:
            o = json.loads(l)
        except json.JSONDecodeError:
            continue
        hw = nf(o.get("headword") or o.get("term"))
        if hw and hw not in d:
            d[hw] = {"definition": o.get("definition", ""), "reading": nf(o.get("reading", ""))}
    return d


def load_gold(path):
    g = {}
    for l in open(path, encoding="utf-8"):
        o = json.loads(l)
        g.setdefault(nf(o["term"]), []).append(o)
    return g


def load_jlt(path):
    d = {}
    if not path or not os.path.exists(path):
        return d
    for row in csv.DictReader(open(path, encoding="utf-8")):
        t = nf(row.get("用語"))
        if not t:
            continue
        e = d.setdefault(t, {"reading": nf(row.get("読み")), "en": []})
        tr = nf(row.get("訳語候補"))
        if tr and tr not in e["en"]:
            e["en"].append(tr)
    return d


def build(term, gold, Y, G, J):
    t = nf(term)
    yu = Y.get(t); ga = G.get(t); jl = J.get(t)
    readings = {}
    if jl and jl["reading"]:
        readings["JLT"] = jl["reading"]
    if yu and yu["reading"]:
        readings["有斐閣"] = yu["reading"]
    if ga and ga["reading"]:
        readings["学陽"] = ga["reading"]
    card = {
        "concept": t,
        "readings": readings,
        "reading_agreement": (len(set(readings.values())) == 1) if readings else None,
        "statutory_definitions": [
            {"law": g["law_name"], "uri": g["uri"], "authority_rank": g["authority_rank"],
             "definition_type": g.get("definition_type"), "confidence": g.get("confidence"),
             "definition": g["definition"]}
            for g in gold.get(t, [])
        ],
        "glosses": {**({"有斐閣": yu["definition"]} if yu else {}),
                    **({"学陽": ga["definition"]} if ga else {})},
        "jlt": ({"reading": jl["reading"], "en": jl["en"]} if jl else None),
    }
    return card


def pretty(card):
    L = [f"══════ GOLDEN TERM CARD 【{card['concept']}】 ══════"]
    if card["readings"]:
        ag = "（多源一致）" if card["reading_agreement"] else "（不一致＝要判定）"
        L.append("読み: " + " / ".join(f"{k}={v}" for k, v in card["readings"].items()) + " " + ag)
    for s in card["statutory_definitions"]:
        L.append(f"\n◆[錨] 法定定義 authority={s['authority_rank']} [{s.get('definition_type')}/{s.get('confidence')}]  {s['law']} {s['uri']}")
        L.append(f"  {s['definition'][:120]}")
    if not card["statutory_definitions"]:
        L.append("\n◆[錨] 法定定義: （e-Gov定義なし＝辞書gloss/JLTのみのノード）")
    for src, d in card["glosses"].items():
        L.append(f"\n・{src} gloss: {d[:120]}…")
    if card["jlt"] and card["jlt"]["en"]:
        L.append(f"\n・JLT 英訳: {' / '.join(card['jlt']['en'])}")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("terms", nargs="+")
    ap.add_argument("--gold", default="data/egov/egov_statutory_definitions_7laws.jsonl")
    ap.add_argument("--yuhikaku")
    ap.add_argument("--gakuyo", default="data/gakuyo/gakuyo_all_entries.jsonl")
    ap.add_argument("--jlt-csv")
    ap.add_argument("--out-dir", default="data/cards")
    args = ap.parse_args(argv)
    gold = load_gold(args.gold)
    Y = load_jsonl_map(args.yuhikaku)
    G = load_jsonl_map(args.gakuyo)
    J = load_jlt(args.jlt_csv)
    os.makedirs(args.out_dir, exist_ok=True)
    for term in args.terms:
        card = build(term, gold, Y, G, J)
        with open(f"{args.out_dir}/golden_term_card_{nf(term)}.json", "w", encoding="utf-8") as f:
            json.dump(card, f, ensure_ascii=False, indent=1)
        print(pretty(card) + "\n", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
