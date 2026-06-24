#!/usr/bin/env python3
"""homograph 44件の owner レビューパケット生成 (read-only).

build_hubs が「同 (pref+reading) だが定義の重なりが閾値未満」で別 hub にした
homograph_conflict を、anchor 側の定義と並べて owner が split/merge を判断できる形に出力する.

同一スキーマ内の genuine な同綴異義のみが対象 (cross-scheme は常に merge ポリシー).
出力: markdown(人間レビュー用) + JSONL(機械処理用). DBに書かない.

    python3 tools/vocab_hub/homograph_review.py            # Box自動探索
    python3 tools/vocab_hub/homograph_review.py --out ~/homograph_review
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import build_hub_dryrun as bh
import run_2dict as r2


def collect_pairs(terms, threshold=0.6):
    """homograph_split された hub を anchor 側と対にして返す."""
    hubs, mem, stats = bh.build_hubs(terms, threshold, quality_filter=True)
    by_tid = {bh._tid(t): t for t in terms}

    # (pref, reading) -> 非homograph の主 hub (anchor 側)
    main_by_key = {}
    for h in hubs:
        if not h.get("homograph_conflict") and not h.get("specialty_only") and not h.get("reading_missing"):
            main_by_key.setdefault((h["hub_label"], h.get("reading", "")), h)

    pairs = []
    for h in hubs:
        if not h.get("homograph_conflict"):
            continue
        key = (h["hub_label"], h.get("reading", ""))
        main = main_by_key.get(key)
        conflict_t = by_tid.get(h["anchor_term_id"], {})
        anchor_t = by_tid.get(main["anchor_term_id"], {}) if main else {}
        pairs.append({
            "pref": h["hub_label"],
            "reading": h.get("reading", ""),
            "overlap": h.get("homograph_overlap"),
            "anchor": {
                "term_id": bh._tid(anchor_t),
                "scheme_id": anchor_t.get("scheme_id"),
                "authority_rank": anchor_t.get("authority_rank"),
                "definition": anchor_t.get("definition", ""),
            },
            "conflict": {
                "term_id": h["anchor_term_id"],
                "scheme_id": conflict_t.get("scheme_id"),
                "authority_rank": conflict_t.get("authority_rank"),
                "definition": conflict_t.get("definition", ""),
            },
            "same_scheme": str(conflict_t.get("scheme_id")) == str(anchor_t.get("scheme_id")),
        })
    return pairs, stats


def to_markdown(pairs, stats, threshold):
    lines = [
        "# homograph レビューパケット (owner判断用 / read-only)",
        "",
        f"> 同 (正規化見出し + 読み) だが定義の char-bigram Jaccard < {threshold} で**別hubに分離**した候補。",
        f"> 各件 split(別概念として維持) か merge(同概念・OCR/言い換え差) を判断してください。",
        f"> homograph 総数: **{len(pairs)}** (stats.homograph_conflicts={stats['homograph_conflicts']})",
        "",
        "判断の目安: 定義が**別概念**(例: 社員=会社法上の地位 vs 労働者一般) なら split 維持。",
        "同概念の**言い換え/OCR揺れ/詳しさの差**なら merge 指定。",
        "",
        "| # | 見出し | 読み | overlap | 同scheme | 判断(split/merge) |",
        "|---|---|---|---|---|---|",
    ]
    for i, p in enumerate(pairs, 1):
        ov = f"{p['overlap']:.3f}" if p["overlap"] is not None else "-"
        lines.append(f"| {i} | {p['pref']} | {p['reading']} | {ov} | "
                     f"{'✓' if p['same_scheme'] else '×'} |  |")
    lines += ["", "---", ""]
    for i, p in enumerate(pairs, 1):
        ov = f"{p['overlap']:.3f}" if p["overlap"] is not None else "-"
        lines += [
            f"## {i}. {p['pref']}（{p['reading']}） overlap={ov}",
            "",
            f"- **A (anchor)** [{p['anchor']['scheme_id']} / rank{p['anchor']['authority_rank']}]:",
            f"  > {p['anchor']['definition'] or '(定義なし)'}",
            "",
            f"- **B (split)** [{p['conflict']['scheme_id']} / rank{p['conflict']['authority_rank']}]:",
            f"  > {p['conflict']['definition'] or '(定義なし)'}",
            "",
            "判断: [ ] split維持  [ ] merge  メモ: ",
            "",
        ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="homograph owner レビューパケット (read-only)")
    ap.add_argument("--yuhikaku-terms", default=None)
    ap.add_argument("--yuhikaku-labels", default=None)
    ap.add_argument("--hourei-entries", default=None)
    ap.add_argument("--out", default=str(Path.home() / "homograph_review"))
    ap.add_argument("--threshold", type=float, default=0.6)
    a = ap.parse_args(argv)

    yt = r2.find_one("yuhikaku_legal_dict_terms_stg_v3.jsonl", a.yuhikaku_terms)
    yl = r2.find_one("yuhikaku_legal_dict_labels_stg_v3.jsonl", a.yuhikaku_labels)
    he = r2.find_one("hourei_all_entries_v0.2_20260612.jsonl", a.hourei_entries)
    if not yt:
        print("ERROR: 有斐閣 terms が見つかりません。--yuhikaku-terms で明示。", file=sys.stderr)
        return 2

    terms, n_y, n_h = r2.load_terms(yt, yl, he)
    print(f"[homograph] terms: 有斐閣={n_y} 学陽={n_h} 計={len(terms)}")

    pairs, stats = collect_pairs(terms, a.threshold)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "homograph_review.md").write_text(to_markdown(pairs, stats, a.threshold), encoding="utf-8")
    with (out / "homograph_review.jsonl").open("w", encoding="utf-8") as fh:
        for p in pairs:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")

    same = sum(1 for p in pairs if p["same_scheme"])
    print(f"[homograph] 候補 {len(pairs)} 件 (同scheme {same} / cross {len(pairs)-same}) -> {out}/homograph_review.md")
    print("[homograph] cross-scheme が残っていれば merge ポリシー漏れ. owner は md の各件で split/merge を判断.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
