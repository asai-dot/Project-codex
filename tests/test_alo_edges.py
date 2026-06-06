import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codex.alo_edges import transform_node_links, work_uri_for_bib


def _node(text, bib_id="alo:book:manual:title_1", ordinal=3, pub_year=2018):
    return {"bib_id": bib_id, "ordinal": ordinal, "pub_year": pub_year, "text": text}


def test_statute_link_becomes_interprets_edge():
    node = _node("民法709条の不法行為")
    links = [{"scheme": "jp_statute_ref", "law_id": "129AC0000000089",
              "article": "709", "uri": "egov:129AC0000000089:art:709",
              "confidence": "high", "match_text": "民法709条", "char_start": 0,
              "article_in_egov": True}]
    out = transform_node_links(node, links)
    assert len(out["edges"]) == 1
    e = out["edges"][0]
    assert e["edge_type"] == "interprets"
    assert e["src_type"] == "commentary" and e["dst_type"] == "statute"
    assert e["assertion_mode"] == "vendor_implicit"
    assert e["assertion_confidence"] is None      # llm_inferred 専用 → NULL
    assert e["weight"] == 1.0                       # high
    assert e["dst_uri"] == "egov:129AC0000000089:art:709"
    assert e["valid_from"] == "2018-01-01"          # pub_year proxy
    # Gate-5: evidence + pointer が付く
    assert len(out["edge_evidence"]) == 1
    assert out["edge_evidence"][0]["role"] == "source_field"
    assert len(out["pointers"]) == 1


def test_medium_conf_weight_and_low_excluded():
    node = _node("会社法の改正と特別刑法における刑法")
    links = [
        {"scheme": "jp_statute_ref", "law_id": "417AC0000000086", "article": None,
         "uri": "egov:417AC0000000086", "confidence": "medium",
         "match_text": "会社法", "char_start": 0, "article_in_egov": None},
        {"scheme": "jp_statute_ref", "law_id": "140AC0000000045", "article": None,
         "uri": "egov:140AC0000000045", "confidence": "low",
         "match_text": "刑法", "char_start": 12, "article_in_egov": None},
    ]
    out = transform_node_links(node, links)
    assert len(out["edges"]) == 1                   # low は除外
    assert out["edges"][0]["weight"] == 0.7         # medium
    assert out["skipped_low"] == 1


def test_case_citation_is_resolution_candidate_not_edge():
    node = _node("最判平成20年1月28日を題材に")
    links = [{"scheme": "jp_case_citation", "match_text": "最判平成20年1月28日",
              "char_start": 0, "court": "最判", "era": "平成",
              "cite_key": "最判平成20年1月28日"}]
    out = transform_node_links(node, links)
    assert out["edges"] == []                       # canonical case URI 不能 → edge 化しない
    assert len(out["case_candidates"]) == 1
    c = out["case_candidates"][0]
    assert c["resolution_status"] == "needs_case_uri"
    assert c["intended_edge_type"] == "evaluates"


def test_dedup_same_statute_in_one_node():
    node = _node("民法709条と民法709条")
    link = {"scheme": "jp_statute_ref", "law_id": "129AC0000000089", "article": "709",
            "uri": "egov:129AC0000000089:art:709", "confidence": "high",
            "match_text": "民法709条", "char_start": 0, "article_in_egov": True}
    link2 = dict(link, char_start=6)
    out = transform_node_links(node, [link, link2])
    assert len(out["edges"]) == 1                   # 同一(src,dst,type,valid_from)は1本


def test_work_uri_keeps_alo_prefix():
    assert work_uri_for_bib("alo:book:manual:title_9").startswith("alo:book:manual")
    assert work_uri_for_bib("NOBN_x").startswith("alo:work:bencom:")
