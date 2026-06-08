#!/usr/bin/env python3
"""
select_template_sample.py — 法律書式テンプレ corpus から「解剖用 30 件」を決定論的に層化サンプリングする。

目的（GPT お目付け監査 DESIGN_MODIFY_REQUIRED の立て直し）:
  書式テンプレを文献として outline 化するのをやめ、type 別 structure_profile を
  「実物 .docx を逆算」して起こす。月30件の .docx ダウンロード枠は希少なので、
  ランダムでなく **設計判断が分かれる類型に層化** して 30 件を選ぶ。

このスクリプトは DB も外部も触らない（read-only）。templates.json を読んで
  - 各書式を keyword ルールで stratum(類型) に振り分け、
  - stratum 別 quota に従い、stratum 内では title 多様性を最大化して決定論的に選び、
  - 選んだ 30 件の manifest(JSON + 人間可読 MD) を出力する。
ダウンロード自体は worker 側の既存 .docx 取得経路が manifest の source_url を使って行う。

field 名は corpus により異なるので load_legallib.py と同じ inspect→bind 方式。
未解決 key があれば *_KEYS の先頭に実キー名を足す（最小差分）。
"""
from __future__ import annotations
import argparse, json, os, re, sys
from collections import defaultdict, OrderedDict

# --- field binding (corpus 実キーが違えば先頭に追記) ---
ID_KEYS       = ("id", "template_id", "book_id", "doc_id", "stem")
TITLE_KEYS    = ("title", "name", "form_title", "書式名", "タイトル")
FORMTYPE_KEYS = ("formType", "form_type", "type", "category", "書式種別")
OUTLINE_KEYS  = ("outline", "headings", "toc", "structure")
URL_KEYS      = ("source_url", "sourceUrl", "url", "docx_url", "download_url")

# --- stratum quota（合計 30）: 設計判断が分かれる所に厚く配分 ---
QUOTA = OrderedDict([
    ("contract",     8),   # 「契約だけ条項見出し」を検証。サブ型を散らす
    ("other",        8),   # その他45%の闇を割る → formType入口改善に直結
    ("court_filing", 5),   # slot抽出の妥当性（訴状/答弁/督促/保全/執行）
    ("notice",       4),   # slot（催告/解除/内容証明/債権譲渡通知）
    ("registry",     4),   # slot（商業/不動産登記・各種届出）
    ("notarial",     1),   # 契約とslotの中間（公正証書/合意/和解/示談）
])
# 余りを回す順（quota 充足できない stratum の不足分の振替先）
SPILL_ORDER = ["other", "contract", "court_filing", "notice", "registry"]

# stratum 判定（title / formType を見る。上から順に最初に当たったもの）
STRATUM_RULES = [
    ("court_filing", r"申立|訴状|答弁|準備書面|支払督促|保全|仮処分|仮差押|強制執行|執行|上申|意見書|陳述"),
    ("registry",     r"登記|登録|届出|届け?出|申請書|嘱託|抹消|設定"),
    ("notarial",     r"公正証書|和解|示談|合意書|覚書|協議書"),
    ("notice",       r"通知|催告|内容証明|督促|請求書|照会|回答|解除|解約|債権譲渡"),
    ("contract",     r"契約|約款|規約|誓約|念書|委任状|同意書|承諾書"),
]

def pick(d, keys):
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] not in (None, "", [], {}):
            return d[k]
    return None

