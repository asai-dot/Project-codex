"""DD-XDOC-001 v0.8 §8 受入試験7（CDC capability）+ nb1 + determinism。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xdoc_method import (  # noqa: E402
    build_default_registry, method_registry_id, AlignmentMethodFields,
    MethodRegistryEntry, validate_capability, MethodValidationError,
    DETERMINISTIC, NONDETERMINISTIC,
)

CDC = method_registry_id("CDC", "v1")
CHASH = method_registry_id("content_hash", "v1")


def _fields(**over):
    base = dict(
        facet="text", primary_method_registry_id=CDC,
        applied_companion_method_registry_ids=[], method_capability_rule_id="R-CDC-STANDALONE",
        candidate_relation_types=[], comparison_intent="text_reuse",
        method_determinism=DETERMINISTIC, result_payload_digest=None,
    )
    base.update(over)
    return AlignmentMethodFields(**base)


class TestCDCCapability(unittest.TestCase):
    def setUp(self):
        self.reg = build_default_registry()

    def test_07_cdc_standalone_no_segment_identity(self):
        """CDC 単独（applied=[]）で segment_identity_candidate を出そうとすると違反。"""
        a = _fields(method_capability_rule_id="R-CDC-STANDALONE",
                    candidate_relation_types=["segment_identity_candidate"])
        with self.assertRaises(MethodValidationError):
            validate_capability(a, self.reg)

    def test_07_cdc_standalone_empty_ok(self):
        validate_capability(_fields(), self.reg)  # relation=[] は OK

    def test_07_cdc_hash_allows_segment_identity(self):
        """CDC + content_hash（applied に含む）→ R-CDC-HASH → segment_identity_candidate 可。"""
        a = _fields(
            applied_companion_method_registry_ids=[CHASH],
            method_capability_rule_id="R-CDC-HASH",
            candidate_relation_types=["segment_identity_candidate"],
            comparison_intent="near_duplicate",
        )
        validate_capability(a, self.reg)  # 例外なし

    def test_07_cdc_hash_rule_without_companion_fails(self):
        """R-CDC-HASH を当てるが content_hash 未適用 → required ⊄ applied 違反。"""
        a = _fields(
            applied_companion_method_registry_ids=[],
            method_capability_rule_id="R-CDC-HASH",
            candidate_relation_types=["segment_identity_candidate"],
        )
        with self.assertRaises(MethodValidationError):
            validate_capability(a, self.reg)

    def test_select_rule_most_specific(self):
        """companion content_hash があれば most-specific=R-CDC-HASH を一意選択。"""
        r = self.reg.select_rule(CDC, [CHASH])
        self.assertEqual(r.rule_id, "R-CDC-HASH")
        r2 = self.reg.select_rule(CDC, [])
        self.assertEqual(r2.rule_id, "R-CDC-STANDALONE")


class TestCompanionGuards(unittest.TestCase):
    def setUp(self):
        self.reg = build_default_registry()

    def test_duplicate_companion_rejected(self):
        a = _fields(applied_companion_method_registry_ids=[CHASH, CHASH],
                    method_capability_rule_id="R-CDC-HASH",
                    candidate_relation_types=["segment_identity_candidate"],
                    comparison_intent="near_duplicate")
        with self.assertRaises(MethodValidationError):
            validate_capability(a, self.reg)

    def test_unknown_companion_rejected(self):
        a = _fields(applied_companion_method_registry_ids=["nonexistent"],
                    method_capability_rule_id="R-CDC-STANDALONE")
        with self.assertRaises(MethodValidationError):
            validate_capability(a, self.reg)


class TestDeterminism(unittest.TestCase):
    def setUp(self):
        self.reg = build_default_registry()
        # nondeterministic method を追加
        self.emb = MethodRegistryEntry("embedding", "v1", "text", NONDETERMINISTIC, True, (), ())
        self.reg.register(self.emb)

    def test_determinism_equality_enforced(self):
        a = _fields(method_determinism=NONDETERMINISTIC)  # primary CDC は deterministic
        with self.assertRaises(MethodValidationError):
            validate_capability(a, self.reg)

    def test_nondeterministic_requires_digest(self):
        from xdoc_method import method_registry_id as mid
        emb_id = mid("embedding", "v1")
        # embedding を primary にした alignment（rule は別途要・ここでは determinism チェック前に primary 確認）
        a = AlignmentMethodFields(
            facet="text", primary_method_registry_id=emb_id,
            applied_companion_method_registry_ids=[], method_capability_rule_id="R-CDC-STANDALONE",
            candidate_relation_types=[], comparison_intent="text_reuse",
            method_determinism=NONDETERMINISTIC, result_payload_digest=None,
        )
        with self.assertRaises(MethodValidationError):  # digest 欠落
            validate_capability(a, self.reg)


if __name__ == "__main__":
    unittest.main()
