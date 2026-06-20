"""make_edition_adversarial_gold — DD-EDIDENT-001-IMPL H5 の独立 adversarial gold 生成。

監査 H5: 回帰 oracle が classifier 自身の補助関数と循環している (件数固定はできても意味は
独立検証できない)。本ジェネレータは **classifier から独立な人手 truth** を符号化する。
各ケースは raw fields a/b・期待ラベル・理由・class・reviewer・決定日を固定する。

監査 §3 H5 が要求する最低 10 class を双方向 (true same / true different) で網羅。
合成データのみ (実書名でない) ・stdlib のみ・決定的。
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "tests" / "golden" / "edition" / "adversarial_gold.jsonl"

REVIEWER = "CC (DD-EDIDENT-001-IMPL corrective patch)"
DECIDED = "2026-06-17"

S_SAME = "resolved_same_manifestation"
S_DIFF = "suspected_different_manifestation"
S_REVIEW = "insufficient_evidence"


def _c(case_id, klass, a, b, expected, why):
    return {"case_id": case_id, "class": klass, "a": a, "b": b,
            "expected": expected, "why": why, "reviewer": REVIEWER, "decided": DECIDED}


def cases() -> list[dict]:
    return [
        # class 1: 同一タイトル・異 ISBN → 別 manifestation。
        _c("isbn_mismatch", "1_isbn",
           {"title": "民法総論", "isbn": "9784000000001", "year": "2020"},
           {"title": "民法総論", "isbn": "9784000000002", "year": "2020"},
           S_DIFF, "異なる ISBN は別 manifestation。title 一致でも merge 不可。"),
        # class 2: explicit edition フィールド不一致。
        _c("explicit_edition_mismatch", "2_edition_field",
           {"title": "会社法", "isbn": "X", "edition": "第2版", "year": "2019"},
           {"title": "会社法", "isbn": "X", "edition": "第3版", "year": "2021"},
           S_DIFF, "明示 edition 第2版 vs 第3版 は別版。"),
        # class 3: volume 不一致。
        _c("volume_mismatch", "3_volume",
           {"title": "判例コンメンタール", "isbn": "X", "volume": "上巻", "year": "2020"},
           {"title": "判例コンメンタール", "isbn": "X", "volume": "下巻", "year": "2020"},
           S_DIFF, "上巻 vs 下巻 は別物理単位。"),
        # class 4: title containment・ISBN 不明 → positive 不可で review。
        _c("title_containment_no_isbn", "4_containment",
           {"title": "民法", "year": "2020"},
           {"title": "民法判例百選", "year": "2020"},
           S_REVIEW, "substring は positive 同一性証拠でない。独立 id が無ければ review。"),
        # class 5: 同一 marker・大きな年乖離 (ISBN 不明) → 別版疑い。
        _c("same_sig_large_year_gap", "5_year_gap",
           {"title": "刑法 改訂版", "publisher": "甲社", "year": "2005"},
           {"title": "刑法 改訂版", "publisher": "甲社", "year": "2025"},
           S_DIFF, "edition signature 一致でも 20 年差は別版 (H3: signature は年免除しない)。"),
        # class 6: marker の prefix/suffix 移動 = 同一本 (ISBN 一致)。
        _c("marker_move_same", "6_marker_move",
           {"title": "〔改訂版〕物権法", "isbn": "9784111111111", "year": "2020"},
           {"title": "物権法（改訂版）", "isbn": "9784111111111", "year": "2020"},
           S_SAME, "同 ISBN・marker 位置差のみ → 同一 (H4: false split しない)。"),
        # class 7a: 異なる版 family (3訂版 vs 補訂2版) → 別版。
        _c("tei_vs_hotei", "7_grammar_diff",
           {"title": "行政法 3訂版", "publisher": "甲社", "year": "2020"},
           {"title": "行政法 補訂2版", "publisher": "甲社", "year": "2020"},
           S_DIFF, "3訂版 と 補訂2版 は別 revision family (H4: 一律 rev に潰さない)。"),
        # class 7b: 同一 family・同番号 (補訂2版 同士)・ISBN 一致 → 同一。
        _c("same_grammar_same", "7_grammar_same",
           {"title": "行政法 補訂2版", "isbn": "9784222222222", "year": "2020"},
           {"title": "行政法〔補訂2版〕", "isbn": "9784222222222", "year": "2020"},
           S_SAME, "同 ISBN・同 marker (補訂2版) → 同一。"),
        # class 8: 和暦と西暦の混在 (parse error) → review。
        _c("wareki_parse_error", "8_year_parse",
           {"title": "労働法", "publisher": "乙社", "year": "平成20年"},
           {"title": "労働法", "publisher": "乙社", "year": "2008"},
           S_REVIEW, "和暦は parse_error。重要 field の parse_error は silent same にしない (H8)。"),
        # class 9: 未知 marker → review。
        _c("unknown_marker", "9_unknown_marker",
           {"title": "税法 特装版", "year": "2020"},
           {"title": "税法", "year": "2020"},
           S_REVIEW, "未知の版様トークン (特装版) は unknown_edition_marker で review (H4)。"),
        # class 9b: malformed / missing fields → positive 不可で review。
        _c("missing_fields", "9_missing",
           {"title": "知財法"},
           {"title": "知財法"},
           S_REVIEW, "year/publisher/isbn 全欠 → positive evidence 不足で review。"),
        # class 10a: true same (ISBN 一致・年差±1 reprint)。
        _c("true_same_isbn_reprint", "10_true_same",
           {"title": "国際法", "isbn": "9784333333333", "year": "2020"},
           {"title": "国際法", "isbn": "9784333333333", "year": "2021"},
           S_SAME, "同 ISBN・±1 年は reprint → 同一。"),
        # class 10b: true same (ISBN 無・核一致+publisher+page の複数信号)。
        _c("true_same_multi_signal", "10_true_same_signals",
           {"title": "憲法", "publisher": "丙社", "year": "2020", "page_count": 500},
           {"title": "憲法", "publisher": "丙社", "year": "2020", "page_count": 503},
           S_SAME, "核一致 + publisher 一致 + page 近接 (複数独立信号) → 同一。"),
        # class 10c: true different (title edition 番号衝突)。
        _c("true_diff_edition_number", "10_true_diff",
           {"title": "民事訴訟法 第7版", "publisher": "丁社", "year": "2020"},
           {"title": "民事訴訟法 第4版", "publisher": "丁社", "year": "2010"},
           S_DIFF, "title 由来 第7版 vs 第4版 = 別版。"),
        # class 補: cosmetic 括弧差・ISBN 一致 → 同一。
        _c("cosmetic_same_isbn", "1_cosmetic",
           {"title": "特許法〔第2版〕", "isbn": "9784444444444", "year": "2017"},
           {"title": "特許法 第2版", "isbn": "9784444444444", "year": "2017"},
           S_SAME, "同 ISBN・隅付き括弧差のみ → 同一。"),
        # class 補: publisher 不一致 (ISBN 不明) → review。
        _c("publisher_mismatch", "8_publisher",
           {"title": "民法", "publisher": "甲社", "year": "2020"},
           {"title": "民法", "publisher": "乙社", "year": "2020"},
           S_REVIEW, "publisher 不一致は確定不可 → review。"),
    ]


def main() -> int:
    rows = cases()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    ids = [r["case_id"] for r in rows]
    assert len(ids) == len(set(ids)), "case_id 重複"
    print(json.dumps({"out": str(OUT.relative_to(Path.cwd())), "cases": len(rows),
                      "classes": sorted({r["class"] for r in rows})}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
