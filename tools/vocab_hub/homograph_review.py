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
# 番号サブ項目の続き: 2)〜9) / 先頭 1.〜9. / 次に・また・なお
_SUBITEM_START = re.compile(
    r"^[2-9２-９]\s*[）)]|^[（(]?[2-9２-９][）)]|^[1-9１-９]\s*[.．]|^(?:次に|また[，、]|なお[，、])")
_CONT_START = re.compile(r"^(?:も[^のっ]|により|たり[，、]|又は|及び)")  # B が前行の続きで始まる断片


def _is_stub(s: str) -> bool:
    """読み/相互参照の短い断片 (文末記号で終わらない短文)."""
    return bool(s) and len(s) <= 16 and not s.endswith(("。", "．"))


def classify_pair(pref, a_def, b_def):
    """homograph候補を 3クラスに自動分類する.

    artifact_* : staging の定義断片化/スタブ/空/番号サブ項目/リストマーカー見出し
                 = owner判断不要(staging再結合/除去で解決).
    merge_candidate : A/B 双方が見出し語を含む同概念の重複定義
                 = provisional では1 hubに統合(owner はスポット確認のみ).
    genuine_split : 別概念 or OCR矛盾 (片方が見出し語を含まない等)
                 = **唯一の真の owner 判断**.
    保守的: artifact 判定を厚くし、残りを merge/split に分ける.
    """
    a = (a_def or "").strip()
    b = (b_def or "").strip()
    if _LIST_HEADWORD.match(pref or ""):
        return "artifact_list_marker", "見出しがリストマーカー(語ではない)"
    if (not b or b == "(定義なし)") or (not a or a == "(定義なし)"):
        return "artifact_empty", "片側定義が空"
    if _HEADER_ONLY.match(b) or _HEADER_ONLY.match(a):
        return "artifact_header", "片側が見出し記号のみ(【n)】等)"
    # スタブ: A/B どちらかが読み/相互参照の短い断片
    if _is_stub(a) or _is_stub(b):
        return "artifact_stub", "片側が短いスタブ(読み/相互参照断片)"
    # 断片化: A が文末記号で終わらず途中で切れている = 次行(B)への continuation
    if a and a[-1] not in _TERMINATORS:
        return "artifact_continuation", "A側が文途中で切れB側へ continuation"
    # 番号サブ項目の続き / B が前行の続きで始まる
    if _SUBITEM_START.match(b) or _CONT_START.match(b):
        return "artifact_subitem", "B側が番号サブ項目/前行の続き(2)3)/1./次に/も/により)"
    # 残り: A/B 双方が見出し語(先頭2字)を含むか で merge/split を分ける
    core = pref[:2] if len(pref) >= 2 else pref
    if core and core in a and core in b:
        return "merge_candidate", "A/B双方が見出し語を含む同概念の重複定義(統合可)"
    return "genuine_split", "別概念 or OCR矛盾(片方が見出し語を含まない等) — 要owner判断"


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
    splits = [p for p in pairs if p["klass"] == "genuine_split"]
    merges = [p for p in pairs if p["klass"] == "merge_candidate"]
    artifacts = [p for p in pairs if p["klass"] in _ARTIFACT_CLASSES]
    klass_counts = {}
    for p in pairs:
        klass_counts[p["klass"]] = klass_counts.get(p["klass"], 0) + 1

    lines = [
        "# homograph レビューパケット (owner判断用 / read-only)",
        "",
        f"> 同 (正規化見出し + 読み) だが定義の char-bigram Jaccard < {threshold} で**別hubに分離**した候補を",
        "> **3クラスに自動分類**した。`genuine_split` のみ owner の真の判断が要る。",
        "> `merge_candidate` は同概念の重複定義(provisionalでは統合、スポット確認のみ)。",
        "> `artifact_*` は staging の定義断片化/スタブ/空行(再結合・除去で解決、owner判断不要)。",
        f"> 総数 **{len(pairs)}**  /  **genuine_split {len(splits)}**(要判断)  /  "
        f"merge {len(merges)}(統合)  /  artifact {len(artifacts)}(前処理)",
        "",
        "## 自動分類サマリ",
        "| クラス | 件数 | 扱い |",
        "|---|---|---|",
    ]
    _handling = {
        "genuine_split": "**owner判断**(別概念/OCR矛盾 — split維持かmergeか)",
        "merge_candidate": "1 hubに統合(同概念の重複定義. スポット確認のみ)",
        "artifact_continuation": "staging再結合(定義が途中で切れ次行へ)",
        "artifact_subitem": "staging再結合(番号サブ項目の続き)",
        "artifact_stub": "除去(読み/相互参照スタブ)",
        "artifact_empty": "除去(空定義)",
        "artifact_header": "除去(見出し記号のみ)",
        "artifact_list_marker": "除去(見出しがリストマーカー)",
    }
    for k in ["genuine_split", "merge_candidate", "artifact_continuation", "artifact_subitem",
              "artifact_stub", "artifact_empty", "artifact_header", "artifact_list_marker"]:
        if klass_counts.get(k):
            lines.append(f"| {k} | {klass_counts[k]} | {_handling[k]} |")

    lines += [
        "",
        "## A. genuine_split — owner の真の判断が要る",
        "",
        "別概念(例: 参議=官職 vs 家事審判役)なら split 維持、OCR矛盾(例: 重懲役=禁錮 vs 懲役)なら",
        "正しい方を採用。下の各件で判断してください。",
        "",
    ]
    if splits:
        for i, p in enumerate(splits, 1):
            lines += _detail_block(i, p)
    else:
        lines += ["_(genuine_split なし)_", ""]

    lines += [
        "---",
        "",
        "## B. merge_candidate — 同概念の重複定義 (統合・スポット確認のみ)",
        "",
        "A/B双方が見出し語を含む同概念の重複(辞書内の言い換え/詳しさ違い)。",
        "provisional では1 hubに統合してよい。念のため数件スポット確認を。",
        "",
    ]
    for i, p in enumerate(merges, 1):
        lines += _detail_block(i, p)

    lines += [
        "---",
        "",
        "## C. artifact_* — staging前処理で解決 (owner判断不要・参考)",
        "",
        "genuine な多義ではなく staging の定義断片化・スタブ・空行。",
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
    splits = sum(1 for p in pairs if p["klass"] == "genuine_split")
    merges = sum(1 for p in pairs if p["klass"] == "merge_candidate")
    klass_counts = {}
    for p in pairs:
        klass_counts[p["klass"]] = klass_counts.get(p["klass"], 0) + 1
    print(f"[homograph] 候補 {len(pairs)} 件 (同scheme {same} / cross {len(pairs)-same})")
    print(f"[homograph] 自動分類: genuine_split(要owner判断) {splits} / "
          f"merge_candidate(統合) {merges} / artifact(前処理) {len(pairs)-splits-merges}")
    for k, v in sorted(klass_counts.items()):
        print(f"             {k}: {v}")
    print(f"[homograph] -> {out}/homograph_review.md (A.genuine_split が owner判断)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
