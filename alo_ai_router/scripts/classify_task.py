#!/usr/bin/env python3
"""
classify_task.py — L1 deterministic 部分: タイトル/パスから task_type を機械分類。
LLM不要部分のみ。UNKNOWNなものは triage_needed としてpassthroughし、別途L1 cheap modelで分類。

入力: queue_snapshot.json
出力: route_candidates.yaml (task_type + 仮 cog_level + 推奨ルール ID)
"""
import argparse, json, re, sys, yaml
from pathlib import Path

PATTERNS = [
    # (regex, task_type, default_risk)
    (re.compile(r"AUDIT.*REQUEST|RED.?TEAM|metaaudit|REVIEW", re.I), "audit", "high"),
    (re.compile(r"CANONICAL|accepted_promotion|external_publish", re.I), "canonical_promotion", "critical"),
    (re.compile(r"DD-|design_decision|architecture", re.I), "architecture_decision", "high"),
    (re.compile(r"ORCH-.*ORDER|order_\d", re.I), "dd_draft", "medium"),
    (re.compile(r"PATCH|bounded_code|implementation", re.I), "bounded_code_patch", "medium"),
    (re.compile(r"SUMMAR|tagging|checklist", re.I), "summary", "low"),
    (re.compile(r"extract|normalize|frontmatter|labeling", re.I), "metadata_extraction", "low"),
    (re.compile(r"scan|count|diff|hash|schema_validation", re.I), "schema_validation", "low"),
]


def classify_one(item):
    title = item.get("title", "") + " " + item.get("source", "")
    for rx, task_type, risk in PATTERNS:
        if rx.search(title):
            return task_type, risk
    return None, None


def cog_level_from_task(task_type):
    if task_type in ("hash", "count", "diff", "schema_validation", "status_scan", "exact_duplicate_detection"):
        return "L0_DETERMINISTIC", "R0_deterministic"
    if task_type in ("metadata_extraction", "filename_normalization", "frontmatter_generation", "simple_labeling"):
        return "L1_CHEAP_EXTRACTION", "R1_cheap_extraction"
    if task_type in ("summary", "tagging", "checklist_generation", "request_compression"):
        return "L2_LIGHT_SUMMARY", "R2_light_summary"
    if task_type in ("dd_draft", "result_candidate", "bounded_code_patch", "bounded_audit"):
        return "L3_NORMAL_WORK", "R3_normal_work"
    if task_type in ("architecture_decision", "canonical_boundary", "db_schema_decision", "conflict_resolution", "legal_strategy", "xl_split_plan"):
        return "L4_DEEP_REASONING", "R4_deep_reasoning"
    if task_type in ("audit", "red_team", "metaaudit", "result_review"):
        return "L5_INDEPENDENT_AUDIT", "R5_independent_audit"
    if task_type in ("processed_mark", "canonical_promotion", "production_db_write", "accepted_decision", "external_publication"):
        return "L6_HUMAN_FINAL", "R6_finalization"
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    snap = json.loads(args.snapshot.read_text())
    candidates = []
    triage_needed = 0
    for item in snap.get("items", []):
        task_type, risk = classify_one(item)
        if task_type is None:
            candidates.append({
                "request_id": item["request_id"],
                "title": item["title"],
                "task_type": None,
                "cog_level": None,
                "rule_id": None,
                "status": "triage_needed",
                "reason": "no pattern matched; route to L1 cheap classifier or human triage",
            })
            triage_needed += 1
            continue
        cog, rule = cog_level_from_task(task_type)
        candidates.append({
            "request_id": item["request_id"],
            "title": item["title"],
            "task_type": task_type,
            "risk_level_guess": risk,
            "cog_level": cog,
            "rule_id": rule,
            "status": "routed_deterministic",
        })

    out = {
        "version": "v0.1",
        "snapshot": str(args.snapshot),
        "candidates": candidates,
        "total": len(candidates),
        "triage_needed": triage_needed,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False))
    print(f"[classify_task] wrote {args.out}  routed={len(candidates) - triage_needed} triage={triage_needed}")


if __name__ == "__main__":
    main()
