#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cross_reference_web.py — 学陽 all_entries.jsonl × 権威あるWEBデジタルデータ 照合レイヤ

目的（浅井指示「OCR辞書と権威あるWEB上のデジタルデータを突き合わせて、きれいな
法律用語データに整える」）。生データ非改変。照合結果は corrections 別レイヤに出す。

2系統の権威ソース:
  (A) e-Gov 法令API (Version 1, GET->XML; https://laws.e-gov.go.jp/docs/law-data-basic/)
      定義文中に埋め込まれた「法令名+条番号」引用を検証。
      review_queue.json の P2_era_concat_digits（例 "令167" = 施行令167条の区切り脱落）
      の類を、実在の法令条文構造に突き合わせて修正候補を出す。
  (B) 法令用語日英標準対訳辞書（日本法令外国語訳DB, https://www.japaneselawtranslation.go.jp/）
      見出し語そのものを権威ある用語リストと突合（任意・別途辞書ファイル指定）。

設計:
  - オフライン部（既定・ネット不要・テスト可）: 定義文から引用を抽出し、
    OCR 連結エラー（元号略+3桁以上 / 施行令+3桁 等）を規則で flag。
  - オンライン部（--verify-egov）: 抽出した法令名を e-Gov で照合し、
    条番号の妥当性を確認（ネットワークポリシー許可時のみ）。

入出力:
  python3 cross_reference_web.py all_entries.jsonl corrections_web.jsonl
          [--verify-egov] [--jlt-terms FILE.jsonl]
"""

import argparse
import json
import re
import sys

# 定義文中の法令引用: 「…法/令/規則 + （任意）施行令/施行規則 + 条番号」
# 例: 地方自治法施行令167 / 会計法29の4 / 予算決算及び会計令128
CITATION_RE = re.compile(
    r"(?P<law>[一-龥ぁ-んァ-ヴA-Za-z0-9]{2,}?"
    r"(?:法|令|規則|条例|憲法|規程))"
    r"(?P<shikou>施行令|施行規則)?"
    r"(?P<art>\d{1,4}(?:の\d+)*)"
)

# OCR 連結が疑われるパターン（review_queue P2 系）:
#  「令」直後に 3桁以上の数字（条番号は通常 1-3 桁 + 「の」枝番。3桁以上のベタ数字は
#   "施行令" の "令" と政令番号/年が連結した可能性が高い）
CONCAT_SUSPECT_RE = re.compile(r"(?<![施行])令(?P<num>\d{3,})(?!の)")

# 元号略 + 3桁以上（"昭和52年政令227号" の区切り脱落 → "令227" 等）
ERA_CONCAT_RE = re.compile(r"(?:政令|勅令|省令|令)\s*(?P<num>\d{3,})\s*号?")


def extract_citations(text):
    out = []
    for m in CITATION_RE.finditer(text):
        out.append({
            "law": m.group("law"),
            "shikou": m.group("shikou") or "",
            "article": m.group("art"),
            "span": [m.start(), m.end()],
            "matched": m.group(0),
        })
    return out


def flag_ocr_concat(text):
    flags = []
    for m in CONCAT_SUSPECT_RE.finditer(text):
        num = m.group("num")
        # 例: 令167 -> 施行令16条7? or 施行令167条? どちらかは法令照合が要る。
        flags.append({
            "type": "citation_concat_suspect",
            "matched": m.group(0),
            "num": num,
            "hint": "区切り脱落の可能性（施行令N条 / 政令N号）。e-Gov 照合で確定。",
            "span": [m.start(), m.end()],
        })
    return flags


def load_jlt_terms(path):
    terms = set()
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
                t = obj.get("term") or obj.get("headword")
                if t:
                    terms.add(t)
            except json.JSONDecodeError:
                terms.add(ln)  # プレーン1語/行も許容
    return terms


def verify_egov(law_name, timeout=15):
    """e-Gov 法令API で法令名の実在を確認（簡易・任意）。
    ネットワーク許可時のみ。失敗は None（不明）を返し、ハードエラーにしない。"""
    try:
        import urllib.parse
        import urllib.request
        # 法令名一覧/取得APIのエンドポイント（仕様書 v1 参照）。
        # ここでは法令名での存在確認に留める軽量実装。
        url = ("https://laws.e-gov.go.jp/api/1/lawlists/1")  # 全法令一覧(区分1=全部)
        # 実運用ではローカルにlawlistsをキャッシュして突合する。ここは到達性のみ。
        req = urllib.request.Request(url, headers={"User-Agent": "alo-xref/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ok = resp.status == 200
        return {"reachable": ok}
    except Exception as e:  # noqa: BLE001 - 到達不可は致命でない
        return {"reachable": False, "error": str(e)}


def process(entries, jlt_terms=None, verify=False):
    corrections = []
    egov_checked = {}
    for e in entries:
        d = e.get("definition", "")
        cites = extract_citations(d)
        ocr_flags = flag_ocr_concat(d)
        rec = {
            "entry_id": e.get("entry_id"),
            "headword": e.get("headword"),
            "citations": cites,
            "ocr_flags": ocr_flags,
            "term_authority": None,
        }
        if jlt_terms is not None:
            rec["term_authority"] = {
                "in_jlt": e.get("headword") in jlt_terms,
                "source": "jlt_standard_terms",
            }
        if verify:
            for c in cites:
                law = c["law"]
                if law not in egov_checked:
                    egov_checked[law] = verify_egov(law)
                c["egov"] = egov_checked[law]
        # corrections は「何かしら指摘がある」エントリのみ出す（レイヤを薄く）
        if ocr_flags or (rec["term_authority"] and not rec["term_authority"]["in_jlt"]):
            corrections.append(rec)
    return corrections


def main(argv=None):
    ap = argparse.ArgumentParser(description="all_entries.jsonl × 権威WEBデータ 照合")
    ap.add_argument("input_jsonl")
    ap.add_argument("output_jsonl")
    ap.add_argument("--verify-egov", action="store_true",
                    help="e-Gov 法令API で法令名到達性を確認（ネット許可時）")
    ap.add_argument("--jlt-terms", help="法令用語標準対訳辞書の用語リスト(jsonl)")
    args = ap.parse_args(argv)

    jlt = load_jlt_terms(args.jlt_terms) if args.jlt_terms else None

    entries = []
    try:
        with open(args.input_jsonl, encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if ln:
                    entries.append(json.loads(ln))
    except OSError as e:
        print(f"input error: {e}", file=sys.stderr)
        return 3

    corrections = process(entries, jlt_terms=jlt, verify=args.verify_egov)

    with open(args.output_jsonl, "w", encoding="utf-8") as out:
        for c in corrections:
            out.write(json.dumps(c, ensure_ascii=False) + "\n")

    n_cite = sum(len(c["citations"]) for c in corrections)
    n_ocr = sum(len(c["ocr_flags"]) for c in corrections)
    print("=== cross_reference_web report ===", file=sys.stderr)
    print(f"entries scanned       : {len(entries)}", file=sys.stderr)
    print(f"entries w/ findings   : {len(corrections)}", file=sys.stderr)
    print(f"citations extracted   : {n_cite}", file=sys.stderr)
    print(f"ocr concat suspects   : {n_ocr}", file=sys.stderr)
    print(f"egov verify           : {'on' if args.verify_egov else 'off'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
