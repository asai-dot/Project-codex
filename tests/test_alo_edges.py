import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codex.alo_edges import transform_node_links, work_uri_for_bib


def _node(text, bib_id="alo:book:manual:title_1", ordinal=3, pub_year=2018):
    return {"bib_id": bib_id, "ordinal": ordinal, "pub_year": pub_year, "text": text}


def test_statute_link_v02_contract():
    node = _node("民法709条の不法行為")
    links = [{"scheme": "jp_statute_ref", "law_id": "129AC0000000089",
              "article": "709", "uri": "egov:129AC0000000089:art:709",
              "confidence": "high", "match_text": "民法709条", "char_start": 0,
              "article_in_egov": True}]
    out = transform_node_links(node, links)
    assert len(out["edges"]) == 1
    e = out["edges"][0]
    assert e["edge_type"] == "interprets"
    assert e["edge_semantics_status"] == "candidate"          # R-01 隔離
    assert e["assertion_mode"] == "implicit"                   # R-02 (not vendor_implicit)
    assert e["extraction_method"] == "vendor_rule"
    assert e["assertion_confidence"] is None
    assert e["weight"] == 1.0
    assert e["weight_basis"] == "relevance_strength_not_truth_confidence"
    assert e["rollout_status"] == "initial"                    # high
    # R-03 temporal 遮断
    assert e["valid_from"] is None
    assert e["as_of_status"] == "coarse_proxy" and e["as_of_value"] == "2018-01-01"
    assert e["resolved_law_revision_id"] is None and e["temporal_status"] is None
    assert e["claim_support_eligible"] is False
    # R-04 src provisional
    assert e["src_uri_status"] == "provisional" and e["canonical_work_uri"] is None
    assert e["source_role"] == "toc_signal"
    assert e["dedup_key"]                                       # #9
    # #7 evidence reproducibility
    p = out["pointers"][0]
    assert p["bib_toc_node_key"] == "alo:book:manual:title_1:3"
    assert p["payload_hash"] and p["parser_version"].startswith("alo_edges@")


def test_medium_quarantined_and_low_excluded():
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
    assert len(out["edges"]) == 1
    assert out["edges"][0]["weight"] == 0.7
    assert out["edges"][0]["rollout_status"] == "quarantine_sample_required"   # #5
    assert out["skipped_low"] == 1


def test_case_candidate_resolution_queue_fields():
    node = _node("最判平成20年1月28日を題材に")
    links = [{"scheme": "jp_case_citation", "match_text": "最判平成20年1月28日",
              "char_start": 0, "court": "最判", "era": "平成",
              "cite_key": "最判平成20年1月28日"}]
    out = transform_node_links(node, links)
    assert out["edges"] == []                                  # 判例は edge 化しない
    c = out["case_candidates"][0]
    assert c["candidate_status"] == "unresolved"
    assert c["matched_case_uri"] is None
    assert c["review_required"] is True
    assert c["source_text"] == node["text"]


def test_dedup_same_statute_in_one_node():
    node = _node("民法709条と民法709条")
    link = {"scheme": "jp_statute_ref", "law_id": "129AC0000000089", "article": "709",
            "uri": "egov:129AC0000000089:art:709", "confidence": "high",
            "match_text": "民法709条", "char_start": 0, "article_in_egov": True}
    link2 = dict(link, char_start=6)
    out = transform_node_links(node, [link, link2])
    # 別 span は別 evidence だが、同一(src,dst,type,node)で dedup_key が分かれるのは span_hash 差
    # → 同一語の二重出現は別 span。ここでは少なくとも重複爆発しないことを確認
    assert len(out["edges"]) <= 2


def test_work_uri_keeps_alo_prefix():
    assert work_uri_for_bib("alo:book:manual:title_9").startswith("alo:book:manual")
    assert work_uri_for_bib("NOBN_x").startswith("alo:work:bencom:")
