#!/usr/bin/env python3
# ORCH-DATA-PROFILE — 雑誌オブジェクト全体の統計プロファイル (read-only)
# 入力(すべて read-only):
#   artifacts/periodical/article_join_dryrun_v0.1.csv   (記事→号 接合, 主テーブル)
#   artifacts/periodical/article_series_v0.1.csv        (連載検出)
#   artifacts/periodical/issue_feature_v0.1.csv         (特集検出)
# 出力:
#   artifacts/periodical/data_profile_v0.1.md
#   artifacts/periodical/data_profile_anomalies_v0.1.csv  (issue_id, anomaly_type, evidence)
import csv, collections, re, sys, os

BASE = sys.argv[1] if len(sys.argv) > 1 else "artifacts/periodical"
OUT  = sys.argv[2] if len(sys.argv) > 2 else BASE
AJ   = os.path.join(BASE, "article_join_dryrun_v0.1.csv")
SER  = os.path.join(BASE, "article_series_v0.1.csv")
FEAT = os.path.join(BASE, "issue_feature_v0.1.csv")

# ---- 評釈(判例評釈)判定 ----
ERA = r"(?:令和|平成|昭和|大正|明治|令元)"
RE_COURT_DATE = re.compile(r"[（(][^（）()]*" + ERA + r"[^（）()]*(?:判|決|審|命令|裁決)[^（）()]*[)）]")
RE_HYO_KW = re.compile(r"判例(?:研究|評釈|批評|紹介|解説|評論)|判批|最高裁判所判例解説|裁判例研究")
def is_hyoshaku(title):
    if not title:
        return False
    return bool(RE_COURT_DATE.search(title) or RE_HYO_KW.search(title))

# ---- tsuukan parse ----
def parse_single(t):
    t = t.strip()
    return int(t) if re.fullmatch(r"\d+", t) else None
def parse_range(t):
    m = re.fullmatch(r"(\d+)\s*[-‐-―~]\s*(\d+)", t.strip())
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if b >= a and b - a < 20:
            return list(range(a, b + 1))
    return None
RE_VOLISSUE = re.compile(r"^v(\d+)n(\d+)$")

# ============ load article_series (article_id set + per-journal) ============
series_articles = set()
with open(SER, newline="", encoding="utf-8") as f:
    r = csv.reader(f); h = next(r); ix = {c: i for i, c in enumerate(h)}
    for row in r:
        if len(row) != len(h):
            continue
        series_articles.add(row[ix["article_id"]])

# ============ load issue_feature (issue_id -> feature rows) ============
feat_by_issue = collections.defaultdict(list)
feat_total = 0
with open(FEAT, newline="", encoding="utf-8") as f:
    r = csv.reader(f); h = next(r); ix = {c: i for i, c in enumerate(h)}
    for row in r:
        if len(row) != len(h):
            continue
        feat_by_issue[row[ix["issue_id"]]].append(row[ix["feature_title"]])
        feat_total += 1

# ============ load article_join (main) ============
# per-journal aggregates
J = collections.defaultdict(lambda: dict(arts=0, joined=0, hyo=0, ser=0, issues=set(),
                                         key_types=collections.Counter()))
year_arts = collections.Counter()
year_issues = collections.defaultdict(set)
# issue-level
issues = {}   # issue_id -> attrs
malformed = 0
total = 0
with open(AJ, newline="", encoding="utf-8") as f:
    r = csv.reader(f); h = next(r); ix = {c: i for i, c in enumerate(h)}
    for row in r:
        if len(row) != len(h):
            malformed += 1
            continue
        total += 1
        iid = row[ix["issue_id"]]
        j   = row[ix["journal_canonical"]]
        aid = row[ix["article_id"]]
        yr  = row[ix["pub_year"]]
        st  = row[ix["join_status"]]
        ttl = row[ix["title"]]
        d = J[j]
        d["arts"] += 1
        if st == "joined":
            d["joined"] += 1
        if is_hyoshaku(ttl):
            d["hyo"] += 1
        if aid in series_articles:
            d["ser"] += 1
        d["issues"].add(iid)
        d["key_types"][row[ix["key_type"]]] += 1
        if yr.isdigit():
            year_arts[int(yr)] += 1
            year_issues[int(yr)].add(iid)
        if iid not in issues:
            issues[iid] = dict(journal=j, key_type=row[ix["key_type"]], key_value=row[ix["key_value"]],
                               tsu=row[ix["tsuukan_or_ym"]], year=yr, vol=row[ix["vol"]],
                               issue_no=row[ix["issue_no"]], n=0)
        issues[iid]["n"] += 1

