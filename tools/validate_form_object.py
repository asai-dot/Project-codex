#!/usr/bin/env python3
"""
validate_form_object: DD-FORMOBJ-002 v0.2 の 12 ゲートをコード化し、
form_object.v0.2-poc データに dry-run 強制する。
監査 DDFORMOBJ2_PASS_WITH_NOTES(実装ゲート化 go) の must_fix/新ゲート/negative test を実装。

★これは gate code + dry-run + negative test のみ。DDL/DB書込み・schema freeze・corpus展開・
  filled_instance投入は HOLD(owner ratify 前)。

ゲート(8継承 + 4新設):
  G_FORM_FIRST_CLASS              form_object に親FK(biblio_item_id/procedure_id/parent_*_id)を持たない
  G_FORM_LAYER_SPLIT             4層を混在させない(witnessed_in存在・filled_instance不在)
  G_NO_PARALLEL_CANONICAL        clause本文キーは witness_canonical_text(裸の'canonical'禁止)
  G_FORM_ID_OPAQUE              form_uid=alo:form:{uuidv7|PROVISIONAL:slug}、ISBN/vendor焼込み禁止
  G_WITNESS_EDITION_VERIFIED    witnessは verified_status を持つ。EDITION_MISMATCH は adopted 不可
  G_MANDATORY_GROUNDED          mandatory系 requisite は法令/forum/規則接地必須
  G_ADVISORY_SOURCE_TYPED       advisable/optional は source_type 必須
  G_FILLED_INSTANCE_SEPARATED   実案件データ(client/matter_id/filled_*)を持たない
  G_VARIANT_SPLIT_REASON_PRESENT       form_variant は variant_split_reason(enum)必須
  G_PRIVATE_CONTRACT_DEFECT_HAS_SOURCE_BASIS  私契約の mandatory は source_basis+confidence 必須
  G_NO_OPTIONAL_DESIGN_AS_INVALIDITY   optional_design に invalidity を付けない
  G_FORUM_REQUIRED_ONLY_WHEN_FORUM_EXISTS  forum_required は forum 実在時のみ

usage:
  python3 tools/validate_form_object.py                # PoC2件 dry-run + negative tests
  python3 tools/validate_form_object.py <formobj.json>
"""
import json, os, re, sys

HERE = os.path.dirname(__file__)
POC = [os.path.join(HERE, "..", "docs/tmplstruct/poc_e2e/teikan_mandatory.formobj.json"),
       os.path.join(HERE, "..", "docs/tmplstruct/poc_e2e/seizo_kihon.formobj.v2.json")]

MANDATORY = {"statute_required", "regulation_or_rule_required", "forum_required",
             "validity_required", "enforceability_required"}
DEFECTS = {"invalidity", "rejection_by_forum", "registration_defect", "evidentiary_weakness", "risk_warning"}
SPLIT_REASONS = {"legal_function_shift", "party_posture_shift", "forum_shift",
                 "regulatory_context_shift", "risk_allocation_shift"}
FORM_UID_RE = re.compile(r"^alo:form:(PROVISIONAL:[a-z0-9_]+|[0-9a-f-]{32,36})$")
PARENT_FK_FORBIDDEN = ("biblio_item_id", "procedure_id", "parent_item_id", "parent_form_id", "item_id")
FILLED_FORBIDDEN = ("filled_instance", "filled_values", "client", "client_name",
                    "matter_id", "case_id", "party_actual_name", "counterparty_name")
PRIVATE_FORUM_MARKERS = ("私人間", "提出先なし", "none", "null", "社内")


def _is_private(forum):
    if not forum:
        return True
    return any(m in str(forum) for m in PRIVATE_FORUM_MARKERS)


def _all_requisites(fo):
    return list(fo.get("requisites", [])) + list(fo.get("advisable_examples", []))


