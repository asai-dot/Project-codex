#!/usr/bin/env python3
"""データ品質監査: 辞書ゴールド(有斐閣/学陽)は本当に「きれい」か実測する.

STATUS_dict_gold の「2,100一致(78.9%)」は *見出し一致率* であって *フィールド健全性* ではない.
本ツールは各辞書を直接測る: 読み欠落 / 空定義 / 末尾切れ疑い / 重複 / OCRゴミ / 長さ分布.
read-only. 出力は数字のみ.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import adapt_hourei as ah
import build_hub_dryrun as bh

CANDIDATE_ROOTS = ["Library/CloudStorage", "Box"]
_KANA = re.compile(r"^[ぁ-んァ-ヴーゝゞ・\s]+$")
_OCR_BAD = re.compile(r"[�□�\x00-\x08\x0e-\x1f]")          # 置換文字・制御文字
_LATIN_RUN = re.compile(r"[A-Za-zＡ-Ｚａ-ｚ]{4,}")               # 不自然な英字連続


def find_one(name, override=None):
    if override:
        return Path(override)
    for root in CANDIDATE_ROOTS:
        base = Path.home() / root
        if base.exists():
            for p in base.rglob(name):
                return p
    return None


def median(xs):
    s = sorted(xs)
    n = len(s)
    return 0 if n == 0 else (s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2)


def audit(name, rows, get_pref, get_reading, get_def, export_dir=None, tag=""):
    n = len(rows)
    if n == 0:
        print(f"\n## {name}: 0 件"); return
    miss_read = empty_def = short_def = ocr_bad = latin = bad_reading = long_hw = empty_hw = 0
    deflens, prefs, prefread = [], {}, {}
    buckets = {"empty_def": [], "short_def": [], "long_headword": [], "no_reading": []}
    for r in rows:
        pref = (get_pref(r) or "").strip()
        rd = get_reading(r)
        df = (get_def(r) or "").strip()
        rec = {"headword": pref, "reading": rd, "definition": df[:80]}
        if not pref:
            empty_hw += 1
        elif len(pref) > 25:
            long_hw += 1
            buckets["long_headword"].append(rec)
        if not rd or not str(rd).strip():
            miss_read += 1
            buckets["no_reading"].append(rec)
        elif not _KANA.match(unicodedata.normalize("NFKC", str(rd))):
            bad_reading += 1
        if not df:
            empty_def += 1
            buckets["empty_def"].append(rec)
        else:
            deflens.append(len(df))
            if len(df) < 8:
                short_def += 1
                buckets["short_def"].append(rec)
            if _OCR_BAD.search(df):
                ocr_bad += 1
            if _LATIN_RUN.search(df):
                latin += 1
        prefs[pref] = prefs.get(pref, 0) + 1
        k = (bh.norm_pref(pref), bh.norm_reading(str(rd or "")))
        prefread[k] = prefread.get(k, 0) + 1
    dup_pref = sum(v - 1 for v in prefs.values() if v > 1)
    dup_prefread = sum(v - 1 for v in prefread.values() if v > 1)

    def pct(x):
        return f"{x} ({100*x/n:.1f}%)"
    print(f"\n## {name}: {n} 件")
    print(f"  見出し空        : {pct(empty_hw)}")
    print(f"  見出し長すぎ(>25): {pct(long_hw)}   <- parse/結合ミス疑い")
    print(f"  読み欠落        : {pct(miss_read)}   <- 統合の主障害")
    print(f"  読みが非かな    : {pct(bad_reading)}")
    print(f"  空定義          : {pct(empty_def)}")
    print(f"  短定義(<8字)    : {pct(short_def)}   <- 末尾切れ/OCR脱落 疑い")
    print(f"  定義にOCRゴミ   : {pct(ocr_bad)}   <- 置換/制御文字")
    print(f"  定義に英字連続  : {pct(latin)}   <- OCR誤認 疑い")
    print(f"  重複 見出し     : {dup_pref}")
    print(f"  重複 (見出し+読み): {dup_prefread}")
    if deflens:
        print(f"  定義長 min/中央/max: {min(deflens)} / {int(median(deflens))} / {max(deflens)}")
    if export_dir:
        ed = Path(export_dir)
        ed.mkdir(parents=True, exist_ok=True)
        for bname, recs in buckets.items():
            if recs:
                fp = ed / f"{tag}_{bname}.jsonl"
                with fp.open("w", encoding="utf-8") as fh:
                    for x in recs:
                        fh.write(json.dumps(x, ensure_ascii=False) + "\n")
        print(f"  [export] 問題 records -> {ed}/{tag}_*.jsonl")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="辞書ゴールド データ品質監査 (read-only)")
    ap.add_argument("--yt", default=None)
    ap.add_argument("--yl", default=None)
    ap.add_argument("--he", default=None)
    ap.add_argument("--export", default=None, help="問題 records の出力先 dir (例: ~/dict_quality)")
    a = ap.parse_args(argv)
    yt = find_one("yuhikaku_legal_dict_terms_stg_v3.jsonl", a.yt)
    yl = find_one("yuhikaku_legal_dict_labels_stg_v3.jsonl", a.yl)
    he = find_one("hourei_all_entries_v0.2_20260612.jsonl", a.he)
    print(f"[quality] 有斐閣 terms : {yt}")
    print(f"[quality] 有斐閣 labels: {yl}")
    print(f"[quality] 学陽 entries : {he}")

    if yt:
        y = list(bh.read_jsonl(yt))
        if yl:
            bh.attach_definitions(y, bh.read_jsonl(yl))
        audit("有斐閣『法律用語辞典』(rank101)", y,
              lambda r: r.get("normalized_pref") or r.get("pref_label"),
              lambda r: r.get("reading"), lambda r: r.get("definition"),
              export_dir=a.export, tag="yuhikaku")
    if he:
        h = [json.loads(x) for x in Path(he).read_text(encoding="utf-8").splitlines() if x.strip()]
        audit("学陽『法令用語辞典』(rank102)", h,
              lambda r: r.get("headword"), lambda r: r.get("reading"), lambda r: r.get("definition"),
              export_dir=a.export, tag="hourei")

    print("\n=== 結論 ===")
    print("「きれい」かどうかは上の実数で判断する. 読み欠落/短定義/OCRゴミが多ければ、")
    print("hub 統合前に再OCR・読み補完(MeCab等)・末尾切れ救済が要る = まだ前処理が残っている.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