# feature count per journal (via issue_id membership)
feat_by_journal = collections.Counter()
issue_journal = {iid: d["journal"] for iid, d in issues.items()}
for iid, feats in feat_by_issue.items():
    j = issue_journal.get(iid)
    if j is not None:
        feat_by_journal[j] += len(feats)

# ============ ANOMALY DETECTION ============
anomalies = []  # (issue_id, anomaly_type, evidence)
by_j = collections.defaultdict(list)
for iid, d in issues.items():
    by_j[d["journal"]].append((iid, d))

R = 5  # 欠号run最大長 (これ以下かつ両端present のみ flag)
tsu_journal_set = set()
volissue_journal_set = set()

for j, lst in by_j.items():
    # --- tsuukan regime? ---
    present = set(); singleton_iid = collections.defaultdict(set)
    range_members = collections.defaultdict(set)  # value -> set(iid) covered by a range issue
    range_issue = {}  # iid -> (a,b)
    parsed = 0
    for iid, d in lst:
        s = parse_single(d["tsu"])
        if s is not None:
            present.add(s); singleton_iid[s].add(iid); parsed += 1
        else:
            rg = parse_range(d["tsu"])
            if rg:
                present.update(rg); parsed += 1; range_issue[iid] = (rg[0], rg[-1])
                for v in rg:
                    range_members[v].add(iid)

    if parsed >= 0.5 * len(lst) and len(present) >= 10:
        tsu_journal_set.add(j)
        nums = sorted(present)
        # --- year-leak suspects: dense-core cluster jump ---
        core = nums[:]
        sus = []
        # find big jump near top: split off trailing values that are year-like & far above core
        # iterate: while top value is year-like AND (top - core_median*1.5) big OR jump>100 below it
        # robust: locate largest gap in upper half; values above it that are years -> suspect
        if len(core) > 5:
            # candidate suspects: any value in [1981,2027] greater than 1.3*(95th pct of the rest)
            base = sorted(v for v in core if not (1981 <= v <= 2027))
            ref = base[int(len(base) * 0.95)] if base else core[-1]
            for v in list(core):
                if 1981 <= v <= 2027 and v > max(ref * 1.3, ref + 80):
                    sus.append(v); core.remove(v)
        for v in sus:
            iids = singleton_iid.get(v, set()) | range_members.get(v, set())
            rep = sorted(iids)[0] if iids else f"{j}#tsu:{v}"
            anomalies.append((rep, "tsuukan_value_outlier",
                              f"journal={j}; 通巻値={v} は年号(1981-2026)域かつ正規系列(<= {int(ref)} 付近)から逸脱。年が通巻欄に混入の疑い"))
        # low-side outlier trim (除外のみ, flagしない)
        while len(core) >= 2 and core[1] - core[0] > 50:
            core.pop(0)
        # --- bounded short gap runs ---
        coreset = set(core)
        if core:
            lo, hi = core[0], core[-1]
            missing = [v for v in range(lo, hi + 1) if v not in coreset]
            i = 0
            while i < len(missing):
                k = i
                while k + 1 < len(missing) and missing[k + 1] == missing[k] + 1:
                    k += 1
                run = missing[i:k + 1]
                a, b = run[0], run[-1]
                if len(run) <= R and (a - 1 in coreset) and (b + 1 in coreset):
                    label = f"{a}" if a == b else f"{a}-{b}"
                    anomalies.append((f"{j}#tsu_gap:{label}", "tsuukan_gap",
                                      f"journal={j}; 通巻{label}が欠落(記事0件); 前後{a-1}・{b+1}は存在; 系列範囲[{lo},{hi}]"))
                i = k + 1
        # --- duplicate 通巻 (二重発行): 同一通巻が複数issue_id ---
        for v, iids in singleton_iid.items():
            if len(iids) > 1:
                il = sorted(iids)
                anomalies.append((il[0], "tsuukan_duplicate",
                                  f"journal={j}; 通巻{v}が{len(iids)}件のissue_idに重複: {il[:4]}"))
        # --- range/singleton overlap (合併号と単独号の重複計上) ---
        for v, riids in range_members.items():
            if v in singleton_iid:
                il = sorted(singleton_iid[v]) ; rl = sorted(riids)
                anomalies.append((il[0], "tsuukan_range_overlap",
                                  f"journal={j}; 通巻{v}が単独号{il[:2]}と合併号{rl[:2]}に二重に出現"))
        continue

    # --- volume/issue regime (vNnM) ---
    vol_issues = collections.defaultdict(lambda: collections.defaultdict(set))  # vol -> issueno -> set(iid)
    pn = 0
    for iid, d in lst:
        m = RE_VOLISSUE.match(d["tsu"].strip())
        if m:
            v, n = int(m.group(1)), int(m.group(2))
            vol_issues[v][n].add(iid); pn += 1
    if pn >= 0.5 * len(lst) and pn >= 10:
        volissue_journal_set.add(j)
        for v, ns in vol_issues.items():
            present_n = sorted(ns)
            if len(present_n) < 3:
                continue
            mx = present_n[-1]
            miss = [x for x in range(1, mx + 1) if x not in ns]
            if miss:
                # 連続runにまとめ
                i = 0
                while i < len(miss):
                    k = i
                    while k + 1 < len(miss) and miss[k + 1] == miss[k] + 1:
                        k += 1
                    run = miss[i:k + 1]
                    if len(run) <= R:
                        lab = f"{run[0]}" if run[0] == run[-1] else f"{run[0]}-{run[-1]}"
                        anomalies.append((f"{j}#v{v}_gap:{lab}", "volissue_gap",
                                          f"journal={j}; 第{v}巻 第{lab}号が欠落(観測max号={mx})"))
                    i = k + 1
            for n, iids in ns.items():
                if len(iids) > 1:
                    il = sorted(iids)
                    anomalies.append((il[0], "volissue_duplicate",
                                      f"journal={j}; 第{v}巻第{n}号が{len(iids)}件のissue_idに重複: {il[:4]}"))

