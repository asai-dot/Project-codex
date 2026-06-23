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


class TestRealSchemaJoin(unittest.TestCase):
    def test_attach_definitions_from_labels(self):
        # 有斐閣実スキーマ: 定義は labels(label_type=definition) 側. stg_term_key で join.
        terms = [{"stg_term_key": "t1", "normalized_pref": "占有", "reading": "せんゆう"}]
        labels = [
            {"stg_term_key": "t1", "label_type": "reading", "label_text": "せんゆう"},
            {"stg_term_key": "t1", "label_type": "definition", "label_text": "物を事実上支配すること"},
        ]
        bh.attach_definitions(terms, labels)
        self.assertEqual(terms[0]["definition"], "物を事実上支配すること")

    def test_field_map_termid_from_stg_key(self):
        # term_id ← stg_term_key の field-map で build が回る
        terms = [
            {"stg_term_key": "t1", "scheme_id": "yuhikaku_legal_dict", "authority_rank": 101,
             "normalized_pref": "債権", "reading": "さいけん", "definition": "給付請求権", "term_tier": 1},
        ]
        mapped = bh.remap_records(terms, {"term_id": "stg_term_key"})
        hubs, _, stats = bh.build_hubs(mapped)
        self.assertEqual(stats["hubs"], 1)
        self.assertEqual(hubs[0]["anchor_term_id"], "t1")

    def test_build_works_without_term_id_uses_stg_key(self):
        # field-map 無しでも stg_term_key を識別子に使えること
        terms = [
            {"stg_term_key": "tA", "scheme_id": "yuhikaku_legal_dict", "authority_rank": 101,
             "normalized_pref": "占有", "reading": "せんゆう", "definition": "物を事実上支配", "term_tier": 1},
            {"stg_term_key": "tB", "scheme_id": "hourei", "authority_rank": 102,
             "normalized_pref": "占有", "reading": "せんゆう", "definition": "物を事実上支配する状態", "term_tier": 1},
        ]
        hubs, mem, stats = bh.build_hubs(terms)
        self.assertEqual(stats["hubs"], 1)
        self.assertIn(hubs[0]["anchor_term_id"], {"tA", "tB"})
        self.assertTrue(all(m["term_id"] for m in mem))  # 空 id にならない


class TestCrossDictAndNorm(unittest.TestCase):
    def test_reading_normalization_katakana_hiragana(self):
        self.assertEqual(bh.norm_reading("センユウ"), bh.norm_reading("せんゆう"))

    def test_norm_pref_fullwidth(self):
        self.assertEqual(bh.norm_pref("ＡＢ会社"), "AB会社")

    def test_cross_dict_merge_yuhikaku_plus_hourei(self):
        # 有斐閣(101, normalized_pref) + 学陽(102, headword生) 同義+読み(カナ/かな差) -> 1 hub に統合
        terms = [
            {"stg_term_key": "y1", "scheme_id": "yuhikaku_legal_dict", "authority_rank": 101,
             "normalized_pref": "占有", "reading": "せんゆう", "definition": "物を事実上支配すること", "term_tier": 1},
            {"stg_term_key": "h1", "scheme_id": "hourei_yougo_jiten_11", "authority_rank": 102,
             "pref_label": "占有", "normalized_pref": "占有", "reading": "センユウ",
             "definition": "物を事実上支配する状態をいう", "term_tier": 1},
        ]
        hubs, mem, stats = bh.build_hubs(terms, threshold=0.3)
        self.assertEqual(stats["hubs"], 1)
        self.assertEqual(hubs[0]["member_count"], 2)
        self.assertEqual(set(hubs[0]["authority_ranks"]), {"101", "102"})

    def test_cross_dict_low_overlap_homograph_split(self):
        terms = [
            {"stg_term_key": "y1", "scheme_id": "yuhikaku_legal_dict", "authority_rank": 101,
             "normalized_pref": "社員", "reading": "しゃいん", "definition": "会社法上の構成員たる地位", "term_tier": 1},
            {"stg_term_key": "h1", "scheme_id": "hourei_yougo_jiten_11", "authority_rank": 102,
             "normalized_pref": "社員", "reading": "しゃいん", "definition": "労働者一般を指す日常語", "term_tier": 1},
        ]
        _, _, stats = bh.build_hubs(terms, threshold=0.6)
        self.assertEqual(stats["homograph_conflicts"], 1)
        self.assertEqual(stats["hubs"], 2)


