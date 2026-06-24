"""DD-INDEP-LINEAGE-001 v0.1 受入試験（監査 B4 修正版 fixture・object_id では数えない）。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indep_lineage import (  # noqa: E402
    ContentLineageBinding, ObservationRun,
    content_independent, observation_independent, content_independence_group,
    observation_lineage_root, xmodal_confirmed_independent, binding_change_invalidates,
    BINDING_ACTIVE, BINDING_STALE,
)


def _b(binding_id, obj, upstream, collapse=None, status=BINDING_ACTIVE):
    return ContentLineageBinding(
        binding_id=binding_id, source_artifact_ref="art:" + binding_id,
        content_object_id=obj, upstream_lineage_id=upstream,
        same_origin_collapse_key=collapse, independence_policy_version="v1", binding_status=status,
    )


def _run(run_id, raw_hash, ocr="tesseract"):
    return ObservationRun(run_id=run_id, raw_input_hash=raw_hash,
                          acquisition_event_id="acq:" + run_id, ocr_engine=ocr,
                          parser="p", normalization_profile="n", scan_source_id="scan:" + run_id)


class TestContentLineage(unittest.TestCase):
    def test_fix1_diff_record_same_upstream_one_vote(self):
        """別 record ID でも upstream lineage 同一 → 1票（同一原稿の別 provider record）。"""
        a = _b("recA", "obj:民法541#provA", "upstream:原稿X")
        b = _b("recB", "obj:民法541#provB", "upstream:原稿X")  # 別 record・別 object・同一上流
        self.assertFalse(content_independent([a, b]))

    def test_fix2_diff_object_same_group_one_vote(self):
        """別 object でも independence_group（collapse_key）同一 → 1票。"""
        a = _b("a", "obj:条文1", "up:A", collapse="grp:同一editorial")
        b = _b("b", "obj:条文2", "up:B", collapse="grp:同一editorial")  # 別 object/別上流だが同一 collapse
        self.assertFalse(content_independent([a, b]))

    def test_fix3_same_objtype_independent_lineage_two_votes(self):
        """同一 object type でも独立 authority/editorial lineage なら2票になり得る。"""
        a = _b("a", "obj:民法541", "up:authorityP")
        b = _b("b", "obj:最判平X", "up:authorityQ")  # 別系譜
        self.assertTrue(content_independent([a, b]))

    def test_group_not_object_id(self):
        """独立票は group 単位（object_id ではない）。"""
        a = _b("a", "objX", "up:same")
        b = _b("b", "objY", "up:same")
        self.assertEqual(content_independence_group(a), content_independence_group(b))  # 同群

    def test_stale_binding_not_counted(self):
        a = _b("a", "o1", "up:A")
        b = _b("b", "o2", "up:B", status=BINDING_STALE)  # stale は数えない
        self.assertFalse(content_independent([a, b]))

    def test_note5_unknown_lineage_not_independent(self):
        """note5: upstream/collapse 不明な binding だけでは independent にしない。"""
        a = ContentLineageBinding("a", "art:a", "o1", upstream_lineage_id="",
                                  same_origin_collapse_key=None, independence_policy_version="v1")
        b = ContentLineageBinding("b", "art:b", "o2", upstream_lineage_id="",
                                  same_origin_collapse_key=None, independence_policy_version="v1")
        self.assertFalse(content_independent([a, b]))  # 2件とも unknown → 独立でない
        # 既知1 + 不明1 でも独立2源にならない
        known = _b("k", "o3", "up:known")
        self.assertFalse(content_independent([a, known]))


class TestObservationLineage(unittest.TestCase):
    def test_fix4_same_raw_hash_diff_run_one_lineage(self):
        """同一 raw_input_hash の別 run（別 OCR）→ observation 1系統。"""
        r1 = _run("r1", "rawhash#1", ocr="tesseract")
        r2 = _run("r2", "rawhash#1", ocr="abbyy")   # 別 run・別 OCR・同一 raw bytes
        self.assertFalse(observation_independent([r1, r2]))

    def test_distinct_raw_hash_independent(self):
        r1 = _run("r1", "rawhash#1")
        r2 = _run("r2", "rawhash#2")  # 別 raw bytes（別取り込み）
        self.assertTrue(observation_independent([r1, r2]))

    def test_root_is_raw_hash_not_scan_id(self):
        """root は raw_input_hash（複製 scan_source_id では系統を増やせない・B3）。"""
        r1 = _run("r1", "rawhash#1")
        r2 = _run("r2", "rawhash#1")  # scan_source_id は別だが raw 同一
        self.assertEqual(observation_lineage_root(r1), observation_lineage_root(r2))


class TestConsumerAndBinding(unittest.TestCase):
    def test_confirmed_uses_content_group(self):
        same = [_b("a", "o1", "up:X"), _b("b", "o2", "up:X")]  # 同一上流
        self.assertFalse(xmodal_confirmed_independent(same))
        diff = [_b("a", "o1", "up:X"), _b("b", "o2", "up:Y")]
        self.assertTrue(xmodal_confirmed_independent(diff))

    def test_fix5_binding_change_triggers_reeval(self):
        """binding 変更で独立群が変われば既存 assessment を stale/re-eval。"""
        old = _b("a", "o1", "up:X")
        new = _b("a", "o1", "up:Y")  # upstream 変更 → group 変化
        self.assertTrue(binding_change_invalidates(old, new))
        same = _b("a", "o1", "up:X")
        self.assertFalse(binding_change_invalidates(old, same))


if __name__ == "__main__":
    unittest.main()
