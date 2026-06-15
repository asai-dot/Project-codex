#!/usr/bin/env python3
"""
shared_term_registry バリデータ v0.2 (R0 registry shell)

監査(DDREGSHELL PASS_WITH_NOTES, 2026-06-15)反映:
  - status 3系統を改称: term_identity_status / l2_anchor_status / l4_design_status
  - term_kind / source_lane / usage_scope 追加(Q5 必須・PJ横断混在防止)
  - narrower_terms -> narrower_relations[{child_term_id, narrower_kind, basis}]
  - anchor -> anchors[](evidence_purpose 必須)
  - owner_override 構造化、L4 accepted に no_unresolved_contradiction / applicable_scope
DDL/DB書込みは行わない(設計のみ・HOLD)。

ゲート:
  STRUCT       必須項目/enum/term_id命名(snake_case)
  G_UNIQUE     term_id 一意
  G_TERM_KIND_PRESENT   term_kind 必須(Q5)
  G_SOURCE_LANE_PRESENT source_lane 非空(Q5)
  G_USAGE_SCOPE_PRESENT usage_scope 非空(Q5)
  G_SOURCE_BASIS_TYPED  source_basis_kind が enum
  G_ANCHOR_PURPOSE      各 anchor に evidence_purpose
  G_NO_FORK / G_NARROWER_CHILD_EXISTS  narrower child は registry 内 term
  G_NARROWER_NOT_SELF   自己参照禁止
  G_NARROWER_NO_CYCLE   narrower グラフに閉路なし
  G_L4_KEY     L4実体があるなら L2識別性必須
  G_SINGLE     独立源<=1 で l4_design_status=accepted 不可(単一書籍はcandidate止まり)
  G_L4_ACC     l4 accepted = 独立源>=2 + 独立性確認 + 矛盾なし + scope明示
               + 参照L2>=candidate + label_cohesion (or owner_override)
  G_L2_ACC     l2 accepted = authoritative_anchor + label_cohesion (or owner_override)
  G_TERM_ACC   term accepted = owner_ratified (or owner_override)
  G_OWNER_OVERRIDE_STRUCTURED  owner_override は構造体(reason/decided_by/decided_at/scope)

使い方:
  python3 tools/validate_shared_term_registry.py            # self-test + seed検査
  python3 tools/validate_shared_term_registry.py <path.jsonl>
"""
import json, sys, os, re

STATUSES = {"seed", "candidate", "accepted", "deprecated"}
DOMAINS = {"civil_obligation", "civil_contract", "corporate", "labor",
           "procedural", "cross_practice", "general", "boilerplate"}
TERM_KINDS = {"legal_concept", "clause_type", "remedy_type", "procedure_type",
              "document_type", "actor_role", "issue_label", "bibliographic_label"}
SOURCE_LANES = {"tmplstruct", "d1lic", "alo_kb", "biblio", "lawsubtrans", "egov", "office_dynamic"}
USAGE_SCOPES = {"template_l2", "template_l4", "case_issue", "statute_definition", "literature_toc", "sf_binding"}
AUTHORITY = {"authoritative_anchor", "weak_observation_anchor", "non_anchor"}
EVIDENCE_PURPOSE = {"identity_anchor", "design_rationale", "drafting_guidance", "observed_variation"}
SOURCE_BASIS_KINDS = {"observed_in_office_templates", "commentary", "a_frame_stabilizer", "mixed"}
NARROWER_KINDS = {"subfunction", "option_axis", "remedy", "party_role_variant", "procedural_variant"}
OVERRIDE_REQ = {"reason", "decided_by", "decided_at", "scope"}
TERM_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _struct_errors(r):
    e = []
    for k in ("term_id", "pref_label", "term_identity_status", "domain", "term_kind",
              "source_lane", "usage_scope", "source_basis", "source_basis_kind", "version",
              "linked_l2", "linked_l4"):
        if k not in r:
            e.append(f"missing required field: {k}")
    if "term_id" in r and not TERM_RE.match(str(r["term_id"])):
        e.append(f"term_id not snake_case: {r.get('term_id')!r}")
    if r.get("term_identity_status") not in STATUSES:
        e.append(f"bad term_identity_status: {r.get('term_identity_status')}")
    if r.get("domain") not in DOMAINS:
        e.append(f"bad domain: {r.get('domain')}")
    l2 = r.get("linked_l2") or {}
    if l2.get("l2_anchor_status") not in STATUSES:
        e.append(f"bad linked_l2.l2_anchor_status: {l2.get('l2_anchor_status')}")
    if not isinstance(l2.get("label_cohesion_reviewed"), bool):
        e.append("linked_l2.label_cohesion_reviewed must be bool")
    for a in l2.get("anchors", []):
        if a.get("authority_class") not in AUTHORITY:
            e.append(f"bad anchor.authority_class: {a.get('authority_class')}")
    l4 = r.get("linked_l4") or {}
    if l4.get("l4_design_status") not in STATUSES:
        e.append(f"bad linked_l4.l4_design_status: {l4.get('l4_design_status')}")
    for k in ("design_knowledge_count", "n_independent"):
        if not isinstance(l4.get(k), int):
            e.append(f"linked_l4.{k} must be int")
    for k in ("source_independence_checked", "no_unresolved_contradiction"):
        if not isinstance(l4.get(k), bool):
            e.append(f"linked_l4.{k} must be bool")
    return e