class TestReadingMissing(unittest.TestCase):
    def _terms(self):
        return [
            {"stg_term_key": "y1", "scheme_id": "yuhikaku_legal_dict", "authority_rank": 101,
             "normalized_pref": "占有", "reading": "せんゆう", "definition": "物を事実上支配すること", "term_tier": 1},
            # 学陽: 読み欠落(OCR), 定義は近い
            {"stg_term_key": "h1", "scheme_id": "hourei_yougo_jiten_11", "authority_rank": 102,
             "normalized_pref": "占有", "reading": None, "definition": "物を事実上支配する状態をいう", "term_tier": 1},
        ]

    def test_defmatch_rescues_reading_missing(self):
        hubs, mem, stats = bh.build_hubs(self._terms(), threshold=0.3, reading_missing="defmatch")
        self.assertEqual(stats["reading_missing_matched"], 1)
        self.assertEqual(stats["hubs"], 1)  # 1 hub に救済統合
        rm = [m for m in mem if m["map_type"] == "reading_missing_def_match"]
        self.assertEqual(len(rm), 1)
        self.assertEqual(set(hubs[0]["authority_ranks"]), {"101", "102"})

    def test_strict_keeps_reading_missing_separate(self):
        _, _, stats = bh.build_hubs(self._terms(), threshold=0.3, reading_missing="strict")
        self.assertEqual(stats.get("reading_missing_matched", 0), 0)
        self.assertEqual(stats["hubs"], 2)  # 読み違いで別 hub

    def test_cross_scheme_low_overlap_still_attaches(self):
        # cross-scheme では定義が乖離していても pref 一致で attach する
        # (異辞書間は同概念でも bigram Jaccard が構造的に低い)
        terms = self._terms()
        terms[1]["definition"] = "全く無関係な別の概念xyz"
        hubs, mem, stats = bh.build_hubs(terms, threshold=0.6, reading_missing="defmatch")
        self.assertEqual(stats["reading_missing_matched"], 1)  # cross-scheme -> 常に attach
        self.assertEqual(stats["hubs"], 1)
        rm = [m for m in mem if m["map_type"] == "reading_missing_def_match"]
        self.assertTrue(rm[0]["cross_scheme"])

    def test_same_scheme_low_overlap_makes_own_hub(self):
        # 同一スキーマ内で読み欠落 + 定義不一致 -> 単独 hub (homograph 防止)
        terms = [
            {"stg_term_key": "y1", "scheme_id": "yuhikaku_legal_dict", "authority_rank": 101,
             "normalized_pref": "占有", "reading": "せんゆう", "definition": "物を事実上支配すること", "term_tier": 1},
            {"stg_term_key": "y2", "scheme_id": "yuhikaku_legal_dict", "authority_rank": 101,
             "normalized_pref": "占有", "reading": None, "definition": "全く無関係な別の概念xyz", "term_tier": 1},
        ]
        _, _, stats = bh.build_hubs(terms, threshold=0.6, reading_missing="defmatch")
        self.assertEqual(stats["reading_missing_seed"], 1)  # 同スキーマ重なり不足 -> 単独hub
        self.assertEqual(stats["hubs"], 2)


class TestHoureiAdapter(unittest.TestCase):
    def test_adapt_sets_rank_and_pref(self):
        import adapt_hourei as ah
        entries = [{"scheme_id": "hourei_yougo_jiten_11", "entry_id": "h__00001",
                    "headword": "明渡裁決", "reading": "あけわたしさいけつ", "definition": "..."}]
        terms = ah.adapt(entries, "hourei_yougo_jiten_11", 102)
        self.assertEqual(terms[0]["authority_rank"], 102)
        self.assertEqual(terms[0]["term_tier"], 1)
        self.assertEqual(terms[0]["normalized_pref"], "明渡裁決")
        self.assertEqual(terms[0]["definition"], "...")

    def test_adapt_skips_empty_headword(self):
        import adapt_hourei as ah
        self.assertEqual(ah.adapt([{"headword": "", "definition": "x"}], "s", 102), [])


if __name__ == "__main__":
    unittest.main()
