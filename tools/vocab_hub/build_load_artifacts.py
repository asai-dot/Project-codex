#!/usr/bin/env python3
"""P2 load 生成物ビルダ: defrag済 terms -> schema 対応の load-ready JSONL (DB非接続).

01_vocab_hub_schema.sql の各テーブルに 1:1 対応する JSONL を出力する.
実DBには書かない. owner GO + GPT監査 後に canary/batch loader がこの生成物を投入する想定.

入力: defrag済 terms (--terms ~/defrag/terms_defragged.jsonl) か Box から生成.
出力(--out, 既定 ~/vocab_load):
  alo_concept_schemes.jsonl / alo_terms.jsonl / alo_hubs.jsonl
  alo_hub_memberships.jsonl / alo_term_relations.jsonl / manifest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import build_hub_dryrun as bh
import defrag_terms as dft
import run_2dict as r2
import short_def_triage as sdt
import xref_extract as xr

# scheme_id -> (name, authority_rank, role, ingest_policy)
SCHEME_META = {
    "egov":                  ("e-Gov 法令用語(定義)", "100", "bedrock", "seed"),
    "yuhikaku_legal_dict":   ("有斐閣 法律用語辞典",  "101", "bedrock", "seed"),
    "hourei_yougo_jiten_11": ("学陽 法令用語辞典 第11次", "102", "bedrock", "seed"),
}


def _def_quality(t):
    d = (t.get("definition") or "").strip()
    if not d:
        return "empty"
    if len(d) < bh.SHORT_DEF_LEN:
        return sdt.classify_short(d)[0]   # cross_reference/valid_short/truncation/other
    return "ok"


def build_artifacts(terms, threshold=0.6):
    hubs, memberships, stats = bh.build_hubs(terms, threshold, quality_filter=True)
    by_tid = {bh._tid(t): t for t in terms}
    edges, _unresolved = xr.build_alias_edges(terms, threshold)

    # schemes (実在 scheme のみ)
    seen_schemes = {}
    for t in terms:
        sid = str(t.get("scheme_id"))
        if sid not in seen_schemes:
            name, rank, role, pol = SCHEME_META.get(
                sid, (sid, str(t.get("authority_rank")), "specialty", "attach"))
            seen_schemes[sid] = {"scheme_id": sid, "name": name, "authority_rank": rank,
                                 "role": role, "ingest_policy": pol}
    schemes = list(seen_schemes.values())

    # terms
    term_rows = []
    for t in terms:
        term_rows.append({
            "term_id": bh._tid(t), "scheme_id": t.get("scheme_id"),
            "normalized_pref": t.get("normalized_pref") or t.get("pref_label") or t.get("headword"),
            "reading": t.get("reading"), "definition": t.get("definition"),
            "term_tier": int(str(t.get("term_tier", 1)) or 1),
            "source_item_key": t.get("source_item_key") or t.get("source_term_key"),
            "reading_source": t.get("reading_source", "original"),
            "def_quality": _def_quality(t),
        })

    # hubs (needs_preprocessing / homograph_genuine 反映)
    hub_rows = []
    for h in hubs:
        anchor = by_tid.get(h["anchor_term_id"], {})
        hub_rows.append({
            "hub_id": h["hub_id"], "anchor_term_id": h["anchor_term_id"],
            "hub_label": h["hub_label"], "reading": h.get("reading"),
            "hub_status": "provisional",
            "identity_scope": "vocab_hub_provisional_noncanonical",
            "needs_preprocessing": h.get("needs_preprocessing", []),
            "homograph_genuine": bool(anchor.get("homograph_genuine", False)
                                      or h.get("homograph_conflict", False)),
        })

    # relations (alias エッジ: 解決分のみ load. 未解決は dst_label 保持で別レーン)
    rel_rows = []
    for e in edges:
        rel_rows.append({
            "src_term_id": e["source_term_id"],
            "dst_term_id": None,            # term_id 解決は hub->anchor 経由で loader が埋める
            "dst_label": e["target_pref"],
            "relation_type": e["relation"],
            "source": "xref_extract",
            "target_hub_id": e["target_hub_id"],
        })

    return {
        "alo_concept_schemes": schemes,
        "alo_terms": term_rows,
        "alo_hubs": hub_rows,
        "alo_hub_memberships": memberships,
        "alo_term_relations": rel_rows,
    }, stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="P2 load 生成物ビルダ (DB非接続)")
    ap.add_argument("--terms", default=None)
    ap.add_argument("--yuhikaku-terms", default=None)
    ap.add_argument("--yuhikaku-labels", default=None)
    ap.add_argument("--hourei-entries", default=None)
    ap.add_argument("--out", default=str(Path.home() / "vocab_load"))
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
    print(f"[load-artifacts] terms: {len(terms)}")

    tables, stats = build_artifacts(terms)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, rows in tables.items():
        with (out / f"{name}.jsonl").open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        manifest[name] = len(rows)
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[load-artifacts] 生成物 (DB非接続 / canary前提):")
    for name, n in manifest.items():
        print(f"  {name}: {n}")
    print(f"[load-artifacts] -> {out}/  (manifest.json 同梱). 実load は owner GO+監査後の loader.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
