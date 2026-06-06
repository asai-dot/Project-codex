"""漢数字・全角数字を整数へ変換するユーティリティ.

条文番号 (例: 「第七百九条」「四二三」「４２３」) を 709 / 423 に正規化するために使う。
位取り表記 (七百九 = 709) と単純桁並べ (七〇九 = 709) の両方に対応する。
"""

from __future__ import annotations

# 全角数字 → 半角
_ZEN2HAN = {ord("０") + i: str(i) for i in range(10)}

# 漢数字 (単純桁)
_KANJI_DIGIT = {
    "〇": 0, "零": 0,
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9,
}
# 位 (myriad 以下)
_KANJI_UNIT = {"十": 10, "百": 100, "千": 1000}

# 条番号として現れうる文字の集合 (枝番の「の」を除く)
KANJI_NUM_CHARS = "〇零一二三四五六七八九十百千"


def zenkaku_to_hankaku_digits(s: str) -> str:
    """全角数字を半角数字へ。それ以外の文字はそのまま。"""
    return s.translate(_ZEN2HAN)


def kanji_to_int(s: str) -> int | None:
    """漢数字文字列を int へ。解釈不能なら None.

    対応:
      - 位取り: 七百九 -> 709, 千二百三十四 -> 1234, 二十 -> 20
      - 桁並べ: 七〇九 -> 709 (位取り文字を一切含まない場合のみ)
      - 単独位: 十 -> 10, 百 -> 100
    """
    s = (s or "").strip()
    if not s:
        return None

    has_unit = any(c in _KANJI_UNIT for c in s)

    # 桁並べ表記 (位文字を含まない) は各桁を連結
    if not has_unit:
        digits = []
        for c in s:
            if c not in _KANJI_DIGIT:
                return None
            digits.append(str(_KANJI_DIGIT[c]))
        return int("".join(digits)) if digits else None

    # 位取り表記
    total = 0
    section = 0  # 直近の数 (位を掛ける対象)
    seen = False
    for c in s:
        if c in _KANJI_DIGIT:
            section = _KANJI_DIGIT[c]
            seen = True
        elif c in _KANJI_UNIT:
            unit = _KANJI_UNIT[c]
            # 「十」のように数が先行しない場合は 1 とみなす
            total += (section if section != 0 else 1) * unit
            section = 0
            seen = True
        else:
            return None
    total += section
    return total if seen else None


def normalize_article_number(s: str) -> str | None:
    """条番号の文字列表現を egov の article 形式 (例: "709", "100_11") へ正規化.

    入力例:
      "七百九"        -> "709"
      "４２３"        -> "423"
      "三百六十二の二" -> "362_2"   (枝番「の」対応)
      "100の11"       -> "100_11"
    """
    s = (s or "").strip()
    if not s:
        return None
    # 枝番の「の」/「ノ」で分割
    import re

    parts = re.split(r"[のノ]", s)
    out = []
    for part in parts:
        part = part.strip()
        if not part:
            return None
        han = zenkaku_to_hankaku_digits(part)
        if han.isdigit():
            out.append(str(int(han)))
        else:
            val = kanji_to_int(part)
            if val is None:
                return None
            out.append(str(val))
    return "_".join(out)
