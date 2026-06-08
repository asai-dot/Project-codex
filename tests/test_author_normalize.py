import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codex.author_normalize import normalize_author, author_keys


def test_basic():
    r = normalize_author("仲道祐樹")
    assert r["display"] == "仲道祐樹"
    assert r["key"] == "仲道祐樹"
    assert r["roles"] == []


def test_strip_internal_space():
    assert normalize_author("山口　厚")["key"] == "山口厚"
    assert normalize_author("山口 厚")["key"] == "山口厚"


def test_honorific_stripped():
    assert normalize_author("田中亘先生")["display"] == "田中亘"
    assert normalize_author("神田秀樹氏")["display"] == "神田秀樹"
    assert normalize_author("潮見佳男ほか")["display"] == "潮見佳男"


def test_affiliation_paren_removed():
    r = normalize_author("山田太郎（東京大学）")
    assert r["display"] == "山田太郎"


def test_role_prefix():
    r = normalize_author("司会・宮川光治")
    assert r["display"] == "宮川光治"
    assert "司会" in r["roles"]


def test_role_only():
    r = normalize_author("司会")
    assert r["display"] == ""
    assert r["key"] == ""
    assert "司会" in r["roles"]


def test_nfkc_fullwidth_latin():
    r = normalize_author("ＡＢＣ")
    assert r["key"] == "abc"


def test_author_keys_dedup_and_drop_empty():
    keys = author_keys(["司会", "神田秀樹", "神田　秀樹", "藤田友敬"])
    # 司会 -> empty (dropped), 神田秀樹 重複は 1 回
    assert keys == ["神田秀樹", "藤田友敬"]