def validate(fo):
    v = []  # (gate, msg)
    foo = fo.get("form_object", {})
    forum = foo.get("forum")
    private = _is_private(forum)

    # G_FORM_FIRST_CLASS
    for k in PARENT_FK_FORBIDDEN:
        if k in foo:
            v.append(("G_FORM_FIRST_CLASS", f"form_object has forbidden parent FK: {k}"))

    # G_FILLED_INSTANCE_SEPARATED (scan whole doc keys, shallow+one level)
    def scan(d, path=""):
        if isinstance(d, dict):
            for k, val in d.items():
                if k in FILLED_FORBIDDEN:
                    v.append(("G_FILLED_INSTANCE_SEPARATED", f"filled/matter data present: {path}{k}"))
                scan(val, path + k + ".")
        elif isinstance(d, list):
            for it in d:
                scan(it, path)
    scan(fo)

    # G_FORM_LAYER_SPLIT
    if "witnessed_in" not in fo:
        v.append(("G_FORM_LAYER_SPLIT", "no witnessed_in layer (witness not separated)"))

    # G_FORM_ID_OPAQUE
    uid = foo.get("form_uid", "")
    if not FORM_UID_RE.match(uid):
        v.append(("G_FORM_ID_OPAQUE", f"form_uid not opaque alo:form form: {uid!r}"))
    if re.search(r"\d{13}|isbn|9784", uid, re.I):
        v.append(("G_FORM_ID_OPAQUE", f"form_uid embeds ISBN/vendor: {uid!r}"))

    # G_NO_PARALLEL_CANONICAL (clause text key, if any clause carries text)
    for r in _all_requisites(fo):
        if "canonical" in r and "witness_canonical_text" not in r:
            v.append(("G_NO_PARALLEL_CANONICAL", f"{r.get('term')}: bare 'canonical' key (use witness_canonical_text)"))

    # G_WITNESS_EDITION_VERIFIED
    for w in fo.get("witnessed_in", []):
        vs = w.get("verified_status")
        if not vs:
            v.append(("G_WITNESS_EDITION_VERIFIED", f"witness has no verified_status: {w.get('source_identifier')}"))
        if vs == "EDITION_MISMATCH_FLAGGED" and w.get("adopted") is True:
            v.append(("G_WITNESS_EDITION_VERIFIED", f"edition-mismatch witness adopted: {w.get('source_identifier')}"))

    # requisite-level gates
    for r in fo.get("requisites", []):
        cls = r.get("requisite_class")
        # G_MANDATORY_GROUNDED
        if cls in MANDATORY:
            g = r.get("grounded_in") or {}
            if not (g.get("law") or g.get("forum_rule")):
                v.append(("G_MANDATORY_GROUNDED", f"{r.get('term')}: mandatory but no law/forum_rule grounding"))
        # G_PRIVATE_CONTRACT_DEFECT_HAS_SOURCE_BASIS
        if private and cls in MANDATORY:
            if not r.get("source_basis") or r.get("confidence") is None:
                v.append(("G_PRIVATE_CONTRACT_DEFECT_HAS_SOURCE_BASIS",
                          f"{r.get('term')}: private-contract mandatory needs source_basis+confidence"))
        # G_FORUM_REQUIRED_ONLY_WHEN_FORUM_EXISTS
        if cls == "forum_required" and private:
            v.append(("G_FORUM_REQUIRED_ONLY_WHEN_FORUM_EXISTS",
                      f"{r.get('term')}: forum_required but forum is private/none ({forum})"))

    # optional/advisable gates
    for r in _all_requisites(fo):
        cls = r.get("requisite_class")
        if cls in ("advisable", "optional_design"):
            # G_ADVISORY_SOURCE_TYPED
            src = r.get("grounded_in_source") or {}
            if not src.get("source_type"):
                v.append(("G_ADVISORY_SOURCE_TYPED", f"{r.get('term')}: advisory/optional without source_type"))
            # G_NO_OPTIONAL_DESIGN_AS_INVALIDITY
            if cls == "optional_design" and r.get("defect_kind_if_missing") == "invalidity":
                v.append(("G_NO_OPTIONAL_DESIGN_AS_INVALIDITY", f"{r.get('term')}: optional_design tagged invalidity"))

    # G_VARIANT_SPLIT_REASON_PRESENT
    for fv in fo.get("form_variants", []):
        if fv.get("variant_split_reason") not in SPLIT_REASONS:
            v.append(("G_VARIANT_SPLIT_REASON_PRESENT", f"variant '{fv.get('variant')}' missing valid variant_split_reason"))

    return v


