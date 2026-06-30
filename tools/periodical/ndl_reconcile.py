#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ORCH-NDL-RECONCILE — authority v14 と NDL最新書誌の整合チェック

目的:
  authority v14 (d1_journal_issn_authority_ALL_resolved_v14.csv) の各誌について、
  NDL Search SRU API から「逐次刊行物の書誌タイトルレコード」(dpid=iss-ndl-opac, type:title)
  を JSON 化して再取得し、刊行状態(継続刊行中/刊行終了)と承継イベント
  (継続前誌/継続後誌/改題/吸収・統合/分割)を検出する。

  改題を見逃すと L4 で誌の同一性が崩れるため、承継チェーンを CSV/JSON で提案する。

入力:
  artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v14.csv
出力:
  artifacts/periodical/journal_lifecycle_v0.1.csv
      (journal_canonical, ndl_status, succession_event, related_ncid)
  artifacts/periodical/journal_lifecycle_summary_v0.1.json
      (active/discontinued/renamed, succession_clusters)

性質: read-only(外部読取のみ)。NDL 公開 SRU API へ GET のみ。Ollama 不使用。DB 書込なし。

NDL SRU 仕様メモ:
  - endpoint: https://ndlsearch.ndl.go.jp/api/sru
  - 雑誌記事索引(type:article, R000000004)が ISSN 検索で大量にヒットするため、
    CQL に `AND dpid="iss-ndl-opac"` を付けて NDL-OPAC の逐次刊行物書誌に限定する。
  - 承継情報は逐次刊行物のタイトルレコード(dcterms:description = "type : title")に格納:
      dcterms:replaces      rdfs:label="継続前 : <誌名> (ISSN:XXXX-XXXX)"
      dcterms:isReplacedBy  rdfs:label="継続後 : <誌名> (ISSN:XXXX-XXXX)"
      dcterms:relation      rdfs:label="改題/吸収/統合/分割 : <誌名> ..."  (巻次共有/関連資料は除外)
      dcndl:publicationStatus  継続刊行中 | 刊行終了
      dcterms:identifier(NIIBibID) = NCID
