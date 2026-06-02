#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cross_reference_web.py — 学陽 all_entries.jsonl × 権威あるWEBデジタルデータ 照合レイヤ

★訂正履歴（重要・2026-06-02）★
  初版は review_queue.json の P2_era_concat_digits 129件を「令+3桁のOCR連結エラー」と
  誤って性格づけし、それを直す前提でフラガを書いていた。これは誤り。実物では 129件の
  大半（>9割）は正規の引用（地方自治法施行令167 / 昭和52年政令227号 / 総務省組織令127 …）
  で、検出器が「令」を令和の元号略と誤認して発火しているだけ。本物の誤りは 4桁以上に潰れた
  少数（令9921=会計令99の2の1 / 令2210=組織令22の10 / 令5710=会計令57の10 / 令991 …）。
  → canonical 再評価: REVIEW_QUEUE_REASSESSMENT_20260602.md（Box dict_ocr_hourei）。
  本スクリプトは「129件を直す」設計を廃し、以下に再定義する:
    ① citation_link_candidates: 定義文中の全引用を e-Gov ノードへの【リンク候補】として抽出
       （誤り扱いしない。修正もしない）。
    ② collapse_suspects: 令+【4桁以上】のみを「枝番の・中黒が落ちた疑い」として advisory フラグ。
       3桁は正規引用が大半で regex では真偽判定不能 → フラグしない（e-Gov 照合でのみ確定）。
    ③ term_authority: 見出し語を権威用語リスト（法務省JLT等）と突合。
  生データは一切改変しない。自動修正は一切しない（false-positive で正しい引用を壊さないため）。

権威ソース:
  (A) e-Gov 法令API Version 2（JSON; base https://laws.e-gov.go.jp/api/2 ；事務所標準）
      /keyword, /laws, /law_data/{id}。引用の存在確認に使う（確定は人/CCの判断）。
  (B) 法務省 日本法令外国語訳DB「法令用語日英標準対訳辞書」(JLT) v19.0
      ※正典 v19.0 は Box 着地待ち。--jlt-terms で権威用語リスト(jsonl/txt)を渡す。

入出力:
  python3 cross_reference_web.py all_entries.jsonl xref_layer.jsonl
          [--verify-egov] [--jlt-terms FILE]
"""

import argparse
import json
import re
import sys

# 定義文中の法令引用（リンク候補の抽出元）。誤り判定はしない。
# 例: 地方自治法施行令167 / 会計法29の4 / 予算決算及び会計令128 / 政令227号
CITATION_RE = re.compile(
    r"(?P<law>[一-龥ぁ-んァ-ヴA-Za-z0-9]{2,}?"
    r"(?:法|令|規則|条例|憲法|規程))"
    r"(?P<art>\d{1,4}(?:の\d+)*)"
)

# 「枝番の/中黒が潰れた」真の収縮エラー候補のみ: 令 直後に【4桁以上】のベタ数字。
# 条番号・政令番号は通常 1-3 桁なので、4桁ベタ連続は収縮の強い兆候。
# 3桁（167/227/189…）は正規引用が大半で regex では真偽不能のためフラグしない
# （誤検知で正しい引用を壊すより、取りこぼして e-Gov 照合に委ねる方を選ぶ）。
COLLAPSE_SUSPECT_RE = re.compile(r"令(?P<num>\d{4,})(?!の)")

EGOV_V2_BASE = "https://laws.e-gov.go.jp/api/2"


def extract_citations(text):
    out = []
    for m in CITATION_RE.finditer(text):
        out.append({
            "law": m.group("law"),
            "article": m.group("art"),
            "matched": m.group(0),
            "span": [m.start(), m.end()],
        })
    return out


def detect_collapse_suspects(text):
    """枝番収縮の疑い（令+4桁以上）のみ。advisory。自動修正はしない。"""
    suspects = []
    for m in COLLAPSE_SUSPECT_RE.finditer(text):
        suspects.append({
            "type": "branch_collapse_suspect",
            "matched": m.group(0),
            "num": m.group("num"),
            "hint": "枝番の/中黒の脱落候補（例 令5710→会計令57の10）。"
                    "e-Gov 照合で確定。自動修正禁止。",
            "span": [m.start(), m.end()],
            "auto_fix": False,
        })
    return suspects


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


def egov_reachable(timeout=15):
    """e-Gov 法令API v2 への到達性のみ確認（advisory）。失敗は致命にしない。"""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{EGOV_V2_BASE}/laws?limit=1",
            headers={"User-Agent": "alo-xref/0.2", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"reachable": resp.status == 200, "api": "v2"}
    except Exception as e:  # noqa: BLE001
        return {"reachable": False, "api": "v2", "error": str(e)}


def process(entries, jlt_terms=None, verify=False):
    layer = []
    egov = egov_reachable() if verify else None
    for e in entries:
        d = e.get("definition", "")
        cites = extract_citations(d)
        suspects = detect_collapse_suspects(d)
        rec = {
            "entry_id": e.get("entry_id"),
            "headword": e.get("headword"),
            "citation_link_candidates": cites,   # 誤りではない・リンク用
            "collapse_suspects": suspects,        # 4桁のみ・advisory・no auto-fix
            "term_authority": None,
        }
        if jlt_terms is not None:
            rec["term_authority"] = {
                "in_authority_list": e.get("headword") in jlt_terms,
                "source": "jlt_v19_0",
            }
        # レイヤを薄く: リンク候補/疑い/語彙照合のいずれかがある行だけ出す
        if cites or suspects or rec["term_authority"]:
            layer.append(rec)
    return layer, egov


def main(argv=None):
    ap = argparse.ArgumentParser(description="all_entries.jsonl × 権威WEBデータ 照合レイヤ")
    ap.add_argument("input_jsonl")
    ap.add_argument("output_jsonl")
    ap.add_argument("--verify-egov", action="store_true",
                    help="e-Gov 法令API v2 到達性を確認（ネット許可時）")
    ap.add_argument("--jlt-terms", help="権威用語リスト(jsonl/txt)。正典JLT v19.0着地後に指定")
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

    layer, egov = process(entries, jlt_terms=jlt, verify=args.verify_egov)

    with open(args.output_jsonl, "w", encoding="utf-8") as out:
        for rec in layer:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    n_links = sum(len(r["citation_link_candidates"]) for r in layer)
    n_susp = sum(len(r["collapse_suspects"]) for r in layer)
    print("=== cross_reference_web report ===", file=sys.stderr)
    print(f"entries scanned          : {len(entries)}", file=sys.stderr)
    print(f"rows w/ findings         : {len(layer)}", file=sys.stderr)
    print(f"citation LINK candidates : {n_links}  (誤りではない/リンク用)", file=sys.stderr)
    print(f"collapse suspects (4桁+) : {n_susp}  (advisory/自動修正なし)", file=sys.stderr)
    if egov is not None:
        print(f"e-Gov v2 reachable       : {egov}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
