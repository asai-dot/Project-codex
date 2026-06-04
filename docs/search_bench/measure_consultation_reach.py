#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A1 実相談検索観測ベースライン (Consultation Search Observation Baseline)

これは検索ベンチ(評価)ではない。観測装置である。
Stage1 では、Claude/本スクリプトは法律構成・期待概念・関連書籍を一切推定しない。
観測された文字列一致と、観測された DB 応答だけを保存する。bib_terms 投入前の before スナップショット。

入力(すべて別工程で取得した決定的スナップショット):
  --raw    SF leala__Consultation__c 生JSON (private, 非コミット)  [Id, Name, leala__CaseOutline__c, ALO_Inferred_CaseCategory__c]
  --terms  biblio.terms スナップショット JSON (554, statutory definitions; not PII)
  --probe  raw_probe_results.json (指標C; 無ければ raw_probe は pending)
出力:
  build/search_bench/a1_consultation_queries_private.csv      (PIIあり・非コミット)
  build/search_bench/a1_consultation_queries_report_safe.csv  (匿名・コミット候補)
  build/search_bench/a1_term_matches.csv                       (全term match・span/context)
  build/search_bench/a1_raw_probe_hits.csv                     (生全文プローブ結果)
  build/search_bench/a1_summary.json                           (再実行比較用・機械可読)
  build/search_bench/raw_probe_phrases.json                    (指標C 実行用フレーズ要求)

