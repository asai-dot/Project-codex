#!/usr/bin/env python3
"""短定義 anchor (489件) の triage (read-only).

defrag 後も残る短定義(<8字)anchor は homograph とは別問題(単一行で元々短い).
本ツールは各短定義を3分類する:
  - truncation   : 末尾切れ/OCR脱落 (文末記号で終わらない/助詞止め) → 再OCR(DD-DICT-006)候補
  - valid_short  : 正規の短定義 (「〜の略。」「〜に同じ。」「〜をいう。」等) → そのまま load 可
  - other        : 上記以外 (要目視)

defrag 済 terms を入力にできる(--terms). 無指定なら Box から生で組んで defrag 後に測る.
出力: 分類レポート markdown + JSONL. DBに書かない.

    python3 tools/vocab_hub/short_def_triage.py
    python3 tools/vocab_hub/short_def_triage.py --terms ~/defrag/terms_defragged.jsonl
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

_TERMINATORS = "。．.！？!?」』）)"
# 正規の短定義パターン: 相互参照・略語・同義
_VALID_SHORT = re.compile(r"(?:の略|に同じ|をいう|を見よ|参照|に同|の意|の旧称|の俗称|に当たる)[。．]?$")
# 助詞/接続で終わる = 途中切れ疑い
_PARTICLE_END = re.compile(r"[ぁ-ん，、・]$")


def classify_short(definition: str) -> tuple:
    d = (definition or "").strip()
    if not d:
        return "empty", "定義が空"
    if _VALID_SHORT.search(d):
        return "valid_short", "相互参照/略語/同義の正規短定義"
    if d[-1] not in _TERMINATORS or _PARTICLE_END.search(d):
        return "truncation", "文末記号で終わらない/助詞止め(末尾切れ疑い)"
    return "other", "短いが末尾は完結(要目視)"


def collect_short_anchors(terms, threshold=0.6):
    """short_def anchor の hub を集め, 定義を3分類して返す."""
    hubs, _, _ = bh.build_hubs(terms, threshold, quality_filter=True)
    by_tid = {bh._tid(t): t for t in terms}
    rows = []
    for h in hubs:
        if h.get("anchor_quality") != "short_def":
            continue
        t = by_tid.get(h["anchor_term_id"], {})
        d = (t.get("definition") or "").strip()
        klass, reason = classify_short(d)
        rows.append({
            "pref": h["hub_label"], "reading": h.get("reading", ""),
            "scheme_id": t.get("scheme_id"), "authority_rank": t.get("authority_rank"),
            "definition": d, "len": len(d), "klass": klass, "reason": reason,
        })
    return rows


def to_markdown(rows):
    counts = defaultdict(int)
    for r in rows:
        counts[r["klass"]] += 1
    lines = [
        "# 短定義 anchor triage (read-only)",
        "",
        f"> 短定義(<{bh.SHORT_DEF_LEN}字)が anchor の hub を3分類。homograph とは別問題(単一行で元々短い)。",
        f"> 総数 **{len(rows)}**  /  truncation {counts['truncation']}  /  "
        f"valid_short {counts['valid_short']}  /  other {counts['other']}  /  empty {counts['empty']}",
        "",
        "| クラス | 件数 | 扱い |",
        "|---|---|---|",
        f"| truncation | {counts['truncation']} | 末尾切れ → 再OCR(DD-DICT-006)候補 |",
        f"| valid_short | {counts['valid_short']} | 正規短定義 → そのまま load 可 |",
        f"| other | {counts['other']} | 短いが末尾完結 → 要目視 |",
        f"| empty | {counts['empty']} | 空 → 除去/再OCR |",
        "",
    ]
    for klass in ["truncation", "other", "valid_short", "empty"]:
        sub = [r for r in rows if r["klass"] == klass]
        if not sub:
            continue
        lines += [f"## {klass} ({len(sub)})", ""]
        for r in sorted(sub, key=lambda x: x["len"]):
            lines.append(f"- **{r['pref']}**（{r['reading']}） [{r['len']}字] `{r['definition']}`")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="短定義 anchor triage (read-only)")
    ap.add_argument("--terms", default=None, help="defrag済 terms JSONL (無指定ならBoxから生→defrag)")
    ap.add_argument("--yuhikaku-terms", default=None)
    ap.add_argument("--yuhikaku-labels", default=None)
    ap.add_argument("--hourei-entries", default=None)
    ap.add_argument("--out", default=str(Path.home() / "short_def_triage"))
    a = ap.parse_args(argv)

    if a.terms:
        terms = list(bh.read_jsonl(Path(a.terms)))
        print(f"[short_def] terms (defrag済): {len(terms)}")
    else:
        yt = r2.find_one("yuhikaku_legal_dict_terms_stg_v3.jsonl", a.yuhikaku_terms)
        yl = r2.find_one("yuhikaku_legal_dict_labels_stg_v3.jsonl", a.yuhikaku_labels)
        he = r2.find_one("hourei_all_entries_v0.2_20260612.jsonl", a.hourei_entries)
        if not yt:
            print("ERROR: 有斐閣 terms が見つかりません。", file=sys.stderr)
            return 2
        raw, _, _ = r2.load_terms(yt, yl, he)
        terms, _ = dft.defrag(raw)
        print(f"[short_def] terms (Box→defrag): {len(terms)}")

    rows = collect_short_anchors(terms)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "short_def_triage.md").write_text(to_markdown(rows), encoding="utf-8")
    with (out / "short_def_triage.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    counts = defaultdict(int)
    for r in rows:
        counts[r["klass"]] += 1
    print(f"[short_def] 短定義 anchor {len(rows)} 件:")
    for k in ["truncation", "valid_short", "other", "empty"]:
        if counts[k]:
            print(f"             {k}: {counts[k]}")
    print(f"[short_def] -> {out}/short_def_triage.md")
    print("[short_def] truncation=再OCR候補 / valid_short=そのままload可 / other=要目視")
    return 0


if __name__ == "__main__":
    sys.exit(main())
