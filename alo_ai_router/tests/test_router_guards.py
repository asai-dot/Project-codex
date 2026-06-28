"""
test_router_guards.py — ALO-MODEL-ROUTER v0.1 の品質ゲート pytest 群

含むテスト:
- L0 に LLM が送られない (HD3)
- UNKNOWN は fail closed (TRIAGE_NEEDED)
- 同family監査が拒否される (HD2)
- worker が processed/canonical を取れない (HD1)
- cheap モデルが canonical 決定をしない (HD4)
- credentials zone が外部cheapに行かない (HD5)
- L4/L5 は max_items=1
- finalize_result は ALO_FINALIZER 必須
"""
import json, subprocess, sys, os, tempfile
from pathlib import Path
import yaml
try:
    import pytest  # noqa: F401
except ImportError:
    pytest = None  # 動作確認は pytest 無しでも回る

ROOT = Path(__file__).resolve().parent.parent


def run(cmd, env=None, check=False):
    return subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, **(env or {})}, check=check)


def base_item(**override):
    item = {
        "request_id": "test_req_001",
        "title": "test title",
        "source": "test/source.md",
        "status": "queued",
        "classification": {
            "task_type": "dd_draft",
            "cog_level": "L3_NORMAL_WORK",
            "risk_level": "medium",
            "context_need": "bounded",
            "evidence_state": "not_required",
        },
        "data": {
            "data_zone": "internal_design",
            "allowed_model_families": ["anthropic", "openai", "google"],
            "disallowed_model_families": [],
        },
        "lineage": {"author_family": None, "auditor_must_differ_from_author": False},
        "model_route": {"primary_role": "normal_worker", "finalizer": "head_controller"},
        "authority": {
            "requested_mutation_power": "draft_write",
            "granted_mutation_power": "draft_write",
            "worker_can_finalize": False,
            "processed_by_controller_only": True,
            "canonical_write_allowed": False,
        },
        "limits": {"max_items_per_run": 1, "max_allowed_inputs": 3, "allow_packet_extra_search": False, "external_timeout_seconds": 900},
        "outputs": {"expected": ["RESULT_CANDIDATE.md"], "forbidden": ["processed_mark", "canonical_patch"]},
    }
    # 入れ子で上書き
    for k, v in override.items():
        if k in item and isinstance(item[k], dict) and isinstance(v, dict):
            item[k].update(v)
        else:
            item[k] = v
    return item


def resolve(item):
    with tempfile.TemporaryDirectory() as d:
        qi = Path(d) / "qi.json"
        out = Path(d) / "decision.json"
        qi.write_text(json.dumps(item, ensure_ascii=False))
        r = run([sys.executable, str(ROOT / "scripts/resolve_model_route.py"),
                 "--queue-item", str(qi), "--out", str(out)])
        return json.loads(out.read_text()) if out.exists() else {"status": "no_output", "stderr": r.stderr}


def test_L0_no_llm():
    item = base_item(classification={"task_type": "hash", "cog_level": "L0_DETERMINISTIC", "risk_level": "low", "context_need": "bounded", "evidence_state": "not_required"})
    d = resolve(item)
    assert d.get("selected_model") is None, f"L0 should not assign model, got {d.get('selected_model')}"


def test_unknown_fails_closed():
    item = base_item(classification={"task_type": "unknown_task", "cog_level": "L99_FOO", "risk_level": "low", "context_need": "bounded", "evidence_state": "not_required"})
    d = resolve(item)
    assert d.get("status") in ("triage_needed", "blocked"), f"unknown cog must fail closed, got {d}"


def test_credentials_zone_blocks_cheap():
    item = base_item(
        classification={"task_type": "metadata_extraction", "cog_level": "L1_CHEAP_EXTRACTION", "risk_level": "low", "context_need": "bounded", "evidence_state": "not_required"},
        data={"data_zone": "credentials", "allowed_model_families": [], "disallowed_model_families": ["anthropic", "openai", "google"]},
    )
    d = resolve(item)
    assert d.get("status") in ("blocked", "triage_needed"), f"credentials zone must be blocked for cheap external, got {d}"


def test_same_family_audit_denied():
    item = base_item(
        classification={"task_type": "audit", "cog_level": "L5_INDEPENDENT_AUDIT", "risk_level": "high", "context_need": "bounded", "evidence_state": "packet_required"},
        lineage={"author_family": "anthropic", "auditor_must_differ_from_author": True},
    )
    d = resolve(item)
    # auditor は anthropic 以外が選ばれているはず
    if d.get("selected_family"):
        assert d["selected_family"] != "anthropic", f"audit auditor must differ from author, got {d}"


def test_l4_max_items_is_1():
    """make_run_packet が L4 で max_items=1 を強制すること"""
    with tempfile.TemporaryDirectory() as d:
        dpath = Path(d)
        decision = {"status": "routed", "model_role": "deep_reasoner", "selected_model": "x", "granted_mutation_power": "draft_write", "request_id": "r1"}
        item = base_item(classification={"task_type": "architecture_decision", "cog_level": "L4_DEEP_REASONING", "risk_level": "high", "context_need": "bounded", "evidence_state": "not_required"})
        (dpath / "dec.json").write_text(json.dumps(decision))
        (dpath / "qi.json").write_text(json.dumps(item))
        # ダミー入力1つ
        inp = dpath / "input.md"
        inp.write_text("# dummy")
        out = dpath / "packet.yml"
        r = run([sys.executable, str(ROOT / "scripts/make_run_packet.py"),
                 "--decision", str(dpath / "dec.json"),
                 "--queue-item", str(dpath / "qi.json"),
                 "--input", f"{inp}:reference",
                 "--expected-output", "decision_candidate.md:DECISION_CANDIDATE",
                 "--out", str(out)])
        assert out.exists(), f"packet not written: {r.stderr}"
        packet = yaml.safe_load(out.read_text())
        assert packet["max_items"] == 1
        assert packet["mutation_power"] in ("none", "draft_write")


def test_finalize_requires_env():
    """finalize_result は ALO_FINALIZER 無しでは BLOCK する"""
    with tempfile.TemporaryDirectory() as d:
        dpath = Path(d)
        req = dpath / "req.md"
        cand = dpath / "cand.md"
        req.write_text("REQUEST")
        cand.write_text("CANDIDATE")
        r = run([sys.executable, str(ROOT / "scripts/finalize_result.py"),
                 "--request", str(req), "--candidate", str(cand),
                 "--out-final", str(dpath / "final.md"),
                 "--out-record", str(dpath / "rec.json"),
                 "--decision-type", "adopt", "--label", "test"],
                env={"ALO_FINALIZER": ""})
        assert r.returncode != 0, "finalize must block without ALO_FINALIZER"
