#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quote_check_egov.py — A1: 定義内の法令引用句 × e-Gov 権威本文 で誤字脱字を局在

辞書定義の「…」引用句のうち、**直後の出典が当該法令** のものを取り出し、e-Gov の
権威本文へ突き合わせる。句読点様式（、/，/。/空白）を正規化した上で：
- 権威本文に逐語部分一致 → clean（引用は正確）。
- 一致しない → 引用句中の distinctive アンカーで本文位置を特定し、その窓と差分（difflib）。
  差分文字が出れば **OCR誤字脱字候補**（言い換え/旧法/別条なら差分大→低信頼として別扱い）。

生データ非改変・出力は suspect 層（自動修正しない）。どちらが誤りかは権威=e-Gov を基準にする。

使い方:
  python3 quote_check_egov.py --entries gakuyo_all_entries.jsonl \
        --law-name 民法 --law-text <egov_民法.txt> --out minpou_quote_suspects.jsonl
"""
import argparse
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("，", "、").replace(",", "、")          # 読点様式を統一
    s = re.sub(r"[\s　]", "", s)                          # 空白除去
    return s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries", required=True)
    ap.add_argument("--law-name", required=True)
    ap.add_argument("--law-text", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-len", type=int, default=15)
    ap.add_argument("--anchor", type=int, default=10)
    args = ap.parse_args(argv)

    # e-Gov JSON から日本語の文字列値（条文テキスト）だけ抽出してブロブ化。
    # 生JSONを正規化すると "}] 等の構造文字が混入し誤検出するため。
    raw = open(args.law_text, encoding="utf-8").read()
    jp = re.compile(r"[぀-ゟ゠-ヿ一-鿿]")
    vals = [v for v in re.findall(r'"((?:[^"\\]|\\.)*)"', raw) if jp.search(v)]
    blob = norm("".join(vals))
    law = args.law_name

    # 引用句 + 直後の出典(（…law…）)。出典に law 名が含まれるものだけ帰属。
    # 例: 「…推定する」（民法229） / 「…」(民法第二百二十九条)
    pat = re.compile(r"「([^「」]{%d,})」\s*[（(]([^（）()]{0,40})[）)]" % args.min_len)

    clean = 0
    suspects = []
    n_attr = 0
    for ln in open(args.entries, encoding="utf-8"):
        o = json.loads(ln)
        d = o.get("definition", "")
        for m in pat.finditer(d):
            quote, cite = m.group(1), m.group(2)
            if law not in cite:
                continue
            n_attr += 1
            qn = norm(quote)
            if len(qn) < args.min_len:
                continue
            if qn in blob:
                clean += 1
                continue
            # アンカーで本文位置特定 → 窓を取り差分
            anchor = None
            for i in range(0, len(qn) - args.anchor + 1):
                a = qn[i:i + args.anchor]
                p = blob.find(a)
                if p != -1:
                    anchor = (i, p)
                    break
            if anchor is None:
                # 本文に痕跡なし＝言い換え/旧法/別法の可能性。低信頼。
                suspects.append({"entry": o["headword"], "cite": cite, "quote": quote[:80],
                                 "status": "no_anchor", "diffs": []})
                continue
            qi, bp = anchor
            ws = bp - qi
            # 窓は引用長ちょうど（+余白を取らない）。学陽が条文の前半だけ引用した場合に
            # e-Gov の続き(次文・次条見出し)を誤って差分に数えないため。
            window = blob[max(0, ws):ws + len(qn)]
            sm = SequenceMatcher(None, qn, window)
            sim = sm.ratio()
            diffs = []
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag != "equal":
                    diffs.append({"op": tag, "dict": qn[i1:i2], "egov": window[j1:j2]})
            # 句読点のみの差（引用の切れ目の 。/、/. 等）は誤字でないので除外
            PUNCT = set("。、，,.・「」『』（）()　 ー-－")
            def ponly(s):
                return all(c in PUNCT for c in s)
            diffs = [d for d in diffs if not (ponly(d["dict"]) and ponly(d["egov"]))]
            if not diffs:
                clean += 1
                continue
            if sim >= 0.85 and diffs:  # 高一致だが差分あり＝誤字脱字候補
                suspects.append({"entry": o["headword"], "cite": cite, "quote": quote[:80],
                                 "status": "char_diff", "sim": round(sim, 3), "diffs": diffs})

    sus_diff = [s for s in suspects if s["status"] == "char_diff"]
    sus_noanchor = [s for s in suspects if s["status"] == "no_anchor"]
    with open(args.out, "w", encoding="utf-8") as out:
        for s in suspects:
            out.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"=== quote_check_egov ({law}) ===", file=sys.stderr)
    print(f"attributed quotes : {n_attr}", file=sys.stderr)
    print(f"clean (verbatim)  : {clean}", file=sys.stderr)
    print(f"char_diff suspects: {len(sus_diff)}  (高一致+差分=誤字脱字候補)", file=sys.stderr)
    print(f"no_anchor         : {len(sus_noanchor)}  (言い換え/旧法/別条の可能性=低信頼)", file=sys.stderr)
    print("--- char_diff 候補 ---", file=sys.stderr)
    for s in sus_diff[:25]:
        ds = "; ".join(f"{d['op']}:辞[{d['dict']}]≠e[{d['egov']}]" for d in s["diffs"][:4])
        print(f"  [{s['entry']}]({s['cite']}) sim={s['sim']}  {ds}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