def _build_child_map(records):
    m = {}
    for r in records:
        kids = [nr.get("child_term_id") for nr in (r.get("linked_l4") or {}).get("narrower_relations", [])]
        m[r.get("term_id")] = [k for k in kids if k]
    return m


def _has_cycle(start, child_map):
    seen, stack = set(), [start]
    first = True
    while stack:
        n = stack.pop()
        if n == start and not first:
            return True
        first = False
        if n in seen:
            continue
        seen.add(n)
        stack.extend(child_map.get(n, []))
    return False


def validate(records):
    v = []
    ids = {r.get("term_id") for r in records}
    child_map = _build_child_map(records)
    seen = set()
    for r in records:
        tid = r.get("term_id", "<?>")
        for msg in _struct_errors(r):
            v.append((tid, "STRUCT", msg))
        if tid in seen:
            v.append((tid, "G_UNIQUE", "duplicate term_id"))
        seen.add(tid)

        l2 = r.get("linked_l2") or {}
        l4 = r.get("linked_l4") or {}
        anchors = l2.get("anchors", [])
        override = r.get("owner_override")
        has_override = isinstance(override, dict)

        # Q5 fields
        if r.get("term_kind") not in TERM_KINDS:
            v.append((tid, "G_TERM_KIND_PRESENT", f"bad/missing term_kind: {r.get('term_kind')}"))
        sl = r.get("source_lane") or []
        if not (isinstance(sl, list) and sl and all(x in SOURCE_LANES for x in sl)):
            v.append((tid, "G_SOURCE_LANE_PRESENT", f"bad/empty source_lane: {sl}"))
        us = r.get("usage_scope") or []
        if not (isinstance(us, list) and us and all(x in USAGE_SCOPES for x in us)):
            v.append((tid, "G_USAGE_SCOPE_PRESENT", f"bad/empty usage_scope: {us}"))
        if r.get("source_basis_kind") not in SOURCE_BASIS_KINDS:
            v.append((tid, "G_SOURCE_BASIS_TYPED", f"bad source_basis_kind: {r.get('source_basis_kind')}"))

        # anchors evidence_purpose
        for a in anchors:
            if a.get("evidence_purpose") not in EVIDENCE_PURPOSE:
                v.append((tid, "G_ANCHOR_PURPOSE", f"anchor missing evidence_purpose: {a.get('anchor_ref')}"))

        # narrower relations
        for nr in l4.get("narrower_relations", []):
            ch = nr.get("child_term_id")
            if nr.get("narrower_kind") not in NARROWER_KINDS:
                v.append((tid, "STRUCT", f"bad narrower_kind: {nr.get('narrower_kind')}"))
            if ch == tid:
                v.append((tid, "G_NARROWER_NOT_SELF", f"narrower self-reference: {ch}"))
            if ch not in ids:
                v.append((tid, "G_NARROWER_CHILD_EXISTS", f"narrower child not in registry (fork): {ch}"))
        if _has_cycle(tid, child_map):
            v.append((tid, "G_NARROWER_NO_CYCLE", "narrower graph cycle"))

        # owner_override structured
        if override is not None and not has_override:
            v.append((tid, "G_OWNER_OVERRIDE_STRUCTURED", "owner_override must be object or null"))
        if has_override and not OVERRIDE_REQ.issubset(override):
            v.append((tid, "G_OWNER_OVERRIDE_STRUCTURED", f"owner_override missing keys: {OVERRIDE_REQ - set(override)}"))

        # L4 keyed by L2
        has_l4 = bool(l4.get("design_knowledge_ref")) or (l4.get("design_knowledge_count", 0) > 0)
        if has_l4 and not l2.get("clause_type"):
            v.append((tid, "G_L4_KEY", "linked_l4 present but no linked_l2.clause_type"))

        # single source cap
        if l4.get("l4_design_status") == "accepted" and l4.get("n_independent", 0) <= 1 and not has_override:
            v.append((tid, "G_SINGLE", "l4 accepted with n_independent<=1 (single source -> candidate only)"))

        # L4 accepted prerequisites
        if l4.get("l4_design_status") == "accepted" and not has_override:
            if l4.get("n_independent", 0) < 2:
                v.append((tid, "G_L4_ACC", "accepted L4 needs n_independent>=2"))
            if not l4.get("source_independence_checked"):
                v.append((tid, "G_L4_ACC", "accepted L4 needs source_independence_checked=true"))
            if not l4.get("no_unresolved_contradiction"):
                v.append((tid, "G_L4_ACC", "accepted L4 needs no_unresolved_contradiction=true"))
            if not l4.get("applicable_scope"):
                v.append((tid, "G_L4_ACC", "accepted L4 needs explicit applicable_scope"))
            if l2.get("l2_anchor_status") not in ("candidate", "accepted"):
                v.append((tid, "G_L4_ACC", "accepted L4 needs referenced L2 >= candidate (N5)"))
            if not l2.get("label_cohesion_reviewed"):
                v.append((tid, "G_L4_ACC", "accepted L4 needs L2 label_cohesion_reviewed (N5)"))

        # L2 accepted prerequisites
        if l2.get("l2_anchor_status") == "accepted" and not has_override:
            if not any(a.get("authority_class") == "authoritative_anchor" for a in anchors):
                v.append((tid, "G_L2_ACC", "accepted L2 needs an authoritative_anchor (FF-1)"))
            if not l2.get("label_cohesion_reviewed"):
                v.append((tid, "G_L2_ACC", "accepted L2 needs label_cohesion_reviewed (FF-2)"))

        # term accepted
        if r.get("term_identity_status") == "accepted" and not r.get("owner_ratified") and not has_override:
            v.append((tid, "G_TERM_ACC", "term_identity_status=accepted needs owner_ratified=true"))
    return v


