"""phase0_inventory の版判定ロジック単体テスト (実データ点検で観測した実例を凍結)。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from phase0_inventory import (  # noqa: E402
    edition_signature,
    is_real_suspect,
    norm_isbn,
    parse_year,
    title_diff_kind,
)


@pytest.mark.parametrize("title,sig", [
    ("刑法各論講義 第7版", "v7"),
    ("刑法各論講義 (第4版)", "v4"),
    ("環境訴訟法［第２版］", "v2"),       # 全角 + 隅付き
    ("労働法[第2版]", "v2"),
    ("家族法〔第4版〕", "v4"),
    ("業務委託契約書作成のポイント〈第２版〉", "v2"),
    ("労働法 第13版", "v13"),            # 2桁
    ("金融法講義 新版", "rev"),
    ("契約法〔新版〕", "rev"),
    ("国際取引法", ""),                  # 版表記なし
])
def test_edition_signature(title, sig):
    assert edition_signature(title) == sig


def test_title_diff_kind_cosmetic():
    # 全半角・読点・隅付き括弧だけの差 → 同一
    assert title_diff_kind("特許法 第2版", "特許法〔第2版〕") == "cosmetic"
    assert title_diff_kind(
        "第３版 Ｑ＆Ａ 遺言・信託 税金、執行",
        "第3版 Q&A 遺言・信託 税金,執行") == "cosmetic"


def test_title_diff_kind_edition_number_conflict():
    assert title_diff_kind("刑法各論講義 第7版", "刑法各論講義 (第4版)") == "edition_number_conflict"
    assert title_diff_kind("商標 第6版", "商標 第5版") == "edition_number_conflict"


def test_title_diff_kind_subtitle():
    assert title_diff_kind(
        "実務裁判例 交通事故における過失相殺率 自転車・駐車場事故を中心にして",
        "実務裁判例 交通事故における過失相殺率") == "subtitle_difference"


def test_title_diff_kind_marker_asymmetry():
    assert title_diff_kind("家族法", "家族法〔第4版〕") == "edition_marker_asymmetry"


def _row(reason, **kw):
    base = {"status": "suspected_different_manifestation", "reason": reason,
            "title_diff_kind": None, "year_gap": None,
            "legallib_edition_sig": "", "canonical_edition_sig": ""}
    base.update(kw)
    return base


def test_is_real_suspect_filters_artifacts():
    assert is_real_suspect(_row("title divergence", title_diff_kind="cosmetic")) is False
    assert is_real_suspect(_row("title divergence", title_diff_kind="subtitle_difference")) is False
    assert is_real_suspect(_row("title divergence", title_diff_kind="edition_number_conflict")) is True


def test_is_real_suspect_year_rule():
    # ±1 年は弱信号
    assert is_real_suspect(_row("year divergence", year_gap=1)) is False
    # 年差≧2 は要レビュー
    assert is_real_suspect(_row("year divergence", year_gap=8)) is True
    # 版番号一致なら年差が大きくても重版扱い (= not real)
    assert is_real_suspect(_row("year divergence", year_gap=8,
                                legallib_edition_sig="v3", canonical_edition_sig="v3")) is False


def test_is_real_suspect_resolved_same():
    assert is_real_suspect({"status": "resolved_same_manifestation", "reason": "x"}) is False


def test_norm_isbn_and_year():
    assert norm_isbn("978-4-8178-4197-1") == "9784817841971"
    assert parse_year("2014年 11月") == "2014"
    assert parse_year("2014-11-28") == "2014"
    assert parse_year("") == ""