"""
import csv, json, re, html, sys, time, os, hashlib, urllib.parse, urllib.request

SRU = "https://ndlsearch.ndl.go.jp/api/sru"
UA = "alo-ndl-reconcile/0.1 (read-only authority reconcile; contact owner)"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IN_CSV = os.path.join(ROOT, "artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v14.csv")
OUT_CSV = os.path.join(ROOT, "artifacts/periodical/journal_lifecycle_v0.1.csv")
OUT_JSON = os.path.join(ROOT, "artifacts/periodical/journal_lifecycle_summary_v0.1.json")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ndl_cache")

# 承継(誌の同一性に影響する)イベントのラベル分類
SUCCESSION_KINDS = {
    "継続前": "succeeds_from",   # この誌は前誌を継承(継続前誌)
    "継続後": "succeeded_by",    # この誌は後誌に継承された(継続後誌)
    "改題":   "retitled",
    "吸収":   "absorbed",
    "合併":   "merged",
    "統合":   "merged",
    "分割":   "split",
    "分離":   "split",
}
# 承継ではない関連(誌一覧には残すが succession_event には数えない)
NON_SUCCESSION = ("巻次共有", "関連資料", "別冊", "増刊", "別タイトル")


def sru_fetch(query, n=10, retries=3):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.md5(f"{query}|n={n}".encode("utf-8")).hexdigest()
    cpath = os.path.join(CACHE, key + ".xml")
    if os.path.exists(cpath) and os.path.getsize(cpath) > 0:
        with open(cpath, encoding="utf-8") as f:
            return f.read()
    url = f"{SRU}?operation=searchRetrieve&recordSchema=dcndl&maximumRecords={n}&query=" + urllib.parse.quote(query)
    last = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
            with open(cpath, "w", encoding="utf-8") as f:
                f.write(data)
            time.sleep(0.25)  # politeness
            return data
        except Exception as e:
            last = str(e)
            time.sleep(1.0 + attempt)
    sys.stderr.write(f"[warn] fetch failed: {query} : {last}\n")
    return ""


def records(xml):
    return [html.unescape(r) for r in re.findall(r'<recordData[^>]*>(.*?)</recordData>', xml, re.S)]


def parse_title_record(r):
    """逐次刊行物タイトルレコード1件 -> dict。type:title でなければ None。"""
    if "type : title" not in r:
        return None
    title = re.findall(r'<dcterms:title>([^<]*)</dcterms:title>', r)
    issns = re.findall(r'datatype="http://ndl\.go\.jp/dcndl/terms/ISSN">([^<]*)<', r)
    ncids = re.findall(r'datatype="http://ndl\.go\.jp/dcndl/terms/NIIBibID">([^<]*)<', r)
    status = re.findall(r'<dcndl:publicationStatus>([^<]*)</dcndl:publicationStatus>', r)
    mat = re.findall(r'<dcndl:materialType[^>]*rdfs:label="([^"]*)"', r)
    # (tag, label) ペア。資源URLからISSNも拾う。
    rels = re.findall(r'<dcterms:(replaces|isReplacedBy|relation)\s+rdf:resource="([^"]*)"\s+rdfs:label="([^"]*)"', r)
    return {
        "title": title[0] if title else "",
        "issns": issns,
        "ncids": ncids,
        "status": status[0] if status else "",
        "materialType": mat[0] if mat else "",
        "relations": [{"tag": t, "resource": res, "label": lab} for (t, res, lab) in rels],
    }


def classify_relation(label):
    """ラベル -> (kind, related_title, related_issn)。承継でなければ kind=None。"""
    for word in NON_SUCCESSION:
        if label.startswith(word):
            return (None, None, None)
    kind = None
    for word, k in SUCCESSION_KINDS.items():
        if label.startswith(word) or label.split(" :")[0].strip() == word:
            kind = k
            break
    if kind is None:
        return (None, None, None)
    name = ""
    m = re.match(r'[^:]*:\s*(.+)', label)
    if m:
        name = m.group(1).strip()
    issn = ""
    mi = re.search(r'ISSN:\s*([0-9Xx]{4}-[0-9Xx]{4})', label)
    if mi:
        issn = mi.group(1)
    # 誌名から ISSN 括弧を除去
    name = re.sub(r'\s*\(ISSN:[^)]*\)\s*', '', name).strip()
    name = re.sub(r'\s*/.*$', '', name).strip()  # 責任表示を落とす
    name = html.unescape(name)  # NDL の二重エスケープ(&amp; 等)を解消
    return (kind, name, issn)


def norm(s):
    return re.sub(r'\s+', '', (s or '')).replace('=', '').lower()


def find_serial(journal, issn, ncid):
    """逐次刊行物タイトルレコードを取得。共有ISSN(別冊書籍)等で埋もれる場合は窓を広げる。"""
    if issn:
        q = f'issn="{issn}" AND dpid="iss-ndl-opac"'
    else:
        q = f'title="{journal}" AND dpid="iss-ndl-opac"'
    for n in (50, 200):
        xml = sru_fetch(q, n=n)
        if not xml:
            return None
        rec = pick_record(records(xml), want_issn=issn, want_ncid=ncid, want_title=journal)
        if rec:
            return rec
        # type:title が窓内に1件も無ければ窓を広げて再試行(共有ISSNの別冊書籍対策)
        total = re.findall(r'<numberOfRecords>(\d+)</numberOfRecords>', xml)
        if total and int(total[0]) <= n:
            break  # これ以上レコードは無い
    return None


def pick_record(recs, want_issn=None, want_ncid=None, want_title=None):
    """取得レコード群から対象誌のタイトルレコードを1件選ぶ。"""
    parsed = [p for p in (parse_title_record(r) for r in recs) if p]
    if not parsed:
        return None
    # 1) ISSN 完全一致
    if want_issn:
        for p in parsed:
            if want_issn in p["issns"]:
                return p
    # 2) NCID 完全一致
    if want_ncid:
        for p in parsed:
            if want_ncid in p["ncids"]:
                return p
    # 3) タイトル一致(完全一致 → 前方一致 → 部分一致 の優先順)
    if want_title:
        nt = norm(want_title)
        cands = [(p, norm(p["title"].split('=')[0])) for p in parsed]
        for p, c in cands:
            if c == nt:
                return p
        for p, c in cands:
            if c.startswith(nt) or nt.startswith(c):
                return p
        for p, c in cands:
            if nt in c:
                return p
        # タイトルのみキー(issn/ncid 無し)は曖昧一致を避け、無理に拾わない
        if not want_issn and not want_ncid:
            return None
    # 4) ISSN/NCID 指定でクエリ自体がそのIDで絞り込まれている → 先頭(関連度1位)
    return parsed[0]


def process_journal(task):
    """1誌分の NDL 突合(ネットワーク取得 + 承継抽出)。スレッドから安全に呼べる純関数。
    返り値: dict(journal, status, events, edges, related_ncid, found)。"""
    journal, issn, ncid = task
    rec = find_serial(journal, issn, ncid)
    if not rec:
        return {"journal": journal, "found": False, "status": "not_found",
                "events": [], "edges": [], "related_ncid": ""}
    status = rec["status"] or "unknown"
    self_title = rec["title"].split('=')[0].strip()
    events, edges = [], []
    for r in rec["relations"]:
        kind, rname, rissn = classify_relation(r["label"])
        if kind is None or not rname:
            continue  # 名前なしラベル(bib/issn資源の重複行)は捨てる
        tag = f"{kind}:{rname}" + (f"(ISSN:{rissn})" if rissn else "")
        events.append(tag)
        if kind == "succeeds_from":
            edges.append((rname, self_title))      # 前誌 -> 当誌
        else:
            edges.append((self_title, rname))       # 当誌 -> 後誌/関連
    events = sorted(set(events))
    return {
        "journal": journal, "found": True, "status": status,
        "events": events, "edges": edges,
        "related_ncid": "|".join(sorted(set(rec["ncids"]))) if rec["ncids"] else "",
    }


def main():
    from concurrent.futures import ThreadPoolExecutor, as_completed

    rows = []
    with open(IN_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    # 1) 入力誌のタスク列を作る(行順を保持)
    tasks = []
    for row in rows:
        journal = (row.get("journal_canonical") or "").strip()
        if not journal:
            continue
        ktype = (row.get("key_type") or "").strip()
        kval = (row.get("key_value") or "").strip()
        issn = kval if ktype == "issn" and re.match(r'^[0-9]{4}-[0-9Xx]{4}$', kval) else None
        ncid = kval if ktype == "ncid" and re.match(r'^[A-Z]{2}\d+', kval) else None
        tasks.append((journal, issn, ncid))

    # 2) NDL 取得は並列(API へは GET のみ・キャッシュ済みは再取得しない)。集計は後段で逐次。
    results = [None] * len(tasks)
    done = 0
    with ThreadPoolExecutor(max_workers=int(os.environ.get("NDL_WORKERS", "8"))) as ex:
        futs = {ex.submit(process_journal, t): idx for idx, t in enumerate(tasks)}
        for fut in as_completed(futs):
            idx = futs[fut]
            results[idx] = fut.result()
            done += 1
            if done % 50 == 0:
                sys.stderr.write(f"[progress] {done}/{len(tasks)}\n")

    # 3) 逐次集計(決定的)
    out_rows = []
    n_active = n_discont = n_renamed = n_notfound = 0
    succession_events = 0
    edges = []
    for res in results:
        if not res["found"]:
            out_rows.append([res["journal"], "not_found", "", ""])
            n_notfound += 1
            continue
        status = res["status"]
        events = res["events"]
        edges.extend(res["edges"])
        if events:
            succession_events += 1
            if any(e.startswith(("retitled", "succeeds_from", "succeeded_by")) for e in events):
                n_renamed += 1
        if "継続刊行中" in status or status == "刊行中":
            n_active += 1
        elif "刊行終了" in status or "終了" in status or "廃" in status:
            n_discont += 1
        out_rows.append([res["journal"], status, "; ".join(events), res["related_ncid"]])

    # CSV 出力
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["journal_canonical", "ndl_status", "succession_event", "related_ncid"])
        w.writerows(out_rows)

    # 承継クラスタ(連結成分, size>=2)
    adj = {}
    nodes = set()
    for a, b in edges:
        if not a or not b:
            continue
        a, b = a.strip(), b.strip()
        nodes.add(a); nodes.add(b)
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    seen = set()
    clusters = []
    for node in sorted(nodes):
        if node in seen:
            continue
        stack = [node]; comp = set()
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur); comp.add(cur)
            stack.extend(adj.get(cur, ()))
        if len(comp) >= 2:
            clusters.append(sorted(comp))
    clusters.sort(key=lambda c: (-len(c), c[0]))

    # v0.2: 機関分割クラスタを承継から除外。
    # 大学の親紀要が複数の学部誌に分割されると連結成分で全学部誌が1クラスタに誤併合される
    # (改題承継でなく同一機関の別系統)。同一機関名を>=3 含むクラスタは succession から外す。
    _INST = re.compile(r"(.{2,12}?(?:大学|大學|学院))")
    def _institution_of(name):
        m = _INST.search(name)
        return m.group(1) if m else None
    def _is_institutional_grouping(cluster):
        ins = [i for i in (_institution_of(x) for x in cluster) if i]
        if not ins:
            return False
        from collections import Counter as _C
        return _C(ins).most_common(1)[0][1] >= 3
    institutional_clusters = [c for c in clusters if _is_institutional_grouping(c)]
    clusters = [c for c in clusters if not _is_institutional_grouping(c)]

    summary = {
        "source": "NDL Search SRU (dpid=iss-ndl-opac, recordSchema=dcndl)",
        "input": "d1_journal_issn_authority_ALL_resolved_v14.csv",
        "generated_by": "tools/periodical/ndl_reconcile.py",
        "read_only": True,
        "journals_total": len([r for r in rows if (r.get('journal_canonical') or '').strip()]),
        "matched_ndl_serial": sum(1 for r in out_rows if r[1] != "not_found"),
        "not_found": n_notfound,
        "active": n_active,
        "discontinued": n_discont,
        "renamed": n_renamed,
        "succession_events_detected": succession_events,
        "succession_clusters_count": len(clusters),
        "succession_clusters": clusters,
        "excluded_institutional_clusters_count": len(institutional_clusters),
        "excluded_institutional_clusters": institutional_clusters,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    sys.stderr.write(
        f"[done] journals={summary['journals_total']} matched={summary['matched_ndl_serial']} "
        f"active={n_active} discontinued={n_discont} renamed={n_renamed} "
        f"succession_events={succession_events} clusters={len(clusters)}\n")


if __name__ == "__main__":
    main()
