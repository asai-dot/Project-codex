#\!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""extract_issue_feature.py — ORCH-ISSUE-FEATURE

各 issue_id に紐づく「特集タイトル」を集約する（DD-PERIODICAL-002 / L4補助メタ）。

入力候補（順に確認・存在するものを使う）:
  1. build/labeled_v0.2.1/article_meta_labeled.jsonl の special_feature 列（最優先）
  2. Supabase staging_periodical.issue_stage.special_feature（SELECTのみ）
  3. fallback: 記事タイトルからの特集語抽出
     （article_join_dryrun_v0.1.csv の title 列を使用）

本リポジトリ現状では (1)(2) が未提供のため (3) title_extract 経路を使う。
すべて read-only。出力は新規ファイルのみ。

出力:
  artifacts/periodical/issue_feature_v0.1.csv
     issue_id, feature_title, source(meta|sql|title_extract), article_count, confidence
  artifacts/periodical/issue_feature_summary_v0.1.json
     total_issues_with_feature, source_breakdown{}, top20_features_by_articles[]
  artifacts/periodical/issue_feature_v0.1.audit.json   (補助)
     曖昧 issue（複数 feature 候補）とその候補リストを併記。

article_count の定義: その issue 内で「採用した feature_title を支持した記事数」（最頻値の票数）。
"""
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PERIODICAL = os.path.join(ROOT, "artifacts", "periodical")

CAND1_JSONL = os.path.join(ROOT, "build", "labeled_v0.2.1", "article_meta_labeled.jsonl")
FALLBACK_CSV = os.path.join(PERIODICAL, "article_join_dryrun_v0.1.csv")

OUT_CSV = os.path.join(PERIODICAL, "issue_feature_v0.1.csv")
OUT_SUMMARY = os.path.join(PERIODICAL, "issue_feature_summary_v0.1.json")
OUT_AUDIT = os.path.join(PERIODICAL, "issue_feature_v0.1.audit.json")

# --- 特集名抽出パターン ----------------------------------------------------
# Rule A: 括弧内に特集マーカー — （特集 NAME） / （＜特集＞ NAME 6） / (大特集 NAME)
RULE_A = re.compile(
    r"[（(]\s*[＜<]?\s*(?:第[0-9０-９一二三四五六七八九十]+)?\s*(?:大|拡大|小|別冊|緊急)?特集\s*[＞>]?"
    r"\s*[:：・／/]?\s*(?P<name>[^（）()]+?)\s*[)）]"
)
# Rule B: 接尾マーカー — NAME＜特集＞ / NAME＜大特集＞ / NAME＜拡大特集＞ / NAME【特集】
RULE_B = re.compile(
    r"(?P<name>.+?)\s*[＜<【]\s*(?:大|拡大|小|別冊|緊急)?特集\s*[＞>】]\s*$"
)
# Rule C: 先頭マーカー — 【特集】NAME / 特集／NAME
RULE_C = re.compile(
    r"^\s*(?:【\s*特集\s*】|特集[／/])\s*(?P<name>.+?)\s*$"
)

TRAIL_NUM = re.compile(r"[\s　]*[0-9０-９]+\s*$")
SUBTITLE = re.compile(r"\s*(?:――|—|--|―).*$")


def normalize_name(name):
    if not name:
        return ""
    s = name.strip().strip("　 \t")
    s = re.sub(r"^[＜<【]?\s*(?:大|拡大)?特集\s*[＞>】]?\s*[:：・／/]?\s*", "", s)
    s = SUBTITLE.sub("", s)
    s = TRAIL_NUM.sub("", s)
    s = s.strip("　 \t:：・／/")
    s = re.sub(r"[\s　]+", " ", s).strip()
    return s


def extract_feature(title):
    if not title:
        return None
    if "特集" not in title:
        return None
    for rule in (RULE_A, RULE_B, RULE_C):
        m = rule.search(title)
        if m:
            name = normalize_name(m.group("name"))
            if len(name) >= 2:
                return name
    return None


def load_candidate1():
    if not os.path.exists(CAND1_JSONL):
        return None
    rows = []
    with open(CAND1_JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            sf = (o.get("special_feature") or "").strip()
            iid = o.get("issue_id")
            if iid and sf:
                rows.append((iid, normalize_name(sf)))
    return rows if rows else None


def main():
    cand1 = load_candidate1()
    if cand1 is not None:
        source = "meta"
        per_issue = defaultdict(Counter)
        for iid, feat in cand1:
            if feat:
                per_issue[iid][feat] += 1
        print("[info] candidate1 (meta/special_feature) 使用: %d issues" % len(per_issue), file=sys.stderr)
    else:
        if not os.path.exists(FALLBACK_CSV):
            print("[fatal] fallback 入力が見つからない: %s" % FALLBACK_CSV, file=sys.stderr)
            sys.exit(2)
        source = "title_extract"
        print("[info] candidate1/2 未提供 → fallback title_extract 使用: %s" % FALLBACK_CSV, file=sys.stderr)
        per_issue = defaultdict(Counter)
        n_rows = 0
        n_hits = 0
        with open(FALLBACK_CSV, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                n_rows += 1
                iid = (row.get("issue_id") or "").strip()
                if not iid:
                    continue
                feat = extract_feature(row.get("title") or "")
                if feat:
                    per_issue[iid][feat] += 1
                    n_hits += 1
        print("[info] rows=%d feature_hits=%d issues_with_feature=%d" % (n_rows, n_hits, len(per_issue)), file=sys.stderr)

    records = []
    audit_ambiguous = []
    for iid, counter in per_issue.items():
        ranked = counter.most_common()
        top_feat, top_cnt = ranked[0]
        ambiguous = len(ranked) > 1 and ranked[1][1] >= max(2, top_cnt * 0.5)
        if source in ("meta", "sql"):
            confidence = "high"
        else:
            if ambiguous:
                confidence = "low"
            elif top_cnt >= 2:
                confidence = "medium"
            else:
                confidence = "low"
        records.append({
            "issue_id": iid,
            "feature_title": top_feat,
            "source": source,
            "article_count": top_cnt,
            "confidence": confidence,
        })
        if len(ranked) > 1:
            audit_ambiguous.append({
                "issue_id": iid,
                "chosen": top_feat,
                "chosen_count": top_cnt,
                "candidates": [{"feature_title": f, "count": c} for f, c in ranked],
                "ambiguous": ambiguous,
            })

    records.sort(key=lambda x: (-x["article_count"], x["issue_id"]))

    os.makedirs(PERIODICAL, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["issue_id", "feature_title", "source", "article_count", "confidence"])
        w.writeheader()
        for rec in records:
            w.writerow(rec)

    source_breakdown = Counter(r["source"] for r in records)
    conf_breakdown = Counter(r["confidence"] for r in records)
    feat_articles = Counter()
    feat_issues = Counter()
    for rec in records:
        feat_articles[rec["feature_title"]] += rec["article_count"]
        feat_issues[rec["feature_title"]] += 1
    top20 = [
        {"feature_title": f, "article_count": feat_articles[f], "issue_count": feat_issues[f]}
        for f, _ in feat_articles.most_common(20)
    ]
    summary = {
        "total_issues_with_feature": len(records),
        "source_breakdown": dict(source_breakdown),
        "confidence_breakdown": dict(conf_breakdown),
        "ambiguous_issue_count": sum(1 for a in audit_ambiguous if a["ambiguous"]),
        "top20_features_by_articles": top20,
    }
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    with open(OUT_AUDIT, "w", encoding="utf-8") as f:
        json.dump({
            "note": "曖昧 issue（複数 feature 候補）。CSVは最頻値1件、ここに候補リストを併記。",
            "ambiguous_count": sum(1 for a in audit_ambiguous if a["ambiguous"]),
            "multi_candidate_count": len(audit_ambiguous),
            "issues": audit_ambiguous,
        }, f, ensure_ascii=False, indent=2)

    print("[done] issues=%d -> %s" % (len(records), OUT_CSV), file=sys.stderr)
    print("[done] summary -> %s" % OUT_SUMMARY, file=sys.stderr)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
