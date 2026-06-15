#!/usr/bin/env python3
"""
shared_term_registry バリデータ (R0 registry shell v0.1)

監査(DDFORMOBJ/DDTMPLINTEG PASS_WITH_NOTES)で確定したゲートを強制する。
DDL/DB書込みは行わない(設計のみ・HOLD)。JSONL台帳を読み、構造とゲートを検査する。

ゲート:
  STRUCT     スキーマ必須項目/enum/term_id命名(snake_case)
  G_UNIQUE   term_id の一意性
  G_NO_FORK  narrower_terms は registry 内の既存 term_id のみ (gate_no_vocab_fork)
  G_L4_KEY   linked_l4 を持つなら linked_l2(=term識別性) が必須 (gate_l4_keyed_by_l2)
  G_SINGLE   独立源1 (n_independent<=1) で l4_status=accepted は不可 (単一書籍はcandidate止まり / R4)
  G_L4_ACC   l4_status=accepted には n_independent>=2 + source_independence_checked
             + 参照先L2が candidate以上 + label_cohesion_reviewed (or owner_override) (N5/G_l4_accepted_requires_l2_candidate)
  G_L2_ACC   l2_status=accepted には authoritative_anchor + label_cohesion_reviewed (or owner_override) (SEED監査FF-1/FF-2)
  G_TERM_ACC term.status=accepted には owner_ratified=true (or owner_override)
  G_NARROW   narrower_terms と self の循環/自己参照禁止

使い方:
  python3 tools/validate_shared_term_registry.py            # self-test + seed検査
  python3 tools/validate_shared_term_registry.py <path.jsonl>
"""
import json, sys, os, re

STATUSES = {"seed", "candidate", "accepted", "deprecated"}
DOMAINS = {"civil_obligation", "civil_contract", "corporate", "labor",
           "procedural", "cross_practice", "general", "boilerplate"}
AUTHORITY = {"authoritative_anchor", "weak_observation_anchor", "non_anchor"}
TERM_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _struct_errors(r):
    """スキーマ最小検査。返り値: エラー文字列のリスト。"""
    e = []
    for k in ("term_id", "pref_label", "status", "domain", "source_basis", "version", "linked_l2", "linked_l4"):
        if k not in r:
            e.append(f"missing required field: {k}")
    if "term_id" in r and not TERM_RE.match(str(r["term_id"])):
        e.append(f"term_id not snake_case: {r.get('term_id')!r}")
    if r.get("status") not in STATUSES:
        e.append(f"bad status: {r.get('status')}")
    if r.get("domain") not in DOMAINS:
        e.append(f"bad domain: {r.get('domain')}")
    l2 = r.get("linked_l2") or {}
    if l2.get("l2_status") not in STATUSES:
        e.append(f"bad linked_l2.l2_status: {l2.get('l2_status')}")
    a = l2.get("anchor") or {}
    if a.get("authority_class") not in AUTHORITY:
        e.append(f"bad anchor.authority_class: {a.get('authority_class')}")
    for b in ("anchored", "label_cohesion_reviewed"):
        if not isinstance(a.get(b), bool):
            e.append(f"anchor.{b} must be bool")
    l4 = r.get("linked_l4") or {}
    if l4.get("l4_status") not in STATUSES:
        e.append(f"bad linked_l4.l4_status: {l4.get('l4_status')}")
    for k in ("design_knowledge_count", "n_independent"):
        if not isinstance(l4.get(k), int):
            e.append(f"linked_l4.{k} must be int")
    if not isinstance(l4.get("source_independence_checked"), bool):
        e.append("linked_l4.source_independence_checked must be bool")
    return e


def validate(records):
    """records: list[dict]. 返り値: list[(term_id, gate, msg)] の違反。"""
    v = []
    ids = [r.get("term_id") for r in records]
    seen = set()
    for r in records:
        tid = r.get("term_id", "<?>")
        for msg in _struct_errors(r):
            v.append((tid, "STRUCT", msg))
        # G_UNIQUE
        if tid in seen:
            v.append((tid, "G_UNIQUE", "duplicate term_id"))
        seen.add(tid)

        l2 = r.get("linked_l2") or {}
        l4 = r.get("linked_l4") or {}
        a = l2.get("anchor") or {}
        override = bool(r.get("owner_override"))

        # G_NO_FORK + G_NARROW
        for nt in l4.get("narrower_terms", []):
            if nt == tid:
                v.append((tid, "G_NARROW", f"narrower_terms self-reference: {nt}"))
            if nt not in ids:
                v.append((tid, "G_NO_FORK", f"narrower term not in registry (vocab fork): {nt}"))

        # G_L4_KEY: L4 実体(ref or count>0)を持つなら L2 識別性必須
        has_l4 = bool(l4.get("design_knowledge_ref")) or (l4.get("design_knowledge_count", 0) > 0)
        if has_l4 and not l2.get("clause_type"):
            v.append((tid, "G_L4_KEY", "linked_l4 present but no linked_l2.clause_type"))

        # G_SINGLE: 単一書籍(独立源<=1)で accepted 不可
        if l4.get("l4_status") == "accepted" and l4.get("n_independent", 0) <= 1 and not override:
            v.append((tid, "G_SINGLE", "l4_status=accepted with n_independent<=1 (single source -> candidate only)"))

        # G_L4_ACC
        if l4.get("l4_status") == "accepted" and not override:
            if l4.get("n_independent", 0) < 2:
                v.append((tid, "G_L4_ACC", "accepted L4 needs n_independent>=2"))
            if not l4.get("source_independence_checked"):
                v.append((tid, "G_L4_ACC", "accepted L4 needs source_independence_checked=true"))
            if l2.get("l2_status") not in ("candidate", "accepted"):
                v.append((tid, "G_L4_ACC", "accepted L4 needs referenced L2 term >= candidate (N5)"))
            if not a.get("label_cohesion_reviewed"):
                v.append((tid, "G_L4_ACC", "accepted L4 needs L2 label_cohesion_reviewed (N5)"))

        # G_L2_ACC
        if l2.get("l2_status") == "accepted" and not override:
            if a.get("authority_class") != "authoritative_anchor":
                v.append((tid, "G_L2_ACC", "accepted L2 needs authoritative_anchor (FF-1)"))
            if not a.get("label_cohesion_reviewed"):
                v.append((tid, "G_L2_ACC", "accepted L2 needs label_cohesion_reviewed (FF-2)"))

        # G_TERM_ACC
        if r.get("status") == "accepted" and not r.get("owner_ratified") and not override:
            v.append((tid, "G_TERM_ACC", "term status=accepted needs owner_ratified=true"))
    return v