def _run_poc():
    ok = True
    for p in POC:
        if not os.path.exists(p):
            continue
        fo = json.load(open(p, encoding="utf-8"))
        viol = validate(fo)
        name = os.path.basename(p)
        if viol:
            ok = False
            print(f"  [FAIL] {name}: {len(viol)} violations")
            for g, m in viol:
                print(f"        {g} :: {m}")
        else:
            print(f"  [PASS] {name}: 0 violations (12-gate dry-run clean)")
    return ok


def _negative_tests():
    """わざと違反データを食わせて、該当ゲートが発火することを確認。"""
    base = json.load(open(POC[1], encoding="utf-8"))  # seizo (private contract)
    import copy
    cases = []

    # 1. optional を invalidity に
    r = copy.deepcopy(base)
    r["advisable_examples"][0]["defect_kind_if_missing"] = "invalidity"
    cases.append(("optional_as_invalidity", r, "G_NO_OPTIONAL_DESIGN_AS_INVALIDITY"))

    # 2. edition mismatch witness を adopted に
    r = copy.deepcopy(base)
    for w in r["witnessed_in"]:
        if w.get("verified_status") == "EDITION_MISMATCH_FLAGGED":
            w["adopted"] = True
    cases.append(("edition_mismatch_adopted", r, "G_WITNESS_EDITION_VERIFIED"))

    # 3. variant の split_reason を外す
    r = copy.deepcopy(base)
    del r["form_variants"][0]["variant_split_reason"]
    cases.append(("variant_no_split_reason", r, "G_VARIANT_SPLIT_REASON_PRESENT"))

    # 4. filled_instance(実案件データ)混入
    r = copy.deepcopy(base)
    r["filled_instance"] = {"client_name": "○○株式会社", "matter_id": "M-2026-001"}
    cases.append(("filled_instance_leak", r, "G_FILLED_INSTANCE_SEPARATED"))

    # 5. 私契約に forum_required
    r = copy.deepcopy(base)
    r["requisites"][0]["requisite_class"] = "forum_required"
    cases.append(("forum_required_in_private", r, "G_FORUM_REQUIRED_ONLY_WHEN_FORUM_EXISTS"))

    # 6. form_uid に ISBN 焼込み
    r = copy.deepcopy(base)
    r["form_object"]["form_uid"] = "alo:form:9784502406010"
    cases.append(("form_uid_isbn", r, "G_FORM_ID_OPAQUE"))

    ok = True
    for name, rec, expect in cases:
        gates = {g for g, _ in validate(rec)}
        passed = expect in gates
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] neg:{name}: expect {expect} -> {'fired' if passed else 'MISSED'}")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1:
        fo = json.load(open(sys.argv[1], encoding="utf-8"))
        viol = validate(fo)
        for g, m in viol:
            print(f"  {g} :: {m}")
        print("OK" if not viol else f"{len(viol)} violations")
        sys.exit(0 if not viol else 1)
    print("=== PoC dry-run (12 gates) ===")
    a = _run_poc()
    print("\n=== negative tests (違反を弾けるか) ===")
    b = _negative_tests()
    print(f"\nresult: poc={'PASS' if a else 'FAIL'} / negative={'PASS' if b else 'FAIL'}")
    sys.exit(0 if (a and b) else 1)