def load_catalog(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        # {id: {...}} か {"templates":[...]} の両対応
        if "templates" in data and isinstance(data["templates"], list):
            return data["templates"]
        return [{"id": k, **(v if isinstance(v, dict) else {"value": v})} for k, v in data.items()]
    if isinstance(data, list):
        return data
    raise SystemExit(f"unexpected catalog shape: {type(data)}")

def classify(rec):
    hay = " ".join(str(pick(rec, TITLE_KEYS) or "") for _ in (0,)) + " " + str(pick(rec, FORMTYPE_KEYS) or "")
    ft = str(pick(rec, FORMTYPE_KEYS) or "")
    for stratum, pat in STRATUM_RULES:
        if re.search(pat, hay):
            return stratum
    # 明示的「その他」/ 未分類 → other
    return "other"

def outline_weak(rec):
    o = pick(rec, OUTLINE_KEYS)
    if o is None: return True
    if isinstance(o, (list, dict)): return len(o) <= 1
    return len(str(o).strip()) == 0

def diversity_key(title):
    t = re.sub(r"[\s　]+", "", str(title or ""))
    # 先頭の意味トークン（最初の区切りまで）で粗くグループ化
    m = re.match(r"^[（(【\[]?([^（()\[\]【】・\-—:：/／]{2,8})", t)
    return m.group(1) if m else (t[:4] or "_")

def choose(cands, n):
    """stratum 内で title 多様性を最大化して決定論的に n 件。
    title グループでバケット化 → id 昇順 → バケット round-robin。"""
    buckets = defaultdict(list)
    for r in cands:
        buckets[diversity_key(pick(r, TITLE_KEYS))].append(r)
    for k in buckets:
        buckets[k].sort(key=lambda r: str(pick(r, ID_KEYS)))
    order = sorted(buckets.keys())
    out, i = [], 0
    while len(out) < n and any(buckets[k] for k in order):
        k = order[i % len(order)]
        if buckets[k]:
            out.append(buckets[k].pop(0))
        i += 1
        if i > 100000: break
    return out[:n]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=os.path.expanduser("~/alo-ai/work/legallib_dl/templates.json"),
                    help="templates.json（app/data/templates.json でも可）")
    ap.add_argument("--out", default="docs/tmplstruct/SAMPLE30_manifest")
    ap.add_argument("--inspect", action="store_true", help="検出フィールドと stratum 分布だけ出して終了")
    args = ap.parse_args()

    recs = load_catalog(args.catalog)
    if args.inspect:
        sample = recs[0] if recs else {}
        print("total records:", len(recs))
        print("top-level keys (1件目):", sorted(sample.keys()) if isinstance(sample, dict) else type(sample))
        print("bound -> id:%r title:%r formType:%r url:%r" % (
            pick(sample, ID_KEYS), pick(sample, TITLE_KEYS), pick(sample, FORMTYPE_KEYS), pick(sample, URL_KEYS)))
        dist = defaultdict(int)
        for r in recs: dist[classify(r)] += 1
        print("stratum distribution:", dict(dist))
        miss = [k for k, v in (("id",ID_KEYS),("title",TITLE_KEYS),("url",URL_KEYS)) if pick(sample, v) is None]
        if miss: print("!! unresolved fields (add real key to *_KEYS head):", miss)
        return

    by_stratum = defaultdict(list)
    for r in recs:
        by_stratum[classify(r)].append(r)
    # other は「その他/未分類」をテストしたいので formType=その他 を優先、無ければ全 other
    other_pref = [r for r in by_stratum["other"] if str(pick(r, FORMTYPE_KEYS) or "") in ("その他", "", "None")]
    if other_pref:
        by_stratum["other"] = other_pref + [r for r in by_stratum["other"] if r not in other_pref]
    # 非 contract 系は outline が弱い実物を優先（slot 仮説をハードケースで検証）
    for s in ("court_filing", "notice", "registry", "notarial"):
        by_stratum[s].sort(key=lambda r: (not outline_weak(r), str(pick(r, ID_KEYS))))

    chosen, picked_ids = OrderedDict(), set()
    shortfall = 0
    for stratum, q in QUOTA.items():
        got = choose([r for r in by_stratum[stratum] if str(pick(r, ID_KEYS)) not in picked_ids], q)
        chosen[stratum] = got
        for r in got: picked_ids.add(str(pick(r, ID_KEYS)))
        shortfall += q - len(got)
    # 不足分を spill 先から補充（合計を 30 に保つ）
    for stratum in SPILL_ORDER:
        if shortfall <= 0: break
        extra = choose([r for r in by_stratum[stratum] if str(pick(r, ID_KEYS)) not in picked_ids], shortfall)
        chosen.setdefault(stratum, []).extend(extra)
        for r in extra: picked_ids.add(str(pick(r, ID_KEYS)))
        shortfall -= len(extra)

    manifest = {"policy": "stratified-30 for structure_profile reverse-engineering",
                "quota": QUOTA, "total_selected": len(picked_ids), "budget_docx": 30, "items": []}
    for stratum, recs2 in chosen.items():
        for r in recs2:
            manifest["items"].append({
                "stratum": stratum,
                "id": pick(r, ID_KEYS),
                "title": pick(r, TITLE_KEYS),
                "formType_current": pick(r, FORMTYPE_KEYS),
                "outline_weak": outline_weak(r),
                "source_url": pick(r, URL_KEYS),
            })

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out + ".json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    lines = [f"# SAMPLE30 manifest — total {manifest['total_selected']} (budget docx=30)", ""]
    for stratum in QUOTA:
        items = [it for it in manifest["items"] if it["stratum"] == stratum]
        lines.append(f"## {stratum} ({len(items)})")
        for it in items:
            lines.append(f"- [{it['id']}] {it['title']}  (formType={it['formType_current']}, outline_weak={it['outline_weak']})")
        lines.append("")
    with open(args.out + ".md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"selected {manifest['total_selected']} -> {args.out}.json / .md")
    if manifest["total_selected"] != 30:
        print(f"!! WARNING: selected {manifest['total_selected']} != 30 (corpus 不足?). 監査ログに記録のこと。", file=sys.stderr)

if __name__ == "__main__":
    main()