# --- ISBN (isbn_per_issue) 重複検出 ---
isbn_by_val = collections.defaultdict(set)   # (journal,key_value) -> issue_ids
isbn_issue_vals = collections.defaultdict(set)  # issue_id -> key_values
isbn_journals = set()
for iid, d in issues.items():
    if d["key_type"] == "isbn_per_issue":
        isbn_journals.add(d["journal"])
        if d["key_value"]:
            isbn_by_val[(d["journal"], d["key_value"])].add(iid)
            isbn_issue_vals[iid].add(d["key_value"])
isbn_dup_groups = 0
for (j, val), iids in isbn_by_val.items():
    if len(iids) > 1:
        isbn_dup_groups += 1
        il = sorted(iids)
        anomalies.append((il[0], "isbn_duplicate",
                          f"journal={j}; ISBN/識別子 {val} が{len(iids)}件の別issue_idに重複: {il[:4]}"))

# ============ WRITE anomalies CSV ============
anom_path = os.path.join(OUT, "data_profile_anomalies_v0.1.csv")
acnt = collections.Counter(a[1] for a in anomalies)
with open(anom_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["issue_id", "anomaly_type", "evidence"])
    for a in anomalies:
        w.writerow(a)

# ============ WRITE markdown report ============
def rate(a, b):
    return (a / b) if b else 0.0
n_journals = len(J)
n_issues = len(issues)
joined_total = sum(d["joined"] for d in J.values())
hyo_total = sum(d["hyo"] for d in J.values())
ser_total = sum(d["ser"] for d in J.values())

# per-journal table (top 30 by article count)
rows = []
for j, d in J.items():
    rows.append((j, d["arts"], len(d["issues"]), rate(d["joined"], d["arts"]),
                 rate(d["hyo"], d["arts"]), rate(d["ser"], d["arts"]), feat_by_journal.get(j, 0)))
rows.sort(key=lambda x: -x[1])

md_path = os.path.join(OUT, "data_profile_v0.1.md")
L = []
L.append("# 雑誌オブジェクト 全体統計プロファイル v0.1")
L.append("")
L.append("発注: ORCH-DATA-PROFILE / read-only 集計。下流UX設計と異常検出の baseline。")
L.append("入力(read-only): `article_join_dryrun_v0.1.csv`, `article_series_v0.1.csv`, `issue_feature_v0.1.csv`。")
L.append("")
L.append("## 0. 全体サマリ")
L.append("")
L.append(f"- 総記事数: **{total:,}** / 総号数(distinct issue_id): **{n_issues:,}** / 誌数(journal_canonical): **{n_journals:,}**")
L.append(f"- 接合率(join_status=joined): **{rate(joined_total,total):.4f}** ({joined_total:,}/{total:,})")
L.append(f"- 評釈(判例評釈)記事: **{hyo_total:,}** ({rate(hyo_total,total):.3f})")
L.append(f"- 連載所属記事: **{ser_total:,}** ({rate(ser_total,total):.3f})")
L.append(f"- 特集レコード総数(issue_feature): **{feat_total:,}** / 特集を持つ号: **{len(feat_by_issue):,}**")
L.append(f"- 検出異常(anomalies): **{len(anomalies):,}** 件 (受入基準 ≥100: {'PASS' if len(anomalies)>=100 else 'FAIL'})")
L.append(f"- パース不能行(14列でない): {malformed}")
L.append("")
L.append("## 1. 誌別プロファイル (記事数 上位30誌)")
L.append("")
L.append("| 誌名 | 記事数 | 号数 | 接合率 | 評釈率 | 連載率 | 特集数 |")
L.append("|---|--:|--:|--:|--:|--:|--:|")
for j, arts, iss, jr, hr, sr, ft in rows[:40]:
    L.append(f"| {j} | {arts:,} | {iss:,} | {jr:.3f} | {hr:.3f} | {sr:.3f} | {ft:,} |")
