#!/usr/bin/env python3
"""staging 定義断片化の再結合 (read-only / source は書き換えない).

homograph_review.py が明らかにした「同 (scheme+pref+reading) で1エントリが複数 term 行に
割れている」断片化を、グループ単位で再結合・除去してクリーン term セットを生成する.
homograph_review.classify_pair の判定を流用:
  - continuation / subitem : base 定義へ連結(rejoin)
  - stub / empty / header / list_marker : 除去(drop)
  - merge_candidate : 長い方を残す(同概念の重複)
  - genuine_split : 別 term として保持(別概念/OCR矛盾 → owner)

出力: クリーン terms JSONL + 変更レポート. build_hubs を前後で回し homograph/短定義の縮みを実測.
DBに書かない.

    python3 tools/vocab_hub/defrag_terms.py            # Box自動探索→効果実測
    python3 tools/vocab_hub/defrag_terms.py --out ~/defrag
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import build_hub_dryrun as bh
import homograph_review as hr
import run_2dict as r2


def _def(t):
    return (t.get("definition") or "").strip()


def defrag(terms):
    """同 (scheme, norm_pref, norm_reading) グループの断片を再結合/除去する.

    戻り値: (cleaned_terms, stats). bedrock の tier1 のみ対象 (specialty/非tier1 はそのまま通す).
    """
    passthrough, target = [], []
    for t in terms:
        if bh.is_bedrock(t.get("authority_rank")) and str(t.get("term_tier", "1")) == "1":
            target.append(t)
        else:
            passthrough.append(t)

    groups = defaultdict(list)
    for t in target:
        key = (str(t.get("scheme_id")), bh.norm_pref(
            t.get("normalized_pref") or t.get("pref_label") or t.get("headword") or ""),
            bh.norm_reading(t.get("reading", "")))
        groups[key].append(t)

    cleaned = []
    stats = {"groups_multi": 0, "rejoined": 0, "dropped": 0, "merged": 0,
             "genuine_kept": 0, "klass": defaultdict(int)}
    for key, grp in groups.items():
        if len(grp) == 1:
            cleaned.append(grp[0])
            continue
        stats["groups_multi"] += 1
        # 原順序: stg_term_key/term_id 昇順 = 断片の並び
        grp = sorted(grp, key=lambda t: bh._tid(t))
        base = dict(grp[0])
        pref = key[1]
        for t in grp[1:]:
            klass, _ = hr.classify_pair(pref, _def(base), _def(t))
            stats["klass"][klass] += 1
            if klass == "artifact_continuation":
                # A が語の途中で切れている -> 区切りなしで連結 (規+定し=規定し)
                base["definition"] = (_def(base) + _def(t)).strip()
                stats["rejoined"] += 1
            elif klass == "artifact_subitem":
                # 番号サブ項目 -> 空白区切りで連結 (1)… 5)…)
                base["definition"] = (_def(base) + " " + _def(t)).strip()
                stats["rejoined"] += 1
            elif klass in ("artifact_stub", "artifact_empty", "artifact_header", "artifact_list_marker"):
                stats["dropped"] += 1
            elif klass == "merge_candidate":
                if len(_def(t)) > len(_def(base)):
                    keep_def = _def(t)
                    base["definition"] = keep_def
                stats["merged"] += 1
            else:  # genuine_split: 別 term として確定し base を切り替える
                cleaned.append(base)
                base = dict(t)
                base["homograph_genuine"] = True
                stats["genuine_kept"] += 1
        cleaned.append(base)

    stats["klass"] = dict(stats["klass"])
    stats["terms_in"] = len(terms)
    stats["terms_out"] = len(cleaned) + len(passthrough)
    return cleaned + passthrough, stats


def _short_anchor_count(terms, threshold=0.6):
    _, _, st = bh.build_hubs(terms, threshold, quality_filter=True)
    return st


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="staging 定義断片の再結合 (read-only)")
    ap.add_argument("--yuhikaku-terms", default=None)
    ap.add_argument("--yuhikaku-labels", default=None)
    ap.add_argument("--hourei-entries", default=None)
    ap.add_argument("--out", default=str(Path.home() / "defrag"))
    a = ap.parse_args(argv)

    yt = r2.find_one("yuhikaku_legal_dict_terms_stg_v3.jsonl", a.yuhikaku_terms)
    yl = r2.find_one("yuhikaku_legal_dict_labels_stg_v3.jsonl", a.yuhikaku_labels)
    he = r2.find_one("hourei_all_entries_v0.2_20260612.jsonl", a.hourei_entries)
    if not yt:
        print("ERROR: 有斐閣 terms が見つかりません。--yuhikaku-terms で明示。", file=sys.stderr)
        return 2

    terms, n_y, n_h = r2.load_terms(yt, yl, he)
    print(f"[defrag] terms in: 有斐閣={n_y} 学陽={n_h} 計={len(terms)}")

    before = _short_anchor_count(terms)
    cleaned, st = defrag(terms)
    after = _short_anchor_count(cleaned)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "terms_defragged.jsonl").open("w", encoding="utf-8") as fh:
        for t in cleaned:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")

    print(f"\n[defrag] 多member グループ {st['groups_multi']} を処理:")
    print(f"  rejoin(連結)     : {st['rejoined']}")
    print(f"  drop(除去)       : {st['dropped']}")
    print(f"  merge(重複統合)  : {st['merged']}")
    print(f"  genuine_split保持: {st['genuine_kept']}")
    print(f"  term 数: {st['terms_in']} -> {st['terms_out']}")
    print(f"\n[defrag] === 効果 (build_hubs 前後) ===")
    print(f"{'':16}{'before':>10}{'after':>10}")
    print(f"{'hubs':16}{before['hubs']:>10}{after['hubs']:>10}")
    print(f"{'homograph':16}{before['homograph_conflicts']:>10}{after['homograph_conflicts']:>10}")
    print(f"{'短def anchor':14}{before.get('anchors_short_def',0):>10}{after.get('anchors_short_def',0):>10}")
    print(f"{'空def anchor':14}{before.get('anchors_empty_def',0):>10}{after.get('anchors_empty_def',0):>10}")
    print(f"\n[defrag] cleaned -> {out}/terms_defragged.jsonl (read-only candidate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
