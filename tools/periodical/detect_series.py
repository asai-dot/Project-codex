#!/usr/bin/env python3
"""
detect_series.py — ORCH-SERIES-DETECT executor (L4補助メタ, read-only)

記事タイトルから「連載シリーズ」を検出し series_id で記事をクラスタリングする。
連載＝同一テーマ/同一研究会の長期論考。下流で「同一連載の記事群を引く」
「連載の前後号を辿る」が可能になる。分類の粗種別「連載・コラム」とは独立
(本ORCHは具体的にどの連載かを特定する)。

Inputs
  --in       artifacts/periodical/article_join_dryrun_v0.1.csv
             (列: article_id, issue_id, journal_canonical, pub_year, title ほか)
Outputs
  --out-csv  artifacts/periodical/article_series_v0.1.csv
             series_id, article_id, journal_canonical, seq_in_series,
             title_normalized, signals_matched, confidence
  --out-json artifacts/periodical/article_series_summary_v0.1.json
             total_series, articles_in_series, avg_series_length, top10_longest_series[]

Read-only。authority CSV を触らない。入力CSVだけ読み、series_* 出力のみ生成する。
DB/Box/ネット書込なし。canonical promotion / accepted edge化 / 外部公開なし。

参照: ORCH-SERIES-DETECT_order_20260627.md / DD-PERIODICAL-002
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

DEFAULT_IN = "artifacts/periodical/article_join_dryrun_v0.1.csv"
DEFAULT_OUT_CSV = "artifacts/periodical/article_series_v0.1.csv"
DEFAULT_OUT_JSON = "artifacts/periodical/article_series_summary_v0.1.json"

CSV_HEADERS = [
    "series_id", "article_id", "journal_canonical", "seq_in_series",
    "title_normalized", "signals_matched", "confidence",
]

# --- 括弧（NFKC後: 全角は半角化される） ---
# ＜＞ → <>, （） → (), 【】〔〕「」『』［］ → そのまま/半角
OPEN = "<(【〔[「『"
CLOSE = ">)】〕]」』"
BRACKET_RE = re.compile(
    r"[" + re.escape(OPEN) + r"]"
    r"([^" + re.escape(OPEN + CLOSE) + r"]+?)"   # ラベル本体（非貪欲）
    r"([0-9]+)\s*"                                  # 末尾通し番号
    r"[" + re.escape(CLOSE) + r"]"
)

# 連番/分割の各シグナル（NFKC後の半角前提）
KAISUU_RE = re.compile(r"第\s*([0-9]+)\s*回")
# (N)・（N）はNFKC後 (N)。研究会等の (N) も拾うが、グルーピングで単発は落とす
PAREN_NUM_RE = re.compile(r"\(\s*([0-9]+)\s*\)")
PART_RE = re.compile(r"[(（]\s*(前編|後編|上|中|下|前|後|完|終)\s*[)）]")
PART_SEQ = {"前編": 1, "後編": 2, "上": 1, "中": 2, "下": 3, "前": 1, "後": 2, "完": 9, "終": 9}

# シリーズ性の高いラベルに含まれやすいキーワード（複数括弧から本命を選ぶのに使う）
SERIES_KW_RE = re.compile(
    r"研究|判例|解説|ノート|相談|事情|紹介|講座|演習|入門|シリーズ|連載|実務|事例|"
    r"百選|展望|動向|レポート|だより|窓口|Q&A|最前線|ガイド|読本|考える"
)
# 日付ラベル（誤検出除外用）: 令和5.10.3公取委発表 等
DATE_LABEL_RE = re.compile(r"(令和|平成|昭和|大正|西暦)\s*[0-9]")
# ラベルに最低1つ日本語文字を要求（数字/記号だけのゴミ除外）
JP_CHAR_RE = re.compile(r"[぀-ヿ㐀-鿿一-龥々ー]")

# 弱シグナル（補助的フラグ。連番/分割が無くてもタイトル正規化グルーピングに寄与）
RENZOKU_RE = re.compile(r"続編|続報|続々|新連載|連載完|連載第|連載")

# 数字の通し番号を含む末尾括弧を剥がしてシリーズ名を作る用
TRAIL_NUM_BRACKET_RE = re.compile(
    r"[" + re.escape(OPEN) + r"][^" + re.escape(OPEN + CLOSE) + r"]*[0-9]+\s*"
    r"[" + re.escape(CLOSE) + r"]\s*$"
)


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").strip()


def journal_slug(journal: str) -> str:
    """可読な誌スラグ（空白除去）。一意性は series_id のhashが担保。"""
    return re.sub(r"\s+", "", journal or "")


def norm_name(name: str) -> str:
    """シリーズ名の正規化（空白圧縮・前後記号除去）。"""
    name = nfkc(name)
    name = re.sub(r"\s+", "", name)
    name = name.strip("・,，.。:：;；-―ー—‐/／|｜")
    return name


def make_series_id(journal: str, name: str) -> str:
    h = hashlib.md5(f"{journal}\x1f{name}".encode("utf-8")).hexdigest()[:8]
    return f"series:{journal_slug(journal)}#{h}"


def extract_signals(title: str):
    """タイトルから候補シグナルを抽出。
    戻り値: (best, all_signals) — best=(name, seq, sig_type, strength) or None。
    各記事は best 1件のみに採番（同一article_idが複数seriesに属さない不変条件）。
    """
    t = nfkc(title)
    all_sigs = []

    # 1) 括弧つきラベル+通し番号（最強・法律雑誌の長期研究会連載の主成分）
    bracket_cands = []
    for m in BRACKET_RE.finditer(t):
        label = m.group(1).strip()
        num = int(m.group(2))
        if len(label) < 2:
            continue
        if DATE_LABEL_RE.search(label):
            continue
        if not JP_CHAR_RE.search(label):
            continue
        bracket_cands.append((norm_name(label), num, m.start()))
    if bracket_cands:
        # 本命選択: シリーズキーワード持ち優先 → 後方の括弧優先（研究会名は末尾に来やすい）
        kw = [c for c in bracket_cands if SERIES_KW_RE.search(c[0])]
        pool = kw if kw else bracket_cands
        pool.sort(key=lambda c: c[2])  # 出現位置
        name, num, _ = pool[-1]
        all_sigs.append(f"bracket={name}:{num}")
        best = (name, num, "bracket_label_num", 0.90)
        return best, all_sigs

    # 2) 第N回（テーマ連載）
    mk = KAISUU_RE.search(t)
    if mk:
        num = int(mk.group(1))
        # 第N回トークンと番号括弧/日付括弧を剥がした残りをシリーズ名に
        rem = KAISUU_RE.sub("", t)
        rem = TRAIL_NUM_BRACKET_RE.sub("", rem)
        rem = re.sub(r"[(（][^()（）]*[)）]\s*$", "", rem)  # 末尾の判決日括弧等を除去
        name = norm_name(rem)
        all_sigs.append(f"kaisuu={num}")
        if len(name) >= 4:
            return (name, num, "kaisuu", 0.80), all_sigs

    # 3) 上中下/前後/完（分割物）
    mp = PART_RE.search(t)
    if mp:
        part = mp.group(1)
        seq = PART_SEQ[part]
        rem = PART_RE.sub("", t)
        rem = re.sub(r"[(（][^()（）]*[)）]\s*$", "", rem)
        name = norm_name(rem)
        all_sigs.append(f"part={part}")
        if len(name) >= 4:
            return (name, seq, "part", 0.70), all_sigs

    # 4) (N) 連番（弱め: ラベル本体=残りタイトル）
    mn = PAREN_NUM_RE.search(t)
    if mn:
        num = int(mn.group(1))
        rem = PAREN_NUM_RE.sub("", t)
        name = norm_name(rem)
        all_sigs.append(f"parennum={num}")
        if len(name) >= 6:
            return (name, num, "paren_num", 0.65), all_sigs

    if RENZOKU_RE.search(t):
        all_sigs.append("renzoku")
    return None, all_sigs


def sort_key(rec):
    py = rec["pub_year"]
    try:
        py = int(py)
    except (TypeError, ValueError):
        py = 0
    return (py, rec["issue_id"] or "", rec["seq_num"] if rec["seq_num"] is not None else 0,
            rec["article_id"] or "")


def main(argv=None):
    ap = argparse.ArgumentParser(description="連載シリーズ検出 (read-only)")
    ap.add_argument("--in", dest="inp", default=DEFAULT_IN)
    ap.add_argument("--out-csv", default=DEFAULT_OUT_CSV)
    ap.add_argument("--out-json", default=DEFAULT_OUT_JSON)
    ap.add_argument("--min-len", type=int, default=2,
                    help="series化する最小記事数（既定2: 単発はseries化しない）")
    args = ap.parse_args(argv)

    inp = Path(args.inp)
    if not inp.exists():
        print(f"[FATAL] input not found: {inp}", file=sys.stderr)
        return 2

    # group_key=(journal, name) -> list[record]
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    seen_articles: set[str] = set()
    n_rows = 0
    n_signal = 0

    with inp.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            n_rows += 1
            aid = row.get("article_id") or ""
            if not aid or aid in seen_articles:
                continue
            seen_articles.add(aid)
            title = row.get("title") or ""
            journal = row.get("journal_canonical") or ""
            best, all_sigs = extract_signals(title)
            if not best:
                continue
            n_signal += 1
            name, seq, sig_type, strength = best
            groups[(journal, name)].append({
                "article_id": aid,
                "journal_canonical": journal,
                "issue_id": row.get("issue_id") or "",
                "pub_year": row.get("pub_year") or "",
                "seq_num": seq,
                "title_normalized": name,
                "signals_matched": ";".join(all_sigs),
                "sig_type": sig_type,
                "strength": strength,
            })

    # series 確定 + 採番
    out_rows = []
    series_meta = []
    article_to_series: dict[str, str] = {}
    for (journal, name), recs in groups.items():
        # 同一article重複は除去済み。distinct記事数でフィルタ
        if len(recs) < args.min_len:
            continue
        recs.sort(key=sort_key)
        series_id = make_series_id(journal, name)
        n = len(recs)

        # 信頼度: 基礎=シグナル強度。証拠量・通し番号単調性で加点
        base = max(r["strength"] for r in recs)
        nums = [r["seq_num"] for r in recs]
        monotonic = all(b >= a for a, b in zip(nums, nums[1:]))
        distinct_nums = len(set(nums)) >= max(2, int(n * 0.5))
        conf = base
        if n >= 3:
            conf += 0.05
        if n >= 5:
            conf += 0.05
        if monotonic and distinct_nums:
            conf += 0.05
        conf = round(min(1.0, conf), 3)

        for i, r in enumerate(recs, start=1):
            article_to_series[r["article_id"]] = series_id
            out_rows.append({
                "series_id": series_id,
                "article_id": r["article_id"],
                "journal_canonical": journal,
                "seq_in_series": i,
                "title_normalized": name,
                "signals_matched": r["signals_matched"],
                "confidence": conf,
            })
        series_meta.append({
            "series_id": series_id,
            "journal_canonical": journal,
            "title_normalized": name,
            "length": n,
            "sig_type": max(set(r["sig_type"] for r in recs),
                            key=lambda s: sum(1 for r in recs if r["sig_type"] == s)),
            "confidence": conf,
        })

    # 出力CSV
    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        w.writeheader()
        for r in sorted(out_rows, key=lambda x: (x["series_id"], x["seq_in_series"])):
            w.writerow(r)

    # サマリ + 自己監査
    total_series = len(series_meta)
    articles_in_series = len(out_rows)
    avg_len = round(articles_in_series / total_series, 2) if total_series else 0.0
    series_meta.sort(key=lambda s: -s["length"])
    confs = sorted(s["confidence"] for s in series_meta)
    median_conf = confs[len(confs) // 2] if confs else 0.0
    len_ge3 = sum(1 for s in series_meta if s["length"] >= 3)
    sig_dist = defaultdict(int)
    for s in series_meta:
        sig_dist[s["sig_type"]] += 1

    summary = {
        "total_series": total_series,
        "articles_in_series": articles_in_series,
        "avg_series_length": avg_len,
        "top10_longest_series": [
            {
                "series_id": s["series_id"],
                "journal_canonical": s["journal_canonical"],
                "title_normalized": s["title_normalized"],
                "length": s["length"],
                "confidence": s["confidence"],
            }
            for s in series_meta[:10]
        ],
        "_audit": {
            "input_rows": n_rows,
            "rows_with_signal": n_signal,
            "series_len_ge3": len_ge3,
            "median_series_confidence": median_conf,
            "min_len_threshold": args.min_len,
            "sig_type_distribution": dict(sig_dist),
            "acceptance": {
                "series_len_ge3_>=50": len_ge3 >= 50,
                "no_article_collision": len(article_to_series) == articles_in_series,
                "median_conf_>=0.6": median_conf >= 0.6,
            },
        },
    }
    out_json = Path(args.out_json)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # コンソール要約
    print(f"[OK] input_rows={n_rows} rows_with_signal={n_signal}")
    print(f"[OK] total_series={total_series} articles_in_series={articles_in_series} "
          f"avg_len={avg_len}")
    print(f"[OK] series_len>=3={len_ge3} median_conf={median_conf}")
    print(f"[OK] acceptance: {summary['_audit']['acceptance']}")
    print(f"[OK] sig_type_dist: {dict(sig_dist)}")
    print(f"[OK] wrote {out_csv} , {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
