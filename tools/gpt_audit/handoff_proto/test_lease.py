"""Offline negative/positive fixtures for the lease mutating-dispatch gate.

Normative: LEASE_SUBSYSTEM_DESIGN_v0.5_20260625.md §4/§7 (GPT Pro
LEASE_PASS_WITH_NOTES, result 2312201353719). Pure offline: no I/O, no Box, no
writes. Each negative perturbs exactly one field of a known-good reference case
so digests stay correct and the asserted block_reason is the only cause.

Run from this dir:  python -m unittest test_lease
"""

from __future__ import annotations

import copy
import unittest

import lease
from lease import (
    LeaseContext,
    OP_REGISTRY,
    PolicyRegistry,
    build_chain,
    build_ledger_view,
    canonical_digest,
    derive_required_scopes,
    lease_set_digest,
    required_lock_domains,
    validate_mutating_dispatch,
)
from validator import Env, validate_dispatch

KEY = b"unit-test-hmac-key"
KEYS = {("k1", "v1"): KEY}
HOLDER = {"assignee": "codex", "machine_id": "m1", "runner_instance_id": "r1"}
PRINCIPAL = "svc:codex-mutator"
SCHEMA_PIN = ("handoff-dispatch-mutating", "0.5", "sha256:schema_patch_v05")
FUTURE = "2026-12-31T00:00:00Z"
NOW = "2026-06-27T00:00:00Z"

# generic HANDOFF packet fields so the upstream validate_dispatch checks pass.
BASE_PACKET = {
    "next_action_type": "code_patch",
    "assignee": "codex",
    "execution_role": "worker",
    "data_access_class": "internal",
}


def _grant(lease_id, key, scope, holder=None, expires=FUTURE):
    return {
        "lease_event_type": "grant",
        "lease_id": lease_id,
        "canonical_target_key": key,
        "scope": list(scope),
        "holder": holder or HOLDER,
        "granted_at": NOW,
        "expires_at": expires,
    }


def _release(lease_id):
    return {"lease_event_type": "release", "lease_id": lease_id}


def _view(raw_events, **kw):
    return build_ledger_view(build_chain(raw_events, key=KEY), hmac_keys=KEYS, **kw)


def _resign(ev, *, prior=None):
    """Re-seal one event after tampering: hmac first (signs body), then
    record_hash (covers hmac). Lets a test isolate one downstream check."""
    if prior is not None:
        ev["prior_event_hash"] = prior
    ev.pop("record_hash", None)
    ev["hmac"] = lease.sign_event(ev, KEY)
    ev["record_hash"] = lease._record_hash(ev)


def _ctx(view, *, policy=None, box_state=None, holder=None, principal=PRINCIPAL,
         now=NOW, schema_pins=None):
    return LeaseContext(
        schema_pins=schema_pins if schema_pins is not None else {SCHEMA_PIN},
        op_registry=OP_REGISTRY,
        ledger_view=view,
        policy=policy or PolicyRegistry("p1", {(PRINCIPAL, "box_metadata_set"),
                                              (PRINCIPAL, "box_file_move")}),
        box_state=box_state or {},
        trusted_holder=holder or HOLDER,
        trusted_principal=principal,
        now_utc=now,
    )


def reference_metadata_case():
    """A fully valid box_metadata_set dispatch (single domain, with payload)."""
    args = {
        "target_item_type": "file",
        "target_item_id": "111",
        "metadata_template_scope": "enterprise",
        "metadata_template_key": "case",
        "expected_item_type": "file",
        "expected_etag_or_sequence": "etag-1",
    }
    payload = {"field": "status", "value": "active"}
    domains = required_lock_domains("box_metadata_set", args)
    scopes = derive_required_scopes("box_metadata_set", args)
    box_state = {"box:file:111": {"item_type": "file", "parent_id": "900", "etag": "etag-1"}}

    view = _view([_grant("L1", "box:file:111", ["metadata_write"])])
    rec = view.active_for("box:file:111", "metadata_write")[0]
    refs = [{
        "lease_id": "L1",
        "canonical_target_key": "box:file:111",
        "scope": "metadata_write",
        "grant_event_hash": rec.grant_event_hash,
        "expires_at": rec.expires_at,
    }]

    packet = dict(BASE_PACKET)
    packet.update({
        "side_effect_flags": ["persistent_write"],
        "mutation_op": "box_metadata_set",
        "mutation_op_content_hash": OP_REGISTRY["box_metadata_set"].content_hash,
        "mutation_args": args,
        "mutation_payload": payload,
        "mutation_payload_digest": canonical_digest(payload),
        "conflict_policy": "no_overwrite",
        "declared_scopes": list(scopes),
        "required_scopes_digest": canonical_digest(scopes),
        "required_lock_domains_digest": canonical_digest(domains),
        "lease_set_digest": lease_set_digest(refs),
        "authz_policy_id": "policy-mutating",
        "authz_policy_version": "p1",
        "authz_policy_content_hash": "sha256:policy_v1",
        "authenticated_principal": PRINCIPAL,
        "target_schema_id": SCHEMA_PIN[0],
        "target_schema_version": SCHEMA_PIN[1],
        "target_schema_hash": SCHEMA_PIN[2],
        "lease_refs": refs,
    })
    return packet, _ctx(view, box_state=box_state)


