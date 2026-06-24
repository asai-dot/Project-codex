#!/usr/bin/env python3
"""homograph候補の owner レビューパケット生成 + 自動分類 (read-only).

build_hubs が「同 (pref+reading) だが定義の重なりが閾値未満」で別 hub にした
homograph_conflict を、anchor 側の定義と並べて出力する.

実データ(44件)を見ると大半は genuine な多義ではなく **staging の定義断片化アーティファクト**
(定義が文途中で切れ次行へ continuation / 番号サブ項目 / 読み・相互参照スタブ / 空・ヘッダのみ /
リストマーカー見出し). これを classify_pair で自動分類し:
  - genuine_candidate: owner判断(split維持/merge)が要る少数
  - artifact_*       : staging再結合・除去で homograph から消える(owner判断不要)
に振り分ける. 同じ断片化が短定義489の一部も水増ししている可能性が高い.

同一スキーマ内のみ対象 (cross-scheme は常に merge ポリシー).
出力: markdown(人間レビュー用) + JSONL(機械処理用). DBに書かない.

    python3 tools/vocab_hub/homograph_review.py            # Box自動探索
    python3 tools/vocab_hub/homograph_review.py --out ~/homograph_review
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import build_hub_dryrun as bh
import run_2dict as r2

_TERMINATORS = "。．.！？!?」』）)"
_LIST_HEADWORD = re.compile(r"^(?:その\d+|[イロハニホヘトチリヌ][\)）]|[（(]?\d+[）)]|[①-⑳㋐-㋾])$")
_HEADER_ONLY = re.compile(r"^[【\[][^】\]]*[】\]]\s*$")
_SUBITEM_START = re.compile(r"^[2-9２-９]\s*[）)]|^[（(]?[2-9２-９][）)]|^(?:次に|また[，、]|なお[，、])")


def classify_pair(pref, a_def, b_def):
    """homograph候補を staging artifact か genuine 多義かに自動分類する.

    断片化(定義が文途中で切れ次行へ続く)/スタブ/空/番号サブ項目/リストマーカー見出し は
    parse artifact = owner判断不要(staging再結合/除去で解決). それ以外を genuine_candidate.
    保守的: 曖昧なものは genuine 側に残して owner が見る(誤って自動mergeしない).
    """
    a = (a_def or "").strip()
    b = (b_def or "").strip()
    if _LIST_HEADWORD.match(pref or ""):
        return "artifact_list_marker", "見出しがリストマーカー(語ではない)"
    if not b or b == "(定義なし)":
        return "artifact_empty", "B側定義が空"
    if _HEADER_ONLY.match(b):
        return "artifact_header", "B側が見出し記号のみ(【n)】等)"
    # スタブ: 短く文末記号で終わらない (読み/相互参照/語片)
    if len(b) <= 16 and not b.endswith(("。", "．")):
        return "artifact_stub", "B側が短いスタブ(読み/相互参照断片)"
    # 断片化: A が文末記号で終わらず途中で切れている = 次行(B)への continuation
    if a and a[-1] not in _TERMINATORS:
        return "artifact_continuation", "A側が文途中で切れB側へ continuation"
    # 番号付きサブ項目の続き (1)→2)5) 等)
    if _SUBITEM_START.match(b):
        return "artifact_subitem", "B側が番号サブ項目の続き(2)3)5)/次に/また)"
    return "genuine_candidate", "A/B双方が完結した別定義(要owner判断)"


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
        a_def = anchor_t.get("definition", "")
        b_def = conflict_t.get("definition", "")
        klass, reason = classify_pair(h["hub_label"], a_def, b_def)
        pairs.append({
            "pref": h["hub_label"],
            "reading": h.get("reading", ""),
            "overlap": h.get("homograph_overlap"),
            "klass": klass,
            "klass_reason": reason,
            "anchor": {
                "term_id": bh._tid(anchor_t),
                "scheme_id": anchor_t.get("scheme_id"),
                "authority_rank": anchor_t.get("authority_rank"),
                "definition": a_def,
            },
            "conflict": {
                "term_id": h["anchor_term_id"],
                "scheme_id": conflict_t.get("scheme_id"),
                "authority_rank": conflict_t.get("authority_rank"),
                "definition": b_def,
            },
            "same_scheme": str(conflict_t.get("scheme_id")) == str(anchor_t.get("scheme_id")),
        })
    return pairs, stats


_ARTIFACT_CLASSES = ("artifact_list_marker", "artifact_empty", "artifact_header",
                     "artifact_stub", "artifact_continuation", "artifact_subitem")


def _detail_block(i, p):
    ov = f"{p['overlap']:.3f}" if p["overlap"] is not None else "-"
    return [
        f"### {i}. {p['pref']}（{p['reading']}） overlap={ov}  [{p['klass']}]",
        f"_{p['klass_reason']}_",
        "",
        f"- **A (anchor)** [{p['anchor']['scheme_id']} / rank{p['anchor']['authority_rank']}]:",
        f"  > {p['anchor']['definition'] or '(定義なし)'}",
        "",
        f"- **B (split)** [{p['conflict']['scheme_id']} / rank{p['conflict']['authority_rank']}]:",
        f"  > {p['conflict']['definition'] or '(定義なし)'}",
        "",
        "判断: [ ] split維持  [ ] merge(再結合)  メモ: ",
        "",
    ]


def to_markdown(pairs, stats, threshold):
    genuine = [p for p in pairs if p["klass"] == "genuine_candidate"]
    artifacts = [p for p in pairs if p["klass"] in _ARTIFACT_CLASSES]
    klass_counts = {}
    for p in pairs:
        klass_counts[p["klass"]] = klass_counts.get(p["klass"], 0) + 1

    lines = [
        "# homograph レビューパケット (owner判断用 / read-only)",
        "",
        f"> 同 (正規化見出し + 読み) だが定義の char-bigram Jaccard < {threshold} で**別hubに分離**した候補を",
        "> **自動分類**した。`genuine_candidate` のみ owner 判断が要る。`artifact_*` は staging の",
        "> 定義断片化/スタブ/空行で、再結合・除去で解決する(owner判断不要)。",
        f"> homograph 総数: **{len(pairs)}**  /  genuine(要判断): **{len(genuine)}**  /  artifact: **{len(artifacts)}**",
        "",
        "## 自動分類サマリ",
        "| クラス | 件数 | 扱い |",
        "|---|---|---|",
    ]
    _handling = {
        "genuine_candidate": "**owner判断**(split維持/merge)",
        "artifact_continuation": "staging再結合(定義が途中で切れ次行へ)",
        "artifact_subitem": "staging再結合(番号サブ項目の続き)",
        "artifact_stub": "除去(読み/相互参照スタブ)",
        "artifact_empty": "除去(空定義)",
        "artifact_header": "除去(見出し記号のみ)",
        "artifact_list_marker": "除去(見出しがリストマーカー)",
    }
    for k in ["genuine_candidate", "artifact_continuation", "artifact_subitem",
              "artifact_stub", "artifact_empty", "artifact_header", "artifact_list_marker"]:
        if klass_counts.get(k):
            lines.append(f"| {k} | {klass_counts[k]} | {_handling[k]} |")

    lines += [
        "",
        "## A. genuine_candidate — owner判断が要る",
        "",
        "定義が**別概念**(例: 社員=会社法上の地位 vs 労働者一般)なら split 維持、",
        "同概念の**言い換え/OCR揺れ**なら merge。下の各件で判断してください。",
        "",
    ]
    if genuine:
        for i, p in enumerate(genuine, 1):
            lines += _detail_block(i, p)
    else:
        lines += ["_(genuine 候補なし — 全件 staging artifact)_", ""]

    lines += [
        "---",
        "",
        "## B. artifact_* — staging前処理で解決 (owner判断不要・参考)",
        "",
        "これらは genuine な多義ではなく、staging の定義断片化・スタブ・空行。",
        "再結合(continuation/subitem)または除去(stub/empty/header/list_marker)で homograph から消える。",
        "**短定義489 の一部も同じ断片化が原因の可能性が高い**(断片=短い)。",
        "",
    ]
    for i, p in enumerate(artifacts, 1):
        lines += _detail_block(i, p)
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
    genuine = sum(1 for p in pairs if p["klass"] == "genuine_candidate")
    klass_counts = {}
    for p in pairs:
        klass_counts[p["klass"]] = klass_counts.get(p["klass"], 0) + 1
    print(f"[homograph] 候補 {len(pairs)} 件 (同scheme {same} / cross {len(pairs)-same})")
    print(f"[homograph] 自動分類: genuine(要owner判断) {genuine} 件 / artifact {len(pairs)-genuine} 件")
    for k, v in sorted(klass_counts.items()):
        print(f"             {k}: {v}")
    print(f"[homograph] -> {out}/homograph_review.md (A.genuine が owner判断, B.artifact は staging前処理)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
