#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORCH-CITATION-EXTRACT — タイトルからの法令・判例引用シグナル抽出 (read-only/分析のみ)

入力 (read-only):
  1. artifacts/periodical/article_join_dryrun_v0.1.csv  (article_id, title, ...)
  2. artifacts/periodical/citation_law_dict_v0.1.yaml    (法令名+略称辞書)

処理:
  1. 法令名抽出: 辞書 alias を surface としてタイトル部分一致(canonical へ正規化)
  2. 判例日付抽出: ORCH-L5-FEASIBILITY の正規表現を流用(元年含む, 和暦→西暦, court 正規化)
  3. article_id 単位で indexing。同一 article_id 内の重複 evidence_span は1件に正規化。

出力:
  artifacts/periodical/title_law_citation_v0.1.csv   (article_id, law_name, evidence_span)
  artifacts/periodical/title_case_citation_v0.1.csv  (article_id, court, date, evidence_span)
  artifacts/periodical/title_citation_summary_v0.1.json
      (per_law_articles, top10_laws, top10_cited_dates, ほか統計)

書込なし(DB/edge/本体)。タイトルは雑誌側既存メタなので出力可。
"""
import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

import yaml

csv.field_size_limit(10 ** 7)

# 出力 REPO はこのスクリプトの所在から導出(worktree でも main でも動く)。
HERE = os.path.dirname(os.path.abspath(__file__))   # .../artifacts/periodical
REPO = os.path.dirname(os.path.dirname(HERE))
# 入力タイトル CSV は .gitignore 済みのローカルデータ。main checkout 側を read-only 参照。
DATA_REPO = os.environ.get("CITATION_DATA_REPO", "/Users/yuta/Project-codex")
JOIN = f"{DATA_REPO}/artifacts/periodical/article_join_dryrun_v0.1.csv"
LAW_DICT = f"{REPO}/artifacts/periodical/citation_law_dict_v0.2.yaml"
OUT_LAW = f"{REPO}/artifacts/periodical/title_law_citation_v0.2.csv"
OUT_CASE = f"{REPO}/artifacts/periodical/title_case_citation_v0.2.csv"
OUT_JSON = f"{REPO}/artifacts/periodical/title_citation_summary_v0.2.json"

ERA_BASE = {"令和": 2018, "平成": 1988, "昭和": 1925, "大正": 1911, "明治": 1867}
KANJI_NUM = {"一": "1", "二": "2", "三": "3", "1": "1", "2": "2", "3": "3"}

# ORCH-L5-FEASIBILITY DATE_COURT_RE を流用 (元年/和暦, 末尾 判|決定|決|裁決)
DATE_COURT_RE = re.compile(
    r"(令和|平成|昭和|大正|明治)(\d{1,2}|元)[.・](\d{1,2})[.・](\d{1,2})"
    r"([^（）()0-9]{1,12}?)(判|決定|決|裁決)"
)


def z2h(s):
    return unicodedata.normalize("NFKC", s)


def normalize_court(raw):
    """生 court_raw を表示用に正規化(L5 の縮約方針を踏襲しつつ表示は1本化)。"""
    s = z2h(raw).strip().replace("第", "")
    m = re.search(r"最(?:高)?([一二三123])小", s)
    if m:
        n = KANJI_NUM.get(m.group(1), m.group(1))
        return f"最高第{n}小法廷"
    if "最高" in s or s.startswith("最"):
        if "大法廷" in s or s.endswith("大"):
            return "最高大法廷"
        return "最高裁"
    return raw.strip()


def load_law_dict(path):
    with open(path, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    laws = d.get("laws", {})
    # (surface, canonical) を surface 長の降順に。長い表記を先に当て、部分被りを防ぐ。
    pairs = []
    for canonical, aliases in laws.items():
        for a in aliases:
            pairs.append((z2h(a), canonical))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs


def extract_laws(title_n, pairs):
    """title_n(NFKC済) から (canonical, surface) を抽出。
    surface 単位で重複排除し、より長い surface が当たった区間は短い surface で再カウントしない。"""
    hits = []  # (canonical, surface)
    consumed = [False] * len(title_n)
    for surface, canonical in pairs:
        start = 0
        slen = len(surface)
        while True:
            i = title_n.find(surface, start)
            if i < 0:
                break
            if not any(consumed[i:i + slen]):
                hits.append((canonical, surface))
                for k in range(i, i + slen):
                    consumed[k] = True
            start = i + slen
    return hits


def main():
    pairs = load_law_dict(LAW_DICT)

    # article_id 単位で indexing。同一 article_id が入力に複数行あっても evidence_span を
    # グローバルに一意化する(受入基準「同一article_id内の重複evidence_spanは1件に正規化」)。
    law_index = defaultdict(dict)   # article_id -> {evidence_span: law_name}
    case_index = defaultdict(dict)  # article_id -> {evidence_span: (court, date)}

    n_titles = 0
    n_titles_with_law = 0
    n_titles_with_case = 0
    seen_total = 0
    n_empty_aid = 0

    with open(JOIN, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            seen_total += 1
            aid = (r.get("article_id", "") or "").strip()
            title = r.get("title", "") or ""
            if not title.strip():
                continue
            if not aid:
                n_empty_aid += 1
                continue  # article_id 単位 index 不可の行は対象外
            n_titles += 1
            tn = z2h(title)

            lmap = law_index[aid]
            for canonical, surface in extract_laws(tn, pairs):
                lmap.setdefault(surface, canonical)  # span 一意, 先勝ち(=最長一致優先)

            cmap = case_index[aid]
            for m in DATE_COURT_RE.finditer(tn):
                era, y, mo, d, court_raw, _suf = m.groups()
                base = ERA_BASE.get(era)
                if base is None:
                    continue
                yv = 1 if y == "元" else int(y)
                yyyymmdd = f"{base + yv:04d}{int(mo):02d}{int(d):02d}"
                span = m.group(0)
                cmap.setdefault(span, (normalize_court(court_raw), yyyymmdd))

    # --- 集計 + 行生成(article_id, evidence_span でソート) ---
    per_law_articles = Counter()   # canonical -> distinct article_id 数
    cited_dates = Counter()        # YYYYMMDD -> 件数(行ベース)
    court_count = Counter()
    law_rows = []
    case_rows = []

    for aid in sorted(law_index):
        spans = law_index[aid]
        if not spans:
            continue
        n_titles_with_law += 1
        seen_law = set()
        for surface in sorted(spans):
            law_name = spans[surface]
            law_rows.append((aid, law_name, surface))
            if law_name not in seen_law:
                seen_law.add(law_name)
                per_law_articles[law_name] += 1

    for aid in sorted(case_index):
        spans = case_index[aid]
        if not spans:
            continue
        n_titles_with_case += 1
        for span in sorted(spans):
            court, date = spans[span]
            case_rows.append((aid, court, date, span))
            cited_dates[date] += 1
            court_count[court] += 1

    # 出力 CSV
    with open(OUT_LAW, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["article_id", "law_name", "evidence_span"])
        w.writerows(law_rows)

    with open(OUT_CASE, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["article_id", "court", "date", "evidence_span"])
        w.writerows(case_rows)

    top10_laws = [
        {"law_name": k, "articles": v} for k, v in per_law_articles.most_common(10)
    ]
    top10_dates = [
        {"date": k, "count": v} for k, v in cited_dates.most_common(10)
    ]

    summary = {
        "order": "ORCH-CITATION-EXTRACT",
        "mode": "read-only / analysis-only (no DB/edge write)",
        "input": {
            "title_source": os.path.relpath(JOIN, REPO),
            "law_dict": os.path.relpath(LAW_DICT, REPO),
            "rows_scanned": seen_total,
            "titles_nonempty_with_article_id": n_titles,
            "rows_skipped_empty_article_id": n_empty_aid,
        },
        "law_extraction": {
            "rows": len(law_rows),
            "distinct_articles_with_law": n_titles_with_law,
            "distinct_laws": len(per_law_articles),
        },
        "case_extraction": {
            "rows": len(case_rows),
            "distinct_articles_with_case": n_titles_with_case,
            "distinct_dates": len(cited_dates),
        },
        "acceptance": {
            "law_rows_ge_50000": len(law_rows) >= 50000,
            "case_rows_ge_20000": len(case_rows) >= 20000,
        },
        "per_law_articles": dict(per_law_articles.most_common()),
        "top10_laws": top10_laws,
        "top10_cited_dates": top10_dates,
        "top10_courts": [
            {"court": k, "count": v} for k, v in court_count.most_common(10)
        ],
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "law_rows": len(law_rows),
        "case_rows": len(case_rows),
        "articles_with_law": n_titles_with_law,
        "articles_with_case": n_titles_with_case,
        "distinct_laws": len(per_law_articles),
        "distinct_dates": len(cited_dates),
        "acceptance": summary["acceptance"],
        "top10_laws": top10_laws,
        "top10_cited_dates": top10_dates,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
