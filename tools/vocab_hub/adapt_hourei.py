#!/usr/bin/env python3
"""学陽『法令用語辞典 第11次改訂版』entries -> 語彙Hub用 Term JSONL アダプタ (read-only).

入力: hourei_all_entries_v0.2_20260612.jsonl
  各行: {"scheme_id","entry_id","headword","reading","definition","flags",...}
  (phase1_5_parse_md_v0.2_calibrated.py 出力. 定義はインライン)

出力: build_hub_dryrun.py の Term スキーマ:
  {"stg_term_key","scheme_id","authority_rank":102,"term_tier":1,
   "pref_label","normalized_pref","reading","definition"}

normalized_pref は build_hub_dryrun.norm_pref と同一ロジック(有斐閣と揃える).
依存ゼロ. DBに書かない.
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

_FW_ALNUM = str.maketrans(
    "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")


def norm_pref(s: str) -> str:
    return unicodedata.normalize("NFC", str(s or "")).strip().translate(_FW_ALNUM)


def adapt(entries, scheme_id: str, authority_rank: int):
    out = []
    for e in entries:
        hw = (e.get("headword") or "").strip()
        if not hw:
            continue
        sid = e.get("scheme_id") or scheme_id
        eid = e.get("entry_id") or f"{sid}__{len(out) + 1:05d}"
        out.append({
            "stg_term_key": f"hstg_{eid}",
            "scheme_id": sid,
            "authority_rank": authority_rank,
            "term_tier": 1,
            "pref_label": hw,
            "normalized_pref": norm_pref(hw),
            "reading": e.get("reading") or None,
            "definition": (e.get("definition") or "").strip(),
            "source_item_key": eid,
        })
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="学陽 entries -> Hub用 Term JSONL (read-only)")
    ap.add_argument("--entries", required=True, type=Path)
    ap.add_argument("--scheme", default="hourei_yougo_jiten_11")
    ap.add_argument("--authority-rank", type=int, default=102)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)

    entries = []
    with a.entries.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    terms = adapt(entries, a.scheme, a.authority_rank)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8") as fh:
        for t in terms:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"[adapt-hourei] entries={len(entries)} -> terms={len(terms)} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
