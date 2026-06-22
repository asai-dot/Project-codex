"""Statute-reference grammar, source-type inference, and drafter-claim cues.

Japanese legislative commentary references provisions as 第N条[第N項][第N号]
in arabic (第709条) or kanji (第七百九条), with branch numbers 第三条の二 → 3-2.
Old/new markers (改正前/改正後/新/旧/現行) carry a revision-side hint.

Drafter-claim cues map a commentary sentence to a DD §2.1 change_type. The
classic 確認的(=declares existing law, no change) vs 創設的(=creates new law)
distinction is captured directly.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# kanji numerals -> int (article numbers: up to a few thousand)
# ---------------------------------------------------------------------------
_K_DIGIT = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9}
_K_UNIT = {"十": 10, "百": 100, "千": 1000}


def kanji_to_int(s: str) -> str | None:
    """Convert a kanji/arabic article ordinal to a canonical arabic string.

    Returns None if it cannot be parsed. Mixed forms like 「7百9」 are not
    expected; arabic-only and pure-kanji are handled.
    """
    s = s.strip()
    if s.isdigit():
        return str(int(s))
    # zenkaku digits
    z = s.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    if z.isdigit():
        return str(int(z))
    total, cur = 0, 0
    seen = False
    for ch in s:
        if ch in _K_DIGIT:
            cur = _K_DIGIT[ch]
            seen = True
        elif ch in _K_UNIT:
            unit = _K_UNIT[ch]
            cur = cur if cur != 0 else 1
            total += cur * unit
            cur = 0
            seen = True
        else:
            return None
    total += cur
    return str(total) if seen else None


_NUMTOK = r"[0-9０-９一二三四五六七八九十百千〇零]+"

# optional revision-side marker and (loosely) a law name preceding 第N条
REVISION_MARKER = r"(?:改正後の?|改正前の?|新|旧|現行)?"
LAWNAME = r"(?:[一-龥ぁ-ゖ・]{2,20}法(?:律)?|[一-龥]{2,10}令|憲法)?"

ARTICLE_RE = re.compile(
    rf"(?P<marker>{REVISION_MARKER})(?P<lawname>{LAWNAME})"
    rf"第(?P<article>{_NUMTOK})条(?:の(?P<branch>{_NUMTOK}))?"
    rf"(?:第(?P<para>{_NUMTOK})項)?(?:第(?P<item>{_NUMTOK})号)?"
)


def article_path(m: re.Match) -> str | None:
    art = kanji_to_int(m.group("article"))
    if art is None:
        return None
    if m.group("branch"):
        br = kanji_to_int(m.group("branch"))
        if br is None:
            return None
        art = f"{art}-{br}"
    path = f"art:{art}"
    if m.group("para"):
        p = kanji_to_int(m.group("para"))
        if p:
            path += f":para:{p}"
    if m.group("item"):
        it = kanji_to_int(m.group("item"))
        if it:
            path += f":item:{it}"
    return path


def revision_side(prefix: str) -> str:
    """Infer revision side from the marker+lawname prefix.

    The lawname token can absorb a leading 旧/新/現行 (e.g. 「旧民法」), so we
    scan the whole prefix rather than relying on the marker group alone.
    """
    prefix = prefix or ""
    if "改正後" in prefix:
        return "after"
    if "改正前" in prefix:
        return "before"
    if "現行" in prefix:
        return "current"
    # bare 新/旧 only when adjacent to 法/令/憲法 or at the very start
    if prefix.startswith("旧") or "旧民法" in prefix or "旧法" in prefix:
        return "before"
    if prefix.startswith("新") or "新民法" in prefix or "新法" in prefix:
        return "after"
    return "unknown"


# ---------------------------------------------------------------------------
# source_type inference (genre -> §2.4 source_type, all tier 2)
# ---------------------------------------------------------------------------
SOURCE_TIER = {
    "legislative_drafter": 2,
    "ministry_commentary": 2,
    "legislative_record": 2,
}
DEFAULT_SOURCE_TYPE = "legislative_drafter"


def infer_source_type(hint: str | None) -> str:
    if not hint:
        return DEFAULT_SOURCE_TYPE
    h = hint
    if any(k in h for k in ("国会", "審議", "委員会会議録", "議事録", "答弁")):
        return "legislative_record"
    if any(k in h for k in ("通達", "所管庁", "ガイドライン", "解釈通知", "省令解説")):
        return "ministry_commentary"
    # 一問一答 / 逐条解説 / 立案担当者 / 部会資料 -> drafter
    return "legislative_drafter"


# ---------------------------------------------------------------------------
# drafter-claim cues -> DD §2.1 change_type  (precision-first; medium ceiling)
# (pattern_id, regex, change_type, confidence, confirmatory_flag)
# ---------------------------------------------------------------------------
CUES = [
    # --- drafter claims NO substantive change (the load-bearing tier-2 claim) -
    ("no_change_jisshitsu",
     re.compile(r"実質的な?(?:変更|改正)(?:は|を伴うもので)?(?:ない|なく|はない)"
                r"|実質的に(?:は)?変わら(?:ない|ず)"),
     "no_substantive_change", "medium", True),
    ("no_change_juurai",
     re.compile(r"従来(?:と同様|どおり|の(?:解釈|取扱い)を変更するもので(?:は)?ない)"
                r"|趣旨を変更するもので(?:は)?ない|変更するものではな(?:い|く)"),
     "no_substantive_change", "medium", True),
    ("confirmatory",
     re.compile(r"確認的(?:に)?(?:規定|定めた|明らかにした)|確認規定(?:である|として)"),
     "no_substantive_change", "medium", True),
    # --- clarification only -------------------------------------------------
    ("clarification",
     re.compile(r"明確化(?:した|するもの|を図)|明文化(?:した|するもの)"
                r"|表現を改めた(?:にすぎ|ものであり)|文言を整理"),
     "wording_clarification", "medium", True),
    # --- requirement changes ------------------------------------------------
    ("req_added",
     re.compile(r"新たに.{0,24}?(?:要件|ことを要件)と(?:した|する)"
                r"|要件を(?:加え|付加)|.{0,16}?を(?:要する|必要とする)こととした"),
     "requirement_added", "medium", False),
    ("req_removed",
     re.compile(r".{0,16}?を要しないこととした|.{0,16}?を不要と(?:した|する)"
                r"|要件を(?:削除|撤廃)"),
     "requirement_removed", "medium", False),
    # --- effect / scope / subject / procedure ------------------------------
    ("effect_changed",
     re.compile(r"効(?:果|力)を(?:改め|変更)|法律効果を.{0,12}?改めた"),
     "effect_changed", "medium", False),
    ("scope_expansion",
     re.compile(r"対象を(?:拡大|拡げ|広げ)|範囲を(?:拡大|拡げ|広げ)"
                r"|.{0,16}?も(?:含む|対象とする)こととした"),
     "scope_expansion", "medium", False),
    ("scope_reduction",
     re.compile(r"対象を(?:限定|縮小)|範囲を(?:狭め|限定|縮小)"
                r"|.{0,16}?を(?:除外|対象から除)"),
     "scope_reduction", "medium", False),
    ("subject_changed",
     re.compile(r"(?:義務|権利|規律)の(?:主体|名宛人)を(?:改め|変更)"),
     "subject_changed", "low", False),
    ("procedure_changed",
     re.compile(r"手続(?:を|的な.{0,8}?)(?:改め|変更)"),
     "procedure_changed", "low", False),
    # --- general substantive change (positive form; runs after specific cues
    #     and after the no_change cues, so 「変更するものではない」 cannot leak) -
    ("substantive_kaitei",
     re.compile(r"規律を(?:改め|変更)|(?:取扱い|解釈)を変更するもの(?:である|と(?:考え|解))"
                r"|改正により.{0,16}?を(?:改め|変更)(?:した|するもの)"),
     "substantive_change_unspecified", "medium", False),
    # --- constitutive: creates new law (創設的) -> unspecified substantive ----
    ("constitutive",
     re.compile(r"創設的(?:に)?(?:規定|な規定)|新設(?:した|された|の規定)"
                r"|新たに(?:設けた|規定(?:した|を設けた))"),
     "substantive_change_unspecified", "low", False),
]

CHANGE_TYPE_DOMAIN = {
    "no_substantive_change", "wording_clarification", "scope_expansion",
    "scope_reduction", "requirement_added", "requirement_removed",
    "effect_changed", "subject_changed", "procedure_changed", "efficacy_change",
    "substantive_change_unspecified", "disputed", "unknown",
}