def reference_move_case():
    """A valid box_file_move dispatch — two lock domains (source + dest parent)."""
    args = {
        "source_file_id": "111",
        "expected_source_parent_id": "900",
        "destination_parent_id": "950",
        "expected_item_type": "file",
        "expected_source_etag_or_sequence": "etag-1",
    }
    domains = required_lock_domains("box_file_move", args)
    scopes = derive_required_scopes("box_file_move", args)
    box_state = {"box:file:111": {"item_type": "file", "parent_id": "900", "etag": "etag-1"}}

    view = _view([
        _grant("L1", "box:file:111", ["move"]),
        _grant("L2", "box:folder:950", ["child_insert"]),
    ])
    refs = []
    for lid, key, scope in (("L1", "box:file:111", "move"),
                            ("L2", "box:folder:950", "child_insert")):
        rec = view.active_for(key, scope)[0]
        refs.append({
            "lease_id": lid, "canonical_target_key": key, "scope": scope,
            "grant_event_hash": rec.grant_event_hash, "expires_at": rec.expires_at,
        })
    refs.sort(key=lambda r: (r["canonical_target_key"], r["scope"]))

    packet = dict(BASE_PACKET)
    packet.update({
        "side_effect_flags": ["file_move"],
        "mutation_op": "box_file_move",
        "mutation_op_content_hash": OP_REGISTRY["box_file_move"].content_hash,
        "mutation_args": args,
        "conflict_policy": "no_overwrite",
        "declared_scopes": list(scopes),
        "required_scopes_digest": canonical_digest(scopes),
        "required_lock_domains_digest": canonical_digest(domains),
        "lease_set_digest": lease_set_digest(refs),
        "authz_policy_version": "p1",
        "authenticated_principal": PRINCIPAL,
        "target_schema_id": SCHEMA_PIN[0],
        "target_schema_version": SCHEMA_PIN[1],
        "target_schema_hash": SCHEMA_PIN[2],
        "lease_refs": refs,
    })
    return packet, _ctx(view, box_state=box_state)


class TestPositive(unittest.TestCase):
    def test_metadata_dispatchable(self):
        packet, ctx = reference_metadata_case()
        self.assertIsNone(validate_mutating_dispatch(packet, ctx))

    def test_move_dispatchable(self):
        packet, ctx = reference_move_case()
        self.assertIsNone(validate_mutating_dispatch(packet, ctx))

    def test_end_to_end_via_validate_dispatch(self):
        # the whole HANDOFF validator delegates the mutating lane to the gate.
        packet, ctx = reference_metadata_case()
        v = validate_dispatch(packet, Env(lease_subsystem_available=True, lease_ctx=ctx))
        self.assertTrue(v.dispatchable)
        self.assertEqual(v.mutation_class, "mutating")


