#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gate_egov_anchors.py — e-Gov 法定定義錨に「機械ゲート」をかけ、出所権威と抽出成功度を分離する

GPTレビュー（2026-06-03）次手①②の実装:
  ① egov_statutory_definitions_*.jsonl に機械ゲート（article欠落 / uriのNone / 括弧・引用符バランス /
     term長・definition長 / law_id有無 / confidence↔definition_type整合）。
  ② authority_rank=100 を以下に分解（「e-Gov由来＝100点」の誤読を防ぐ）:
       source_authority_rank : 出所の権威（e-Gov=100）。不変。
       extraction_confidence : 正規表現抽出の成功度（元の confidence: high/medium）。
       canonical_status      : candidate（ゲート通過）/ quarantined（ハード失格）。
       review_status         : unreviewed / needs_review（ソフトフラグ）。
     gate_reasons[] に失格・要確認理由を残す。生データ非改変・auto_apply=false。

出力: <out_prefix>_gated.jsonl（canonical候補）/ <out_prefix>_quarantine.jsonl（失格、理由付き）。
使い方: python3 gate_egov_anchors.py IN.jsonl OUT_PREFIX
"""
import argparse
import json
import re
import sys
from collections import Counter

DEF_TAIL = re.compile(r"(をいう|をいい|という)。?$")
HIGH_TYPES = {"item_definition", "inline_toha", "paren_definition"}
MEDIUM_TYPES = {"paren_abbreviation"}


def balanced(s):
    return s.count("（") == s.count("）") and s.count("「") == s.count("」")


def gate(d):
    """returns (hard_fail_reasons, soft_review_reasons)"""
    hard, soft = [], []
    term, defi = d.get("term", ""), d.get("definition", "")
    dtype, conf = d.get("definition_type"), d.get("confidence")

    # --- ハード失格（canonical候補に入れない） ---
    if d.get("article") in (None, ""):
        hard.append("article_null")
    if "None" in (d.get("uri") or "") or ":art::" in (d.get("uri") or ""):
        hard.append("uri_none")
    if not d.get("law_id"):
        hard.append("law_id_missing")
    if not balanced(defi):
        hard.append("bracket_imbalance")
    if not term or not defi:
        hard.append("empty_field")
    # 定義型と末尾の整合（略称型 paren_abbreviation は被定義語＝末尾「をいう」不要）
    if dtype in HIGH_TYPES and not DEF_TAIL.search(defi):
        hard.append("no_definition_tail")
    # confidence↔type 整合
    if dtype in HIGH_TYPES and conf != "high":
        hard.append("conf_type_mismatch")
    if dtype in MEDIUM_TYPES and conf != "medium":
        hard.append("conf_type_mismatch")

    # --- ソフト（残すが要確認） ---
    if len(term) > 30:
        soft.append("term_too_long")
    if len(defi) > 200:
        soft.append("definition_too_long")
    if len(defi) < 6:
        soft.append("definition_too_short")
    return hard, soft


def relabel(d, hard, soft):
    """authority_rank を4フィールドに分解した新レコードを返す（生フィールドは保持）。"""
    out = dict(d)
    out["source_authority_rank"] = d.get("authority_rank", 100)   # e-Gov由来＝100（出所権威）
    out["extraction_confidence"] = d.get("confidence")            # 抽出成功度（high/medium）
    out["canonical_status"] = "quarantined" if hard else "candidate"
    out["review_status"] = "needs_review" if (soft and not hard) else "unreviewed"
    out["gate_reasons"] = hard + soft
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out_prefix")
    args = ap.parse_args(argv)

    gated, quarantine = [], []
    hard_c, soft_c = Counter(), Counter()
    for l in open(args.inp, encoding="utf-8"):
        l = l.strip()
        if l[:1] != "{":
            continue
        d = json.loads(l)
        hard, soft = gate(d)
        rec = relabel(d, hard, soft)
        for r in hard:
            hard_c[r] += 1
        for r in soft:
            soft_c[r] += 1
        (quarantine if hard else gated).append(rec)

    with open(f"{args.out_prefix}_gated.jsonl", "w", encoding="utf-8") as f:
        for d in gated:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    with open(f"{args.out_prefix}_quarantine.jsonl", "w", encoding="utf-8") as f:
        for d in quarantine:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    total = len(gated) + len(quarantine)
    gh = sum(1 for d in gated if d["extraction_confidence"] == "high")
    gm = sum(1 for d in gated if d["extraction_confidence"] == "medium")
    nr = sum(1 for d in gated if d["review_status"] == "needs_review")
    print("=== gate_egov_anchors ===", file=sys.stderr)
    print(f"in {total} → gated {len(gated)} (high {gh} / medium {gm}; needs_review {nr}) "
          f"/ quarantine {len(quarantine)}", file=sys.stderr)
    print(f"hard fails: {dict(hard_c)}", file=sys.stderr)
    print(f"soft flags: {dict(soft_c)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
