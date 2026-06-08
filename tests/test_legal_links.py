import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codex.jp_numerals import kanji_to_int, normalize_article_number
from codex.egov_index import EgovIndex
from codex.legal_links import (
    extract_statute_refs,
    extract_case_citations,
)

EGOV = os.path.join(os.path.dirname(__file__), "..", "data", "egov",
                    "egov_statutory_definitions_ALL.jsonl")

_index = None


def index():
    global _index
    if _index is None:
        _index = EgovIndex.load(EGOV)
    return _index


# --- jp_numerals ---

def test_kanji_positional():
    assert kanji_to_int("七百九") == 709
    assert kanji_to_int("千二百三十四") == 1234
    assert kanji_to_int("二十") == 20
    assert kanji_to_int("十") == 10
    assert kanji_to_int("百九十九") == 199


def test_kanji_sequential():
    assert kanji_to_int("七〇九") == 709


def test_normalize_article_number():
    assert normalize_article_number("七百九") == "709"
    assert normalize_article_number("４２３") == "423"
    assert normalize_article_number("三百六十二の二") == "362_2"
    assert normalize_article_number("100の11") == "100_11"


# --- egov index ---

def test_index_core_laws():
    idx = index()
    assert idx.name_to_law.get("民法") == "129AC0000000089"
    assert idx.name_to_law.get("会社法") == "417AC0000000086"
    assert idx.name_to_law.get("刑法") == "140AC0000000045"


# --- statute refs ---

def test_statute_ref_with_kanji_article():
    refs = extract_statute_refs("民法第七百九条の不法行為責任", index())
    assert len(refs) == 1
    r = refs[0]
    assert r["law_id"] == "129AC0000000089"
    assert r["article"] == "709"
    assert r["uri"] == "egov:129AC0000000089:art:709"


def test_statute_ref_arabic_article():
    refs = extract_statute_refs("会社法423条の取締役の責任", index())
    assert refs[0]["article"] == "423"
    assert refs[0]["uri"] == "egov:417AC0000000086:art:423"


def test_statute_ref_branch_article():
    refs = extract_statute_refs("会社法第三百六十二条の二の特則", index())
    assert refs[0]["article"] == "362_2"


def test_statute_ref_without_article():
    refs = extract_statute_refs("労働基準法の解釈をめぐる", index())
    assert len(refs) == 1
    assert refs[0]["article"] is None
    assert refs[0]["uri"] == "egov:322AC0000000049"


def test_greedy_longest_law_name():
    # 「行政手続法」は「行政」等の短い名でなく最長一致される
    refs = extract_statute_refs("行政手続法第十四条事件", index())
    names = [r["law_name"] for r in refs]
    assert "行政手続法" in names
    assert refs[0]["article"] == "14"


# --- case citations ---

def test_case_citation_supreme():
    cites = extract_case_citations("最判平成20年1月28日を題材に")
    assert len(cites) == 1
    assert cites[0]["court"] == "最判"
    assert cites[0]["era"] == "平成"
    assert cites[0]["scheme"] == "jp_case_citation"


def test_case_citation_grand_bench():
    cites = extract_case_citations("最大判昭和60年3月27日租税訴訟")
    assert cites[0]["court"] == "最大判"


def test_case_citation_district():
    cites = extract_case_citations("東京地判令和2年9月30日の意義")
    assert len(cites) == 1
    assert cites[0]["era"] == "令和"
    assert cites[0]["court"] == "東京地判"


def test_case_citation_no_hiragana_prefix():
    # 地名 prefix は漢字のみ。ひらがな「をめぐる」を巻き込まない
    cites = extract_case_citations("解釈をめぐる東京地判令和2年9月30日の意義")
    assert len(cites) == 1
    assert cites[0]["match_text"].startswith("東京地判")
    assert "をめぐる" not in cites[0]["match_text"]


# --- confidence ---

def test_confidence_high_with_article():
    refs = extract_statute_refs("民法709条", index())
    assert refs[0]["confidence"] == "high"


def test_confidence_low_embedded_short_name():
    # 「特別刑法」中の「刑法」は複合語誤検出として low
    refs = extract_statute_refs("特別刑法と人身犯", index())
    hits = [r for r in refs if r["law_name"] == "刑法"]
    assert hits and hits[0]["confidence"] == "low"


def test_confidence_medium_bare_boundary():
    refs = extract_statute_refs("会社法の改正について", index())
    hits = [r for r in refs if r["law_name"] == "会社法"]
    assert hits and hits[0]["confidence"] == "medium"