class TestGateNegatives(unittest.TestCase):
    """One perturbation per negative; asserted reason is the only cause."""

    def _expect(self, mutate, reason, *, move=False):
        packet, ctx = reference_move_case() if move else reference_metadata_case()
        mutate(packet, ctx)
        self.assertEqual(validate_mutating_dispatch(packet, ctx), reason)

    def test_G0_no_ctx(self):
        packet, _ = reference_metadata_case()
        self.assertEqual(validate_mutating_dispatch(packet, None),
                         "lease_required_but_unavailable")

    def test_G_schema_unratified(self):
        self._expect(lambda p, c: c.schema_pins.clear(), "target_schema_unratified")

    def test_G1_op_unknown(self):
        self._expect(lambda p, c: p.__setitem__("mutation_op", "box_nuke"),
                     "mutation_op_unknown")

    def test_G1_op_hash_mismatch(self):
        self._expect(lambda p, c: p.__setitem__("mutation_op_content_hash", "sha256:wrong"),
                     "mutation_op_registry_mismatch")

    def test_G2_args_missing_field(self):
        self._expect(lambda p, c: p["mutation_args"].pop("metadata_template_key"),
                     "mutation_args_invalid")

    def test_G2_expected_state_required(self):
        def mut(p, c):
            p["mutation_args"]["expected_etag_or_sequence"] = ""
        self._expect(mut, "expected_state_required")

    def test_G_args_mismatch_etag(self):
        def mut(p, c):
            c.box_state["box:file:111"]["etag"] = "etag-CHANGED"
        self._expect(mut, "mutation_args_mismatch")

    def test_G_args_mismatch_absent(self):
        self._expect(lambda p, c: c.box_state.clear(), "mutation_args_mismatch")

    def test_G_payload_metadata_value_swap(self):
        # payload values changed but digest left bound to original -> blocked.
        def mut(p, c):
            p["mutation_payload"] = {"field": "status", "value": "DELETED"}
        self._expect(mut, "payload_digest_mismatch")

    def test_G_payload_missing(self):
        self._expect(lambda p, c: p.pop("mutation_payload"), "payload_digest_mismatch")

    def test_G3_scope_understated(self):
        self._expect(lambda p, c: p.__setitem__("declared_scopes", []),
                     "scope_understated")

    def test_G4_lock_domains_digest_mismatch(self):
        self._expect(lambda p, c: p.__setitem__("required_lock_domains_digest", "sha256:x"),
                     "lock_domains_digest_mismatch")

    def test_G_chain_tampered(self):
        # torn trailing line -> invalid view -> fail closed at G_chain.
        def mut(p, c):
            c.ledger_view = build_ledger_view(
                build_chain([_grant("L1", "box:file:111", ["metadata_write"])], key=KEY),
                hmac_keys=KEYS, partial_tail=True)
        self._expect(mut, "lease_ledger_tampered")

    def test_GA_policy_stale(self):
        self._expect(lambda p, c: p.__setitem__("authz_policy_version", "p0"),
                     "authz_policy_stale")

    def test_GA_unauthorized(self):
        self._expect(lambda p, c: setattr(c, "policy", PolicyRegistry("p1", set())),
                     "mutation_unauthorized")

    def test_L0_refs_duplicate(self):
        def mut(p, c):
            p["lease_refs"] = p["lease_refs"] + p["lease_refs"]
        self._expect(mut, "lease_refs_duplicate")

    def test_L0_lease_set_digest_mismatch(self):
        self._expect(lambda p, c: p.__setitem__("lease_set_digest", "sha256:x"),
                     "lease_set_digest_mismatch")

    def test_L0_dest_parent_lease_missing(self):
        # drop the dest-parent ref from a move -> domain set incomplete.
        def mut(p, c):
            p["lease_refs"] = [r for r in p["lease_refs"]
                               if r["canonical_target_key"] != "box:folder:950"]
            p["lease_set_digest"] = lease_set_digest(p["lease_refs"])
        self._expect(mut, "lease_set_incomplete", move=True)

    def test_L_uncovered_after_release(self):
        # lease released in ledger -> no active record for the domain.
        def mut(p, c):
            c.ledger_view = _view([
                _grant("L1", "box:file:111", ["metadata_write"]),
                _release("L1"),
            ])
        self._expect(mut, "lock_domain_uncovered")

    def test_L_double_active(self):
        def mut(p, c):
            c.ledger_view = _view([
                _grant("L1", "box:file:111", ["metadata_write"]),
                _grant("L9", "box:file:111", ["metadata_write"]),
            ])
        self._expect(mut, "lease_double_active")

    def test_L_set_mismatch_lease_id(self):
        # lease_id is in the lease_set_digest basis; recompute the digest so L0
        # passes and the mismatch is caught at the per-ref ledger check (L).
        def mut(p, c):
            p["lease_refs"][0]["lease_id"] = "LX"
            p["lease_set_digest"] = lease_set_digest(p["lease_refs"])
        self._expect(mut, "lease_set_mismatch")

    def test_L_ref_stale_grant_hash(self):
        def mut(p, c):
            p["lease_refs"][0]["grant_event_hash"] = "sha256:stale"
            p["lease_set_digest"] = lease_set_digest(p["lease_refs"])
        self._expect(mut, "lease_ref_stale")

    def test_L_expired_now_equals_expires(self):
        # now_utc == expires_at -> expired (boundary, §5).
        def mut(p, c):
            c.ledger_view = _view([
                _grant("L1", "box:file:111", ["metadata_write"], expires=NOW)])
            rec = c.ledger_view.active_for("box:file:111", "metadata_write")[0]
            p["lease_refs"][0]["grant_event_hash"] = rec.grant_event_hash
            p["lease_refs"][0]["expires_at"] = rec.expires_at
            p["lease_set_digest"] = lease_set_digest(p["lease_refs"])
        self._expect(mut, "lease_expired")

    def test_L_holder_mismatch(self):
        self._expect(lambda p, c: setattr(c, "trusted_holder",
                                          {"runner_instance_id": "OTHER"}),
                     "lease_holder_mismatch")


