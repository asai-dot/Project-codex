#!/usr/bin/env python3
"""P0: 辞書ゴールド -> bedrock Hub 構築 dry-run (read-only, DBに書かない).

DD-DICT-008 §2.4 Stage1-3(+5) を JSONL で回す. 依存ゼロ (Python 3.9+).

監査/設計の不変条件:
  - DBに書かない. canonical 化しない (全 hub_status=provisional).
  - bedrock = authority_rank 100-102 (e-Gov定義/基本辞典/法令用語辞典). 対等 (Q1).
  - exact_match は normalized_pref + reading 一致 かつ 定義重なり率 >= 閾値 のみ (表層一致だけで統合しない).
  - 同綴異義 (同 normalized_pref で reading 違い / 低重なり) は **統合せず別 hub** + homograph フラグ.
  - specialty (rank>=103) は bedrock hub に attach のみ. canonical 昇格しない.
  - anchor は中立規則: e-Gov(rank100) 優先 -> scheme_id 昇順 -> term_id 昇順 (優劣ではない).

入力 (read-only, 既存ゴールド staging):
  --terms  Term JSONL. 期待スキーマ:
    {"term_id","scheme_id","authority_rank":101,"normalized_pref":"占有","reading":"せんゆう",
     "definition":"...", "term_tier":1}

出力 (candidate のみ. 本番 write なし):
  <out>/hub_candidate.jsonl / hub_membership_candidate.jsonl / hub_build_report.md
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Dict, Iterable, List, Optional

DEFAULT_OVERLAP = 0.6  # DD-DICT-008 Q2: 暫定. Wave0 実測で再校正
_FW_ALNUM = str.maketrans(
    "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")


def norm_pref(s: str) -> str:
    """generate_staging_v3.normalize_pref 互換: NFC + 全角英数→半角. 辞書間でキーを揃える."""
    return unicodedata.normalize("NFC", str(s or "")).strip().translate(_FW_ALNUM)


def norm_reading(s: str) -> str:
    """読みの正規化: NFKC + カタカナ→ひらがな + 記号/空白除去 (辞書間の読みキー統一)."""
    r = unicodedata.normalize("NFKC", str(s or ""))
    out = [chr(ord(c) - 0x60) if "ァ" <= c <= "ヴ" else c for c in r]
    return "".join(out).replace(" ", "").replace("　", "").replace("・", "").replace("ー", "").strip()


def _key(t: dict):
    """グループ化キー: (正規化見出し, 正規化読み). normalized_pref が無ければ pref_label/headword から."""
    pref = t.get("normalized_pref") or t.get("pref_label") or t.get("headword") or ""
    return (norm_pref(pref), norm_reading(t.get("reading", "")))


def read_jsonl(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def remap_records(records: Iterable[dict], field_map: Optional[Dict[str, str]]) -> List[dict]:
    out = []
    for r in records:
        if field_map:
            for expected, actual in field_map.items():
                if expected not in r and actual in r:
                    r[expected] = r[actual]
        out.append(r)
    return out


def attach_definitions(terms: List[dict], labels: Iterable[dict],
                       term_key: str = "stg_term_key", label_defkey: str = "stg_term_key") -> None:
    """定義が labels 側(label_type=='definition')にある実スキーマ向け: term へ join.

    有斐閣ゴールド(generate_staging_v3)は terms に definition を持たず, labels の
    {"label_type":"definition","label_text":...,"stg_term_key":...} に持つ. join で term["definition"] を埋める.
    """
    def_by_key: Dict[str, str] = {}
    for lb in labels:
        if lb.get("label_type") == "definition":
            k = lb.get(label_defkey)
            if k is not None and k not in def_by_key:
                def_by_key[str(k)] = lb.get("label_text", "")
    for t in terms:
        if not t.get("definition"):
            t["definition"] = def_by_key.get(str(t.get(term_key, "")), "")


def bigrams(text: str) -> set:
    t = (text or "").replace(" ", "").replace("　", "")
    if len(t) < 2:
        return {t} if t else set()
    return {t[i:i + 2] for i in range(len(t) - 1)}


def overlap(def_a: str, def_b: str) -> float:
    """定義の char-bigram Jaccard. 定義欠落時は 0.0."""
    a, b = bigrams(def_a), bigrams(def_b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_bedrock(rank) -> bool:
    """rank 100-102 (100系列 100a-100d 文字列含む) は bedrock canonical 候補."""
    s = str(rank)
    if s[:3] in ("100",):
        return True
    return s in ("101", "102")


def _tid(t: dict) -> str:
    """term の識別子. term_id が無ければ stg_term_key (実ゴールド) を使う."""
    return str(t.get("term_id") or t.get("stg_term_key") or "")


def _anchor_rule(terms: List[dict]) -> str:
    """中立 anchor: e-Gov(rank100台) 優先 -> scheme_id 昇順 -> term id 昇順."""
    def key(t):
        return (0 if str(t.get("authority_rank")).startswith("100") else 1,
                str(t.get("scheme_id", "")), _tid(t))
    return _tid(sorted(terms, key=key)[0])


def build_hubs(terms: List[dict], threshold: float = DEFAULT_OVERLAP, reading_missing: str = "defmatch"):
    """bedrock seed -> exact_match -> close_match -> specialty attach (DBなし).

    reading_missing: 片側辞書で読み欠落(OCR)時の扱い.
      "defmatch" (既定): 読み無し term は同 pref の hub に定義重なり>=閾値で attach (漏れ救済).
      "strict": 読みも一致条件にする(従来動作).
    """
    by_tid = {_tid(t): t for t in terms}
    bedrock_all = [t for t in terms if is_bedrock(t.get("authority_rank")) and str(t.get("term_tier", "1")) == "1"]
    specialty = [t for t in terms if not is_bedrock(t.get("authority_rank"))]

    # defmatch: 読み欠落 bedrock を分離して第2パスで処理 (groups は読みあり term のみで作る)
    if reading_missing == "defmatch":
        bedrock = [t for t in bedrock_all if norm_reading(t.get("reading", ""))]
        bedrock_noread = [t for t in bedrock_all if not norm_reading(t.get("reading", ""))]
    else:
        bedrock, bedrock_noread = bedrock_all, []

    # key = (正規化見出し, 正規化読み) — 辞書間でキーを揃える
    groups: Dict[tuple, List[dict]] = defaultdict(list)
    for t in bedrock:
        groups[_key(t)].append(t)

    hubs: List[dict] = []
    memberships: List[dict] = []
    homograph_conflicts = 0
    hub_of_key: Dict[tuple, str] = {}
    hub_by_pref: Dict[str, List[tuple]] = defaultdict(list)  # pref -> [(hub_id, anchor_term)]
    hub_seq = 0

    for (pref, reading), grp in groups.items():
        # exact_match: 群内で anchor と定義重なり>=閾値の term を 1 hub に統合
        anchor_tid = _anchor_rule(grp)
        anchor = by_tid[anchor_tid]
        merged, conflicts = [anchor], []
        for t in grp:
            if _tid(t) == anchor_tid:
                continue
            ov = overlap(anchor.get("definition", ""), t.get("definition", ""))
            if len(grp) == 1 or ov >= threshold or str(t.get("scheme_id")) == str(anchor.get("scheme_id")):
                merged.append(t)
            else:
                conflicts.append((t, ov))

        hub_seq += 1
        hub_id = f"hub:{hub_seq:06d}"
        hub_of_key[(pref, reading)] = hub_id
        hub_by_pref[pref].append((hub_id, anchor))
        hubs.append({
            "hub_id": hub_id, "anchor_term_id": anchor_tid, "hub_label": pref, "reading": reading,
            "member_count": len(merged), "authority_ranks": sorted({str(m.get("authority_rank")) for m in merged}),
            "hub_status": "provisional", "identity_scope": "vocab_hub_provisional_noncanonical",
        })
        for m in merged:
            memberships.append({
                "hub_id": hub_id, "term_id": _tid(m), "scheme_id": m.get("scheme_id"),
                "authority_rank": m.get("authority_rank"),
                "map_type": "bedrock_seed" if len(merged) == 1 else "skos_exact_match",
                "is_anchor": _tid(m) == anchor_tid,
                "definition_overlap": round(overlap(anchor.get("definition", ""), m.get("definition", "")), 3),
            })
        # 低重なり = 同綴異義: 統合せず別 hub (homograph)
        for t, ov in conflicts:
            homograph_conflicts += 1
            hub_seq += 1
            hid = f"hub:{hub_seq:06d}"
            hubs.append({
                "hub_id": hid, "anchor_term_id": _tid(t), "hub_label": pref, "reading": reading,
                "member_count": 1, "authority_ranks": [str(t.get("authority_rank"))],
                "hub_status": "provisional", "identity_scope": "vocab_hub_provisional_noncanonical",
                "homograph_conflict": True, "homograph_overlap": round(ov, 3),
            })
            memberships.append({
                "hub_id": hid, "term_id": _tid(t), "scheme_id": t.get("scheme_id"),
                "authority_rank": t.get("authority_rank"), "map_type": "homograph_split",
                "is_anchor": True, "definition_overlap": round(ov, 3),
            })

    # 第2パス: 読み欠落 bedrock term を同 pref の hub へ定義重なりで attach (OCR読み漏れ救済)
    hub_by_id = {h["hub_id"]: h for h in hubs}
    reading_missing_matched = 0
    reading_missing_seed = 0
    for t in bedrock_noread:
        pref = _key(t)[0]
        cands = hub_by_pref.get(pref, [])
        best_hid, best_ov = None, -1.0
        for hid, anchor in cands:
            ov = overlap(anchor.get("definition", ""), t.get("definition", ""))
            if ov > best_ov:
                best_hid, best_ov = hid, ov
        if best_hid is not None and best_ov >= threshold:
            reading_missing_matched += 1
            hub_by_id[best_hid]["member_count"] += 1
            ar = set(hub_by_id[best_hid]["authority_ranks"]) | {str(t.get("authority_rank"))}
            hub_by_id[best_hid]["authority_ranks"] = sorted(ar)
            memberships.append({
                "hub_id": best_hid, "term_id": _tid(t), "scheme_id": t.get("scheme_id"),
                "authority_rank": t.get("authority_rank"), "map_type": "reading_missing_def_match",
                "is_anchor": False, "definition_overlap": round(best_ov, 3),
            })
        else:  # 同 pref hub が無い or 重なり不足 -> 読み無し provisional hub (review 対象)
            reading_missing_seed += 1
            hub_seq += 1
            hid = f"hub:{hub_seq:06d}"
            hubs.append({
                "hub_id": hid, "anchor_term_id": _tid(t), "hub_label": pref, "reading": "",
                "member_count": 1, "authority_ranks": [str(t.get("authority_rank"))],
                "hub_status": "provisional", "identity_scope": "vocab_hub_provisional_noncanonical",
                "reading_missing": True,
            })
            memberships.append({
                "hub_id": hid, "term_id": _tid(t), "scheme_id": t.get("scheme_id"),
                "authority_rank": t.get("authority_rank"), "map_type": "reading_missing_seed",
                "is_anchor": True, "definition_overlap": round(best_ov, 3) if best_ov >= 0 else None,
            })

    # specialty (rank>=103): 同 key の bedrock hub に attach のみ. 無ければ provisional specialty hub.
    specialty_attached = 0
    for t in specialty:
        key = _key(t)
        hid = hub_of_key.get(key)
        if hid:
            specialty_attached += 1
            memberships.append({
                "hub_id": hid, "term_id": _tid(t), "scheme_id": t.get("scheme_id"),
                "authority_rank": t.get("authority_rank"), "map_type": "skos_close_match",
                "is_anchor": False, "definition_overlap": None, "specialty_attach": True,
            })
        else:
            hub_seq += 1
            hid = f"hub:{hub_seq:06d}"
            hubs.append({
                "hub_id": hid, "anchor_term_id": _tid(t), "hub_label": t.get("normalized_pref", ""),
                "reading": t.get("reading", ""), "member_count": 1,
                "authority_ranks": [str(t.get("authority_rank"))], "hub_status": "provisional",
                "identity_scope": "vocab_hub_provisional_noncanonical", "specialty_only": True,
            })
            memberships.append({
                "hub_id": hid, "term_id": _tid(t), "scheme_id": t.get("scheme_id"),
                "authority_rank": t.get("authority_rank"), "map_type": "specialty_seed",
                "is_anchor": True, "definition_overlap": None, "specialty_attach": False,
            })

    stats = {
        "terms_total": len(terms), "bedrock_terms": len(bedrock_all), "specialty_terms": len(specialty),
        "bedrock_reading_missing": len(bedrock_noread),
        "hubs": len(hubs), "homograph_conflicts": homograph_conflicts,
        "specialty_attached": specialty_attached,
        "reading_missing_matched": reading_missing_matched,
        "reading_missing_seed": reading_missing_seed,
        "exact_merged_hubs": sum(1 for h in hubs if h["member_count"] > 1),
    }
    return hubs, memberships, stats


def build_report(hubs, memberships, stats, threshold) -> str:
    sizes = Counter()
    for h in hubs:
        b = h["member_count"]
        sizes["1" if b == 1 else "2" if b == 2 else "3+"] += 1
    canonical_eligible = sum(1 for h in hubs
                             if all(str(r).startswith(("100", "101", "102")) for r in h["authority_ranks"]))
    lines = [
        "# 語彙Hub 構築 dry-run レポート (read-only / DBに書かない)",
        "",
        "> DD-DICT-008 Stage1-3(+5). 全 hub_status=provisional. canonical 昇格なし.",
        f"> 定義重なり率 閾値: {threshold} (Q2: 暫定. Wave0 実測で再校正)",
        "",
        f"- Term 総数: **{stats['terms_total']}**  (bedrock {stats['bedrock_terms']} / specialty {stats['specialty_terms']})",
        f"- 生成 hub: **{stats['hubs']}**  (exact統合 {stats['exact_merged_hubs']} / canonical昇格可(rank≤102のみ) {canonical_eligible})",
        f"- 同綴異義 homograph_conflict(統合せず別hub): **{stats['homograph_conflicts']}**",
        f"- 読み欠落 bedrock: **{stats.get('bedrock_reading_missing', 0)}**  "
        f"(定義一致で hub へ救済 **{stats.get('reading_missing_matched', 0)}** / 単独hub {stats.get('reading_missing_seed', 0)})",
        f"- specialty attach(rank≥103, attachのみ): **{stats['specialty_attached']}**",
        "",
        "## hub member数 分布",
        "| member | hub数 |",
        "|---|---|",
    ]
    for k in ["1", "2", "3+"]:
        if sizes.get(k):
            lines.append(f"| {k} | {sizes[k]} |")
    lines += [
        "",
        "## 監査整合の確認",
        "- exact_match は normalized_pref+reading 一致かつ定義重なり≥閾値のみ(表層一致merge なし).",
        "- 同綴異義は統合せず homograph_split(別hub). 重なり率を保存.",
        "- specialty(rank≥103)は attach のみ. canonical 昇格しない.",
        "- anchor は中立規則(e-Gov優先→scheme_id→term_id). 優劣ではない.",
        "",
        "_dry-run. candidate JSONL 出力のみ. DB write/canonical mint なし._",
    ]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="P0 語彙Hub構築 dry-run (read-only)")
    ap.add_argument("--terms", required=True, type=Path, nargs="+",
                    help="Term JSONL を複数可 (例: 有斐閣 + 学陽). 連結して 1 つの語彙空間で hub 構築.")
    ap.add_argument("--labels", type=Path, default=None,
                    help="定義が labels側(label_type=='definition')にある実スキーマ向け. join する.")
    ap.add_argument("--term-key", default="stg_term_key", help="定義 join 用の term 側キー (既定 stg_term_key)")
    ap.add_argument("--field-map", default=None,
                    help='term フィールド写像. インラインJSON \'{"term_id":"stg_term_key"}\' か JSONファイルパス. '
                         '(term_id 不在時は stg_term_key を自動使用するので通常不要)')
    ap.add_argument("--overlap-threshold", type=float, default=DEFAULT_OVERLAP)
    ap.add_argument("--reading-missing", choices=["defmatch", "strict"], default="defmatch",
                    help="片側辞書の読み欠落(OCR)時: defmatch=定義一致でhub救済(既定) / strict=読みも一致条件")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    fmap = None
    if args.field_map:
        s = args.field_map.strip()
        fmap = json.loads(s) if s.startswith("{") else json.loads(Path(s).read_text(encoding="utf-8"))
    terms = []
    for tp in args.terms:
        terms.extend(read_jsonl(tp))
    if args.labels:  # 定義 join (remap 前: 生キー stg_term_key で突合). 学陽はインライン定義なので skip される
        attach_definitions(terms, read_jsonl(args.labels), term_key=args.term_key)
    terms = remap_records(terms, fmap)
    hubs, memberships, stats = build_hubs(terms, args.overlap_threshold, args.reading_missing)

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "hub_candidate.jsonl").open("w", encoding="utf-8") as fh:
        for h in hubs:
            fh.write(json.dumps(h, ensure_ascii=False) + "\n")
    with (args.out / "hub_membership_candidate.jsonl").open("w", encoding="utf-8") as fh:
        for m in memberships:
            fh.write(json.dumps(m, ensure_ascii=False) + "\n")
    (args.out / "hub_build_report.md").write_text(
        build_report(hubs, memberships, stats, args.overlap_threshold), encoding="utf-8")
    print(f"[vocab-hub] terms={stats['terms_total']} hubs={stats['hubs']} "
          f"homograph={stats['homograph_conflicts']} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
