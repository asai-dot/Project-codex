#!/usr/bin/env python3
"""
DD-FORMOBJ L3 PoC reasoner: 機械可読L3書式を読み、コーパス横断で「議論」する素振り。
目的: L3(条項機能＋意味型slot＋属性)があれば、人手OCR再現ではなく
      「機械が大量書式の構造を保持して横断比較・質問応答」できることを実証する。
"""
import json, glob, sys, os
from collections import defaultdict, Counter

def load(d):
    return [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(os.path.join(d, "*.L3.json")))]

def q_function_matrix(forms):
    funcs = sorted({c["function"] for f in forms for c in f["clauses"]})
    print("【Q1】機能カバレッジ行列 (form × function)")
    print("function".ljust(26), *[f"F{i+1}" for i in range(len(forms))])
    for fn in funcs:
        row = ["●" if any(c["function"]==fn for c in f["clauses"]) else "·" for f in forms]
        print(fn.ljust(26), *[f" {x}" for x in row])
    print("  " + " / ".join(f"F{i+1}={f['form_title'][:20]}" for i,f in enumerate(forms)))

def q_compare(forms, function):
    print(f"\n【Q2】同機能の横断比較: function='{function}'")
    rowsets=[]
    for f in forms:
        for c in f["clauses"]:
            if c["function"]==function:
                rowsets.append((f["form_title"][:18], c.get("attributes",{})))
    keys=[]
    for _,a in rowsets:
        for k in a:
            if k not in keys: keys.append(k)
    print("属性".ljust(20), *[t.ljust(22) for t,_ in rowsets])
    for k in keys:
        print(str(k).ljust(20), *[str(a.get(k,"—")).ljust(22) for _,a in rowsets])

def q_obligations(forms):
    print("\n【Q3】義務一覧 (obligor別・コーパス横断)")
    by=defaultdict(list)
    for f in forms:
        for c in f["clauses"]:
            for o in c.get("obligations",[]):
                by[o["obligor"]].append(f"{o['act']}  〈{f['form_title'][:12]}/{c['no']}〉")
    for ob in sorted(by):
        print(f" ◆{ob} ({len(by[ob])})")
        for a in by[ob]: print("   -", a)

def q_slot_types(forms):
    print("\n【Q4】意味型slotの分布 (型別)")
    c=Counter(s["type"] for f in forms for cl in f["clauses"] for s in cl.get("slots",[]))
    for t,n in c.most_common(): print(f"  {t.ljust(24)} {n}")

def q_missing(forms, function):
    print(f"\n【Q5】機能 '{function}' を(捕捉範囲で)欠く書式 = ギャップ検出")
    for f in forms:
        has=any(c["function"]==function for c in f["clauses"])
        if not has: print("  ⚠", f["form_title"])

def q_archetypes(forms):
    print("【Q0】コーパス概要 (archetype別)")
    by=defaultdict(list)
    for f in forms: by[f.get("archetype","?")].append(f)
    for a in sorted(by):
        print(f"  {a} ({len(by[a])})")
        for f in by[a]:
            ex=f.get("extraction",{})
            print(f"     - {f['form_title'][:34]}  [{f.get('form_kind','?')}] "
                  f"auto_conf={ex.get('confidence','-')}")

def q_extraction_quality(forms):
    print("\n【Q6】自動抽出(vision→L3)の自己申告 confidence と曖昧点")
    for f in forms:
        ex=f.get("extraction")
        if ex:
            print(f"  {f['form_title'][:30]}: conf={ex.get('confidence')} / {ex.get('ambiguity','')[:48]}")

if __name__=="__main__":
    d=sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(__file__),"..","docs/tmplstruct/poc_L3")
    forms=load(d)
    print(f"=== L3 corpus: {len(forms)} forms / {sum(len(f['clauses']) for f in forms)} clauses ===\n")
    q_archetypes(forms)
    print()
    q_function_matrix(forms)
    q_compare(forms,"payment")
    q_obligations(forms)
    q_slot_types(forms)
    q_extraction_quality(forms)
    q_missing(forms,"damages")
