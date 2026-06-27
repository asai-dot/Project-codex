#!/usr/bin/env python3
"""case_bind_guard.py — false-merge 防止ガード (DD-CASEBIND-001)。

判例 observation を case_key へ束ねる際、*別判断の1本化(false merge)* を構造的に防ぐ。
方針: precision優先・split寄り(AN-4)。自動bindは決定的多シグナル合意のみ、疑いは review。

ガード規則 (fail-closed):
  G1 blocking: 比較は決定的キー (forum_code, decision_date, case_number_norm) 内のみ。
     forum_code が違えば *絶対に同一視しない* (same_number_diff_forum を遮断)。
  G2 provisional: case_number_norm が null/unresolved は自動bind禁止。
     observation 単位の provisional case_key、人手で confirmed 昇格。
  G3 multi-signal 合意: 同一決定キー内で外部IDが *同一source内で衝突* するなら、
     自然キー一致でも自動bindせず review (Tier B) へ降格。
  G4 別docket: case_number_norm が異なれば別 case_key (併合は edge、merge しない)。
  G5 Tier: 決定キー合意=Tier A(auto)。外部ID/fuzzyのみの跨ぎ候補=Tier B/C(review, 非merge)。

read-only。DB/DDL なし。DD-CASEEVAL の指標で効果検証 (test_case_bind_guard)。
"""
from __future__ import annotations
import hashlib
from collections import defaultdict


def _ck(prefix: str, key: str) -> str:
    return f"{prefix}:{hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]}"


def decide_bindings(observations: list[dict]):
    """observations -> (assignment, tiers, review_queue)。

    obs: {observation_id, forum_code, decision_date, case_number_norm(None可),
          external_id(""可), external_source(""可), era_resolution_status("resolved"既定)}
    assignment[obs_id]=case_key / tiers[obs_id]=A|B|C|prov / review_queue=[{...}]。
    """
    assignment, tiers, review = {}, {}, []
    blocks = defaultdict(list)

    for o in observations:
        oid = o["observation_id"]
        norm = o.get("case_number_norm")
        era_ok = o.get("era_resolution_status", "resolved") == "resolved"
        # G2: 自然キー不能/元号未解決 → provisional、自動bind禁止
        if not norm or not era_ok:
            assignment[oid] = _ck("PROV", oid)
            tiers[oid] = "prov"
            review.append({"observation_id": oid, "reason": "provisional_no_natural_key",
                           "tier": "prov", "action": "human_confirm"})
            continue
        # G1+G4: 決定的キー(forum+date+norm)で blocking。forum/norm が違えば別ブロック=別case。
        det_key = f"{o['forum_code']}|{o['decision_date']}|{norm}"
        blocks[det_key].append(o)

    for det_key, members in blocks.items():
        # G3: 同一source内で外部IDが衝突 → 自動bindせず review(Tier B)
        by_source = defaultdict(set)
        for m in members:
            if m.get("external_id"):
                by_source[m.get("external_source", "")].add(m["external_id"])
        conflict = any(len(ids) > 1 for ids in by_source.values())
        case_key = _ck("DET", det_key)
        for m in members:
            oid = m["observation_id"]
            assignment[oid] = case_key
            if conflict:
                tiers[oid] = "B"
                review.append({"observation_id": oid, "reason": "external_id_conflict_same_source",
                               "det_key": det_key, "tier": "B", "action": "human_review"})
            else:
                tiers[oid] = "A"   # 決定的多シグナル合意=自動bind可

    return assignment, tiers, review


def fuzzy_review_candidates(fuzzy_pairs: list) -> list[dict]:
    """G5 Tier C: fuzzy(弱類似)候補を *review 専用* に出す。**自動 merge しない**(split寄り)。

    fuzzy_pairs: [(oid_a, oid_b, score)]。外部 fuzzy matcher の出力を受ける hook
    (本ガードは決定的のみ自動 bind。C は人手確認待ちの非merge tier)。
    DD-CASEID-001 の「fuzzy → Tier C → review」を実装則化。
    """
    return [{"pair": (a, b), "score": s, "tier": "C",
             "reason": "fuzzy_weak_match", "action": "human_review"}
            for a, b, s in fuzzy_pairs]


def detect_cross_source_conflicts(assignment: dict, obs_by_id: dict) -> list[dict]:
    """G6 (v0.2 note): 同一外部参照 'source:id' が複数 case_key に跨る矛盾を検出。

    一つの源が「同じレコード」と言うものを採番が割れて束ねた=取りこぼし/誤りの信号。
    merge はせず review に出す(③CORROB conflict_review と同じ非merge方針)。
    """
    ref_to_cases = defaultdict(set)
    for oid, ck in assignment.items():
        o = obs_by_id.get(oid, {})
        if o.get("external_id"):
            ref_to_cases[f'{o.get("external_source","")}:{o["external_id"]}'].add(ck)
    return [{"external_ref": r, "case_keys": sorted(cs),
             "reason": "same_extref_multi_case", "action": "human_review"}
            for r, cs in sorted(ref_to_cases.items()) if len(cs) > 1]


def auto_bound_assignment(observations: list[dict]) -> dict:
    """自動bind(Tier A)のみを採用した assignment。

    review(Tier B/C/prov)は *merge しない* = observation 単位の独立 case_key に倒す
    (split寄り)。DD-CASEEVAL で false_merge を測る pred として使う。
    """
    assignment, tiers, _ = decide_bindings(observations)
    grouped = defaultdict(list)
    for oid, ck in assignment.items():
        grouped[ck].append(oid)
    out = {}
    for ck, oids in grouped.items():
        if all(tiers[o] == "A" for o in oids):
            for o in oids:
                out[o] = ck            # Tier A ブロックは束ねる
        else:
            for o in oids:
                out[o] = f"{ck}:{o}"   # 非A は split (独立)
    return out
