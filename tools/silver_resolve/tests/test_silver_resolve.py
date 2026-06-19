"""silver_resolve ユニットテスト (依存ゼロ unittest).

実行: python3 -m unittest discover -s tools/silver_resolve/tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import silver_cite_id as s1  # noqa: E402
import silver_toc_section as s2  # noqa: E402


class TestSilver1(unittest.TestCase):
    def setUp(self):
        pub = [
            {"hanrei_id": "A", "journal": "労働判例", "issue": "1060", "page": "5"},
            {"hanrei_id": "X", "journal": "判タ", "issue": "850", "page": "100"},
            {"hanrei_id": "Y", "journal": "判タ", "issue": "850", "page": "100"},
        ]
        self.norm = {"労判": "労働判例"}
        self.by_jip, self.by_ji = s1.build_pub_indexes(pub, self.norm)
        self.by_cd = s1.build_canon_index([{"hanrei_id": "A", "court": "最高裁", "date": "1994-07-18"}])

    def test_parse_locator(self):
        self.assertEqual(s1.parse_locator("journal_article:労働判例:1060:5"), ("労働判例", "1060", "5"))
        self.assertIsNone(s1.parse_locator("broken"))

    def test_normalize_journal(self):
        self.assertEqual(s1.normalize_journal("労判", self.norm), "労働判例")
        self.assertEqual(s1.normalize_journal("労 働 判 例"), "労働判例")

    def test_exact_single_is_strong(self):
        e = {"edge_id": "1", "edge_type": "cites_judgment_via_journal",
             "source_locator": "journal_article:労判:1060:5"}
        c = s1.resolve_edge(e, self.by_jip, self.by_ji, self.by_cd, self.norm)
        self.assertEqual(c["decision_status"], "strong")
        self.assertEqual(c["match_method"], "issue_page_exact")
        self.assertEqual(c["resolved_hanrei_id"], ["A"])

    def test_multi_candidate_is_review(self):
        e = {"edge_id": "2", "edge_type": "cites_judgment_via_journal",
             "source_locator": "journal_article:判タ:850:100"}
        c = s1.resolve_edge(e, self.by_jip, self.by_ji, self.by_cd, self.norm)
        self.assertEqual(c["decision_status"], "review")
        self.assertEqual(sorted(c["resolved_hanrei_id"]), ["X", "Y"])

    def test_page_loss_fallback_is_review(self):
        e = {"edge_id": "3", "edge_type": "cites_judgment_via_journal",
             "source_locator": "journal_article:労働判例:1060:"}
        c = s1.resolve_edge(e, self.by_jip, self.by_ji, self.by_cd, self.norm)
        self.assertEqual(c["match_method"], "issue_page_fallback")
        self.assertEqual(c["decision_status"], "review")

    def test_locator_unresolvable(self):
        e = {"edge_id": "4", "edge_type": "cites_judgment_via_journal", "source_locator": "broken"}
        c = s1.resolve_edge(e, self.by_jip, self.by_ji, self.by_cd, self.norm)
        self.assertEqual(c["honest_empty"], "locator_unresolvable")
        self.assertEqual(c["resolved_hanrei_id"], [])

    def test_no_index_is_db_unbuilt(self):
        e = {"edge_id": "5", "edge_type": "cites_judgment_via_journal",
             "source_locator": "journal_article:無誌:1:1"}
        c = s1.resolve_edge(e, self.by_jip, self.by_ji, self.by_cd, self.norm)
        self.assertEqual(c["honest_empty"], "db_unbuilt")

    def test_court_date_is_review(self):
        e = {"edge_id": "6", "edge_type": "cites_judgment_by_date", "court": "最高裁", "date": "1994-07-18"}
        c = s1.resolve_edge(e, self.by_jip, self.by_ji, self.by_cd, self.norm)
        self.assertEqual(c["match_method"], "court_date")
        self.assertEqual(c["decision_status"], "review")  # strong-only: 日付経路は strong にしない

    def test_strong_only_invariant(self):
        # strong は issue_page_exact 単一のみ. 他経路は strong にならない (D2).
        edges = [
            {"edge_id": "a", "edge_type": "cites_judgment_via_journal", "source_locator": "journal_article:判タ:850:100"},
            {"edge_id": "b", "edge_type": "cites_judgment_by_date", "court": "最高裁", "date": "1994-07-18"},
        ]
        cands = s1.resolve_all(edges, self.by_jip, self.by_ji, self.by_cd, self.norm)
        for c in cands:
            if c["decision_status"] == "strong":
                self.assertEqual(c["match_method"], "issue_page_exact")
                self.assertEqual(len(c["resolved_hanrei_id"]), 1)


class TestSilver2(unittest.TestCase):
    def setUp(self):
        self.nodes = [
            {"toc_node_id": "t1", "parent_id": None, "book_id": "b1", "heading": "賃貸借", "kind": "heading"},
            {"toc_node_id": "t2", "parent_id": "t1", "book_id": "b1", "heading": "賃料不払解除", "kind": "heading"},
            {"toc_node_id": "r1", "parent_id": "t2", "book_id": "b1", "kind": "row"},
            {"toc_node_id": "r2", "parent_id": "t2", "book_id": "b1", "kind": "row"},
            {"toc_node_id": "t3", "parent_id": "t1", "book_id": "b1", "heading": "代払機会", "kind": "heading"},
            {"toc_node_id": "r3", "parent_id": "t3", "book_id": "b1", "kind": "row"},
        ]
        self.edges = [
            {"toc_node_id": "r1", "hanrei_id": "A", "book_id": "b1"},
            {"toc_node_id": "r2", "hanrei_id": "B", "book_id": "b1"},
            {"toc_node_id": "r3", "hanrei_id": "C", "book_id": "b1"},
        ]

    def test_nearest_heading_walks_up(self):
        nodes = {str(n["toc_node_id"]): n for n in self.nodes}
        self.assertEqual(s2.nearest_heading("r1", nodes), "t2")
        self.assertEqual(s2.nearest_heading("r3", nodes), "t3")

    def test_section_grouping_and_harvest_title(self):
        secs, _, _ = s2.resolve_sections(self.nodes, self.edges, {})
        by_id = {s["issue_section_id"]: s for s in secs}
        self.assertEqual(sorted(by_id["t2"]["member_hanrei_ids"]), ["A", "B"])
        self.assertEqual(by_id["t2"]["section_heading"], "賃料不払解除")  # 論点タイトル harvest

    def test_cooccurrence_within_section_only(self):
        # A,B は同section t2 -> 共起1ペア. C は別section -> A/B と共起しない (書籍全結合を採らない).
        _, co, stats = s2.resolve_sections(self.nodes, self.edges, {})
        pairs = {(c["hanrei_a"], c["hanrei_b"]) for c in co}
        self.assertEqual(pairs, {("A", "B")})
        self.assertEqual(stats["section_pairs"], 1)
        self.assertEqual(stats["naive_book_pairs"], 3)  # A,B,C 全結合 = 3 (置換前の無意味共起)

    def test_importance_from_hyoshaku(self):
        _, co, _ = s2.resolve_sections(self.nodes, self.edges, {"A": 11, "B": 5})
        c = co[0]
        self.assertEqual(c["importance"], 16)
        self.assertEqual(c["decision_status"], "strong")

    def test_trace_absent_when_no_hyoshaku(self):
        secs, _, _ = s2.resolve_sections(self.nodes, self.edges, {})
        for s in secs:
            self.assertEqual(s["decision_status"], "review")  # 評釈密度ゼロ = trace_absent 相当


class TestAdapters(unittest.TestCase):
    def test_s1_remap_records(self):
        # 実データ風: hanrei_id が case_id, source_locator が cite_str
        recs = [{"edge_id": "1", "edge_type": "cites_judgment_via_journal", "cite_str": "journal_article:労判:1060:5"}]
        out = list(s1.remap_records(recs, {"source_locator": "cite_str"}))
        self.assertEqual(out[0]["source_locator"], "journal_article:労判:1060:5")

    def test_s1_remap_no_overwrite(self):
        recs = [{"hanrei_id": "A", "case_id": "B"}]
        out = list(s1.remap_records(recs, {"hanrei_id": "case_id"}))
        self.assertEqual(out[0]["hanrei_id"], "A")  # 既存 expected は上書きしない

    def test_s2_remap_records(self):
        recs = [{"node": "t1", "parent": None, "title": "賃貸借"}]
        out = s2.remap_records(recs, {"toc_node_id": "node", "parent_id": "parent", "heading": "title"})
        self.assertEqual(out[0]["toc_node_id"], "t1")
        self.assertEqual(out[0]["heading"], "賃貸借")

    def test_s2_infer_kind(self):
        nodes = [{"toc_node_id": "t1"}, {"toc_node_id": "r1"}]
        edges = [{"toc_node_id": "r1", "hanrei_id": "A"}]
        s2.infer_kind(nodes, edges)
        kinds = {n["toc_node_id"]: n["kind"] for n in nodes}
        self.assertEqual(kinds, {"t1": "heading", "r1": "row"})

    def test_s2_infer_kind_respects_existing(self):
        nodes = [{"toc_node_id": "t1", "kind": "row"}]
        s2.infer_kind(nodes, [])
        self.assertEqual(nodes[0]["kind"], "row")  # 既存 kind は尊重


if __name__ == "__main__":
    unittest.main()
