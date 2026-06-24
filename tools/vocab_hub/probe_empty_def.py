#!/usr/bin/env python3
"""空定義 term(有斐閣712)が hub 構築でどこへ landing したか追跡する (read-only).

run_2dict の --quality-filter で「空def要前処理=7」と出た. 監査では空定義712件あった.
705件はどこへ消えたのか? 仮説: 同 (見出し+読み) の「定義あり行」に吸収された redundant 行.
本ツールは空定義 term を anchor / 非anchorメンバー / 単独hub に分類して実数で示す.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import adapt_hourei as ah
import build_hub_dryrun as bh

CANDIDATE_ROOTS = ["Library/CloudStorage", "Box"]


def find_one(name, override=None):
    if override:
        return Path(override)
    for root in CANDIDATE_ROOTS:
        base = Path.home() / root
        if base.exists():
            for p in base.rglob(name):
                return p
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="空定義 term の hub landing 追跡 (read-only)")
    ap.add_argument("--yuhikaku-terms", default=None)
    ap.add_argument("--yuhikaku-labels", default=None)
    ap.add_argument("--hourei-entries", default=None)
    a = ap.parse_args(argv)

    yt = find_one("yuhikaku_legal_dict_terms_stg_v3.jsonl", a.yuhikaku_terms)
    yl = find_one("yuhikaku_legal_dict_labels_stg_v3.jsonl", a.yuhikaku_labels)
    he = find_one("hourei_all_entries_v0.2_20260612.jsonl", a.hourei_entries)

    terms = list(bh.read_jsonl(yt))
    if yl:
        bh.attach_definitions(terms, bh.read_jsonl(yl))
    if he:
        # run_2dict と同じく reading補完③(有斐閣pref引き継ぎ)を効かせて整合させる
        y_rmap = {}
        for t in terms:
            np = bh.norm_pref(t.get("normalized_pref") or t.get("pref_label") or "")
            r = bh.norm_reading(t.get("reading", ""))
            if np and r and np not in y_rmap:
                y_rmap[np] = t.get("reading", "")
        entries = [json.loads(x) for x in Path(he).read_text(encoding="utf-8").splitlines() if x.strip()]
        terms.extend(ah.adapt(entries, "hourei_yougo_jiten_11", 102, yuhikaku_reading_map=y_rmap))

    # 空定義 term の id 集合
    empty_terms = [t for t in terms if not (t.get("definition") or "").strip()]
    empty_ids = {bh._tid(t) for t in empty_terms}
    print(f"[probe] 空定義 term: {len(empty_ids)}")

    # 空定義 term の素性分類: なぜ membership に出ないか
    e_nontier1 = sum(1 for t in empty_terms
                     if bh.is_bedrock(t.get("authority_rank")) and str(t.get("term_tier", "1")) != "1")
    e_tier1_bedrock = sum(1 for t in empty_terms
                          if bh.is_bedrock(t.get("authority_rank")) and str(t.get("term_tier", "1")) == "1")
    e_specialty = sum(1 for t in empty_terms if not bh.is_bedrock(t.get("authority_rank")))
    print(f"  内訳: bedrock+tier1={e_tier1_bedrock} / bedrock+非tier1(seed除外)={e_nontier1} / specialty={e_specialty}")

    hubs, mem, stats = bh.build_hubs(terms, 0.6, quality_filter=True)

    # membership を hub 単位に集約
    by_hub = {}
    for m in mem:
        by_hub.setdefault(m["hub_id"], []).append(m)
    hub_member_count = {h["hub_id"]: h["member_count"] for h in hubs}
    anchor_of = {h["hub_id"]: h["anchor_term_id"] for h in hubs}

    as_anchor_multi = as_anchor_single = as_member = unknown = 0
    member_partner_defined = 0
    for m in mem:
        tid = m["term_id"]
        if tid not in empty_ids:
            continue
        hid = m["hub_id"]
        is_anchor = (anchor_of.get(hid) == tid)
        mc = hub_member_count.get(hid, 1)
        if is_anchor and mc == 1:
            as_anchor_single += 1
        elif is_anchor and mc > 1:
            as_anchor_multi += 1
        else:
            as_member += 1
            # この hub の anchor に定義があるか
            ah_tid = anchor_of.get(hid)
            ah_term = next((t for t in terms if bh._tid(t) == ah_tid), None)
            if ah_term and (ah_term.get("definition") or "").strip():
                member_partner_defined += 1

    print(f"  単独hub の anchor (真の空定義穴)   : {as_anchor_single}")
    print(f"  複数memberhub の anchor (空のまま代表): {as_anchor_multi}")
    print(f"  非anchorメンバー (吸収)            : {as_member}")
    print(f"    うち anchor が定義あり (redundant行): {member_partner_defined}")
    print()
    print(f"[probe] needs_preprocessing 付き hub (anchor空定義): {stats['anchors_empty_def']}")
    print(f"[probe] needs_preprocessing 付き hub (anchor短定義): {stats['anchors_short_def']}")
    print()
    print("=== 解釈 ===")
    print("「非anchorメンバー(吸収)」かつ「anchorが定義あり」が多ければ、")
    print("空定義712の大半は同見出し+読みの定義あり行の redundant 重複であり、")
    print("hub レベルでは穴ではない. 真の穴は『単独hubのanchor』の数.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