class TestLedgerIntegrity(unittest.TestCase):
    """§1.5/§1.6 ledger view rejects tampered / malformed logs (invalid view)."""

    def test_valid_chain_ok(self):
        view = _view([_grant("L1", "box:file:1", ["metadata_write"]), _release("L1")])
        self.assertTrue(view.chain_ok())

    def test_hmac_mismatch(self):
        events = build_chain([_grant("L1", "box:file:1", ["metadata_write"])], key=KEY)
        events[0]["holder"] = {"runner_instance_id": "tampered"}  # break signed body
        view = build_ledger_view(events, hmac_keys=KEYS)
        self.assertFalse(view.chain_ok())
        self.assertEqual(view.invalid_reason, "ledger_hmac_mismatch")

    def test_hmac_key_unavailable(self):
        events = build_chain([_grant("L1", "box:file:1", ["metadata_write"])], key=KEY)
        view = build_ledger_view(events, hmac_keys={})
        self.assertEqual(view.invalid_reason, "hmac_key_unavailable")

    def test_fork_broken_prior_link(self):
        events = build_chain([
            _grant("L1", "box:file:1", ["metadata_write"]),
            _release("L1"),
        ], key=KEY)
        _resign(events[1], prior="sha256:wrong")  # valid record_hash, bad prior link
        view = build_ledger_view(events, hmac_keys=KEYS)
        self.assertEqual(view.invalid_reason, "ledger_fork")

    def test_sequence_gap(self):
        events = build_chain([
            _grant("L1", "box:file:1", ["metadata_write"]),
            _release("L1"),
        ], key=KEY)
        events[1]["ledger_sequence_no"] = 5  # prior link stays valid
        _resign(events[1])
        view = build_ledger_view(events, hmac_keys=KEYS)
        self.assertEqual(view.invalid_reason, "ledger_sequence_gap")

    def test_release_before_grant(self):
        view = _view([_release("L1")])
        self.assertEqual(view.invalid_reason, "lease_event_invalid_transition")

    def test_double_release(self):
        view = _view([
            _grant("L1", "box:file:1", ["metadata_write"]),
            _release("L1"),
            _release("L1"),
        ])
        self.assertEqual(view.invalid_reason, "lease_event_invalid_transition")

    def test_grant_only_field_in_release(self):
        events = build_chain([
            _grant("L1", "box:file:1", ["metadata_write"]),
            {"lease_event_type": "release", "lease_id": "L1", "expires_at": FUTURE},
        ], key=KEY)
        view = build_ledger_view(events, hmac_keys=KEYS)
        self.assertEqual(view.invalid_reason, "lease_event_invalid_transition")

    def test_partial_tail(self):
        view = _view([_grant("L1", "box:file:1", ["metadata_write"])], partial_tail=True)
        self.assertEqual(view.invalid_reason, "ledger_partial_tail")


if __name__ == "__main__":
    unittest.main(verbosity=2)
