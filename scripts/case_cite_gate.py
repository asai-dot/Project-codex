#!/usr/bin/env python3
"""case_cite_gate.py — CaseBundle 引用検証ゲート (DD-CASECITE-001)。

出力(回答/CaseBundle)を serve 前に検証し、*根拠が解決しない引用・無根拠 claim* を
fail-closed で弾く。31_case_layer §6.3 guards を実行時ゲート化:
  V1 must_cite_uris            : 各 claim は ≥1 の canonical_uri を引用
  V2 cite_resolves             : 引用 uri は既知 case に解決(ハルシネーション cite 0)
  V3 all_claims_have_evidence  : 各 claim は ≥1 evidence
  V4 pointer_case_match        : evidence.case_uri は claim の cite に含まれ既知
  V5 pointer_range_inbounds    : range は [0, full_text_len] 内・start<=end
  V6 annotation_source_canonical: annotation_used.source は is_canonical
  V7 egress_confidentiality    : global serve は open∧public(=can_global_index)のみ引用(AC-3)

いずれか違反で bundle 不合格(ok=False)→ *serve しない*。read-only。
"""
from __future__ import annotations


def _can_global_index(meta: dict) -> bool:
    return meta.get("confidentiality_class") == "open" and meta.get("redistribution") == "public"


# matter 機密に属するクラス (V8 認可対象)
MATTER_CLASSES = {"matter_scoped_only", "matter_confirmed", "lawyer_client_confidential"}


def validate_bundle(bundle: dict, known_cases: dict, canonical_sources: set,
                    requester_matters: set | None = None) -> dict:
    """known_cases[uri]={full_text_len, confidentiality_class, redistribution[, matter_id]}。
    requester_matters: 要求者が閲覧権を持つ matter_id 集合 (None=matter権限なし=fail-closed)。

    returns {ok, violations:[{claim, code, detail}]}。
    """
    v = []
    scope = bundle.get("serve_scope", "matter")

    # V6 annotation source canonical
    src = (bundle.get("annotation_used") or {}).get("source")
    if src not in canonical_sources:
        v.append({"claim": None, "code": "V6_annotation_source_not_canonical", "detail": src})

    for c in bundle.get("claims", []):
        cid = c.get("id")
        cites = c.get("cites") or []
        evid = c.get("evidence") or []
        # V1
        if not cites:
            v.append({"claim": cid, "code": "V1_no_cite", "detail": "claim cites nothing"})
        # V2 cite resolves
        for u in cites:
            if u not in known_cases:
                v.append({"claim": cid, "code": "V2_cite_unresolved", "detail": u})
            elif scope == "global" and not _can_global_index(known_cases[u]):
                # V7 egress: global で open∧public 以外を引用しない
                v.append({"claim": cid, "code": "V7_egress_non_open_cited", "detail": u})
            elif known_cases[u].get("confidentiality_class") in MATTER_CLASSES:
                # V8 (v0.2 note): matter機密 cite は要求者が当該 matter を認可されている必要
                mid = known_cases[u].get("matter_id")
                if requester_matters is None or mid not in requester_matters:
                    v.append({"claim": cid, "code": "V8_matter_not_authorized",
                              "detail": f"{u} matter_id={mid}"})
        # V3
        if not evid:
            v.append({"claim": cid, "code": "V3_no_evidence", "detail": "claim has no evidence"})
        # V4/V5 evidence integrity
        for e in evid:
            cu = e.get("case_uri")
            if cu not in known_cases:
                v.append({"claim": cid, "code": "V4_evidence_case_unresolved", "detail": cu})
                continue
            if cu not in cites:
                v.append({"claim": cid, "code": "V4_evidence_not_in_cites", "detail": cu})
            flen = known_cases[cu].get("full_text_len", 0)
            s, en = e.get("range_start"), e.get("range_end")
            if s is None or en is None or s < 0 or en < s or en > flen:
                v.append({"claim": cid, "code": "V5_pointer_range_oob",
                          "detail": f"[{s},{en}] flen={flen}"})

    return {"ok": len(v) == 0, "violations": v}
