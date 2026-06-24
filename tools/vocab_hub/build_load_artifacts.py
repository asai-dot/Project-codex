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


_MEMBERSHIP_COLS = ("hub_id", "term_id", "map_type", "is_anchor", "definition_overlap")


def _norm_rank(v):
    """authority_rank を正規化(trim + str). 監査 Finding 5."""
    return str(v).strip() if v is not None else None


def build_artifacts(terms, threshold=0.6):
    hubs, memberships, stats = bh.build_hubs(terms, threshold, quality_filter=True)
    by_tid = {bh._tid(t): t for t in terms}
    edges, _unresolved = xr.build_alias_edges(terms, threshold)
    drops = {"empty_term_id": 0, "dup_term_id": 0}

    # schemes (実在 scheme のみ, rank 正規化)
    seen_schemes = {}
    for t in terms:
        sid = str(t.get("scheme_id"))
        if sid not in seen_schemes:
            name, rank, role, pol = SCHEME_META.get(
                sid, (sid, _norm_rank(t.get("authority_rank")), "specialty", "attach"))
            seen_schemes[sid] = {"scheme_id": sid, "name": name, "authority_rank": _norm_rank(rank),
                                 "role": role, "ingest_policy": pol}
    schemes = list(seen_schemes.values())

    # terms (term_id 非空+一意を保証. 監査 Finding 1: 空/重複は load しない・件数記録)
    term_rows, seen_ids = [], set()
    for t in terms:
        tid = bh._tid(t)
        if not tid:
            drops["empty_term_id"] += 1
            continue
        if tid in seen_ids:
            drops["dup_term_id"] += 1
            continue
        seen_ids.add(tid)
        term_rows.append({
            "term_id": tid, "scheme_id": t.get("scheme_id"),
            "normalized_pref": t.get("normalized_pref") or t.get("pref_label") or t.get("headword"),
            "reading": t.get("reading"), "definition": t.get("definition"),
            "term_tier": int(str(t.get("term_tier", 1)) or 1),
            "source_item_key": t.get("source_item_key") or t.get("source_term_key"),
            "reading_source": t.get("reading_source", "original"),
            "def_quality": _def_quality(t),
        })

    # hubs: anchor が emit 済 term の場合のみ(FK保証). homograph_genuine は defrag フラグのみ(監査 Finding 7)
    hub_rows, kept_hubs = [], set()
    for h in hubs:
        if h["anchor_term_id"] not in seen_ids:
            continue  # anchor が落ちた hub は出さない(FK違反防止)
        anchor = by_tid.get(h["anchor_term_id"], {})
        kept_hubs.add(h["hub_id"])
        hub_rows.append({
            "hub_id": h["hub_id"], "anchor_term_id": h["anchor_term_id"],
            "hub_label": h["hub_label"], "reading": h.get("reading"),
            "hub_status": "provisional",
            "identity_scope": "vocab_hub_provisional_noncanonical",
            "needs_preprocessing": h.get("needs_preprocessing", []),
            "homograph_genuine": bool(anchor.get("homograph_genuine", False)),
        })

    # memberships: DDL 列のみに射影 + FK保証(hub/term 共に emit 済). 監査 Finding 2
    mem_rows = []
    for m in memberships:
        if m["hub_id"] not in kept_hubs or m["term_id"] not in seen_ids:
            continue
        mem_rows.append({k: m.get(k) for k in _MEMBERSHIP_COLS})

    # relations: dst_term_id を builder で解決済にする(監査 Finding 3). DDL 列のみ.
    rel_rows = []
    for e in edges:
        if e["source_term_id"] not in seen_ids:
            continue
        dst = e.get("target_anchor_term_id")
        rel_rows.append({
            "src_term_id": e["source_term_id"],
            "dst_term_id": dst if dst in seen_ids else None,
            "dst_label": e["target_pref"],
            "relation_type": e["relation"],
            "source": "xref_extract",
        })

    stats["load_drops"] = drops
    return {
        "alo_concept_schemes": schemes,
        "alo_terms": term_rows,
        "alo_hubs": hub_rows,
        "alo_hub_memberships": mem_rows,
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
    manifest["_load_drops"] = stats.get("load_drops", {})
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[load-artifacts] 生成物 (DB非接続 / canary前提):")
    for name, n in manifest.items():
        if name != "_load_drops":
            print(f"  {name}: {n}")
    drops = stats.get("load_drops", {})
    if drops.get("empty_term_id") or drops.get("dup_term_id"):
        print(f"  [drop] term_id 空={drops['empty_term_id']} 重複={drops['dup_term_id']} (FK保証のため除外)")
    print(f"[load-artifacts] -> {out}/  (manifest.json 同梱). 実load は owner GO+監査後の loader.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
