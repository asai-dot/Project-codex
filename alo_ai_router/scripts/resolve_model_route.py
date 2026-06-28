#!/usr/bin/env python3
"""
resolve_model_route.py — route_candidates.yaml の各 candidate に対し、
model_router.yml の rules / hard_denies / data_policy.yml / model_registry.yml を当てて
最終的な route_decision を出す。

入力: route_candidates.yaml, queue_item.json (1件分の作業票)
出力: route_decision.json (queue_item.schema に準拠する model_route + authority)

不変条件:
- UNKNOWN は fail closed → status=triage_needed で出す
- HD1〜HD5 を全部評価し、1つでも違反したら deny
- worker は draft_write 以下のみ
"""
import argparse, json, sys, yaml, uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ROUTER = yaml.safe_load((ROOT / "model_router.yml").read_text())
REGISTRY = yaml.safe_load((ROOT / "model_registry.yml").read_text())
DATA_POLICY = yaml.safe_load((ROOT / "data_policy.yml").read_text())


def first_candidate(role, exclude_family=None):
    role_def = REGISTRY["roles"].get(role) or REGISTRY.get("specialty_roles", {}).get(role)
    if not role_def:
        return None, None
    for c in role_def.get("candidates", []):
        if exclude_family and c.get("family") == exclude_family:
            continue
        return c.get("id"), c.get("family")
    return None, None


def check_hard_denies(item):
    failed = []
    # HD1: mutation_power が processed/canonical なのに worker
    if item["authority"]["requested_mutation_power"] in ("processed_mark", "canonical_write", "production_db_write"):
        if item["model_route"]["primary_role"] not in ("head", "controller", "human"):
            failed.append("HD1_worker_cannot_processed")
    # HD2: same family audit
    if item["classification"]["task_type"] in ("audit", "red_team", "metaaudit", "result_review"):
        author = item["lineage"].get("author_family")
        auditor = item["model_route"].get("primary_family")
        if author and auditor and author == auditor:
            failed.append("HD2_no_same_family_audit")
    # HD3: L0 で model を割り当てない
    if item["classification"]["cog_level"] == "L0_DETERMINISTIC":
        if item["model_route"].get("primary_model"):
            failed.append("HD3_no_llm_for_l0")
    # HD4: canonical 級に cheap
    if item["classification"]["task_type"] in ("canonical_boundary", "db_schema_decision", "accepted_decision", "legal_strategy"):
        if item["model_route"].get("primary_role") in ("cheap_extractor", "summary_worker"):
            failed.append("HD4_no_cheap_model_for_canonical")
    # HD5: secret zone を外部 cheap に
    zone = item["data"].get("data_zone")
    zone_policy = DATA_POLICY["zones"].get(zone, {})
    if zone in ("credentials", "passwords", "client_privileged"):
        if item["model_route"].get("primary_role") in ("cheap_extractor",):
            failed.append("HD5_no_secret_zone_to_external_cheap")
    return failed


def resolve(item):
    cog = item["classification"]["cog_level"]
    task_type = item["classification"]["task_type"]
    author_family = item["lineage"].get("author_family")

    # cog_level → model_role の素朴対応
    role_map = {
        "L0_DETERMINISTIC": "script",
        "L1_CHEAP_EXTRACTION": "cheap_extractor",
        "L2_LIGHT_SUMMARY": "summary_worker",
        "L3_NORMAL_WORK": "normal_worker",
        "L4_DEEP_REASONING": "deep_reasoner",
        "L5_INDEPENDENT_AUDIT": "independent_auditor",
        "L6_HUMAN_FINAL": "finalizer",
    }
    role = role_map.get(cog)
    if role is None:
        return {
            "status": "triage_needed",
            "reason": f"unknown cog_level: {cog}",
        }

    # モデル選定
    if role == "script" or role == "finalizer":
        model_id, family = None, None
    elif role == "independent_auditor":
        model_id, family = first_candidate(role, exclude_family=author_family)
        if model_id is None:
            return {"status": "triage_needed", "reason": "no cross-family auditor available"}
    else:
        model_id, family = first_candidate(role)

    # data_zone 適合確認
    zone = item["data"].get("data_zone")
    if not zone:
        return {"status": "triage_needed", "reason": "data_zone unknown (fail closed)"}
    zone_policy = DATA_POLICY["zones"].get(zone)
    if not zone_policy:
        return {"status": "triage_needed", "reason": f"unknown data_zone: {zone}"}
    if family and family in zone_policy.get("disallowed_families", []):
        return {"status": "blocked", "reason": f"family={family} disallowed for zone={zone}"}

    # mutation_power
    if cog == "L0_DETERMINISTIC":
        granted = "none"
    elif cog == "L6_HUMAN_FINAL":
        granted = item["authority"]["requested_mutation_power"]
    else:
        # worker は draft_write 上限
        req = item["authority"]["requested_mutation_power"]
        granted = "draft_write" if req in ("draft_write", "final_write", "processed_mark", "canonical_write") else req

    decision = {
        "route_id": str(uuid.uuid4()),
        "request_id": item["request_id"],
        "model_role": role,
        "selected_model": model_id,
        "selected_family": family,
        "finalizer": "head_controller",
        "route_reason": f"cog={cog} task={task_type}",
        "granted_mutation_power": granted,
        "hard_denies_passed": 0,
        "hard_denies_failed_ids": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # decision を入れた仮 item を作って hard_denies チェック
    tentative = dict(item)
    tentative["model_route"] = {
        "primary_role": role,
        "primary_model": model_id,
        "primary_family": family,
        "finalizer": "head_controller",
    }
    tentative["authority"] = dict(item["authority"])
    failed = check_hard_denies(tentative)
    decision["hard_denies_failed_ids"] = failed
    decision["hard_denies_passed"] = 5 - len(failed)
    if failed:
        decision["status"] = "blocked"
        decision["reason"] = f"hard_denies failed: {failed}"
    else:
        decision["status"] = "routed"
    return decision


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-item", required=True, type=Path, help="queue_item.json (1件)")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    item = json.loads(args.queue_item.read_text())
    decision = resolve(item)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(decision, ensure_ascii=False, indent=2))
    print(f"[resolve_model_route] status={decision.get('status')} model={decision.get('selected_model')} role={decision.get('model_role')}")
    sys.exit(0 if decision.get("status") == "routed" else 1)


if __name__ == "__main__":
    main()
