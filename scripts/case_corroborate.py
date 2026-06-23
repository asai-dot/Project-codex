#!/usr/bin/env python3
"""case_corroborate.py — 多源コロボレーション (DD-CASECORROB-001)。

独立源の一致で confidence を上げ、不一致を review に出す。源の *種類* で効かせ方を分離:
  L1 identity   : 判例DB間(D1/NII/最高裁HP)の自然キー一致 → 同一性の補強
  L2 annotation : D1-LIC crosswalk(解説誌→事件) → 要旨/評釈 source の補強
  L3 relation   : OPAC/CiNii 引用(事件→事件) → 関係(edge)候補
*どの種類も merge はしない*(CASE-001 AN-2: 関係は edge)。コロボは
confidence 付与と review 振り分けのみ。canonical 昇格は別ゲート(HOLD)。

link_type:
  caselaw_same_case     : 同一事件主張(判例DB間)。同一 case_key で identity_corroborated、
                          異なれば conflict_review(false split か crosswalk 誤りの疑い)。
  literature_about_case : 解説/評釈が当該事件に言及。annotation_corroboration(L2)。
  case_cites_case       : 事件が事件を引用。relationship_edge 候補(L3, review-first)。

read-only。DB/DDL なし。検証は test_case_corroborate.py。
"""
from __future__ import annotations
from collections import defaultdict


def corroborate(assignment: dict, obs_by_id: dict, links: list[dict]):
    """assignment[oid]=case_key / obs_by_id[oid]={source, external_id} /
    links=[{a, b, type}] (a,b は 'source:external_id')。

    returns (case_confidence, findings)。
    """
    per_case = defaultdict(lambda: {"sources": set(), "obs": []})
    extref_to_case = {}
    for oid, ck in assignment.items():
        o = obs_by_id[oid]
        per_case[ck]["sources"].add(o["source"])
        per_case[ck]["obs"].append(oid)
        if o.get("external_id"):
            extref_to_case[f'{o["source"]}:{o["external_id"]}'] = ck

    # L1: 独立 *判例DB* 源の数で identity confidence
    CASELAW = {"D1-Law", "NII", "saikousai-hp", "saikousai-db", "hanrei-times", "hanrei-hisho",
               "lexdb-tkc", "westlaw-japan", "kakyu-saibansho-hp", "chizai-kosai-hp"}
    case_confidence = {}
    for ck, d in per_case.items():
        caselaw_sources = d["sources"] & CASELAW
        n = len(caselaw_sources)
        level = ("multi_source_agree" if n >= 2 else
                 "single_source" if n == 1 else "non_caselaw_only")
        case_confidence[ck] = {
            "distinct_caselaw_sources": sorted(caselaw_sources),
            "all_sources": sorted(d["sources"]),
            "identity_corroboration": level,
        }

    findings = []
    for lk in links:
        ca = extref_to_case.get(lk["a"])
        cb = extref_to_case.get(lk["b"])
        lt = lk["type"]
        if ca is None or cb is None:
            findings.append({"link": lk, "status": "unresolved_ref", "action": "skip"})
            continue
        if lt == "caselaw_same_case":
            if ca == cb:
                findings.append({"link": lk, "status": "identity_corroborated",
                                 "case_key": ca, "action": "raise_confidence"})
            else:
                # 同一事件主張だが採番が割れている → merge せず review(G1=forum跨ぎは特に)
                findings.append({"link": lk, "status": "conflict_review",
                                 "case_keys": [ca, cb], "action": "human_review"})
        elif lt == "literature_about_case":
            findings.append({"link": lk, "status": "annotation_corroboration_L2",
                             "case_key": cb if cb else ca, "action": "attach_annotation_candidate"})
        elif lt == "case_cites_case":
            status = ("self_citation_anomaly" if ca == cb else "relationship_edge_candidate_L3")
            findings.append({"link": lk, "status": status, "case_keys": [ca, cb],
                             "action": "review_edge"})
        else:
            findings.append({"link": lk, "status": "unknown_link_type", "action": "fail_closed"})
    return case_confidence, findings
