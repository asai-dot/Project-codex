"""xdoc_method — DD-XDOC-001 v0.8 §8（method registry / capability 検査）。

依存ゼロ・read-only 純関数。受入試験7（CDC 単独→relation=[]、CDC+content_hash→
segment_identity_candidate のみ）と nb1（companion unique/registry存在/facet互換）・
nb2（method_capability_rule_id exactly-one）・determinism equality（B18）を機械証明する。

参照: docs/dd_candidates/DD-XDOC-001_..._v0.8_20260623.md §5,§8
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    from . import xdoc_canonical as _xc
except ImportError:  # pragma: no cover
    import xdoc_canonical as _xc

DETERMINISTIC = "deterministic"
NONDETERMINISTIC = "nondeterministic"


class MethodValidationError(ValueError):
    pass


def method_registry_id(method_id: str, version: str) -> str:
    return _xc.sha256_hex(_xc.canonical_json({"method_id": method_id, "version": version}))


@dataclass(frozen=True)
class MethodRegistryEntry:
    method_id: str
    version: str
    facet: str
    method_determinism: str
    emits_candidate_relation: bool
    allowed_non_candidate_assertion_types: tuple
    prohibited_assertion_types: tuple

    @property
    def registry_id(self) -> str:
        return method_registry_id(self.method_id, self.version)


@dataclass(frozen=True)
class CapabilityRule:
    rule_id: str
    primary_method_registry_id: str
    required_companion_method_registry_ids: tuple
    allowed_comparison_intents: tuple
    allowed_candidate_relation_types: tuple
    specificity: int  # nb2: most-specific 選択用


class MethodRegistry:
    def __init__(self):
        self._by_id: Dict[str, MethodRegistryEntry] = {}
        self._rules: List[CapabilityRule] = []

    def register(self, e: MethodRegistryEntry) -> str:
        self._by_id[e.registry_id] = e
        return e.registry_id

    def add_rule(self, r: CapabilityRule) -> None:
        self._rules.append(r)

    def get(self, registry_id: str) -> Optional[MethodRegistryEntry]:
        return self._by_id.get(registry_id)

    def rule(self, rule_id: str) -> Optional[CapabilityRule]:
        return next((r for r in self._rules if r.rule_id == rule_id), None)

    def select_rule(self, primary_id: str, applied_companions: List[str]) -> CapabilityRule:
        """nb2: 適用可能 rule のうち most-specific を一意選択。同点は validation error。"""
        applied = set(applied_companions)
        cands = [
            r for r in self._rules
            if r.primary_method_registry_id == primary_id
            and set(r.required_companion_method_registry_ids) <= applied
        ]
        if not cands:
            raise MethodValidationError("適用可能な capability rule が無い")
        top = max(r.specificity for r in cands)
        winners = [r for r in cands if r.specificity == top]
        if len(winners) != 1:
            raise MethodValidationError("most-specific rule が一意でない（specificity 同点）")
        return winners[0]


@dataclass
class AlignmentMethodFields:
    facet: str
    primary_method_registry_id: str
    applied_companion_method_registry_ids: List[str]
    method_capability_rule_id: str
    candidate_relation_types: List[str]
    comparison_intent: str
    method_determinism: str
    result_payload_digest: Optional[str] = None


def _facet_compatible(reg_facet: str, align_facet: str) -> bool:
    # 既定: 同一 facet のみ互換（cross-facet は registry 宣言で別途許可）
    return reg_facet == align_facet


def validate_capability(a: AlignmentMethodFields, reg: MethodRegistry) -> None:
    """§8 G_XDOC_METHOD_CAPABILITY_DECLARED の5条件 + nb1 + determinism equality。違反は raise。"""
    primary = reg.get(a.primary_method_registry_id)
    if primary is None:
        raise MethodValidationError("primary method が registry に無い")

    # nb1: companion unique / registry 存在 / facet 互換
    if len(a.applied_companion_method_registry_ids) != len(set(a.applied_companion_method_registry_ids)):
        raise MethodValidationError("applied companion は unique set")
    for cid in a.applied_companion_method_registry_ids:
        ce = reg.get(cid)
        if ce is None:
            raise MethodValidationError(f"companion {cid} が registry に無い")
        if not _facet_compatible(ce.facet, a.facet):
            raise MethodValidationError(f"companion facet 非互換: {ce.facet} vs {a.facet}")

    # B18: determinism equality + nondeterministic → digest 必須
    if a.method_determinism != primary.method_determinism:
        raise MethodValidationError("method_determinism は primary registry と一致必須")
    require_digest = primary.method_determinism == NONDETERMINISTIC or any(
        reg.get(c).method_determinism == NONDETERMINISTIC
        for c in a.applied_companion_method_registry_ids
    )
    if require_digest and not a.result_payload_digest:
        raise MethodValidationError("nondeterministic は result_payload_digest 必須")

    # capability rule 5条件
    rule = reg.rule(a.method_capability_rule_id)
    if rule is None:
        raise MethodValidationError("method_capability_rule_id が registry に無い")
    if rule.primary_method_registry_id != a.primary_method_registry_id:
        raise MethodValidationError("rule.primary != alignment.primary")
    if not set(rule.required_companion_method_registry_ids) <= set(a.applied_companion_method_registry_ids):
        raise MethodValidationError("required companion ⊄ applied（受入試験7）")
    if not set(a.candidate_relation_types) <= set(rule.allowed_candidate_relation_types):
        raise MethodValidationError("candidate_relation_types ⊄ allowed")
    if a.comparison_intent not in rule.allowed_comparison_intents:
        raise MethodValidationError("comparison_intent ∉ allowed_comparison_intents")


# ---- 既定 registry（v0.8 §8 の表を構築するヘルパ） --------------------------------
def build_default_registry() -> MethodRegistry:
    reg = MethodRegistry()
    cdc = MethodRegistryEntry("CDC", "v1", "text", DETERMINISTIC, False, ("boundary_segmentation",), ("segment_identity_standalone",))
    chash = MethodRegistryEntry("content_hash", "v1", "text", DETERMINISTIC, True, (), ("standalone_use",))
    reg.register(cdc)
    reg.register(chash)
    reg.add_rule(CapabilityRule(
        "R-CDC-STANDALONE", cdc.registry_id, (), ("text_reuse",), (), specificity=0))
    reg.add_rule(CapabilityRule(
        "R-CDC-HASH", cdc.registry_id, (chash.registry_id,),
        ("text_reuse", "near_duplicate"), ("segment_identity_candidate",), specificity=1))
    return reg
