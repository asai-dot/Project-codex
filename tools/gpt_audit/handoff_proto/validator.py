"""HEAD_HAND handoff — fixture-bound prototype validator (offline, pure).

Scope: schema validation + 3-axis effect derivation + fail-closed dispatch
gating + JCS-style packet hashing + per-attempt reconciliation.

NON-scope (HOLD): no external calls, no queue/ledger/Box writes, no file moves,
no operational dispatch. This module computes verdicts over in-memory packets
only. The normative source is HANDOFF_SCHEMA_APPENDIX_v0.5_20260619.md.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from typing import Any

# --- enums (appendix §1.1) ---
ASSIGNEES = {"local", "codex", "worker_cc"}
ASSIGNEE_FORBIDDEN = {"gpt", "gpt_pro", "claudehead", "head", "auditor", "owner"}
EXECUTION_ROLES = {"worker", "deterministic"}
MUTATION_FLAGS = {
    "persistent_write",
    "shared_namespace_write",
    "file_move",
    "external_write",
    "destructive",
    "production_effect",
}
RESOURCE_PERMIT_CLASSES = {"quota_metered", "paid", "rate_limited"}
# integrity-required gates (appendix §0 registry)
INTEGRITY_REQUIRED_GATES = {"owner_gated", "auditor_gated", "production", "canonical"}

# fields excluded from packet_hash (appendix §6). runtime_envelope is a single
# object whose entire contents are out-of-hash; packet_hash itself is excluded.
HASH_EXCLUDED_TOP_FIELDS = {"packet_hash", "runtime_envelope"}


@dataclass
class Env:
    """Subsystem availability + policy registries for a validation run."""

    lease_subsystem_available: bool = False
    resource_permit_subsystem_available: bool = False
    audit_permit_available: bool = False
    data_access_registry: set[str] = field(
        default_factory=lambda: {"internal", "public", "confidential"}
    )
    egress_allowlist: set[str] = field(default_factory=lambda: {"public_query"})
    # lease subsystem (LEASE_SUBSYSTEM_DESIGN_v0.5 §4). None until a mutating
    # dispatch packet is evaluated with the lease lane enabled; the full G0..L
    # gate lives in lease.validate_mutating_dispatch. Default None keeps the
    # operational rollout boundary closed (mutating still blocks fail-closed).
    lease_ctx: Any = None


@dataclass
class Verdict:
    dispatchable: bool
    result_status: str  # done-equivalent "dispatchable" | "blocked"
    block_reason: str | None
    mutation_class: str
    egress_decision: str
    resource_effect_class: str
    errors: list[str] = field(default_factory=list)


class ValidationError(ValueError):
    """Raised for hard schema violations that are not a dispatch 'block'."""


# --- 3-axis derivation (appendix §4) ---
def derive_mutation_class(packet: dict[str, Any]) -> str:
    if packet.get("result_artifact_exception") is True:
        # §4.2 — unique RESULT body transport write only.
        return "non_mutating"
    flags = set(packet.get("side_effect_flags", []) or [])
    return "mutating" if flags & MUTATION_FLAGS else "non_mutating"


def derive_resource(packet: dict[str, Any]) -> tuple[str, bool]:
    rd = packet.get("resource_descriptor") or {}
    cls = rd.get("resource_effect_class", packet.get("resource_effect_class", "none"))
    if cls is None:
        cls = "none"
    # §4.5 MF-2C: unknown free bound falls to permit-required side.
    if cls == "free_bounded" and rd.get("bounds_known") is False:
        cls = "rate_limited"
    permit_required = cls in RESOURCE_PERMIT_CLASSES
    return cls, permit_required


def derive_egress(packet: dict[str, Any], env: Env) -> str:
    desc = packet.get("egress_descriptor")
    if desc is None:
        return "none"
    payload = desc.get("outbound_payload_class")
    # confidential payload to external is blocked unless explicitly allowed.
    if payload == "confidential" and not desc.get("explicit_allow", False):
        return "blocked"

    def _eval(dclass: str | None) -> str:
        if dclass in env.egress_allowlist:
            return "allowed"
        # unknown destination → safe side (appendix §4: unknown egress blocked).
        return "blocked"

    decision = _eval(desc.get("destination_class"))
    # §7 should_fix: public GET redirect is re-evaluated against the allowlist.
    redirect = desc.get("redirect_to")
    if decision == "allowed" and redirect is not None:
        return _eval(redirect.get("destination_class"))
    return decision


# old `patch` -> v0.5 next_action_type migration (WORKER_DELEGATION v0.2 §3).
PATCH_MIGRATION = {
    "patch": "design_patch",  # default; doc stays worker_cc
    "design_patch": "design_patch",
    "doc_patch": "doc_patch",
    "code_patch": "code_patch",
    "test_patch": "test_patch",
    "refactor": "refactor",
}


def migrate_next_action_type(old: str, *, code_like: bool = False) -> str:
    """Map a legacy `patch` to the v0.5 enum. code_like routes to code_patch."""
    if old == "patch":
        return "code_patch" if code_like else "design_patch"
    return PATCH_MIGRATION.get(old, old)



# --- JCS-style canonicalization + packet hash (appendix §6) ---
def _nfc(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, dict):
        return {_nfc(k): _nfc(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_nfc(v) for v in value]
    return value


def canonical_hash_payload(packet: dict[str, Any]) -> dict[str, Any]:
    """Allowlist basis: drop excluded top-level fields, NFC-normalize."""
    body = {k: v for k, v in packet.items() if k not in HASH_EXCLUDED_TOP_FIELDS}
    return _nfc(body)


def compute_packet_hash(packet: dict[str, Any]) -> str:
    payload = canonical_hash_payload(packet)
    # JCS approximation: sorted keys, no whitespace, UTF-8, LF-only.
    canon = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    digest = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


# --- dispatch validation (appendix §3/§4/§7, head_hand §9.3) ---
def validate_dispatch(packet: dict[str, Any], env: Env | None = None) -> Verdict:
    env = env or Env()
    mutation = derive_mutation_class(packet)
    resource_cls, permit_required = derive_resource(packet)
    egress = derive_egress(packet, env)

    def block(reason: str) -> Verdict:
        return Verdict(False, "blocked", reason, mutation, egress, resource_cls)

    # ratify is never a dispatch packet (§1.2)
    if packet.get("next_action_type") == "ratify":
        return block("ratify_not_dispatchable")

    # invalid assignee → hard validation error, no silent fallback (§7)
    assignee = packet.get("assignee")
    if assignee in ASSIGNEE_FORBIDDEN or assignee not in ASSIGNEES:
        return block("invalid_assignee")

    # execution_role must be worker|deterministic (§1.2)
    if packet.get("execution_role") not in EXECUTION_ROLES:
        return block("invalid_assignee")

    # data_access_class unknown → dispatch forbidden (§7)
    dac = packet.get("data_access_class")
    if dac not in env.data_access_registry:
        return block("access_class_unknown")

    # assignee not in allowed_assignees → incompatible (§7)
    allowed = set(packet.get("allowed_assignees", list(ASSIGNEES)))
    if assignee not in allowed:
        return block("assignee_incompatible")

    # mutating lane (§4.4 fail-closed; full gate in LEASE_SUBSYSTEM_DESIGN v0.5).
    # G0: no lease subsystem → blocked. Otherwise delegate the G_schema..L gate
    # sequence to the single lease implementation. Operational rollout stays HOLD
    # (Env defaults leave lease_subsystem_available False).
    if mutation == "mutating":
        if not env.lease_subsystem_available:
            return block("lease_required_but_unavailable")
        from lease import validate_mutating_dispatch

        reason = validate_mutating_dispatch(packet, env.lease_ctx)
        if reason is not None:
            return block(reason)

    # resource permit required ∧ no permit subsystem → blocked (§4.5 fail-closed)
    if permit_required and not env.resource_permit_subsystem_available:
        return block("resource_permit_unavailable")

    # egress blocked (§4.3/§7)
    if egress == "blocked":
        return block("egress_forbidden")

    # audit-sensitive requires permit (§4.5 MF-2B)
    if packet.get("external_audit_logging") == "sensitive" and not env.audit_permit_available:
        return block("resource_permit_unavailable")

    # oversize without reason (§8)
    if packet.get("_oversize", False) and not packet.get("oversize_reason"):
        return block("oversize_no_reason")

    # source digest unavailable on integrity-required gate → blocked (§6)
    gate = packet.get("gate")
    if gate in INTEGRITY_REQUIRED_GATES:
        for art in packet.get("source_artifacts", []) or []:
            if art.get("hash_status") == "unavailable":
                return block("stale_packet")

    return Verdict(True, "dispatchable", None, mutation, egress, resource_cls)


# --- per-attempt reconciliation (appendix §5.2) ---
RECONCILIATION_RELATIONS = {
    "representative",
    "duplicate",
    "stale_generation",
    "invalid",
    "conflict",
}


def _grouping_key(attempt: dict[str, Any]) -> tuple:
    return (
        attempt["source_queue_item_id"],
        attempt["packet_generation"],
        attempt["packet_hash"],
    )


def _weak_equivalent(valid: list[dict[str, Any]]) -> bool:
    """§5.4 weak equivalence: identical acceptance-pass set and outputs set
    across all valid attempts, despite differing output_hash."""
    acc_sets = {frozenset(a.get("acceptance_set", [])) for a in valid}
    out_sets = {frozenset(a.get("outputs_set", [])) for a in valid}
    if len(valid) < 2:
        return False
    return len(acc_sets) == 1 and len(out_sets) == 1 and acc_sets != {frozenset()}


def select_active_generation(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    """§5.3 — within one source_queue_item_id, the highest packet_generation is
    active; older generations are stale_generation (not stale_packet, which is a
    dispatch-time digest failure). Returns {active: [...], stale_generation: [...]}.
    """
    if not attempts:
        return {"active": [], "stale_generation": []}
    sqis = {a["source_queue_item_id"] for a in attempts}
    if len(sqis) != 1:
        raise ValidationError("select_active_generation needs one source_queue_item_id")
    newest = max(a["packet_generation"] for a in attempts)
    active = [a for a in attempts if a["packet_generation"] == newest]
    stale = [a for a in attempts if a["packet_generation"] != newest]
    return {"active": active, "stale_generation": stale}


def reconcile(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a local-only reconciliation event for one grouping.

    Each attempt dict carries: attempt_id, source_queue_item_id,
    packet_generation, packet_hash, acceptance_pass (bool), evidence_complete
    (bool), output_hash, recorded_at, schema_valid (bool).
    """
    if not attempts:
        raise ValidationError("reconcile requires >=1 attempt")
    keys = {_grouping_key(a) for a in attempts}
    if len(keys) != 1:
        raise ValidationError("attempts span multiple groupings; split first")

    relations: list[dict[str, Any]] = []
    valid = [a for a in attempts if a.get("schema_valid", True) and a.get("acceptance_pass")]

    representative_id: str | None = None
    needs_head = False
    rep_basis: str | None = None

    if valid:
        hashes = {a.get("output_hash") for a in valid}
        if len(hashes) == 1:
            # exact equivalence → earliest valid is representative
            representative_id = min(valid, key=lambda a: a["recorded_at"])["attempt_id"]
            rep_basis = "exact_equivalence"
        elif _weak_equivalent(valid):
            # §5.4 weak equivalence: same acceptance-pass set + same outputs set.
            # should_fix: weak equivalence must be tagged in basis_codes.
            representative_id = min(valid, key=lambda a: a["recorded_at"])["attempt_id"]
            rep_basis = "weak_equivalence"
        else:
            complete = [a for a in valid if a.get("evidence_complete")]
            if len(complete) == 1:
                representative_id = complete[0]["attempt_id"]
                rep_basis = "evidence_complete"
            else:
                # valid but semantically conflicting → head resolution
                needs_head = True
    else:
        needs_head = True  # all-invalid → head resolution (§5.2)

    for a in attempts:
        aid = a["attempt_id"]
        if aid == representative_id:
            rel, related = "representative", None
        elif not a.get("schema_valid", True) or not a.get("acceptance_pass"):
            rel, related = "invalid", None
        elif representative_id is not None and a.get("output_hash") == next(
            x.get("output_hash") for x in valid if x["attempt_id"] == representative_id
        ):
            rel, related = "duplicate", representative_id
        elif representative_id is None:
            rel, related = "conflict", None
        else:
            rel, related = "duplicate", representative_id

        basis_codes = list(a.get("basis_codes", []))
        if aid == representative_id and rep_basis and rep_basis not in basis_codes:
            basis_codes.append(rep_basis)

        relations.append(
            {
                "attempt_id": aid,
                "relation": rel,
                "related_to_attempt_id": related,
                "basis_codes": basis_codes,
                "acceptance_grade": "pass" if a.get("acceptance_pass") else "fail",
                "output_hash_state": _output_hash_state(a, representative_id, valid),
            }
        )

    g = attempts[0]
    return {
        "reconciliation_id": f"REC_{g['source_queue_item_id']}_{g['packet_generation']}",
        "grouping_key": "+".join(str(x) for x in _grouping_key(g)),
        "source_queue_item_id": g["source_queue_item_id"],
        "packet_generation": g["packet_generation"],
        "packet_hash": g["packet_hash"],
        "attempt_relations": relations,
        "representative_attempt_id": representative_id,  # nullable
        "needs_head_resolution": needs_head,
        "recorded_at": max(a["recorded_at"] for a in attempts),
    }


def _output_hash_state(attempt, representative_id, valid) -> str:
    if attempt.get("output_hash") is None:
        return "absent"
    if representative_id is None:
        return "divergent"
    rep_hash = next(
        x.get("output_hash") for x in valid if x["attempt_id"] == representative_id
    )
    return "matches_representative" if attempt.get("output_hash") == rep_hash else "divergent"
