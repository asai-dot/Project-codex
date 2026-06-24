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
        # 同スキーマ内で pref+reading 同じ、定義が乖離 -> homograph_split で別 hub
        terms = [
            {"term_id": "a", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "社員", "reading": "しゃいん", "definition": "会社法上の構成員たる地位", "term_tier": 1},
            {"term_id": "b", "scheme_id": "yuhikaku", "authority_rank": 101,
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

    def test_cross_dict_always_merges_regardless_of_overlap(self):
        # 法令辞書間では同 pref+reading = 同概念. 定義の散文が違っても merge する.
        # (bigram Jaccard は辞書スタイルの差で構造的に低い)
        terms = [
            {"stg_term_key": "y1", "scheme_id": "yuhikaku_legal_dict", "authority_rank": 101,
             "normalized_pref": "社員", "reading": "しゃいん", "definition": "会社法上の構成員たる地位", "term_tier": 1},
            {"stg_term_key": "h1", "scheme_id": "hourei_yougo_jiten_11", "authority_rank": 102,
             "normalized_pref": "社員", "reading": "しゃいん", "definition": "労働者一般を指す日常語", "term_tier": 1},
        ]
        hubs, _, stats = bh.build_hubs(terms, threshold=0.6)
        self.assertEqual(stats["homograph_conflicts"], 0)  # cross-scheme は threshold 無関係
        self.assertEqual(stats["hubs"], 1)
        self.assertEqual(hubs[0]["member_count"], 2)

    def test_same_scheme_low_overlap_is_homograph(self):
        # 同スキーマ内で pref+reading 同じでも定義が乖離 = homograph_split
        terms = [
            {"stg_term_key": "a1", "scheme_id": "yuhikaku_legal_dict", "authority_rank": 101,
             "normalized_pref": "社員", "reading": "しゃいん", "definition": "会社法上の構成員たる地位", "term_tier": 1},
            {"stg_term_key": "a2", "scheme_id": "yuhikaku_legal_dict", "authority_rank": 101,
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


class TestQualityFilter(unittest.TestCase):
    def _base_terms(self):
        return [
            {"term_id": "a", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "占有", "reading": "せんゆう",
             "definition": "物を事実上支配すること", "term_tier": 1},
            {"term_id": "b", "scheme_id": "hourei", "authority_rank": 102,
             "normalized_pref": "占有", "reading": "せんゆう",
             "definition": "物を事実上支配すること", "term_tier": 1},
        ]

    def test_empty_def_anchor_flagged(self):
        # 空定義 term が anchor になるとき hub に needs_preprocessing が付く
        terms = [
            {"term_id": "e", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "質権", "reading": "しちけん", "definition": "", "term_tier": 1},
        ]
        hubs, _, stats = bh.build_hubs(terms, quality_filter=True)
        self.assertEqual(stats["anchors_empty_def"], 1)
        self.assertIn("empty_def", hubs[0].get("needs_preprocessing", []))
        self.assertEqual(hubs[0]["anchor_quality"], "empty_def")

    def test_short_def_anchor_flagged(self):
        # 短定義(<8字) term が anchor になるとき hub に needs_preprocessing が付く
        terms = [
            {"term_id": "s", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "質権", "reading": "しちけん", "definition": "短い", "term_tier": 1},
        ]
        hubs, _, stats = bh.build_hubs(terms, quality_filter=True)
        self.assertEqual(stats["anchors_short_def"], 1)
        self.assertIn("short_def", hubs[0].get("needs_preprocessing", []))

    def test_quality_filter_off_by_default(self):
        # quality_filter=False (既定) では needs_preprocessing が付かない
        terms = [
            {"term_id": "e", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "質権", "reading": "しちけん", "definition": "", "term_tier": 1},
        ]
        hubs, _, stats = bh.build_hubs(terms)
        self.assertEqual(stats["anchors_empty_def"], 0)
        self.assertNotIn("needs_preprocessing", hubs[0])

    def test_anchor_rule_prefers_def_over_empty(self):
        # 同一グループで定義ありの term が anchor になること(空定義は後回し)
        terms = [
            {"term_id": "empty", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "質権", "reading": "しちけん", "definition": "", "term_tier": 1},
            {"term_id": "full", "scheme_id": "hourei", "authority_rank": 102,
             "normalized_pref": "質権", "reading": "しちけん",
             "definition": "目的物を占有して優先弁済を受ける担保物権", "term_tier": 1},
        ]
        hubs, _, _ = bh.build_hubs(terms)
        self.assertEqual(hubs[0]["anchor_term_id"], "full")

    def test_stats_count_quality_terms(self):
        # terms_empty_def / terms_short_def が正しく集計される
        terms = [
            {"term_id": "a", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "質権", "reading": "しちけん", "definition": "", "term_tier": 1},
            {"term_id": "b", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "抵当", "reading": "ていとう", "definition": "短い", "term_tier": 1},
            {"term_id": "c", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "占有", "reading": "せんゆう",
             "definition": "物を事実上支配すること", "term_tier": 1},
        ]
        _, _, stats = bh.build_hubs(terms, quality_filter=True)
        self.assertEqual(stats["terms_empty_def"], 1)
        self.assertEqual(stats["terms_short_def"], 1)


class TestHomographReview(unittest.TestCase):
    def test_collect_pairs_pairs_anchor_with_split(self):
        import homograph_review as hr
        # 同scheme内 genuine homograph: anchor 側定義と split 側定義を対にする
        terms = [
            {"term_id": "a", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "社員", "reading": "しゃいん",
             "definition": "会社法上の構成員たる地位をいう", "term_tier": 1},
            {"term_id": "b", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "社員", "reading": "しゃいん",
             "definition": "労働者一般を指す日常語のこと", "term_tier": 1},
        ]
        pairs, stats = hr.collect_pairs(terms, 0.6)
        self.assertEqual(len(pairs), 1)
        p = pairs[0]
        self.assertEqual(p["pref"], "社員")
        self.assertTrue(p["same_scheme"])
        self.assertTrue(p["anchor"]["definition"])   # anchor 側定義が引けている
        self.assertTrue(p["conflict"]["definition"])  # split 側定義が引けている
        self.assertNotEqual(p["anchor"]["term_id"], p["conflict"]["term_id"])

    def test_cross_scheme_not_homograph(self):
        import homograph_review as hr
        # cross-scheme は merge ポリシー -> homograph に出ない
        terms = [
            {"term_id": "a", "scheme_id": "yuhikaku", "authority_rank": 101,
             "normalized_pref": "占有", "reading": "せんゆう",
             "definition": "物を事実上支配すること", "term_tier": 1},
            {"term_id": "b", "scheme_id": "hourei", "authority_rank": 102,
             "normalized_pref": "占有", "reading": "せんゆう",
             "definition": "全く無関係な別概念xyzをいう", "term_tier": 1},
        ]
        pairs, _ = hr.collect_pairs(terms, 0.6)
        self.assertEqual(len(pairs), 0)


class TestHomographClassify(unittest.TestCase):
    """実データ44件の素性に基づく自動分類(staging artifact vs genuine 多義)."""
    def setUp(self):
        import homograph_review as hr
        self.hr = hr

    def test_continuation_a_cut_midsentence(self):
        # A が(長文だが)文末記号で終わらず途中で切れている -> continuation
        a = ("「会計」とは，一般的には国，地方公共団体その他の団体又は個人の財産の異動増減及び収支を"
             "計算整理することをいうが。旧会計法は，予算決算，収入支出等を規")
        k, _ = self.hr.classify_pair("会計", a, "定し，この場合の会計は，金銭に関る管理作用の意味をもっていた。")
        self.assertEqual(k, "artifact_continuation")

    def test_empty_b(self):
        k, _ = self.hr.classify_pair("施行法", "ある法律の施行に必要な規定をいう。", "(定義なし)")
        self.assertEqual(k, "artifact_empty")

    def test_stub_b_reading(self):
        # B が読み/相互参照の短いスタブ
        k, _ = self.hr.classify_pair("博士", "学位の一種で，…ものとがある。", "はくし")
        self.assertEqual(k, "artifact_stub")

    def test_header_only_b(self):
        k, _ = self.hr.classify_pair("資本取引", "【1)】", "【2) 国際経済上は】")
        self.assertEqual(k, "artifact_header")

    def test_subitem_b(self):
        k, _ = self.hr.classify_pair("休業補償", "1）労働者が…（労働基準法84I）.",
                                     "2）船員法では，…(船員法 95).")
        self.assertEqual(k, "artifact_subitem")

    def test_list_marker_headword(self):
        k, _ = self.hr.classify_pair("その1", "職務を行う上などに要した費用を償う…",
                                     "防衛出動時における物資の収用等の特権であり…。")
        self.assertEqual(k, "artifact_list_marker")

    def test_stub_on_anchor_side(self):
        # A 側が「「世帯」(せい)」のスタブ, B が本定義 -> artifact_stub
        k, _ = self.hr.classify_pair(
            "世帯", "「世帯」(せい)",
            "普通，社会生活上の単位として住居及び生計を共にする者の集まりを意味する用語として用いられる。")
        self.assertEqual(k, "artifact_stub")

    def test_subitem_leading_digit_period(self):
        # B が「1. …」の番号サブ項目 -> artifact_subitem
        k, _ = self.hr.classify_pair(
            "評定", "一般に，ある事物又は事象を評価し，判定することをいう。",
            "1. 独立行政法人通則法には，各年度に係る業務実績等に関する評価について定めている(同法32Ⅲ).")
        self.assertEqual(k, "artifact_subitem")

    def test_genuine_split_different_concept(self):
        # 参議: A=官職 / B=家事審判役で見出し語を含まない -> genuine_split (別概念)
        k, _ = self.hr.classify_pair(
            "参議", "①職員令(明二)によって設けられた官職で、太政大臣の補佐を任務とした。明治一八年廃止。",
            "家庭裁判所が人事訴訟又は家事審判を行う際、その手続に立ち会うことを職務とする非常勤の国家公務員（人訴九）。")
        self.assertEqual(k, "genuine_split")

    def test_genuine_split_ocr_contradiction(self):
        # 重懲役: A=禁錮/服さない vs B=懲役/服する (見出し語を双方含まない) -> genuine_split
        k, _ = self.hr.classify_pair(
            "重懲役",
            "旧刑法に規定されていた刑名。刑期は九年以上一一年以下で、定役に服さない。現行刑法の有期禁錮の一部に相当する。",
            "旧刑法に規定されていた刑名。重罪に対し科される主刑の一つで、刑期は九年以上一年以下。定役に服する。現行刑法の有期懲役の一部に該当する。")
        self.assertEqual(k, "genuine_split")

    def test_merge_candidate_same_concept(self):
        # 会社: A/B双方が「会社」を含む同概念の重複定義 -> merge_candidate
        k, _ = self.hr.classify_pair(
            "会社",
            "営利を目的とする社団法人。資本、労力を結合し、危険を軽減する機能をもつ。会社法上、株式会社等がある。",
            "営利を目的とする社団法人。株式会社、合名会社、合資会社、合同会社の四種がある（会社二）。")
        self.assertEqual(k, "merge_candidate")


if __name__ == "__main__":
    unittest.main()
