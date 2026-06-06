#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_case_refs.py — normalize_case_ref を実OPACデータに一括適用し被覆率/衝突を測る

入力: opac_parse.py の Stage2 出力 ext_opac_articles.jsonl（各記事に case_ref_text あり）。
      case_ref_text は『最判昭44・5・19…；東京高判…』のように ；区切りの略記判例参照。

測るもの:
  - coverage: 全 case_ref のうち normalize_case_ref が court+判決日を解けた割合
  - collision: 同一 canonical_key に異なる ref_text が何件まとまるか（真の重複 vs 誤併合の点検対象）
  - 失敗サンプル: 解けなかった ref_text の例（regex改善の材料）

使い方:
  python3 scripts/validate_case_refs.py path/to/ext_opac_articles.jsonl
  # フル48MBは本番envで。サンプルでも同じ。--sample-fails N で失敗例数を調整
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.case_identity import normalize_case_ref, extract_case_refs  # noqa: E402

SPLIT_RE = re.compile(r"[；;]")


def iter_refs(path, from_raw=False):
    """from_raw=False: 既存 case_ref_text（；区切り）を使う（地名欠落あり）。
    from_raw=True : raw_text から extract_case_refs で地名込みに再抽出（推奨）。"""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                art = json.loads(line)
            except Exception:
                continue
            if not isinstance(art, dict):
                continue
            if from_raw:
                for ref in extract_case_refs(art.get("raw_text") or art.get("title") or ""):
                    if len(ref) >= 3:
                        yield ref
            else:
                crt = art.get("case_ref_text")
                if not crt:
                    continue
                for ref in SPLIT_RE.split(crt):
                    ref = ref.strip()
                    if len(ref) >= 3:
                        yield ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--from-raw", action="store_true",
                    help="raw_text から地名込みで再抽出（opac_parse の地名欠落を回避）")
    ap.add_argument("--sample-fails", type=int, default=15)
    ap.add_argument("--sample-collisions", type=int, default=10)
    args = ap.parse_args()

    total = parsed = 0
    fails = []
    key_to_refs = defaultdict(set)     # canonical_key -> {ref_text,...}
    by_level = defaultdict(int)
    no_caseno = no_date = 0

    for ref in iter_refs(args.path, from_raw=args.from_raw):
        total += 1
        rec = normalize_case_ref(ref)
        if rec is None:
            if len(fails) < args.sample_fails:
                fails.append(ref)
            continue
        parsed += 1
        key_to_refs[rec["canonical_key"]].add(rec["ref_text"])
        by_level[rec["court_level"]] += 1
        if not rec.get("case_number"):
            no_caseno += 1

    uniq = len(key_to_refs)
    collisions = {k: v for k, v in key_to_refs.items() if len(v) > 1}
    coll_ref_total = sum(len(v) for v in collisions.values())

    print("=" * 60)
    print(f"入力: {args.path}")
    print(f"case_ref 総数            : {total:,}")
    print(f"正本キー化 成功          : {parsed:,}  ({(parsed/total*100 if total else 0):.1f}%)")
    print(f"  失敗                   : {total-parsed:,}")
    print(f"ユニーク正本キー         : {uniq:,}")
    print(f"  うち事件番号なし(citation同定): {no_caseno:,}")
    print(f"衝突グループ(同一キー>1)  : {len(collisions):,}  (関与ref {coll_ref_total:,})")
    print("\n--- 裁判所レベル別 ---")
    for lvl, c in sorted(by_level.items(), key=lambda x: -x[1]):
        print(f"  {lvl:10s}: {c:,}")

    if fails:
        print(f"\n--- 解けなかった ref サンプル({len(fails)}) ---")
        for r in fails:
            print(f"  ✗ {r[:60]}")

    if collisions:
        print(f"\n--- 衝突サンプル({min(args.sample_collisions, len(collisions))}) ---")
        for k, v in list(collisions.items())[:args.sample_collisions]:
            print(f"  {k}")
            for r in list(v)[:3]:
                print(f"      ← {r[:55]}")


if __name__ == "__main__":
    main()
