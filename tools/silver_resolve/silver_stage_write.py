#!/usr/bin/env python3
"""P1: silver candidate -> build側② silver staging への候補書込み (既定 dry-run).

WO-SILVER-WRITE-001 の実装. 依存ゼロ (Python 3.9+).
**SILVER-RESOLUTION-KICKOFF v0.1.1 整合: accepted/reviewed=true は作らない.**

owner ratify 後にのみ --apply。既定は dry-run (何も書かない)。
書込み先は append-only JSONL staging のみ (DDL / DB / canonical graph には触れない)。

- candidate lane     : policy 合致の machine_suggested_*_unreviewed を
                       <staging>/silver_<kind>_candidate.jsonl へ append (reviewed=false 固定)。
- ambiguity_queue    : needs_human_review / ambiguous_or_unresolved 等を
                       <staging>/silver_<kind>_ambiguity_queue.jsonl へ append (siblings 保存)。
- 除外               : blocked / target 無 (candidates jsonl 側に残るので staging へは上げない)。
- ledger             : 書込みイベントを <staging>/_SILVER_WRITE_LEDGER.jsonl へ 1 行 append。
- 冪等               : silver_id で重複書込み抑止。

監査整合の不変条件:
  - reviewed は常に false (このレーンで reviewed=true / canonical / claim_support / alo_edges 化しない)。
  - 解決先は source-record URI (target_source_record_uri)。canonical case key ではない。
  - tier A/B も候補。candidate lane に入っても "accepted" ではない。

policy.json (owner 承認): {"accept_status":[...], "source_scheme_version":..., "suggested_by":"owner"}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

JST = timezone(timedelta(hours=9))

# tier A cite / suggested section の status (candidate lane に上げてよい既定集合)
ST_CITE_A = "machine_suggested_source_record_match_unreviewed"
ST_SECTION = "machine_suggested_issue_section_unreviewed"
DEFAULT_POLICY = {"accept_status": [ST_CITE_A, ST_SECTION],
                  "source_scheme_version": "unknown", "suggested_by": "owner"}


def read_jsonl(path: Optional[Path]) -> List[dict]:
    if not path or not Path(path).exists():
        return []
    out = []
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def policy_hash(policy: dict) -> str:
    return hashlib.sha1(json.dumps(policy, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def _blocked(c: dict) -> bool:
    return bool(c.get("blocker_code")) or c.get("suggestion_status") == "blocked_by_policy_or_provenance"


def _route_cite(c: dict, policy: dict) -> Tuple[str, Optional[str], Optional[dict]]:
    """(lane, silver_id, payload). lane ∈ candidate|ambiguity|exclude."""
    targets = c.get("target_source_record_uri") or []
    if _blocked(c) or not targets:
        return "exclude", None, None
    sid = f"cite:{c.get('lic_edge_id','')}|{'+'.join(map(str, targets))}"
    payload = {"target_source_record_uri": targets, "identity_scope": c.get("identity_scope"),
               "normalized_position_key": c.get("normalized_position_key"),
               "source_ref_hash": c.get("source_ref_hash"), "match_basis": c.get("match_basis"),
               "evidence_tier": c.get("evidence_tier"), "sibling_count": c.get("sibling_count"),
               "non_selection_reason": c.get("non_selection_reason")}
    # candidate lane = tier A 単一のみ. B/C/D は ambiguity_queue (高密度QA/レビュー待ち).
    is_candidate = (c.get("suggestion_status") in policy["accept_status"] and len(targets) == 1)
    return ("candidate" if is_candidate else "ambiguity"), sid, payload


def _route_section(c: dict, policy: dict) -> Tuple[str, Optional[str], Optional[dict]]:
    if c.get("honest_empty") or not c.get("member_hanrei_ids"):
        return "exclude", None, None
    sid = f"section:{c.get('issue_section_id','')}"
    payload = {"section_heading": c.get("section_heading"), "book_id": c.get("book_id"),
               "member_hanrei_ids": c.get("member_hanrei_ids"), "member_count": c.get("member_count"),
               "identity_scope": c.get("identity_scope")}
    lane = "candidate" if (c.get("decision_status") in policy["accept_status"]) else "ambiguity"
    return lane, sid, payload


def _route_cooc(c: dict, policy: dict) -> Tuple[str, Optional[str], Optional[dict]]:
    if c.get("pair_weight", 0) < 1:
        return "exclude", None, None
    a, b = c.get("hanrei_a"), c.get("hanrei_b")
    sid = f"cooc:{a}|{b}"
    payload = {"hanrei_a": a, "hanrei_b": b, "pair_weight": c.get("pair_weight"),
               "importance": c.get("importance"), "shared_section_ids": c.get("shared_section_ids")}
    lane = "candidate" if (c.get("decision_status") in policy["accept_status"]) else "ambiguity"
    return lane, sid, payload


ROUTERS = {"cite_resolved": _route_cite, "issue_section": _route_section, "issue_cooccurrence": _route_cooc}


def existing_silver_ids(staging: Path) -> set:
    ids = set()
    if not staging.exists():
        return ids
    for p in staging.glob("silver_*_*.jsonl"):
        for r in read_jsonl(p):
            if r.get("silver_id"):
                ids.add(r["silver_id"])
    return ids


def plan_writes(cite, section, cooc, policy: dict, already: set):
    """各 candidate を lane 振分け + 既存 skip. 戻り: {lane: {kind: [rows]}}, counts."""
    now = datetime.now(JST).isoformat()
    ph = policy_hash(policy)
    plan: Dict[str, Dict[str, List[dict]]] = {"candidate": {}, "ambiguity": {}}
    counts = {"candidate": 0, "ambiguity": 0, "exclude": 0, "skip_dup": 0}
    for kind, records in (("cite_resolved", cite), ("issue_section", section), ("issue_cooccurrence", cooc)):
        router = ROUTERS[kind]
        for c in records:
            lane, sid, payload = router(c, policy)
            if lane == "exclude":
                counts["exclude"] += 1
                continue
            if sid in already:
                counts["skip_dup"] += 1
                continue
            already.add(sid)
            row = {"silver_id": sid, "kind": kind, "payload": payload,
                   "suggestion_status": c.get("suggestion_status") or c.get("decision_status"),
                   "evidence_tier": c.get("evidence_tier"),
                   "reviewed": False,  # ★このレーンで reviewed=true にしない (監査不変条件)
                   "source_scheme_version": policy["source_scheme_version"],
                   "authority_dataset_version": c.get("authority_dataset_version"),
                   "authority_hash": c.get("authority_hash"),
                   "suggested_by": policy["suggested_by"], "suggested_at": now,
                   "parser_version": "silver_stage_write.py v0.2",
                   "policy_hash": ph, "assertion_kind": "derived_match"}
            plan[lane].setdefault(kind, []).append(row)
            counts[lane] += 1
    return plan, counts


def apply_writes(plan, staging: Path) -> None:
    staging.mkdir(parents=True, exist_ok=True)
    now = datetime.now(JST).isoformat()
    ledger = staging / "_SILVER_WRITE_LEDGER.jsonl"
    with ledger.open("a", encoding="utf-8") as lg:
        for lane, kinds in plan.items():
            suffix = "candidate" if lane == "candidate" else "ambiguity_queue"
            for kind, rows in kinds.items():
                fp = staging / f"silver_{kind}_{suffix}.jsonl"
                with fp.open("a", encoding="utf-8") as fh:
                    for r in rows:
                        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                lg.write(json.dumps({"ts": now, "event": "write", "lane": lane, "kind": kind,
                                     "count": len(rows), "file": fp.name}, ensure_ascii=False) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="P1 silver staging 候補書込み (既定 dry-run / --apply で確定)")
    ap.add_argument("--cite-candidates", type=Path, default=None)
    ap.add_argument("--section-candidates", type=Path, default=None)
    ap.add_argument("--cooc-candidates", type=Path, default=None)
    ap.add_argument("--policy", type=Path, default=None, help="owner 承認 policy.json")
    ap.add_argument("--staging-dir", type=Path, required=True)
    ap.add_argument("--apply", action="store_true", help="owner ratify 後にのみ. 無指定は dry-run")
    args = ap.parse_args(argv)

    policy = dict(DEFAULT_POLICY)
    if args.policy:
        policy.update(json.loads(args.policy.read_text(encoding="utf-8")))

    already = existing_silver_ids(args.staging_dir)
    plan, counts = plan_writes(read_jsonl(args.cite_candidates), read_jsonl(args.section_candidates),
                               read_jsonl(args.cooc_candidates), policy, already)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[silver-write {mode}] accept_status={policy['accept_status']} hash={policy_hash(policy)}")
    print(f"[silver-write {mode}] candidate={counts['candidate']} ambiguity={counts['ambiguity']} "
          f"exclude={counts['exclude']} skip_dup={counts['skip_dup']}")
    if args.apply:
        apply_writes(plan, args.staging_dir)
        print(f"[silver-write APPLY] appended -> {args.staging_dir} (reviewed=false / +ledger)")
    else:
        print("[silver-write DRY-RUN] 何も書いていない. owner ratify 後 --apply で確定.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
