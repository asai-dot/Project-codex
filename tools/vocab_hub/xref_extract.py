#!/usr/bin/env python3
"""cross_reference 短定義を see_alias / see_also エッジ candidate に構造化する (read-only).

short_def_triage で判明した「相互参照」短定義(共有持分`→持分`/計理`「経理」`)を:
  1. target 見出しを抽出 (矢印後 / 「」内)
  2. 同 scheme 内の hub に解決 (hub_label の norm_pref 一致)
  3. alias エッジ candidate を出力: source term -> target hub (alias_of / see_also)

語彙ハブの別名解決 = P3 entity linking(DD-EL-001) の入力資産. DBに書かない.

    python3 tools/vocab_hub/xref_extract.py --terms ~/defrag/terms_defragged.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import build_hub_dryrun as bh
import defrag_terms as dft
import run_2dict as r2
import short_def_triage as sdt

_ARROWS = "↓→⇨↳⇒➡⟶⬆⬇←⟹➔➜"
_ARROW_RE = re.compile(f"[{_ARROWS}]")
_LEAD_ARROW = re.compile(f"^[{_ARROWS}\\s]+")
_QUOTE = re.compile(r"「([^」]+)」")


def parse_xref_target(definition: str):
    """cross_reference 定義から target 見出しを抽出. 取れなければ None."""
    d = (definition or "").strip()
    if not d:
        return None
    # 「X」括弧参照: 最初の括弧内
    mq = _QUOTE.search(d)
    if mq and not _ARROW_RE.search(d):
        return mq.group(1).strip() or None
    # 矢印参照: 最後の矢印より後ろを target とする
    if _ARROW_RE.search(d):
        tail = _ARROW_RE.split(d)[-1]
        tail = _LEAD_ARROW.sub("", tail).strip(" 。．、，「」（）()")
        # 括弧が残ればその中身を優先
        mq2 = _QUOTE.search(tail)
        if mq2:
            return mq2.group(1).strip() or None
        return tail or None
    return None


def build_alias_edges(terms, threshold=0.6):
    """cross_reference term を hub に解決し alias エッジ candidate を返す.

    解決は **同 scheme 内**に限定する(辞書内参照前提). hub の scheme は anchor term から取る.
    target_hub の anchor_term_id も返し、loader が dst_term_id を埋められるようにする.
    """
    hubs, _, _ = bh.build_hubs(terms, threshold, quality_filter=True)
    by_tid = {bh._tid(t): t for t in terms}

    # (anchor scheme, hub_label の norm_pref) -> [(hub_id, anchor_term_id)] 解決用インデックス
    # scheme を混ぜると別辞書の同綴 hub に誤解決するため scheme でキーを切る(監査 Finding 3).
    label_index = defaultdict(list)
    for h in hubs:
        anchor = by_tid.get(h["anchor_term_id"], {})
        sch = str(anchor.get("scheme_id"))
        label_index[(sch, bh.norm_pref(h["hub_label"]))].append((h["hub_id"], h["anchor_term_id"]))
    # hub の scheme は membership が要るが、ここでは hub_label 一致のみで解決(同辞書内参照前提)

    edges, unresolved = [], []
    # cross_reference は anchor に限らず全 bedrock term を走査
    for t in terms:
        if not (bh.is_bedrock(t.get("authority_rank")) and str(t.get("term_tier", "1")) == "1"):
            continue
        d = (t.get("definition") or "").strip()
        klass, _ = sdt.classify_short(d) if len(d) < bh.SHORT_DEF_LEN else ("", "")
        if klass != "cross_reference":
            continue
        target = parse_xref_target(d)
        src_pref = t.get("normalized_pref") or t.get("pref_label") or ""
        rec = {
            "source_term_id": bh._tid(t), "source_pref": src_pref,
            "source_reading": t.get("reading", ""), "scheme_id": t.get("scheme_id"),
            "raw_definition": d, "target_pref": target,
        }
        if not target:
            unresolved.append({**rec, "reason": "target抽出不可(矢印のみ等)"})
            continue
        # 同 scheme 内で target 見出しの hub を引く. 自分が anchor の hub は除外(自己参照防止).
        src_tid = bh._tid(t)
        cands = [(hid, atid) for hid, atid in
                 label_index.get((str(t.get("scheme_id")), bh.norm_pref(target)), [])
                 if atid != src_tid]
        if cands:
            hid, atid = cands[0]
            edges.append({**rec, "target_hub_id": hid, "target_anchor_term_id": atid,
                          "target_hub_candidates": [c[0] for c in cands],
                          "relation": "alias_of" if len(target) >= len(src_pref) else "see_also",
                          "resolved": True})
        else:
            unresolved.append({**rec, "reason": "同scheme内にtarget見出しのhubが無い(別辞書/未収録)"})
    return edges, unresolved


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="cross_reference -> alias エッジ candidate (read-only)")
    ap.add_argument("--terms", default=None)
    ap.add_argument("--yuhikaku-terms", default=None)
    ap.add_argument("--yuhikaku-labels", default=None)
    ap.add_argument("--hourei-entries", default=None)
    ap.add_argument("--out", default=str(Path.home() / "xref_edges"))
    a = ap.parse_args(argv)

    if a.terms:
        terms = list(bh.read_jsonl(Path(a.terms)))
    else:
        yt = r2.find_one("yuhikaku_legal_dict_terms_stg_v3.jsonl", a.yuhikaku_terms)
        yl = r2.find_one("yuhikaku_legal_dict_labels_stg_v3.jsonl", a.yuhikaku_labels)
        he = r2.find_one("hourei_all_entries_v0.2_20260612.jsonl", a.hourei_entries)
        if not yt:
            print("ERROR: 有斐閣 terms が見つかりません。", file=sys.stderr)
            return 2
        raw, _, _ = r2.load_terms(yt, yl, he)
        terms, _ = dft.defrag(raw)
    print(f"[xref] terms: {len(terms)}")

    edges, unresolved = build_alias_edges(terms)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "alias_edges_candidate.jsonl").open("w", encoding="utf-8") as fh:
        for e in edges:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    with (out / "xref_unresolved.jsonl").open("w", encoding="utf-8") as fh:
        for e in unresolved:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    total = len(edges) + len(unresolved)
    rate = 100 * len(edges) / total if total else 0
    print(f"[xref] cross_reference {total} 件:")
    print(f"  解決(alias エッジ) : {len(edges)} ({rate:.0f}%)")
    print(f"  未解決            : {len(unresolved)} (target hub 無し/抽出不可)")
    print(f"[xref] -> {out}/alias_edges_candidate.jsonl (read-only / P3 entity linking 入力)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
