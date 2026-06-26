"""floor_link の単体テスト (stdlib のみ).

_clean_chunks: 接続詞分割 / _shared_concepts: 共有概念抽出 / link: 定款×登記の錨検出。
実行: ``python tests/test_floor_link.py``
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from floor_link import _clean_chunks, _shared_concepts, link  # noqa: E402

_PASS = 0
_FAIL = 0


def check(cond: bool, msg: str) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        print(f"  ❌ FAIL: {msg}")


# ── _clean_chunks ──────────────────────────────────────────────────────────

def test_conjunction_split():
    """及び/又は で割れた漢字チャンクが別々に出る。"""
    chunks = _clean_chunks("氏名又は名称及び住所")
    check("氏名" in chunks, "氏名が chunk に出る")
    check("名称" in chunks, "名称が chunk に出る")
    check("住所" in chunks, "住所が chunk に出る")
    # 接続詞自体は出ない
    check("氏名又は名称" not in chunks, "接続詞まみれの長連鎖は chunk に出ない")


def test_stop_words_filtered():
    """_STOP に載る汎用語はチャンクに出ない。"""
    chunks = _clean_chunks("前号の規定に係る事項")
    check("規定" not in chunks, "規定はSTOP")
    check("事項" not in chunks, "事項はSTOP")
    check("前号" not in chunks, "前号はSTOP")


def test_min_len_1char_excluded():
    """1字の漢字はチャンクに出ない(len>=2が条件)。"""
    chunks = _clean_chunks("及び又は")
    check(chunks == [], "接続詞しかないなら空リスト")


def test_clean_chunks_normal_noun():
    """通常の名詞句は素通り。"""
    chunks = _clean_chunks("資本金の額")
    check("資本金" in chunks, "資本金が chunk に出る")


# ── _shared_concepts ───────────────────────────────────────────────────────

def test_exact_match():
    check("商号" in _shared_concepts({"商号", "目的"}, {"商号", "本店"}),
          "完全一致の 商号 を共有概念として返す")


def test_subset_match_takes_shorter():
    """a が b の部分文字列のとき短い方(a)を代表として返す。"""
    shared = _shared_concepts({"資本金"}, {"資本金の額"})
    check("資本金" in shared, "資本金(短) を代表として採用")
    check("資本金の額" not in shared, "長い側は代表にならない")


def test_minlen_2_chars_pass():
    """2字以上の語が通る(デフォルト minlen=2)。"""
    check("商号" in _shared_concepts({"商号"}, {"商号"}), "2字の商号が通る")


def test_minlen_1char_excluded():
    """1字は minlen=2 で弾かれる。"""
    check("名" not in _shared_concepts({"名"}, {"名"}), "1字は弾く")


def test_no_spurious_match():
    """無関係な語の組は空。"""
    check(_shared_concepts({"資本金"}, {"本店"}) == set(), "資本金×本店は共有なし")


# ── link (end-to-end) ──────────────────────────────────────────────────────

_PROC_27 = {
    "label": "定款(27)", "article": "27",
    "items": [
        {"号": "一", "名称": "目的", "aliases": []},
        {"号": "二", "名称": "商号", "aliases": []},
        {"号": "三", "名称": "本店の所在地", "aliases": []},
        {"号": "五", "名称": "発起人の氏名又は名称及び住所", "aliases": []},
    ],
}
_PROC_911 = {
    "label": "設立登記(911)", "article": "911",
    "items": [
        {"号": "一", "名称": "目的", "aliases": []},
        {"号": "二", "名称": "商号", "aliases": []},
        {"号": "三", "名称": "本店及び支店の所在場所", "aliases": []},
        {"号": "五", "名称": "資本金の額", "aliases": []},
        {"号": "十三", "名称": "取締役の氏名", "aliases": ["取締役の氏名"]},
    ],
}


def test_link_produces_shogo_honten():
    """定款×設立登記 で 商号・本店・目的 が錨として出る。"""
    lns = link([_PROC_27, _PROC_911])
    concepts = {ln["concept"] for ln in lns}
    check("商号" in concepts, "商号が錨に出る(定款二号↔登記二号)")
    check("本店" in concepts, "本店が錨に出る(定款三号↔登記三号)")
    check("目的" in concepts, "目的が錨に出る(定款一号↔登記一号)")


def test_link_correct_go_pairs():
    """商号の錨ペアが 二号↔二号 になる。"""
    lns = link([_PROC_27, _PROC_911])
    shogo = [ln for ln in lns if ln["concept"] == "商号"]
    check(len(shogo) == 1, "商号の錨ペアは1組")
    check(shogo[0]["号_a"] == "二" and shogo[0]["号_b"] == "二",
          "商号は 二号↔二号")


def test_link_floor_labels():
    """錨の floor_a/floor_b ラベルが正しい。"""
    lns = link([_PROC_27, _PROC_911])
    shogo = next(ln for ln in lns if ln["concept"] == "商号")
    check(shogo["floor_a"] == "定款(27)", "floor_a は定款")
    check(shogo["floor_b"] == "設立登記(911)", "floor_b は設立登記")


# ── main ──────────────────────────────────────────────────────────────────

def main() -> int:
    tests = [
        test_conjunction_split, test_stop_words_filtered,
        test_min_len_1char_excluded, test_clean_chunks_normal_noun,
        test_exact_match, test_subset_match_takes_shorter,
        test_minlen_2_chars_pass, test_minlen_1char_excluded,
        test_no_spurious_match,
        test_link_produces_shogo_honten, test_link_correct_go_pairs,
        test_link_floor_labels,
    ]
    for t in tests:
        print(f"• {t.__name__}")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
