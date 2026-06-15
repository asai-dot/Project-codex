#!/usr/bin/env python3
"""
check_mandatory_requisites: 書式の法定記載事項チェック(DD-FORMOBJ-002 v0.2 の payoff)。
form_object.v0.2-poc を読み、ドラフトに存在する term 集合と突き合わせて、
法定欠落を defect_kind(重大度) 別に警告する。一律「瑕疵」にしない(監査必須#4)。

設計のみ・DB書込みなし。実案件データは扱わない(filled_instance分離・監査必須#5)。
  python3 tools/check_mandatory_requisites.py [formobj.json] [--present term1,term2,...]
  python3 tools/check_mandatory_requisites.py --selftest
"""
import json, os, sys

HERE = os.path.dirname(__file__)
DEFAULT = os.path.join(HERE, "..", "docs/tmplstruct/poc_e2e/teikan_mandatory.formobj.json")

# defect_kind の重大度順(高→低)
SEVERITY = ["invalidity", "rejection_by_forum", "registration_defect", "evidentiary_weakness", "risk_warning"]
MANDATORY_CLASSES = {"statute_required", "regulation_or_rule_required", "forum_required",
                     "validity_required", "enforceability_required"}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def check(fo, present_terms):
    present = set(present_terms)
    findings = []
    for r in fo.get("requisites", []):
        if r["term"] not in present:
            findings.append({
                "term": r["term"], "label": r.get("label_ja", r["term"]),
                "class": r["requisite_class"],
                "defect": r.get("defect_kind_if_missing", "risk_warning"),
                "law": (r.get("grounded_in") or {}).get("law"),
                "note": r.get("defect_note", ""),
            })
    # 重大度順にソート
    findings.sort(key=lambda f: SEVERITY.index(f["defect"]) if f["defect"] in SEVERITY else 99)
    return findings


def render(fo, present_terms):
    o = fo["form_object"]
    out = [f"# 記載事項レビュー: {o['document_role']} ({o['practice_domain']})",
           f"_recorded_act_: {o['recorded_act']} / _forum_: {o['forum']}", ""]
    findings = check(fo, present_terms)
    mand_total = sum(1 for r in fo["requisites"] if r["requisite_class"] in MANDATORY_CLASSES)
    out.append(f"法定記載事項 {mand_total}件中、ドラフト欠落 {len(findings)}件:")
    out.append("")
    if not findings:
        out.append("  ✓ 法定記載事項はすべて充足。")
    for f in findings:
        mark = {"invalidity": "🛑 無効", "rejection_by_forum": "⛔ 受理拒否",
                "registration_defect": "⚠ 登記不可", "evidentiary_weakness": "△ 立証弱",
                "risk_warning": "・ 注意"}.get(f["defect"], f["defect"])
        out.append(f"  {mark}  **{f['label']}**（{f['class']} / 根拠={f['law']}）")
        if f["note"]:
            out.append(f"       {f['note']}")
    out.append("")
    out.append("## 任意・設計事項（欠けても無効でないが検討推奨）")
    for a in fo.get("advisable_examples", []):
        fav = f" / 有利={a['favors_role']}" if a.get("favors_role") else ""
        out.append(f"  - {a['label_ja']}（{a['requisite_class']}{fav}）")
    return "\n".join(out)


def selftest():
    fo = load(DEFAULT)
    ok = [0, 0]

    def chk(n, c):
        ok[1] += 1
        ok[0] += bool(c)
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")

    # 全充足 → 欠落0
    all_terms = [r["term"] for r in fo["requisites"]]
    chk("all present -> 0 findings", len(check(fo, all_terms)) == 0)
    # 商号 と 発行可能株式総数 を欠く
    miss = [t for t in all_terms if t not in ("trade_name", "issuable_shares_total")]
    f = check(fo, miss)
    chk("missing 2 -> 2 findings", len(f) == 2)
    # 商号欠落 = invalidity が最上位
    chk("trade_name -> invalidity first", f[0]["term"] == "trade_name" and f[0]["defect"] == "invalidity")
    # 発行可能株式総数 = registration_defect
    chk("issuable_shares -> registration_defect",
        any(x["term"] == "issuable_shares_total" and x["defect"] == "registration_defect" for x in f))
    # 重大度順(invalidity が registration_defect より先)
    chk("severity ordered", SEVERITY.index(f[0]["defect"]) <= SEVERITY.index(f[-1]["defect"]))
    # 全 requisite に grounded_in がある(法令接地・gate_mandatory_grounded)
    chk("all requisites grounded", all((r.get("grounded_in") or {}).get("law") for r in fo["requisites"]))
    print(f"self-test: {ok[0]}/{ok[1]} passed")
    return ok[0] == ok[1]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(0 if selftest() else 1)
    path = DEFAULT
    present = []
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--present":
            present = args[i + 1].split(",")
            i += 2
        else:
            path = args[i]
            i += 1
    fo = load(path)
    # 引数なしのデモ: 商号 と 発行可能株式総数 を欠いたドラフトを想定
    if not present:
        present = [r["term"] for r in fo["requisites"] if r["term"] not in ("trade_name", "issuable_shares_total")]
        print("（デモ: 商号・発行可能株式総数を欠いたドラフトを想定）\n")
    print(render(fo, present))