def _selftest():
    base = {
        "term_id": "x", "pref_label": "X", "status": "seed", "domain": "general",
        "source_basis": "t", "version": "v0.1", "owner_ratified": False, "owner_override": None,
        "linked_l2": {"clause_type": "x", "semantic_type": None, "l2_status": "seed",
                      "anchor": {"anchored": False, "anchor_source": None, "anchor_ref": None,
                                 "anchor_match_kind": None, "authority_class": "non_anchor",
                                 "label_cohesion_reviewed": False}},
        "linked_l4": {"design_knowledge_ref": [], "design_knowledge_count": 0, "n_independent": 0,
                      "source_independence_checked": False, "narrower_terms": [], "l4_status": "seed"},
    }

    def clone(**kw):
        import copy
        r = copy.deepcopy(base)
        for k, val in kw.items():
            r[k] = val
        return r

    cases = []  # (name, records, expect_gate_or_None)
    cases.append(("clean_seed", [clone()], None))
    # bad term_id
    cases.append(("bad_id", [clone(term_id="BadId")], "STRUCT"))
    # duplicate
    cases.append(("dup", [clone(), clone()], "G_UNIQUE"))
    # vocab fork in narrower
    r = clone(); r["linked_l4"]["narrower_terms"] = ["ghost"]
    cases.append(("fork", [r], "G_NO_FORK"))
    # L4 present but no L2 clause_type
    r = clone(); r["linked_l4"]["design_knowledge_count"] = 1; r["linked_l2"]["clause_type"] = ""
    cases.append(("l4_no_l2", [r], "G_L4_KEY"))
    # single source accepted
    r = clone(); r["linked_l4"]["l4_status"] = "accepted"; r["linked_l4"]["n_independent"] = 1
    cases.append(("single_accepted", [r], "G_SINGLE"))
    # L4 accepted missing prerequisites (n_independent>=2 but L2 still seed)
    r = clone()
    r["linked_l4"].update(l4_status="accepted", n_independent=2, source_independence_checked=True)
    cases.append(("l4_acc_l2_seed", [r], "G_L4_ACC"))
    # L4 accepted fully satisfied -> clean
    r = clone()
    r["linked_l4"].update(l4_status="accepted", n_independent=2, source_independence_checked=True)
    r["linked_l2"]["l2_status"] = "candidate"
    r["linked_l2"]["anchor"].update(authority_class="authoritative_anchor", label_cohesion_reviewed=True, anchored=True)
    cases.append(("l4_acc_ok", [r], None))
    # L2 accepted without authoritative anchor
    r = clone(); r["linked_l2"]["l2_status"] = "accepted"
    cases.append(("l2_acc_weak", [r], "G_L2_ACC"))
    # term accepted without ratify
    r = clone(); r["status"] = "accepted"
    cases.append(("term_acc_noratify", [r], "G_TERM_ACC"))
    # owner_override bypasses single_accepted
    r = clone(); r["linked_l4"]["l4_status"] = "accepted"; r["linked_l4"]["n_independent"] = 1
    r["owner_override"] = "owner approved provisional"
    cases.append(("override_single", [r], None))

    ok = 0
    for name, recs, expect in cases:
        gates = {g for _, g, _ in validate(recs)}
        if expect is None:
            passed = len(gates) == 0
        else:
            passed = expect in gates
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}: expect={expect} got={sorted(gates) or '∅'}")
        ok += passed
    print(f"self-test: {ok}/{len(cases)} passed")
    return ok == len(cases)


def _check_file(path):
    recs = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError as ex:
                print(f"  [FAIL] line {i}: JSON error: {ex}")
                return False
    viol = validate(recs)
    print(f"\nseed check: {path}  ({len(recs)} terms)")
    if not viol:
        print(f"  [PASS] 0 violations")
        # 簡易サマリ
        from collections import Counter
        c = Counter((r['linked_l4']['l4_status'], r['linked_l2']['l2_status']) for r in recs)
        for (l4s, l2s), n in sorted(c.items()):
            print(f"    L4={l4s:9} L2={l2s:9} : {n}")
        return True
    for tid, gate, msg in viol:
        print(f"  [FAIL] {tid} :: {gate} :: {msg}")
    return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ok = _check_file(sys.argv[1])
        sys.exit(0 if ok else 1)
    print("=== self-test ===")
    st = _selftest()
    seed = os.path.join(os.path.dirname(__file__), "..", "docs/tmplstruct/registry/shared_term_registry.seed.jsonl")
    sf = _check_file(seed) if os.path.exists(seed) else True
    sys.exit(0 if (st and sf) else 1)