冪等・決定的: 乱数/実行時日付を使わない。基準日は --asof 引数。
"""
import argparse, csv, hashlib, json, os, re, sys, unicodedata
from collections import Counter, defaultdict

# ---- 禁止語(Stage1で成果物に出してはならない概念) : 自己検査に使用 ----
FORBIDDEN_TOKENS = ["expected", "target", "should_reach", "relevant", "gold",
                    "正解", "到達すべき", "期待概念"]

# ---- intake channel(事件種別でなく相談経路) : matter_type 末尾カッコから除去 ----
INTAKE_CHANNELS = [
    "法テラス", "京都弁護士会", "当番弁護", "国選弁護", "遺言・相続センター", "遺言・相談センター",
    "ひまわりほっとダイヤル", "ひまわりホットダイヤル", "犯罪被害者支援委員会", "駅前センター夜間法律相談",
    "犯罪被害者相談", "情報商材被害対策", "LAC", "京都情報商材被害対策弁護団相談案件",
    "欠陥住宅京都ネット相談", "欠陥住宅京都ネット",
]

# ---- 純ノイズ(集計除外・件数は明示) ----
NOISE_EXACT = {"テスト", "レアラ サンプル", "レアラ　サンプル", "サンプル", "執筆"}

# ---- manual stoplist(高頻度・低弁別の法定定義語。本体評価とノイズ評価の分離用。除外しすぎない) ----
MANUAL_STOPLIST = {
    "会社", "株式", "物", "事業", "請求", "手続", "決定", "登記", "承認", "指定", "認定",
    "提出", "関与", "事由", "期間", "計画", "業務", "報酬", "事務所", "申請", "募集",
    "使用", "提供", "登録", "指名", "目的", "基準", "場合", "申出", "請求権", "請求書",
    "法人", "組合", "財産", "権利", "費用", "支払", "商品", "役務", "営業", "金庫",
}

# ---- 指標C 生全文プローブから除外する汎用 matter フレーズ ----
GENERIC_MATTER = {
    "法律相談", "企業法務", "相談", "法律相談(法テラス)", "コーポレート", "経営相談",
    "労務相談", "従業員対応", "支援専門家業務", "顧問", "幹事", "病院幹事",
}

# matter らしさの指標語(これを含まない no_delimiter は依頼者名のみと判断し report_safe で抑制)
MATTER_INDICATORS = ("事件", "請求", "相談", "支援", "整理", "対応", "契約", "破産", "再生", "譲渡",
                     "承継", "後見", "離婚", "相続", "事故", "賠償", "清算", "回収", "開示", "違反",
                     "侵入", "窃盗", "傷害", "暴行", "被害", "労務", "団体交渉", "株主", "顧問", "売買",
                     "慰謝料", "養育費", "廃業", "管財", "弁護", "あっせん", "著作", "不当利得", "欠陥",
                     "ストーカー", "M&A", "レビュー", "作成", "検討", "交渉", "経営", "保証", "団交")

DELIM_RE = re.compile(r"[＿_]")
PAREN_RE = re.compile(r"[（(][^（）()]*[)）]\s*$")  # 末尾カッコ
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
URL_RE = re.compile(r"https?://\S+")
PHONE_RE = re.compile(r"(0\d{1,4}-?\d{1,4}-?\d{3,4}|\d{2,4}-\d{2,4}-\d{3,4})")
POSTAL_RE = re.compile(r"〒?\d{3}-?\d{4}")
LONGNUM_RE = re.compile(r"\d{4,}")
COMPANY_RE = re.compile(r"(株式会社|有限会社|合同会社|社会医療法人|医療法人|宗教法人|一般社団法人|一般財団法人|協同組合)[^\s　、。]*|[(（][株有][)）]")


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def match_norm(s):
    """マッチ専用正規化: NFKC + 空白/区切り/カッコ除去。保存・表示には使わない。"""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"[\s　、。・,，.／/（）()「」『』【】\[\]\-―ー]", "", s)
    return s


def h(s, n=12):
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()[:n]


def strip_intake(s):
    """末尾の intake channel カッコを除去。除去語を返す。"""
    removed = []
    changed = True
    while changed:
        changed = False
        m = PAREN_RE.search(s)
        if m:
            inside = re.sub(r"^[（(]|[)）]\s*$", "", m.group(0)).strip()
            if any(ch in inside for ch in INTAKE_CHANNELS) or inside in INTAKE_CHANNELS:
                removed.append(inside)
                s = s[: m.start()].strip()
                changed = True
    return s, removed


def mask_report(text, client_prefix):
    """report-safe マスク。PIIリスクを検出したら (masked_or_None, pii_risk_bool)。
    保守的: リスク検出時は表示抑制に倒す(過剰抑制は安全側)。"""
    if not text:
        return "", False
    t = nfc(text)
    risk = False
    if EMAIL_RE.search(t) or URL_RE.search(t) or PHONE_RE.search(t) or POSTAL_RE.search(t) or LONGNUM_RE.search(t):
        risk = True
    if COMPANY_RE.search(t):
        risk = True
    # 落とした依頼者名(prefix)が本文に漏れていれば強いPIIシグナル。
    # フルトークンだけでなく姓相当の部分一致も拾うため 2文字窓も照合(保守的)。
    if client_prefix:
        cp = nfc(client_prefix)
        cands = set()
        for tok in re.split(r"[\s　・,、]+", cp):
            tok = tok.strip()
            if len(tok) >= 2:
                cands.add(tok)
                for i in range(len(tok) - 1):  # 2文字窓(姓の部分一致対策)
                    cands.add(tok[i:i + 2])
        if any(c in t for c in cands):
            risk = True
    if risk:
        return "[PIIのため表示抑制]", True
    return t, False


def find_spans(needle_match, source_text):
    """source_text(NFC)内で needle(matchつき) の出現位置を返す。
    マッチは match_norm 空間で判定し、概略spanを NFC 上で近似する。"""
    if not source_text:
        return []
    src_m = match_norm(source_text)
    if needle_match not in src_m:
        return []
    # 近似: match_norm で全出現を取り、対応するNFC窓を返す(spanは概略)
    spans = []
    start = 0
    while True:
        i = src_m.find(needle_match, start)
        if i < 0:
            break
        spans.append((i, i + len(needle_match)))
        start = i + 1
    return spans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.expanduser("~/alo-ai/work/searchbench_a1/consultations_raw.json"))
    ap.add_argument("--terms", default=os.path.join(os.path.dirname(__file__), "..", "..", "build", "search_bench", "terms_554_snapshot.json"))
    ap.add_argument("--probe", default=os.path.join(os.path.dirname(__file__), "..", "..", "build", "search_bench", "raw_probe_results.json"))
    ap.add_argument("--outdir", default=os.path.join(os.path.dirname(__file__), "..", "..", "build", "search_bench"))
    ap.add_argument("--asof", default="UNSET")  # YYYYMMDD ; 実行時日付は使わない
    args = ap.parse_args()
    outdir = os.path.abspath(args.outdir)
    os.makedirs(outdir, exist_ok=True)

    raw = json.load(open(args.raw, encoding="utf-8"))["result"]["records"]
    terms_snap = json.load(open(os.path.abspath(args.terms), encoding="utf-8"))
    terms = terms_snap["terms"]
    bib_terms_count = terms_snap["bib_terms_count"]
    probe = {}
    if os.path.exists(os.path.abspath(args.probe)):
        probe = json.load(open(os.path.abspath(args.probe), encoding="utf-8"))

    # term の match-norm を前計算
    for t in terms:
        t["_m"] = match_norm(t["term"])
        t["_short"] = len(nfc(t["term"])) <= 2

    rows = []          # A層 per-consultation
    matches = []       # B層 per term-match
    term_presence_count = Counter()  # data-driven stoplist 用(相談単位の出現)

    for rec in raw:
        sfid = rec.get("Id") or ""
        name = nfc(rec.get("Name") or "")
        outline = nfc(rec.get("leala__CaseOutline__c") or "")
        inferred = rec.get("ALO_Inferred_CaseCategory__c") or "(未分類)"
        flags = []

        # 区切り分割: 依頼者prefix と matter(最終セグメント)
        parts = DELIM_RE.split(name)
        if len(parts) >= 2:
            client_prefix = parts[0]
            matter_raw = parts[-1]
        else:
            client_prefix = ""
            matter_raw = name
            flags.append("no_delimiter")
        matter_raw, removed_ch = strip_intake(matter_raw.strip())

        if not outline:
            flags.append("outline_missing")

        # ノイズ判定
        mt_strip = matter_raw.strip()
        is_noise = (mt_strip in NOISE_EXACT) or (not mt_strip and not outline) or (nfc(name) in NOISE_EXACT)
        if is_noise:
            flags.append("noise")

        query_text_private = (matter_raw + " " + outline).strip()

        # report-safe マスク
        outline_safe, ol_risk = mask_report(outline, client_prefix)
        matter_safe, mt_risk = mask_report(matter_raw, client_prefix)
        # matter は最終セグメントで低リスクだが、企業名/漏洩検出時はマスク
        # 保守的抑制: 区切り無(依頼者prefixを安全に除去できない) は matter を一律抑制。
        # 区切りありでも、依頼者prefix漏洩/企業トークン/数字検出時は抑制。
        no_delim = "no_delimiter" in flags
        if mt_risk:
            matter_safe_display = "[PIIのため表示抑制]"
        elif no_delim:
            matter_safe_display = "[区切り無・表示抑制]"
        else:
            matter_safe_display = matter_raw
        pii_risk = ol_risk or mt_risk or no_delim
        if pii_risk:
            flags.append("pii_risk_suppressed_from_report")
        query_text_report_safe = (matter_safe_display + ((" " + outline_safe) if (outline and not ol_risk) else (" [PIIのため表示抑制]" if ol_risk else ""))).strip()

        ch = h(sfid)
        row = {
            "consultation_hash": ch,
            "sf_id_hash": h(sfid, 40),
            "name_original_private": name,
            "client_prefix_private": client_prefix,
            "matter_type_from_name": matter_raw,
            "matter_type_report_safe": matter_safe_display,
            "removed_intake_channels": "|".join(removed_ch),
            "case_outline_private": outline,
            "case_outline_report_safe": outline_safe,
            "query_text_private": query_text_private,
            "query_text_report_safe": query_text_report_safe,
            "alo_inferred_case_category": inferred,
            "flags": "|".join(flags),
            "book_reach_via_terms": 0,  # bib_terms=0 → 構造的ゼロ(before基準)
        }

        # ---- B層 term presence (noise は集計対象外だがmatchは記録しない) ----
        seen_terms_this = set()
        if not is_noise:
            # 概要末尾の intake channel カッコもマッチ前に除去(「（京都弁護士会）」由来の
            # 語『弁護士会』等の経路ノイズが事件実体への到達と誤計上されるのを防ぐ)
            outline_for_match, _ = strip_intake(outline)
            q_matter_m = match_norm(matter_raw)
            q_outline_m = match_norm(outline_for_match)
            row_match_spans = []  # (term_id, field, start, end, term_m_len)
            for t in terms:
                tm = t["_m"]
                if not tm:
                    continue
                in_matter = tm in q_matter_m
                in_outline = tm in q_outline_m
                if not (in_matter or in_outline):
                    continue
                field = "both" if (in_matter and in_outline) else ("matter_type" if in_matter else "case_outline")
                # span は実テキスト(NFC)側で近似
                src = matter_raw if in_matter else outline_for_match
                spans = find_spans(tm, src)
                start, end = (spans[0] if spans else (-1, -1))
                ctx = ""
                if spans:
                    s0 = max(0, start - 25)
                    ctx = src[s0:end + 25]
                row_match_spans.append((t, field, start, end, len(tm)))
                seen_terms_this.add(t["term_id"])
                matches.append({
                    "consultation_hash": ch,
                    "term_id": t["term_id"],
                    "term_label": t["term"],
                    "scheme": t["scheme"],
                    "is_stoplisted_manual": int(t["term"] in MANUAL_STOPLIST),
                    "is_short_term": int(t["_short"]),
                    "match_field": field,
                    "start_pos": start,
                    "end_pos": end,
                    "context_window": ctx,
                    "match_type": "",  # 後で compound_embedded を確定
                })
            # compound_embedded: 同一相談で、より長い別matchのspanに包含される短いmatch
            # (match_norm長で近似: 自分の term_m が他の matched term_m の部分文字列)
            matched_terms_m = [(t["_m"], t["term_id"]) for (t, *_rest) in row_match_spans]
            for mtch in matches:
                if mtch["consultation_hash"] != ch:
                    continue
                my = match_norm(mtch["term_label"])
                embedded = any((my != om and my in om) for (om, oid) in matched_terms_m if oid != mtch["term_id"])
                short = bool(mtch["is_short_term"])
                stop = bool(mtch["is_stoplisted_manual"])
                if embedded:
                    mtch["match_type"] = "compound_embedded_hit"
                elif stop:
                    mtch["match_type"] = "stoplist_only_hit"
                elif short:
                    mtch["match_type"] = "short_term_hit"
                else:
                    mtch["match_type"] = "non_stop_term_hit"
            for tid in sorted(seen_terms_this):
                term_presence_count[tid] += 1
        rows.append(row)

    n = len(rows)

    # ---- data-driven stoplist: 出現率>10% を high_frequency_term ----
    data_driven = {tid for tid, c in term_presence_count.items() if c / max(1, n) > 0.10}
    dd_labels = {}
    tid2label = {t["term_id"]: t["term"] for t in terms}
    for tid in data_driven:
        dd_labels[tid] = tid2label.get(tid, tid)
    # match_type 再評価: data-driven stop も stoplist 扱いに統合(non_stop から外す)
    for m in matches:
        if m["match_type"] == "non_stop_term_hit" and m["term_id"] in data_driven:
            m["match_type"] = "stoplist_only_hit"
            m["is_stoplisted_datadriven"] = 1
        else:
            m["is_stoplisted_datadriven"] = int(m["term_id"] in data_driven)

    # ---- 指標C 生全文プローブ: 距離のあるフレーズ集合を要求として書き出す ----
    distinct_phrases = {}
    for r in rows:
        if "noise" in r["flags"]:
            continue
        ph = r["matter_type_from_name"].strip()
        if len(ph) < 2:
            continue
        if ph in GENERIC_MATTER:
            r["flags"] = (r["flags"] + "|generic_matter_type_excluded_from_probe").strip("|")
            continue
        distinct_phrases.setdefault(ph, []).append(r["consultation_hash"])
    json.dump({"phrases": sorted(distinct_phrases.keys())}, open(os.path.join(outdir, "raw_probe_phrases.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)

    # probe 結果をマージ(あれば)
    for r in rows:
        ph = r["matter_type_from_name"].strip()
        pr = probe.get(ph) if probe else None
        r["raw_toc_probe_hit_count"] = (pr or {}).get("toc_hits", "" if not probe else 0)
        r["raw_record_probe_hit_count"] = (pr or {}).get("record_hits", "" if not probe else 0)

    # ---- failure_or_outcome_class (相談単位の主要結果) ----
    by_ch_matchtypes = defaultdict(set)
    for m in matches:
        by_ch_matchtypes[m["consultation_hash"]].add(m["match_type"])
    for r in rows:
        ch = r["consultation_hash"]
        mts = by_ch_matchtypes.get(ch, set())
        if "noise" in r["flags"]:
            oc = "noise_record"
        elif "non_stop_term_hit" in mts:
            oc = "non_stop_term_hit"
        elif mts:  # stoplist/short/compound のみ
            oc = "stoplist_only_hit"
        else:
            toc = r.get("raw_toc_probe_hit_count")
            rcr = r.get("raw_record_probe_hit_count")
            has_probe = (isinstance(toc, int) and toc > 0) or (isinstance(rcr, int) and rcr > 0)
            if has_probe:
                oc = "raw_probe_hit_but_no_term_hit"
            elif probe:
                oc = "no_term_no_raw_probe"
            else:
                oc = "no_term_hit__probe_pending"
        r["failure_or_outcome_class"] = oc

    # ============ 出力 ============
    PRIVATE_COLS = ["consultation_hash", "sf_id_hash", "name_original_private", "client_prefix_private",
                    "matter_type_from_name", "removed_intake_channels", "case_outline_private",
                    "query_text_private", "alo_inferred_case_category", "flags",
                    "book_reach_via_terms", "raw_toc_probe_hit_count", "raw_record_probe_hit_count",
                    "failure_or_outcome_class"]
    SAFE_COLS = ["consultation_hash", "matter_type_report_safe", "case_outline_report_safe",
                 "query_text_report_safe", "alo_inferred_case_category", "flags",
                 "book_reach_via_terms", "raw_toc_probe_hit_count", "raw_record_probe_hit_count",
                 "failure_or_outcome_class"]

    def write_csv(path, cols):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)

    write_csv(os.path.join(outdir, "a1_consultation_queries_private.csv"), PRIVATE_COLS)
    write_csv(os.path.join(outdir, "a1_consultation_queries_report_safe.csv"), SAFE_COLS)

    MATCH_COLS = ["consultation_hash", "term_id", "term_label", "scheme", "is_stoplisted_manual",
                  "is_stoplisted_datadriven", "is_short_term", "match_field", "start_pos", "end_pos",
                  "context_window", "match_type"]
    with open(os.path.join(outdir, "a1_term_matches_private.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MATCH_COLS, extrasaction="ignore")
        w.writeheader()
        for m in matches:
            w.writerow(m)

    with open(os.path.join(outdir, "a1_raw_probe_hits.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["matter_phrase", "n_consultations", "raw_toc_probe_hit_count", "raw_record_probe_hit_count", "probe_status"])
        for ph in sorted(distinct_phrases.keys()):
            pr = probe.get(ph) if probe else None
            w.writerow([ph, len(distinct_phrases[ph]),
                        (pr or {}).get("toc_hits", ""), (pr or {}).get("record_hits", ""),
                        "done" if pr else ("pending" if not probe else "missing")])

    # ---- summary.json (決定的・再実行比較用) ----
    def count_flag(flag):
        return sum(1 for r in rows if flag in r["flags"].split("|"))
    outcome_dist = Counter(r["failure_or_outcome_class"] for r in rows)
    # 種別別
    by_cat = defaultdict(lambda: {"n": 0, "non_stop_term_hit": 0, "zero_or_stop": 0})
    for r in rows:
        c = by_cat[r["alo_inferred_case_category"]]
        c["n"] += 1
        if r["failure_or_outcome_class"] == "non_stop_term_hit":
            c["non_stop_term_hit"] += 1
        elif r["failure_or_outcome_class"] in ("stoplist_only_hit", "no_term_no_raw_probe", "no_term_hit__probe_pending", "raw_probe_hit_but_no_term_hit"):
            c["zero_or_stop"] += 1
    # outline あり/なし 分離
    with_outline = [r for r in rows if "outline_missing" not in r["flags"] and "noise" not in r["flags"]]
    without_outline = [r for r in rows if "outline_missing" in r["flags"] and "noise" not in r["flags"]]

    def reach_rate(subset):
        if not subset:
            return None
        hit = sum(1 for r in subset if r["failure_or_outcome_class"] == "non_stop_term_hit")
        return round(hit / len(subset), 4)

    # match_field 寄与
    field_contrib = Counter(m["match_field"] for m in matches if m["match_type"] == "non_stop_term_hit")
    # stoplist 依存度
    mt_dist = Counter(m["match_type"] for m in matches)

    summary = {
        "name": "A1 consultation search observation baseline",
        "asof": args.asof,
        "is_evaluation": False,
        "note": "kansoku baseline: records only the DB reaction to real consultation text; before-snapshot for the bib_terms bridge",
        "totals": {
            "consultations": n,
            "noise_excluded": count_flag("noise"),
            "no_delimiter": count_flag("no_delimiter"),
            "outline_missing": count_flag("outline_missing"),
            "pii_risk_suppressed_from_report": count_flag("pii_risk_suppressed_from_report"),
            "generic_matter_type_excluded_from_probe": count_flag("generic_matter_type_excluded_from_probe"),
        },
        "structural_facts": {
            "bib_terms_count": bib_terms_count,
            "book_reach_via_terms_all_zero": all(r["book_reach_via_terms"] == 0 for r in rows),
            "terms_count": len(terms),
            "bib_records_total": terms_snap.get("bib_records_total"),
            "bib_toc_total": terms_snap.get("bib_toc_total"),
        },
        "outcome_distribution": dict(outcome_dist),
        "term_match_type_distribution": dict(mt_dist),
        "non_stop_match_field_contribution": dict(field_contrib),
        "reach_rate_non_stop_term": {
            "all_non_noise": reach_rate([r for r in rows if "noise" not in r["flags"]]),
            "with_outline": reach_rate(with_outline),
            "without_outline": reach_rate(without_outline),
        },
        "data_driven_stoplist_terms": sorted(dd_labels.values()),
        "by_inferred_category": {k: v for k, v in sorted(by_cat.items(), key=lambda kv: -kv[1]["n"])},
        "raw_probe_status": "done" if probe else "pending",
        "term_presence_top": [tid2label[tid] for tid, _ in sorted(term_presence_count.items(), key=lambda kv: (-kv[1], tid2label[kv[0]]))[:25]],
    }
    json.dump(summary, open(os.path.join(outdir, "a1_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2, sort_keys=True)

    # ---- owner review 空欄台紙(docs・コミット可・owner_*は空) ----
    obs_terms = defaultdict(list)
    for m in matches:
        if m["match_type"] in ("non_stop_term_hit", "stoplist_only_hit"):
            obs_terms[m["consultation_hash"]].append(m["term_label"] + ("" if m["match_type"] == "non_stop_term_hit" else "(stop)"))
    scaffold = [
        f"# A1 Owner Review Scaffold (asof {args.asof})\n",
        "> これは gold ではない。後日 owner が監修値を入れるための**空欄台紙**。owner_* 欄は Stage1 では空のまま（本スクリプトは埋めない）。",
        "> observed_* は観測値（canonical term は非PII）。query は report-safe（PIIリスク行は抑制済）。noise除外。\n",
        "| consultation_hash | inferred_cat | query_text_report_safe | observed_terms | raw_toc | raw_rec | outcome | owner_review_status_blank | owner_comment_blank | owner_gold_later_blank |",
        "|---|---|---|---|--:|--:|---|---|---|---|",
    ]
    for r in rows:
        if "noise" in r["flags"]:
            continue
        ch = r["consultation_hash"]
        terms = ", ".join(sorted(set(obs_terms.get(ch, [])))) or "—"
        scaffold.append(f"| {ch} | {r['alo_inferred_case_category']} | {r['query_text_report_safe']} | {terms} | {r['raw_toc_probe_hit_count']} | {r['raw_record_probe_hit_count']} | {r['failure_or_outcome_class']} |  |  |  |")
    scaffold_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"owner_review_scaffold_{args.asof}.md")
    open(scaffold_path, "w", encoding="utf-8").write("\n".join(scaffold) + "\n")

    # ============ 自己検査(品質ゲート) ============
    failures = []
    if n != 230:
        failures.append(f"consultation total {n} != 230")
    # 禁止語が出力カラム/サマリキーに非空で存在しないこと
    header_blob = " ".join(PRIVATE_COLS + SAFE_COLS + MATCH_COLS + list(summary.keys()))
    for tok in FORBIDDEN_TOKENS:
        if tok in header_blob:
            failures.append(f"forbidden token in headers/keys: {tok}")
    if not summary["structural_facts"]["book_reach_via_terms_all_zero"]:
        failures.append("book_reach_via_terms not all zero")
    # コミット対象ファイルの中身に禁止語が無いこと(列名・見出し・値すべて)
    for fn in ["a1_summary.json", "a1_consultation_queries_report_safe.csv", "terms_554_snapshot.json"]:
        fp = os.path.join(outdir, fn)
        if os.path.exists(fp):
            blob = open(fp, encoding="utf-8").read()
            for tok in FORBIDDEN_TOKENS:
                if tok in blob:
                    failures.append(f"forbidden token '{tok}' in committable {fn}")
    # report_safe CSV に依頼者prefix列やprivate列が無いこと
    if any(c.endswith("_private") for c in SAFE_COLS):
        failures.append("private column leaked into report_safe")

    print("=== A1 observation baseline ===")
    print(json.dumps(summary["totals"], ensure_ascii=False))
    print("structural:", json.dumps(summary["structural_facts"], ensure_ascii=False))
    print("outcome:", json.dumps(summary["outcome_distribution"], ensure_ascii=False))
    print("match_type:", json.dumps(summary["term_match_type_distribution"], ensure_ascii=False))
    print("reach(non_stop):", json.dumps(summary["reach_rate_non_stop_term"], ensure_ascii=False))
    print("data_driven_stoplist:", summary["data_driven_stoplist_terms"])
    print("raw_probe_status:", summary["raw_probe_status"])
    print("self-check:", "PASS" if not failures else ("FAIL: " + "; ".join(failures)))
    if failures:
        sys.exit(2)


if __name__ == "__main__":
    main()