def _base():
    return {
        "term_id": "x", "pref_label": "X", "provisional_aliases": [],
        "term_identity_status": "seed", "domain": "general", "term_kind": "clause_type",
        "source_lane": ["tmplstruct"], "usage_scope": ["template_l2"],
        "source_basis": "t", "source_basis_kind": "observed_in_office_templates",
        "version": "v0.2", "owner_ratified": False, "owner_override": None,
        "linked_l2": {"clause_type": "x", "semantic_type": None, "l2_anchor_status": "seed",
                      "label_cohesion_reviewed": False, "anchors": []},
        "linked_l4": {"design_knowledge_ref": [], "design_knowledge_count": 0, "n_independent": 0,
                      "source_independence_checked": False, "no_unresolved_contradiction": True,
                      "applicable_scope": None, "narrower_relations": [], "l4_design_status": "seed"},
        "notes": None,
    }


def _selftest():
    import copy

    def clone(**kw):
        r = copy.deepcopy(_base())
        for k, val in kw.items():
            r[k] = val
        return r

    cases = []
    cases.append(("clean_seed", [clone()], None))
    cases.append(("bad_id", [clone(term_id="BadId")], "STRUCT"))
    cases.append(("dup", [clone(), clone()], "G_UNIQUE"))
    cases.append(("no_term_kind", [clone(term_kind="zzz")], "G_TERM_KIND_PRESENT"))
    cases.append(("empty_usage", [clone(usage_scope=[])], "G_USAGE_SCOPE_PRESENT"))
    cases.append(("bad_lane", [clone(source_lane=["nope"])], "G_SOURCE_LANE_PRESENT"))
    cases.append(("bad_basis_kind", [clone(source_basis_kind="zzz")], "G_SOURCE_BASIS_TYPED"))
    # anchor without evidence_purpose
    r = clone(); r["linked_l2"]["anchors"] = [{"authority_class": "weak_observation_anchor"}]
    cases.append(("anchor_no_purpose", [r], "G_ANCHOR_PURPOSE"))
    # narrower child missing
    r = clone(); r["linked_l4"]["narrower_relations"] = [{"child_term_id": "ghost", "narrower_kind": "remedy"}]
    cases.append(("narrower_ghost", [r], "G_NARROWER_CHILD_EXISTS"))
    # narrower self
    r = clone(); r["linked_l4"]["narrower_relations"] = [{"child_term_id": "x", "narrower_kind": "remedy"}]
    cases.append(("narrower_self", [r], "G_NARROWER_NOT_SELF"))
    # narrower cycle a->b->a
    a = clone(); a["term_id"] = "a"; a["linked_l4"]["narrower_relations"] = [{"child_term_id": "b", "narrower_kind": "subfunction"}]
    b = clone(); b["term_id"] = "b"; b["linked_l4"]["narrower_relations"] = [{"child_term_id": "a", "narrower_kind": "subfunction"}]
    cases.append(("narrower_cycle", [a, b], "G_NARROWER_NO_CYCLE"))
    # L4 present no L2
    r = clone(); r["linked_l4"]["design_knowledge_count"] = 1; r["linked_l2"]["clause_type"] = ""
    cases.append(("l4_no_l2", [r], "G_L4_KEY"))
    # single accepted
    r = clone(); r["linked_l4"].update(l4_design_status="accepted", n_independent=1)
    cases.append(("single_accepted", [r], "G_SINGLE"))
    # L4 accepted missing prereqs (L2 still seed)
    r = clone(); r["linked_l4"].update(l4_design_status="accepted", n_independent=2,
                                       source_independence_checked=True, applicable_scope="s")
    cases.append(("l4_acc_l2_seed", [r], "G_L4_ACC"))
    # L4 accepted fully satisfied -> clean
    r = clone()
    r["linked_l4"].update(l4_design_status="accepted", n_independent=2, source_independence_checked=True,
                          no_unresolved_contradiction=True, applicable_scope="scope ok")
    r["linked_l2"].update(l2_anchor_status="candidate", label_cohesion_reviewed=True,
                          anchors=[{"authority_class": "authoritative_anchor", "evidence_purpose": "identity_anchor"}])
    cases.append(("l4_acc_ok", [r], None))
    # L2 accepted weak
    r = clone(); r["linked_l2"]["l2_anchor_status"] = "accepted"
    cases.append(("l2_acc_weak", [r], "G_L2_ACC"))
    # term accepted no ratify
    r = clone(); r["term_identity_status"] = "accepted"
    cases.append(("term_acc_noratify", [r], "G_TERM_ACC"))
    # bad override shape
    r = clone(); r["owner_override"] = "just a string"
    cases.append(("override_unstructured", [r], "G_OWNER_OVERRIDE_STRUCTURED"))
    # structured override bypasses single
    r = clone(); r["linked_l4"].update(l4_design_status="accepted", n_independent=1)
    r["owner_override"] = {"reason": "ok", "decided_by": "owner", "decided_at": "2026-06-15", "scope": "x"}
    cases.append(("override_bypass", [r], None))

    ok = 0
    for name, recs, expect in cases:
        gates = {g for _, g, _ in validate(recs)}
        passed = (len(gates) == 0) if expect is None else (expect in gates)
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
        print("  [PASS] 0 violations")
        from collections import Counter
        c = Counter((r['linked_l4']['l4_design_status'], r['linked_l2']['l2_anchor_status']) for r in recs)
        for (l4s, l2s), n in sorted(c.items()):
            print(f"    L4={l4s:9} L2={l2s:9} : {n}")
        return True
    for tid, gate, msg in viol:
        print(f"  [FAIL] {tid} :: {gate} :: {msg}")
    return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(0 if _check_file(sys.argv[1]) else 1)
    print("=== self-test ===")
    st = _selftest()
    seed = os.path.join(os.path.dirname(__file__), "..", "docs/tmplstruct/registry/shared_term_registry.seed.jsonl")
    sf = _check_file(seed) if os.path.exists(seed) else True
    sys.exit(0 if (st and sf) else 1)