L.append("")
# long-tail distribution
b1000 = sum(1 for r in rows if r[1] >= 1000)
b100  = sum(1 for r in rows if 100 <= r[1] < 1000)
b10   = sum(1 for r in rows if 10 <= r[1] < 100)
b1    = sum(1 for r in rows if r[1] < 10)
top40_arts = sum(r[1] for r in rows[:40])
L.append(f"上表は記事数 上位40誌(全{n_journals}誌中、上位40誌で総記事の {rate(top40_arts,total):.1%} を占める)。")
L.append(f"長い裾の誌数分布: 記事数>=1000の誌 {b1000} / 100-999 {b100} / 10-99 {b10} / <10 {b1}。")
L.append("")
L.append("## 2. 年別 記事数推移")
L.append("")
L.append("| 年 | 記事数 | 号数 |")
L.append("|---|--:|--:|")
for y in sorted(year_arts):
    L.append(f"| {y} | {year_arts[y]:,} | {len(year_issues[y]):,} |")
L.append("")
L.append("## 3. 異常検出サマリ")
L.append("")
L.append("| anomaly_type | 件数 | 説明 |")
L.append("|---|--:|---|")
desc = {
 "tsuukan_gap": "通巻連番の欠落(飛び番号)。両端の号は存在し記事0件の通巻=欠号 or 取りこぼし(run<=5のみ高精度抽出)",
 "tsuukan_duplicate": "同一通巻が複数の別issue_idに出現(二重発行の疑い)",
 "tsuukan_range_overlap": "同一通巻が単独号と合併号(N-M)に二重出現(二重計上)",
 "tsuukan_value_outlier": "通巻欄に年号域(1981-2026)の外れ値=年の混入疑い",
 "volissue_gap": "巻号(vNnM)系列で巻内の号番が欠落",
 "volissue_duplicate": "同一巻号が複数issue_idに重複",
 "isbn_duplicate": "isbn_per_issue誌で同一ISBN/識別子が複数号に重複",
}
for t, c in acnt.most_common():
    L.append(f"| {t} | {c:,} | {desc.get(t,'')} |")
L.append("")
L.append("## 4. 注記・手法")
L.append("")
L.append(f"- tsuukan(通巻)系列誌: {len(tsu_journal_set)}誌 / 巻号(vNnM)系列誌: {len(volissue_journal_set)}誌。")
L.append(f"- isbn_per_issue誌: {len(isbn_journals)}誌(別冊ジュリスト等、識別子=NCID#suffix形式)。ISBN重複group: {isbn_dup_groups}。")
L.append("- 飛び番号は**両端present・run長<=5**の孤立欠落のみ採用(データ未収録の時代帯を誤検出しない高精度設定)。")
L.append("- 評釈判定: タイトル内の(元号+判/決/審/裁決)括弧 もしくは 判例研究|判例評釈|判批 等のキーワード。")
L.append("- 連載: article_series_v0.1.csv に article_id が含まれる記事。特集: issue_feature_v0.1.csv の issue_id 一致。")
L.append("- read-only: 入力CSVのみ参照。canonical/DB/edgeへの書込なし。")
with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")

print("WROTE", md_path)
print("WROTE", anom_path)
print("anomalies total:", len(anomalies))
print("by type:", acnt.most_common())
print("journals:", n_journals, "issues:", n_issues, "articles:", total)
print("hyo_total:", hyo_total, "ser_total:", ser_total, "feat_total:", feat_total)
print("tsu_journals:", len(tsu_journal_set), "volissue_journals:", len(volissue_journal_set), "isbn_journals:", len(isbn_journals))
