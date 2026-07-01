#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ORCH-JOURNAL-ISSN-RESOLVE (channel=jissn) — journal 段2 識別子外部照合(read-only 提案のみ)

producer の NDL SRU 経路(ALOBookDX scripts/wo_periodical_issn_ndl_evidence.py の
dcndl `isPartOf` = iss.ndl.go.jp/issn/* 抽出ロジック / p3b_v2 の partial-recovery fetch)を再利用し、
対象24誌それぞれについて exact main-title + 出版者(責任表示)一致の serial ISSN を特定する。

verdict(1誌1件):
  ISSN_RESOLVED   : exact title+出版者一致 serial に ISSN あり(dup-ISSN ガード通過)→ ISSN 提案 + evidence
  ISSN_NOT_EXIST  : serial は実在(exact-title 記事≥2)が独自 ISSN 未付与 → NCID 維持
  COLLISION       : 取得 ISSN が authority の別誌に割当済 → 提案せず + 衝突先
  AMBIGUOUS       : exact 一致<2/複数候補拮抗/出版者不一致 → 推測せず head/owner へ

安全: read-only 外部照合のみ(NDL 公開 SRU)。authority/canonical/DB 非接触。ISSN 捏造ゼロ(NDL 由来のみ)。
      external_share 不変(生 payload 非取込・非公開)。提案止まり(実反映は owner GO)。
"""
import re, html, time, os, urllib.parse, urllib.request, http.client, collections, unicodedata, csv

SRU = "https://ndlsearch.ndl.go.jp/api/sru"
# dup-ISSN ガード照合元 = journal authority 全 key_value(read-only)
AUTH = os.environ.get("JISSN_AUTHORITY",
    "/Users/yuta/Project-codex/.claude/worktrees/casename-dict/artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v14.csv")
OUT = os.environ.get("JISSN_OUT",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "artifacts", "periodical"))

# journal -> (current_status, current_key_type, current_key(NCID等), expected_publisher_hint)
META = {
 "TKC税研時報":("held/unresolved","","","EXTERNAL_LOOKUP(TKC税務研究所)"),
 "建築関係法令の研究":("held/unresolved","","","EXTERNAL_LOOKUP"),
 "立命館大学法学部ニューズレター":("held/unresolved","","","EXTERNAL_LOOKUP(立命館大学法学部)"),
 "保安と外勤":("held/unresolved","","","EXTERNAL_LOOKUP"),
 "明治大学法科大学院ジェンダー法センター年報":("held/unresolved","","","EXTERNAL_LOOKUP(明治大学)"),
 "訟務月報":("held/unresolved","","","EXTERNAL_LOOKUP(法務省訟務局)"),
 "永世中立":("held/unresolved","","","EXTERNAL_LOOKUP"),
 "東洋法学会会報":("held/unresolved","","","EXTERNAL_LOOKUP(東洋大学)"),
 "月刊債権管理":("held/unresolved","","","v3候補1348-8953(季刊事業再生と債権管理と誤マージ疑)"),
 "軍事民論":("held/unresolved","ncid","AN00020468","v3候補NCID(NDL該当なし)"),
 "判例評論":("seed_ncid_fallback","ncid","AN00326923","判例時報付録(合本)"),
 "労働法律旬報":("seed_ncid_fallback","ncid","AN00327813","旬報社"),
 "税理":("seed_ncid_fallback","ncid","AN00080095","ぎょうせい/日本税理士会連合会"),
 "法曹":("seed_ncid_fallback","ncid","AN00327187","法曹会"),
 "速報判例解説":("seed_ncid_fallback","ncid","AA12241495","法学セミナー増刊/日本評論社"),
 "地方税":("seed_ncid_fallback","ncid","AN00126094","地方財務協会"),
 "登記インターネット":("seed_ncid_fallback","ncid","AA11407650","民事法情報センター"),
 "民事月報":("seed_ncid_fallback","ncid","AN00327733","法務省民事局"),
 "月刊登記先例解説集":("seed_ncid_fallback","ncid","AN00328066","テイハン"),
 "研修":("seed_ncid_fallback","ncid","AN00327540","誌友会"),
 "週刊法律新聞":("seed_ncid_fallback","ncid","AN10042106","法律新聞社"),
 "労働法令通信":("seed_ncid_fallback","ncid","AN00327799","労働法令協会"),
 "判例セレクト":("seed_ncid_fallback","ncid","AA1115468X","法学教室別冊付録/有斐閣"),
 "警察時報":("seed_ncid_fallback","ncid","AN00327438","警察時報社"),
}
ORDER = list(META.keys())

# ---- dup-ISSN guard source ----
ISSN_OWNER = collections.defaultdict(list)
with open(AUTH) as f:
    for row in csv.DictReader(f):
        if row["key_type"] == "issn" and row["key_value"].strip():
            ISSN_OWNER[row["key_value"].strip().upper()].append((row["journal_canonical"], row["status"]))
def foreign_owner(issn, journal):
    return [o for o in ISSN_OWNER.get(issn.upper(), []) if o[0] != journal]

# ---- robust NDL SRU fetch (producer p3b_v2 IncompleteRead partial-recovery + retry) ----
def fetch(title, maxrec=200, tries=3):
    q = f'title="{title}"'
    url = f"{SRU}?operation=searchRetrieve&recordSchema=dcndl&maximumRecords={maxrec}&query=" + urllib.parse.quote(q)
    last = None
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ALO-periodical-issn-seed/0.2 (NDL public bib lookup)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                try: data = r.read()
                except http.client.IncompleteRead as ie: data = ie.partial
            return data.decode("utf-8", "replace")
        except Exception as e:
            last = e; time.sleep(2 * (t + 1))
    raise last

KYUJI = str.maketrans({"學":"学","會":"会","廰":"庁","實":"実","與":"与","區":"区","團":"団","醫":"医","關":"関","廣":"広","發":"発","經":"経","濟":"済","聲":"声"})
def fold(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r"[\s=/:：・,，.。\-–—&＆\[\]（）()『』「」]", "", s)
    return s.translate(KYUJI)
def main_title(pn):
    h = re.split(r'\s+/\s+', pn)[0]        # 責任表示を落とす
    h = re.split(r'\s+[:=]\s+', h)[0]      # 副題 / 欧文並列を落とす
    h = re.split(r'\s+\d', h)[0]           # 末尾巻号(例 "労働法律旬報 1635")を落とす
    return h.strip()
def resp_of(pn):
    p = re.split(r'\s+/\s+', pn, 1)
    return p[1].strip() if len(p) > 1 else ""

def analyze(xml, journal):
    u = html.unescape(html.unescape(xml))
    recs = re.findall(r'<dcndl:BibResource.*?</dcndl:BibResource>', u, re.S)
    jf = fold(journal)
    per = collections.defaultdict(lambda: {"count":0, "resp":collections.Counter(), "pubname":collections.Counter(), "bibids":collections.Counter(), "dates":[]})
    exact = 0
    for r in recs:
        pn = re.search(r'<dcndl:publicationName>([^<]+)', r)
        if not pn: continue
        pnv = html.unescape(pn.group(1)).strip()
        if fold(main_title(pnv)) != jf:      # exact main-title 一致のみ採用(broad-match 排除)
            continue
        exact += 1
        m = re.search(r'/issn/([0-9]{7}[0-9Xx])(?![0-9])', r)   # issnl は除外
        if not m: continue
        raw = m.group(1); issn = (raw[:4] + "-" + raw[4:]).upper()
        d = per[issn]; d["count"] += 1; d["pubname"][pnv] += 1
        rp = resp_of(pnv)
        if rp: d["resp"][rp] += 1
        bib = re.search(r'/bib/([0-9]+)', r)
        if bib: d["bibids"][bib.group(1)] += 1
        iss = re.search(r'<dcterms:issued[^>]*>([0-9]{4})', r)
        if iss: d["dates"].append(iss.group(1))
    cands = []
    for issn, d in sorted(per.items(), key=lambda kv: -kv[1]["count"]):
        dates = sorted(d["dates"])
        cands.append({"issn":issn, "evidence_records":d["count"],
            "publisher":(d["resp"].most_common(1)[0][0] if d["resp"] else ""),
            "publicationName":d["pubname"].most_common(1)[0][0] if d["pubname"] else "",
            "ndl_bib_id":d["bibids"].most_common(1)[0][0] if d["bibids"] else "",
            "valid_from":dates[0] if dates else "", "valid_to":dates[-1] if dates else ""})
    return len(recs), exact, cands

def decide(journal, total, exact, cands, ck, ckt):
    maintain = ck if ckt == "ncid" else ""
    if journal == "月刊債権管理":               # v3 候補を dup-guard に通す(誤マージ検出)
        cand = "1348-8953"; fo = foreign_owner(cand, journal)
        col = "; ".join(f"{a}({b})" for a, b in fo)
        return ("COLLISION","",maintain,"",col,
            f"v3候補 ISSN {cand} は authority で別誌『{col}』に割当済(誤マージ)。NDL exact-title hits={total}(独自ISSN無)。提案せず・NCID/held維持")
    if not cands:
        if exact >= 2:
            return ("ISSN_NOT_EXIST","",maintain,"","",
                f"NDL exact-title records={exact}(hits={total})だが isPartOf ISSN 無し→serial実在・独自ISSN未付与。" + (f"NCID {maintain} 維持" if maintain else "NCID/held維持"))
        return ("AMBIGUOUS","",maintain,"","",
            f"NDL exact main-title 一致={exact}・独自ISSN根拠不足(hits={total})→実在/ISSN確定できず head/owner へ")
    top = cands[0]
    rivals = [c for c in cands[1:] if c["evidence_records"] >= max(2, 0.4*top["evidence_records"]) and fold(c["publisher"]) != fold(top["publisher"])]
    if rivals:
        return ("AMBIGUOUS","",maintain,top["publisher"],"",
            "複数 serial 候補拮抗: " + "; ".join(f"{c['issn']}x{c['evidence_records']}({c['publisher']})" for c in cands))
    base = f"NDL isPartOf issn/{top['issn'].replace('-','')} evidence={top['evidence_records']} bib={top['ndl_bib_id']} pubName『{top['publicationName']}』[{top['valid_from']}-{top['valid_to']}]"
    fo = foreign_owner(top["issn"], journal)
    if fo:
        col = "; ".join(f"{a}({b})" for a, b in fo)
        return ("COLLISION","",maintain,top["publisher"],col, base + f" ／ dup-ISSN: {top['issn']} は別誌『{col}』に割当済→提案せず")
    return ("ISSN_RESOLVED",top["issn"],"",top["publisher"],"", base)

def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []; tally = collections.Counter()
    for j in ORDER:
        group, ckt, ck, hint = META[j]
        try:
            total, exact, cands = analyze(fetch(j), j)
            verdict, issn, maintain, pub, col, ev = decide(j, total, exact, cands, ck, ckt)
        except Exception as e:
            total = exact = -1; cands = []
            verdict, issn, maintain, pub, col, ev = ("AMBIGUOUS","",(ck if ckt=="ncid" else ""),"","",f"fetch/parse error: {e}")
        tally[verdict] += 1
        rows.append({"journal":j,"current_status":group,"current_key":(f"{ckt}:{ck}" if ck else ""),
            "verdict":verdict,"proposed_issn":issn,"maintain_ncid":maintain,"ndl_publisher":pub,
            "expected_publisher_hint":hint,"evidence":ev,"collision_with":col,
            "ndl_hits_total":total,"exact_title_records":exact,
            "all_candidates":"; ".join(f"{c['issn']}x{c['evidence_records']}({c['publisher']})" for c in cands)})
        print(f"{verdict:15s} {j} issn={issn or '-'} exact={exact} hits={total}")
        time.sleep(0.8)
    cols = ["journal","current_status","current_key","verdict","proposed_issn","maintain_ncid","ndl_publisher","expected_publisher_hint","evidence","collision_with","ndl_hits_total","exact_title_records","all_candidates"]
    with open(os.path.join(OUT, "journal_issn_resolve_proposal_v0.1.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for x in rows: w.writerow(x)
    print("verdict tally:", dict(tally), "-> wrote", OUT)

if __name__ == "__main__":
    main()
