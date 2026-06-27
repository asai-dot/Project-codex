"""Lease subsystem — offline, pure validator for the mutating dispatch lane.

Normative source: LEASE_SUBSYSTEM_DESIGN_v0.5_20260625.md
(GPT Pro re-audit result 2312201353719 = LEASE_PASS_WITH_NOTES, owner-ratified
2026-06-27). This module implements §4 (the G0..L gate sequence), the §1.5/§1.6
ledger view (event sourcing + record-hash chain + HMAC), and §2/§3 binding
(typed args, payload digest, exact lease set, authorization registry).

SCOPE (what this computes): the *decision* "may a mutating dispatch card be
emitted" — up to and including dispatchability. NON-SCOPE / HOLD (separate
gate): feature-flag rollout, operational grant/release/revoke, real Box
mutation, external/paid/quota/egress, DB/DDL, canonical, Salesforce writeback,
card->mutation auto-chaining. Nothing here performs I/O, writes, or Box calls;
every input (ledger events, Box current state, policy registry, trusted
holder/principal, now_utc) is injected via LeaseContext for deterministic
offline evaluation.

§10 binding notes (PASS_WITH_NOTES conditions) realized here:
  - payload digest target bytes + canonicalization fixed (canonical_digest, JCS).
  - immutable_payload_ref binds ref version/hash into the packet hash basis.
  - expected_etag_or_sequence required for mutable objects (G2).
  - authorization sourced from an injected policy registry, never hardcoded (GA).
  - unratified target schema cannot emit a card (G_schema).
  - HMAC key id/version/algorithm + old-key read-only verify + fetch-fail block.
  - §8 pre-execution re-verification is a forward contract (documented, not run).
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

GENESIS_PRIOR = "sha256:genesis"
BOX_STABLE_ID = re.compile(r"^box:(file|folder):[0-9]+$")

# event-sourcing states (§1.5)
LEASE_EVENT_TYPES = {"grant", "release", "revoke"}
GRANT_ONLY_FIELDS = {"canonical_target_key", "scope", "holder", "granted_at", "expires_at"}


# --- canonicalization + digest (§2.2 payload digest, §6 packet hash basis) ---
def _nfc(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, dict):
        return {_nfc(k): _nfc(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_nfc(v) for v in value]
    return value


def _canon(obj: Any) -> str:
    """JCS approximation: NFC, sorted keys, no whitespace, UTF-8, LF-only."""
    return json.dumps(
        _nfc(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def canonical_digest(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()


def _parse_utc(ts: str) -> datetime:
    # tz-aware UTC; accept trailing Z. (§5 storage is UTC tz-aware.)
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


# --- operation registry (§2.1/§2.2): op -> content hash + derivations ----------
def _domains_box_file_move(args: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"canonical_target_key": f"box:file:{args['source_file_id']}", "scope": "move"},
        {
            "canonical_target_key": f"box:folder:{args['destination_parent_id']}",
            "scope": "child_insert",
        },
    ]


def _domains_box_metadata_set(args: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "canonical_target_key": f"box:{args['target_item_type']}:{args['target_item_id']}",
            "scope": "metadata_write",
        }
    ]


def _domains_box_file_rename(args: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"canonical_target_key": f"box:file:{args['target_item_id']}", "scope": "rename"}
    ]


def _scopes_box_file_move(args: dict[str, Any]) -> list[str]:
    return ["box.file.move", "box.folder.child_insert"]


def _scopes_box_metadata_set(args: dict[str, Any]) -> list[str]:
    return ["box.metadata.write"]


def _scopes_box_file_rename(args: dict[str, Any]) -> list[str]:
    return ["box.file.rename"]


@dataclass(frozen=True)
class OpSpec:
    content_hash: str
    required_args: tuple[str, ...]
    # mutable-object expected-state field that must be present (§2.2 / G2)
    expected_state_field: str
    domains: Callable[[dict[str, Any]], list[dict[str, str]]]
    scopes: Callable[[dict[str, Any]], list[str]]
    has_payload: bool


OP_REGISTRY: dict[str, OpSpec] = {
    "box_file_move": OpSpec(
        content_hash="sha256:op_box_file_move_v1",
        required_args=(
            "source_file_id",
            "expected_source_parent_id",
            "destination_parent_id",
            "expected_item_type",
            "expected_source_etag_or_sequence",
        ),
        expected_state_field="expected_source_etag_or_sequence",
        domains=_domains_box_file_move,
        scopes=_scopes_box_file_move,
        has_payload=False,
    ),
    "box_metadata_set": OpSpec(
        content_hash="sha256:op_box_metadata_set_v1",
        required_args=(
            "target_item_type",
            "target_item_id",
            "metadata_template_scope",
            "metadata_template_key",
            "expected_item_type",
            "expected_etag_or_sequence",
        ),
        expected_state_field="expected_etag_or_sequence",
        domains=_domains_box_metadata_set,
        scopes=_scopes_box_metadata_set,
        has_payload=True,
    ),
    "box_file_rename": OpSpec(
        content_hash="sha256:op_box_file_rename_v1",
        required_args=(
            "target_item_id",
            "expected_parent_id",
            "expected_item_type",
            "expected_etag_or_sequence",
        ),
        expected_state_field="expected_etag_or_sequence",
        domains=_domains_box_file_rename,
        scopes=_scopes_box_file_rename,
        has_payload=True,
    ),
}


def required_lock_domains(op: str, args: dict[str, Any]) -> list[dict[str, str]]:
    """Pure (§1.3): typed args -> canonical-sorted lock domains."""
    spec = OP_REGISTRY[op]
    return sorted(spec.domains(args), key=lambda d: (d["canonical_target_key"], d["scope"]))


def derive_required_scopes(op: str, args: dict[str, Any]) -> list[str]:
    return sorted(OP_REGISTRY[op].scopes(args))


# --- authorization registry (§3): injected, never hardcoded -------------------
@dataclass
class PolicyRegistry:
    current_version: str
    # set of (principal, op) tuples that are ALLOW; default deny otherwise.
    allow: set[tuple[str, str]] = field(default_factory=set)

    def authorize(self, principal: str, op: str, domains: list[dict[str, str]]) -> bool:
        return (principal, op) in self.allow


# --- ledger view (§1.5 event sourcing, §1.6 atomicity/HMAC) -------------------
def sign_event(event: dict[str, Any], key: bytes) -> str:
    """HMAC over canonical JSON excluding hmac/record_hash (§1.6)."""
    body = {k: v for k, v in event.items() if k not in {"hmac", "record_hash"}}
    return _hmac.new(key, _canon(body).encode("utf-8"), hashlib.sha256).hexdigest()


def _record_hash(event: dict[str, Any]) -> str:
    body = {k: v for k, v in event.items() if k != "record_hash"}
    return canonical_digest(body)


def build_chain(
    raw_events: list[dict[str, Any]],
    *,
    key: bytes,
    key_id: str = "k1",
    key_version: str = "v1",
) -> list[dict[str, Any]]:
    """Test/builder helper: link genesis->tail, fill sequence_no, ordinal,
    prior_event_hash, hmac, record_hash for a list of partial events.
    Each raw event carries at least lease_event_type, lease_id, and grant fields.
    """
    out: list[dict[str, Any]] = []
    prior = GENESIS_PRIOR
    ordinals: dict[str, int] = {}
    for i, raw in enumerate(raw_events, start=1):
        ev = dict(raw)
        ev.setdefault("lease_event_id", f"evt-{i:04d}")
        ev["ledger_sequence_no"] = i
        lid = ev["lease_id"]
        ordinals[lid] = ordinals.get(lid, 0) + 1
        ev["lease_event_ordinal"] = ordinals[lid]
        ev["hmac_key_id"] = key_id
        ev["hmac_key_version"] = key_version
        ev["hmac_algorithm"] = "HMAC-SHA256"
        ev["prior_event_hash"] = prior
        ev["hmac"] = sign_event(ev, key)
        ev["record_hash"] = _record_hash(ev)
        prior = ev["record_hash"]
        out.append(ev)
    return out


@dataclass
class LeaseRecord:
    lease_id: str
    canonical_target_key: str
    scope: list[str]
    holder: dict[str, Any]
    expires_at: str
    grant_event_hash: str


class LedgerView:
    """Validated fold over an append-only event log (§1.5)."""

    def __init__(self, valid: bool, invalid_reason: str | None,
                 active: dict[str, LeaseRecord]):
        self._valid = valid
        self._invalid_reason = invalid_reason
        self._active = active

    @property
    def valid(self) -> bool:
        return self._valid

    @property
    def invalid_reason(self) -> str | None:
        return self._invalid_reason

    def chain_ok(self) -> bool:
        return self._valid

    def active_for(self, canonical_target_key: str, scope: str) -> list[LeaseRecord]:
        if not self._valid:
            return []
        return [
            r for r in self._active.values()
            if r.canonical_target_key == canonical_target_key and scope in r.scope
        ]


def build_ledger_view(
    events: list[dict[str, Any]],
    *,
    hmac_keys: dict[tuple[str, str], bytes],
    partial_tail: bool = False,
) -> LedgerView:
    """Verify chain + HMAC + transitions, then fold to active records.

    `partial_tail=True` models a torn trailing line (§1.6): block, do not fold.
    Returns an *invalid* view (chain_ok()==False) on any integrity failure so the
    gate fails closed at G_chain.
    """
    if partial_tail:
        return LedgerView(False, "ledger_partial_tail", {})

    states: dict[str, str] = {}  # lease_id -> absent/active/terminal
    active: dict[str, LeaseRecord] = {}
    prior = GENESIS_PRIOR
    last_seq = 0
    last_ordinal: dict[str, int] = {}

    for ev in events:
        et = ev.get("lease_event_type")
        if et not in LEASE_EVENT_TYPES:
            return LedgerView(False, "lease_event_invalid_transition", {})

        # HMAC key availability + verification (§1.6)
        key = hmac_keys.get((ev.get("hmac_key_id"), ev.get("hmac_key_version")))
        if key is None:
            return LedgerView(False, "hmac_key_unavailable", {})
        if not _hmac.compare_digest(sign_event(ev, key), ev.get("hmac", "")):
            return LedgerView(False, "ledger_hmac_mismatch", {})

        # record-hash recomputation + prior-link chain (genesis -> tail)
        if _record_hash(ev) != ev.get("record_hash"):
            return LedgerView(False, "ledger_record_hash_mismatch", {})
        if ev.get("prior_event_hash") != prior:
            return LedgerView(False, "ledger_fork", {})

        # global sequence: strictly +1 (gap/fork -> block)
        if ev.get("ledger_sequence_no") != last_seq + 1:
            return LedgerView(False, "ledger_sequence_gap", {})

        lid = ev["lease_id"]
        # per-lease ordinal: strictly +1
        if ev.get("lease_event_ordinal") != last_ordinal.get(lid, 0) + 1:
            return LedgerView(False, "ledger_ordinal_gap", {})

        cur = states.get(lid, "absent")
        if et == "grant":
            # grant-only fields required; transition absent -> active
            if cur != "absent" or not GRANT_ONLY_FIELDS.issubset(ev.keys()):
                return LedgerView(False, "lease_event_invalid_transition", {})
            states[lid] = "active"
            active[lid] = LeaseRecord(
                lease_id=lid,
                canonical_target_key=ev["canonical_target_key"],
                scope=list(ev["scope"]),
                holder=ev["holder"],
                expires_at=ev["expires_at"],
                grant_event_hash=ev["record_hash"],
            )
        else:  # release / revoke: active -> terminal; grant-only fields forbidden
            if cur != "active" or (GRANT_ONLY_FIELDS & ev.keys()):
                return LedgerView(False, "lease_event_invalid_transition", {})
            states[lid] = "terminal"
            active.pop(lid, None)

        prior = ev["record_hash"]
        last_seq = ev["ledger_sequence_no"]
        last_ordinal[lid] = ev["lease_event_ordinal"]

    return LedgerView(True, None, active)


# --- lease context (everything injected; pure offline) -----------------------
@dataclass
class LeaseContext:
    schema_pins: set[tuple[str, str, str]]  # ratified (id, version, hash)
    op_registry: dict[str, OpSpec]
    ledger_view: LedgerView
    policy: PolicyRegistry
    box_state: dict[str, dict[str, Any]]  # canonical_target_key -> current state
    trusted_holder: dict[str, Any]
    trusted_principal: str
    now_utc: str


# --- §4 gate (single implementation, fail-closed) ----------------------------
def validate_mutating_dispatch(packet: dict[str, Any], ctx: LeaseContext) -> str | None:
    """Return a block reason (str) or None if dispatchable. Order = §4.

    G0 (lease_subsystem_available) is enforced by the caller in validator.py;
    a missing ctx is treated as unavailable here as a defensive fail-closed.
    """
    if ctx is None:
        return "lease_required_but_unavailable"

    # G_schema — unratified target schema cannot emit a card
    pin = (
        packet.get("target_schema_id"),
        packet.get("target_schema_version"),
        packet.get("target_schema_hash"),
    )
    if pin not in ctx.schema_pins:
        return "target_schema_unratified"

    # G1 — operation registry
    op = packet.get("mutation_op")
    spec = ctx.op_registry.get(op)
    if spec is None:
        return "mutation_op_unknown"
    if packet.get("mutation_op_content_hash") != spec.content_hash:
        return "mutation_op_registry_mismatch"

    # G2 — typed args + expected-state required for mutable objects
    args = packet.get("mutation_args")
    if not isinstance(args, dict) or any(k not in args for k in spec.required_args):
        return "mutation_args_invalid"
    if not args.get(spec.expected_state_field):
        return "expected_state_required"

    # G_args — resolve current Box state (injected) and compare
    if _args_mismatch(op, args, ctx.box_state):
        return "mutation_args_mismatch"

    # G_payload — packet-bound payload digest must match payload bytes
    if spec.has_payload:
        if "mutation_payload" in packet:
            payload_obj: Any = packet["mutation_payload"]
        elif "immutable_payload_ref" in packet:
            # ref version/hash are bound into the packet hash basis (§10 note 1)
            payload_obj = packet["immutable_payload_ref"]
        else:
            return "payload_digest_mismatch"
        if canonical_digest(payload_obj) != packet.get("mutation_payload_digest"):
            return "payload_digest_mismatch"

    # G3 — required scopes (no understatement)
    derived_scopes = derive_required_scopes(op, args)
    declared = packet.get("declared_scopes", [])
    if not set(declared) >= set(derived_scopes):
        return "scope_understated"
    if canonical_digest(derived_scopes) != packet.get("required_scopes_digest"):
        return "scope_understated"

    # G4 — lock domains
    domains = required_lock_domains(op, args)
    if canonical_digest(domains) != packet.get("required_lock_domains_digest"):
        return "lock_domains_digest_mismatch"
    if any(not BOX_STABLE_ID.match(d["canonical_target_key"]) for d in domains):
        return "target_unsupported"

    # G_chain — whole-ledger integrity
    if not ctx.ledger_view.chain_ok():
        return "lease_ledger_tampered"

    # GA — authorization (policy registry, principal from trusted env)
    if packet.get("authz_policy_version") != ctx.policy.current_version:
        return "authz_policy_stale"
    if not ctx.policy.authorize(ctx.trusted_principal, op, domains):
        return "mutation_unauthorized"

    # L0 — exact lease set binding
    refs = packet.get("lease_refs", [])
    sorted_refs = sorted(refs, key=lambda r: (r["canonical_target_key"], r["scope"]))
    keyed = [(r["canonical_target_key"], r["scope"]) for r in refs]
    if refs != sorted_refs or len(set(keyed)) != len(keyed):
        return "lease_refs_duplicate"
    if lease_set_digest(refs) != packet.get("lease_set_digest"):
        return "lease_set_digest_mismatch"
    if {(d["canonical_target_key"], d["scope"]) for d in domains} != set(keyed):
        return "lease_set_incomplete"

    # L — per-ref active-lease checks (canonical order)
    now = _parse_utc(ctx.now_utc)
    for ref in refs:
        actives = ctx.ledger_view.active_for(ref["canonical_target_key"], ref["scope"])
        if len(actives) == 0:
            return "lock_domain_uncovered"
        if len(actives) > 1:
            return "lease_double_active"
        rec = actives[0]
        if rec.lease_id != ref["lease_id"]:
            return "lease_set_mismatch"
        if rec.grant_event_hash != ref["grant_event_hash"]:
            return "lease_ref_stale"
        if now >= _parse_utc(rec.expires_at):
            return "lease_expired"
        if ref["scope"] not in rec.scope:
            return "lease_scope_mismatch"
        if rec.holder != ctx.trusted_holder:  # echo dropped (B17): trusted-env only
            return "lease_holder_mismatch"

    # All gates passed -> mutating dispatchable. The §8 pre-execution
    # re-verification (flag/authz/packet hash/payload digest/Box state/lease_refs/
    # expires_at) is a forward contract for the *next* gate; not run here.
    return None


def lease_set_digest(refs: list[dict[str, Any]]) -> str:
    """Order-independent digest of the exact lease set (§2.3)."""
    return canonical_digest(_ref_digest_basis(refs))


def _ref_digest_basis(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Canonical, order-independent basis for lease_set_digest."""
    return sorted(
        (
            {
                "lease_id": r["lease_id"],
                "canonical_target_key": r["canonical_target_key"],
                "scope": r["scope"],
                "grant_event_hash": r["grant_event_hash"],
            }
            for r in refs
        ),
        key=lambda r: (r["canonical_target_key"], r["scope"]),
    )


def _args_mismatch(op: str, args: dict[str, Any], box_state: dict[str, dict]) -> bool:
    if op == "box_file_move":
        key = f"box:file:{args['source_file_id']}"
        cur = box_state.get(key)
        if cur is None:
            return True
        return (
            cur.get("item_type") != args["expected_item_type"]
            or cur.get("parent_id") != args["expected_source_parent_id"]
            or cur.get("etag") != args["expected_source_etag_or_sequence"]
        )
    if op == "box_metadata_set":
        key = f"box:{args['target_item_type']}:{args['target_item_id']}"
        cur = box_state.get(key)
        if cur is None:
            return True
        return (
            cur.get("item_type") != args["expected_item_type"]
            or cur.get("etag") != args["expected_etag_or_sequence"]
        )
    if op == "box_file_rename":
        key = f"box:file:{args['target_item_id']}"
        cur = box_state.get(key)
        if cur is None:
            return True
        return (
            cur.get("item_type") != args["expected_item_type"]
            or cur.get("parent_id") != args["expected_parent_id"]
            or cur.get("etag") != args["expected_etag_or_sequence"]
        )
    return True
