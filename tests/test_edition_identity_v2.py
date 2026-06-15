"""edition_identity_v2 強化版 manifestation 同定の単体テスト (Phase0 実例で凍結)。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from edition_identity import INSUFFICIENT, RESOLVED_SAME, SUSPECTED_DIFFERENT  # noqa: E402
from edition_identity_v2 import classify_edition_identity_v2  # noqa: E402


def _s(title, year="", publisher="", page_count=None):
    return {"title": title, "year": year, "publisher": publisher, "page_count": page_count}


def test_single_source_insufficient():
    assert classify_edition_identity_v2([_s("民法")])["status"] == INSUFFICIENT


def test_edition_number_conflict_is_suspected():
    r = classify_edition_identity_v2([_s("刑法各論講義 第7版", "2020"),
                                      _s("刑法各論講義 (第4版)", "2007")])
    assert r["status"] == SUSPECTED_DIFFERENT


def test_cosmetic_is_resolved_same():
    # 全半角・隅付き括弧の差のみ → 同一。
    r = classify_edition_identity_v2([_s("特許法 第2版", "2017", "有斐閣"),
                                      _s("特許法〔第2版〕", "2017", "有斐閣")])
    assert r["status"] == RESOLVED_SAME


def test_subtitle_difference_is_resolved_same():
    r = classify_edition_identity_v2([
        _s("実務裁判例 交通事故における過失相殺率 自転車・駐車場事故を中心にして", "2020"),
        _s("実務裁判例 交通事故における過失相殺率", "2020")])
    assert r["status"] == RESOLVED_SAME


def test_year_pm1_is_noise_resolved_same():
    # 同一『第36版』が 2022 vs 2023 → 重版扱い。
    r = classify_edition_identity_v2([_s("意匠出願のてびき 第36版", "2022"),
                                      _s("意匠出願のてびき 第36版", "2023")])
    assert r["status"] == RESOLVED_SAME


def test_year_gap2_no_version_is_suspected():
    r = classify_edition_identity_v2([_s("アメリカにおける第二の親の決定", "2022"),
                                      _s("アメリカにおける第二の親の決定", "2020")])
    assert r["status"] == SUSPECTED_DIFFERENT


def test_marker_asymmetry_is_insufficient():
    r = classify_edition_identity_v2([_s("家族法", "2020"),
                                      _s("家族法〔第4版〕", "2020")])
    assert r["status"] == INSUFFICIENT


def test_page_count_divergence_blocks_confirm():
    # 同一タイトルでも頁が大きく違えば確定しない (Required note 2)。
    r = classify_edition_identity_v2([_s("会社法", "2020", "有斐閣", 600),
                                      _s("会社法", "2020", "有斐閣", 300)])
    assert r["status"] == INSUFFICIENT


def test_publisher_divergence_blocks_confirm():
    r = classify_edition_identity_v2([_s("会社法", "2020", "有斐閣"),
                                      _s("会社法", "2020", "別の出版社")])
    assert r["status"] == INSUFFICIENT
