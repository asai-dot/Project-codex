#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reading_adjudicate.py — 読み不一致の adjudication（どちらが誤りか確定）

reading_triangulate の不一致を、権威(JLT)＋多数決で裁定し3バケットに分ける:
  - confirmed   : 構造的誤り(欠落/挿入/置換/小書き)。JLT or 多数派を正として訂正確定。
  - review      : 純濁点差。連濁(保健所しょ/じょ, 会社かいしゃ/がいしゃ)の正当ゆれがあり要人手。
                  JLT優先案は出すが自動確定しない。
  - artifact    : 学陽の truncation（読みが他方の部分文字列＝抽出欠け）。辞書誤りでない。

3ソース(JLT/有斐閣/学陽)が揃う語は多数決。JLTが少数派なら JLT を疑う（例: 図画 とが/ずが）。
生データ非改変・訂正は提案層（auto_apply=false）。
"""
import argparse
import json
import sys
import unicodedata
from collections import Counter

DAKU = str.maketrans("がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ",
                     "かきくけこさしすせそたちつてとはひふへほはひふへほ")
SMALL = str.maketrans("ぁぃぅぇぉっゃゅょゎ", "あいうえおつやゆよわ")


def nf(s):
    s = unicodedata.normalize("NFKC", (s or "").strip()).replace("・", "").replace(" ", "")
    # 片仮名→平仮名（JLTは読みを平仮名、有斐閣は外来語を片仮名で持つことがあり、
    # それは表記差であって誤りでないため正規化して同一視する）
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def load(path):
    d = {}
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if ln[:1] != "{":
            continue
        o = json.loads(ln)
        hw = nf(o.get("headword") or o.get("term") or "")
        r = nf(o.get("reading", ""))
        if hw and r:
            d.setdefault(hw, r)
    return d


def difftype(a, b):
    if b in a or a in b:
        return "truncation"
    if a.translate(DAKU) == b.translate(DAKU):
        return "dakuten"
    if a.translate(SMALL) == b.translate(SMALL):
        return "small_kana"
    if a.translate(DAKU).translate(SMALL) == b.translate(DAKU).translate(SMALL):
        return "dakuten+small"
    if len(a) != len(b):
        return "len_diff"
    return "substitution"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--jlt", required=True)
    ap.add_argument("--yuhikaku", required=True)
    ap.add_argument("--gakuyo", required=True)
    ap.add_argument("--out-prefix", required=True)
    args = ap.parse_args(argv)

    J, Y, G = load(args.jlt), load(args.yuhikaku), load(args.gakuyo)
    srcname = {"JLT": J, "有斐閣": Y, "学陽": G}

    confirmed, review, artifact = [], [], []
    for hw in set(J) | set(Y) | set(G):
        rds = {s: d[hw] for s, d in srcname.items() if hw in d}
        if len(rds) < 2:
            continue
        vals = list(rds.values())
        if len(set(vals)) == 1:
            continue  # 一致

        # 多数決（3ソース揃いで2:1）
        cnt = Counter(vals)
        majority = cnt.most_common(1)[0]
        correct_reading = None
        if len(rds) == 3 and majority[1] == 2:
            correct_reading = majority[0]
            wrong_src = [s for s, r in rds.items() if r != correct_reading][0]
            basis = "majority_2of3"
        elif "JLT" in rds:
            correct_reading = rds["JLT"]
            others = [(s, r) for s, r in rds.items() if s != "JLT" and r != correct_reading]
            if not others:
                continue
            wrong_src, _ = others[0]
            basis = "jlt_authority"
        else:
            # JLT不在で2者割れ＝裁定不能
            review.append({"headword": hw, "readings": rds, "diff_type": "no_authority",
                           "note": "JLT読み無し・要人手"})
            continue

        wrong_reading = rds[wrong_src]
        dt = difftype(correct_reading, wrong_reading)
        rec = {"headword": hw, "wrong_source": wrong_src, "wrong_reading": wrong_reading,
               "correct_reading": correct_reading, "diff_type": dt, "basis": basis,
               "readings": rds, "auto_apply": False}
        if dt == "truncation" and wrong_src == "学陽":
            rec["note"] = "学陽の読み抽出欠け（辞書誤りでない）"
            artifact.append(rec)
        elif dt in ("len_diff", "substitution", "small_kana", "dakuten+small"):
            rec["confidence"] = "high"
            confirmed.append(rec)
        else:  # pure dakuten
            rec["confidence"] = "medium"
            rec["note"] = "純濁点差＝連濁の正当ゆれの可能性。JLT優先案だが要確認"
            review.append(rec)

    for name, rows in [("confirmed", confirmed), ("review", review), ("artifact", artifact)]:
        with open(f"{args.out_prefix}_{name}.jsonl", "w", encoding="utf-8") as out:
            for r in rows:
                out.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("=== reading_adjudicate ===", file=sys.stderr)
    print(f"confirmed corrections: {len(confirmed)}", file=sys.stderr)
    print(f"  by source:", dict(Counter(r["wrong_source"] for r in confirmed)), file=sys.stderr)
    print(f"  by type  :", dict(Counter(r["diff_type"] for r in confirmed)), file=sys.stderr)
    print(f"review (dakuten/no-auth): {len(review)}", file=sys.stderr)
    print(f"artifact (学陽 truncation): {len(artifact)}", file=sys.stderr)
    print("--- confirmed sample ---", file=sys.stderr)
    for r in confirmed[:25]:
        print(f"  {r['headword']}: [{r['wrong_source']}]{r['wrong_reading']} → {r['correct_reading']} ({r['diff_type']})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
