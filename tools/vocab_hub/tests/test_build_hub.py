"""語彙Hub構築 dry-run ユニットテスト (依存ゼロ).
実行: python3 -m unittest discover -s tools/vocab_hub/tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_hub_dryrun as bh  # noqa: E402


class TestHelpers(unittest.TestCase):
    def test_is_bedrock(self):
        self.assertTrue(bh.is_bedrock(100))
        self.assertTrue(bh.is_bedrock("100d"))
        self.assertTrue(bh.is_bedrock(101))
        self.assertTrue(bh.is_bedrock(102))
        self.assertFalse(bh.is_bedrock(103))
        self.assertFalse(bh.is_bedrock(105))

    def test_overlap(self):
        self.assertEqual(bh.overlap("", "x"), 0.0)
        self.assertAlmostEqual(bh.overlap("占有する", "占有する"), 1.0)
        self.assertTrue(bh.overlap("物を所持する", "全く別の文章xyz") < 0.3)


class TestHubBuild(unittest.TestCase):
    def test_exact_merge_across_schemes(self):
        # 有斐閣(101)+学陽(102) 同 pref+reading+高重なり -> 1 hub に統合
        terms = [
            {"term_id": "y1", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "占有", "reading": "せんゆう", "definition": "物を事実上支配すること", "term_tier": 1},
            {"term_id": "h1", "scheme_id": "hourei", "authority_rank": 102,
             "normalized_pref": "占有", "reading": "せんゆう", "definition": "物を事実上支配すること", "term_tier": 1},
        ]
        hubs, mem, stats = bh.build_hubs(terms)
        self.assertEqual(stats["hubs"], 1)
        self.assertEqual(hubs[0]["member_count"], 2)
        self.assertEqual(stats["exact_merged_hubs"], 1)
        self.assertEqual({m["map_type"] for m in mem}, {"skos_exact_match"})

    def test_homograph_different_reading_not_merged(self):
        # 遺言 ゆいごん vs いごん -> reading 違い = 別 key = 別 hub (統合しない)
        terms = [
            {"term_id": "a", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "遺言", "reading": "ゆいごん", "definition": "一般的な言い残し", "term_tier": 1},
            {"term_id": "b", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "遺言", "reading": "いごん", "definition": "民法上の死後の意思表示", "term_tier": 1},
        ]
        hubs, _, stats = bh.build_hubs(terms)
        self.assertEqual(stats["hubs"], 2)  # 表層一致でも reading 違いは別

    def test_homograph_same_key_low_overlap_split(self):
        # 同 pref+reading だが定義が全く違う -> homograph_split で別 hub
        terms = [
            {"term_id": "a", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "社員", "reading": "しゃいん", "definition": "会社法上の構成員たる地位", "term_tier": 1},
            {"term_id": "b", "scheme_id": "hourei", "authority_rank": 102,
             "normalized_pref": "社員", "reading": "しゃいん", "definition": "労働者一般を指す日常語", "term_tier": 1},
        ]
        hubs, _, stats = bh.build_hubs(terms, threshold=0.6)
        self.assertEqual(stats["homograph_conflicts"], 1)
        self.assertEqual(stats["hubs"], 2)

    def test_specialty_attach_only_never_canonical(self):
        # 専門辞典(103) は bedrock hub に attach のみ. canonical 化しない.
        terms = [
            {"term_id": "y", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "持分", "reading": "もちぶん", "definition": "権利の量的部分", "term_tier": 1},
            {"term_id": "s", "scheme_id": "fudosan", "authority_rank": 103,
             "normalized_pref": "持分", "reading": "もちぶん", "definition": "共有不動産の所有割合", "term_tier": 1},
        ]
        hubs, mem, stats = bh.build_hubs(terms)
        self.assertEqual(stats["specialty_attached"], 1)
        attach = [m for m in mem if m.get("specialty_attach")]
        self.assertEqual(attach[0]["map_type"], "skos_close_match")
        for h in hubs:
            self.assertEqual(h["hub_status"], "provisional")  # canonical 昇格しない

    def test_anchor_neutral_egov_first(self):
        terms = [
            {"term_id": "h", "scheme_id": "hourei", "authority_rank": 102,
             "normalized_pref": "債権", "reading": "さいけん", "definition": "特定人に給付を請求する権利", "term_tier": 1},
            {"term_id": "e", "scheme_id": "egov", "authority_rank": 100,
             "normalized_pref": "債権", "reading": "さいけん", "definition": "特定人に給付を請求する権利", "term_tier": 1},
        ]
        hubs, _, _ = bh.build_hubs(terms)
        self.assertEqual(hubs[0]["anchor_term_id"], "e")  # e-Gov(rank100) が anchor

    def test_specialty_excluded_from_bedrock_seed(self):
        terms = [
            {"term_id": "s", "scheme_id": "it", "authority_rank": 103,
             "normalized_pref": "サーバ", "reading": "さーば", "definition": "計算機", "term_tier": 1},
        ]
        _, _, stats = bh.build_hubs(terms)
        self.assertEqual(stats["bedrock_terms"], 0)
        self.assertEqual(stats["specialty_terms"], 1)


if __name__ == "__main__":
    unittest.main()
