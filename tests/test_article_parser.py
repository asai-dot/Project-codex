import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codex.article_parser import parse_article, parse_journal, iter_toc_nodes


def k(label, level=1, ordinal=1):
    return parse_article(label, level, ordinal)


def test_section_header_bracket():
    r = k("【特集】特別刑法の世界")
    assert r["kind"] == "section_header"
    assert r["section"] == "【特集】特別刑法の世界"


def test_section_header_like_pattern():
    assert k("第1部　民事手続法の現在")["kind"] == "section_header"
    assert k("第2編　債権")["kind"] == "section_header"
    assert k("序章　問題の所在")["kind"] == "section_header"
    assert k("資料編")["kind"] == "section_header"


def test_basic_article():
    r = k("特別刑法の調べ方、学び方、その面白さ　仲道祐樹")
    assert r["kind"] == "article"
    assert r["title"] == "特別刑法の調べ方、学び方、その面白さ"
    assert r["authors"] == ["仲道祐樹"]


def test_multiple_authors_separators():
    assert k("タイトル　著者A・著者B")["authors"] == ["著者A", "著者B"]
    assert k("タイトル　著者A／著者B／著者C")["authors"] == ["著者A", "著者B", "著者C"]
    assert k("タイトル　著者A、著者B")["authors"] == ["著者A", "著者B"]


def test_title_with_internal_zsp_uses_last():
    r = k("アメリカ法律事情　その３ ── 集団訴訟の最前線　樋口範雄")
    assert r["kind"] == "article"
    assert r["authors"] == ["樋口範雄"]
    assert r["title"].endswith("集団訴訟の最前線")


def test_section_header_with_zsp_not_article():
    # 第1部　民事手続法の現在 は全角空白を含むが section と判定されるべき
    r = k("第1部　民事手続法の現在")
    assert r["kind"] == "section_header"


def test_boilerplate_other():
    for w in ["編集後記", "奥付", "目次", "次号予告"]:
        assert k(w)["kind"] == "other"


def test_series_tag_extracted():
    r = k("表現の自由の現代的展開（連載第3回）　長谷部恭男")
    assert r["kind"] == "article"
    assert r["series_tag"] == "連載第3回"
    assert "（連載第3回）" not in r["title"]


def test_dialogue_keeps_roles_in_authors():
    r = k("対談　会社法改正のゆくえ　司会・神田秀樹・藤田友敬")
    assert r["kind"] == "article"
    assert r["authors"] == ["司会", "神田秀樹", "藤田友敬"]


def test_no_zsp_is_unknown():
    assert k("タイトルだけで著者なし")["kind"] == "unknown"


def test_empty_is_unknown():
    assert k("")["kind"] == "unknown"


def test_author_only_after_zsp_still_parses():
    # 「あ」のような単独見出しは全角空白なし→unknown
    assert k("あ")["kind"] == "unknown"


def test_nested_toc_flatten():
    toc = [
        {"label": "親", "level": 1, "children": [
            {"label": "子1　著者X"}, {"label": "子2　著者Y"}]},
    ]
    nodes = list(iter_toc_nodes(toc))
    labels = [n[0] for n in nodes]
    assert labels == ["親", "子1　著者X", "子2　著者Y"]
    # children は level+1
    assert nodes[1][1] == 2


def test_parse_journal_section_carry():
    journal = {
        "title": "テスト誌",
        "toc": [
            {"label": "【特集】X", "level": 1},
            {"label": "論文1　著者A", "level": 1},
            {"label": "論文2　著者B", "level": 1},
        ],
    }
    rows = parse_journal(journal, "t1")
    assert rows[0]["kind"] == "section_header"
    assert rows[1]["section"] == "【特集】X"
    assert rows[2]["section"] == "【特集】X"
    assert [r["ordinal"] for r in rows] == [1, 2, 3]  # 1 origin
