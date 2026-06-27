#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ORCH-CASENAME-DICT — 評釈タイトルからの事件名辞書構築

入力:
  - article_join_dryrun_v0.1.csv      (タイトル全件; article_id, title 列を使用)
  - article_type_local_pilot_v0.1.csv (判例評釈タグ; パイロット範囲のみ・参考タグ付け用)

処理:
  1. タイトルから「○○事件 / ○○訴訟」を抽出（生表記=variant、NFKC正規化=グループ鍵）
  2. タイトル括弧内の (court, date) を抽出して紐付け
  3. 固有名シグナル(企業/団体/地名/カナ/英字/裁判所+日付アンカー)を持つものだけを
     「事件名」として採用し、一般法律用語(憲法訴訟・株主代表訴訟 等)は除外
  4. 表記ゆれ統合: 第一鍵=(date,court_class)、第二鍵=NFKC名称(suffix包含で短縮形吸収)
     variant_names は生表記の集合（全角/半角・髙/高 等のゆれを保持）

出力:
  - case_name_dict_v0.1.csv      (case_name_normalized, court, date, variant_names[], article_ids[], n_articles, is_hanrei_hyoshaku)
  - case_name_dict_summary_v0.1.json
"""
import csv, json, re, sys, unicodedata, statistics
from collections import defaultdict, Counter

JOIN_CSV  = sys.argv[1]
PILOT_CSV = sys.argv[2]
OUT_CSV   = sys.argv[3]
OUT_JSON  = sys.argv[4]

csv.field_size_limit(10**7)

# ----- 判例評釈 pilot タグ -----
hyoshaku = set()
with open(PILOT_CSV, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r.get("type") == "判例評釈":
            hyoshaku.add(r["article_id"])

# ----- 日付・裁判所 -----
ERA = r'(令和|平成|昭和|大正|明治)'
DATE_RE = re.compile(ERA + r'\s*(元|\d{1,2})\s*[.・年]\s*(\d{1,2})\s*[.・月]\s*(\d{1,2})\s*日?')
COURT_RE = re.compile(
    r'(最(?:高|大)(?:[一二三]小)?(?:法廷)?(?:判決|決定|判|決)'   # 最高裁
    r'|最(?:大判|大決|判|決)'
    r'|知財高裁?(?:判決|決定|判|決)?'                              # 知財高裁
    r'|[一-鿿]{2,6}(?:地|高|簡|家)(?:[一-鿿]{1,4}支)?(?:裁)?(?:判決|決定|判|決)'  # 下級審(漢字地名のみ)
    r'|公正取引委員会|公取委|特許庁|中労委|労委|人事院|審決)'
)

# ----- 名称抽出 -----
SEP = set('―—‐－-「」『』（）()【】〔〕《》〈〉，、。．，,…‥／/｜|：:；;　 ＜＞<>"\'’”“×*＊＝=～~')
for keep in '・ー＝':   # 名称内に残す
    SEP.discard(keep)
NAME_SUFFIX = re.compile(r'(事件|訴訟)')
# 名称構成文字（生表記対応: 全角英数/カナ/漢字/かな/長音/中黒 等を含む）
NAMEUSE = re.compile(
    r'[0-9A-Za-z０-９Ａ-Ｚａ-ｚ'
    r'ぁ-ゖァ-ヺ一-鿿々〆ヶ'
    r'ー・ｰ･＝=＝〓㈱°&＆]'
)

STOP_FULL = {
    "民事訴訟","刑事訴訟","行政訴訟","本件訴訟","別訴訟","本訴訟","当該訴訟","別件訴訟",
    "損害賠償請求訴訟","国家賠償請求訴訟","住民訴訟","行政事件訴訟","民事事件","刑事事件",
    "行政事件","少年事件","家事事件","本件事件","別件事件","当該事件","同事件","本事件",
    "関連事件","刑事事件訴訟","民事訴訟法","行政事件訴訟法","株主代表訴訟","代表訴訟",
    "憲法訴訟","人事訴訟","労働事件","独占禁止法違反事件","不当労働行為事件",
    "不当労働行為事件の行政訴訟","新民事訴訟","国際民事訴訟","ドイツ民事訴訟","行政訴訟事件",
}
STOP_STEM_EXACT = {"民事","刑事","行政","当該","本件","別件","関連","同種","一連","別","本","同",
                   "株主代表","代表","憲法","人事","労働","国際民事","ドイツ民事","新民事"}
# 末尾がこれらの名称は教科書/論題(事件名でない)。アンカー(日付+裁判所)が無ければ除外
GENERIC_TAILS = ("民事訴訟","刑事訴訟","行政訴訟","会社訴訟","民事訴訟法","行政訴訟法",
                 "刑事訴訟法","代表訴訟","株主代表訴訟","少年事件","家事事件","行政事件")

# 固有名シグナル（企業・団体・地名・カナ・英字）
ORG = ("会社|株式|有限|合同|合名|合資|組合|協同|法人|学校|大学|学園|高校|高専|病院|医院|診療"
       "|銀行|信金|信用金庫|金庫|財団|協会|連盟|連合|労組|労働組合|工業|産業|製作所|製鉄|製薬"
       "|製菓|製粉|商事|物産|興業|電機|電力|電鉄|運輸|海運|建設|不動産|新聞|放送|出版|空港|港湾"
       "|ホテル|百貨店|ストア|フーズ|ファーム|ホールディングス|グループ|食品|化学|鉱業|炭鉱"
       "|紡績|繊維|自動車|鉄道|航空|海上|火災|生命|損保|保険|証券|信託|郵便|テレビ|ラジオ"
       "|商店|工場|農協|漁協|生協|共済|事業団|公社|公団|機構|センター|サービス|システム"
       "|党|教会|寺|神社|宗派|塾|幼稚園|保育園|村|町|市|区|県|府|都|郡|藩|ほか")
ORG_RE = re.compile(ORG)
KATAKANA_RE = re.compile(r'[ァ-ヺｦ-ﾝ]{2,}')
LATIN_RE = re.compile(r'[A-Za-zＡ-Ｚａ-ｚ]')

def has_proper_signal(name):
    return bool(ORG_RE.search(name) or KATAKANA_RE.search(name) or LATIN_RE.search(name))

def nrm(s):
    return unicodedata.normalize("NFKC", s)

def extract_raw_names(title):
    """生タイトルから (raw_surface, raw_stem) のリスト"""
    out = []
    for m in NAME_SUFFIX.finditer(title):
        suf = m.group(1); i = m.start(); j = i
        while j > 0:
            c = title[j-1]
            if c in SEP or not NAMEUSE.match(c):
                break
            j -= 1
        stem = title[j:i]
        if len(stem) < 2:
            continue
        out.append((title[j:m.end()], stem))
    return out

def parse_date_court(title_nfkc):
    m = DATE_RE.search(title_nfkc)
    if not m:
        return None, None
    era, y, mo, d = m.group(1), m.group(2), m.group(3), m.group(4)
    y = "1" if y == "元" else y
    date_norm = f"{era}{int(y)}.{int(mo)}.{int(d)}"
    # 裁判所は日付直後(同一括弧内)にのみ出現するため match のみ（緩い search はノイズ源）
    tail = title_nfkc[m.end():m.end()+16].lstrip("（()） 　")
    cm = COURT_RE.match(tail)
    court = cm.group(1) if cm else None
    return date_norm, court

def court_class(c):
    if not c: return None
    if c.startswith("最"): return "最高裁"
    return c

# ----- 1パス目 -----
records = []
n_titles = n_with_name = n_dropped_generic = 0
with open(JOIN_CSV, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        title = r.get("title") or ""
        if not title: continue
        n_titles += 1
        title_nfkc = nrm(title)
        raws = extract_raw_names(title)
        if not raws: continue
        date_norm, court = parse_date_court(title_nfkc)
        aid = r["article_id"]; hy = aid in hyoshaku
        anchored = bool(date_norm and court)
        seen = set()
        kept_any = False
        for raw, raw_stem in raws:
            name_n = nrm(raw)
            stem_n = name_n[:-2]
            if name_n in seen: continue
            seen.add(name_n)
            if name_n in STOP_FULL or stem_n in STOP_STEM_EXACT: continue
            if not re.search(r'[一-鿿ぁ-ヿA-Za-z]', stem_n): continue
            # 所有格「○○の事件」(小説/読み物表現) は事件名でない
            if stem_n.endswith("の"):
                n_dropped_generic += 1; continue
            # 連載コラム見出し「ザ・/新・/続・○○訴訟」(例: ザ・税務訴訟) は事件名でない
            # ※「ザ・トーカイ事件」等の社名(事件 suffix)は除外しない
            if name_n.endswith("訴訟") and name_n[:2] in ("ザ・","新・","続・"):
                n_dropped_generic += 1; continue
            # 教科書/論題の末尾 (アンカー無しなら除外)
            if (not anchored) and name_n.endswith(GENERIC_TAILS):
                n_dropped_generic += 1; continue
            # 採用条件: 固有名シグナル OR (日付+裁判所アンカー)
            if not (has_proper_signal(name_n) or anchored):
                n_dropped_generic += 1
                continue
            records.append({"raw": raw, "name_n": name_n, "stem_n": stem_n,
                            "court": court, "date": date_norm, "aid": aid, "hy": hy})
            kept_any = True
        if kept_any: n_with_name += 1

# ----- グルーピング -----
groups = {}
def gg(key):
    if key not in groups:
        groups[key] = {"vraw": Counter(), "vnorm": Counter(), "courts": Counter(),
                       "dates": Counter(), "aids": set(), "hy": False}
    return groups[key]

for r in records:
    if r["date"]:
        key = ("D", r["date"], court_class(r["court"]) or "?")
    else:
        key = ("N", r["name_n"])
    g = gg(key)
    g["vraw"][r["raw"]] += 1
    g["vnorm"][r["name_n"]] += 1
    if r["court"]: g["courts"][r["court"]] += 1
    if r["date"]: g["dates"][r["date"]] += 1
    g["aids"].add(r["aid"])
    g["hy"] = g["hy"] or r["hy"]

# ----- 名称鍵 suffix 包含マージ -----
name_keys = [k for k in groups if k[0] == "N"]
canon = {k: groups[k]["vnorm"].most_common(1)[0][0] for k in name_keys}
order = sorted(name_keys, key=lambda k: len(canon[k]), reverse=True)
merged_into = {}
for ks in order:
    ns = canon[ks]; stem_s = ns[:-2]
    if len(stem_s) < 5: continue
    for kl in order:
        if kl is ks: continue
        nl = canon[kl]
        if len(nl) <= len(ns): continue
        if nl.endswith(ns) and kl not in merged_into:
            merged_into[ks] = kl; break

def resolve(k):
    seen=set()
    while k in merged_into and k not in seen:
        seen.add(k); k = merged_into[k]
    return k

final = {}
name_to_courtclasses = defaultdict(set)
for k, g in groups.items():
    tgt = resolve(k) if k[0]=="N" else k
    fg = final.setdefault(tgt, {"vraw":Counter(),"vnorm":Counter(),"courts":Counter(),
                                "dates":Counter(),"aids":set(),"hy":False})
    fg["vraw"].update(g["vraw"]); fg["vnorm"].update(g["vnorm"])
    fg["courts"].update(g["courts"]); fg["dates"].update(g["dates"])
    fg["aids"] |= g["aids"]; fg["hy"] = fg["hy"] or g["hy"]

# ----- 出力 -----
rows = []
for key, g in final.items():
    variants = [v for v,_ in g["vraw"].most_common()]
    best = max(g["vnorm"].items(), key=lambda kv:(kv[1], len(kv[0])))[0]
    court = g["courts"].most_common(1)[0][0] if g["courts"] else ""
    date = g["dates"].most_common(1)[0][0] if g["dates"] else (key[1] if key[0]=="D" else "")
    # multi-court 集計用: 代表名 -> court_class 集合
    for c in g["courts"]:
        name_to_courtclasses[best].add(court_class(c))
    rows.append({
        "case_name_normalized": best, "court": court, "date": date,
        "variant_names": variants, "article_ids": sorted(g["aids"]),
        "n_articles": len(g["aids"]), "n_variants": len(variants),
        "is_hanrei_hyoshaku": g["hy"],
    })
rows.sort(key=lambda x:(-x["n_articles"], -x["n_variants"], x["case_name_normalized"]))

with open(OUT_CSV,"w",encoding="utf-8",newline="") as f:
    w=csv.writer(f)
    w.writerow(["case_name_normalized","court","date","variant_names","article_ids","n_articles","is_hanrei_hyoshaku"])
    for r in rows:
        w.writerow([r["case_name_normalized"],r["court"],r["date"],
                    "|".join(r["variant_names"]),"|".join(r["article_ids"]),
                    r["n_articles"],"1" if r["is_hanrei_hyoshaku"] else "0"])

nv=[r["n_variants"] for r in rows]
multi_court=[{"case_name_normalized":n,"court_classes":sorted(cc)} for n,cc in name_to_courtclasses.items() if len(cc)>=2]
nv_dated=[r["n_variants"] for r in rows if r["date"]]
nv_multi=[r["n_variants"] for r in rows if r["n_articles"]>=2]  # 統合が適用される(複数記事)母集団
summary={
  "total_unique_cases":len(rows),
  "total_name_extractions":len(records),
  "titles_scanned":n_titles,
  "titles_with_case_name":n_with_name,
  "dropped_generic_terms":n_dropped_generic,
  "cases_with_date":sum(1 for r in rows if r["date"]),
  "cases_with_court":sum(1 for r in rows if r["court"]),
  "variant_names_median":statistics.median(nv) if nv else 0,
  "variant_names_mean":round(statistics.mean(nv),3) if nv else 0,
  "variant_names_median_dated_cases":statistics.median(nv_dated) if nv_dated else 0,
  "variant_names_median_multicited_cases":statistics.median(nv_multi) if nv_multi else 0,
  "multicited_cases_count":len(nv_multi),
  "cases_multi_variant":sum(1 for x in nv if x>=2),
  "top20_most_cited_cases":[{"case_name_normalized":r["case_name_normalized"],"court":r["court"],
      "date":r["date"],"n_articles":r["n_articles"],"n_variants":r["n_variants"]} for r in rows[:20]],
  "multi_court_cases_count":len(multi_court),
  "multi_court_cases_sample":multi_court[:20],
  "acceptance":{
     "extractions_ge_1500":len(records)>=1500,
     "unique_cases":len(rows),
     "variant_median_ge_2_allcases":(statistics.median(nv) if nv else 0)>=2,
     "variant_median_ge_2_multicited":(statistics.median(nv_multi) if nv_multi else 0)>=2,
     "note":"全件母集団の中央値は long-tail(単独被引用が過半)により1。表記ゆれ統合が適用される複数記事被引用ケースでは中央値を別途報告。",
  },
}
with open(OUT_JSON,"w",encoding="utf-8") as f:
    json.dump(summary,f,ensure_ascii=False,indent=2)

print(json.dumps({k:summary[k] for k in
   ["total_unique_cases","total_name_extractions","titles_with_case_name",
    "dropped_generic_terms","cases_with_date","cases_with_court",
    "variant_names_median","variant_names_median_multicited_cases","multicited_cases_count",
    "variant_names_mean","cases_multi_variant","multi_court_cases_count"]}, ensure_ascii=False, indent=2))
print("\nTOP15:")
for r in rows[:15]:
    print(f'  {r["n_articles"]:3d}x v{r["n_variants"]:2d} {r["case_name_normalized"]} [{r["court"]} {r["date"]}]')
