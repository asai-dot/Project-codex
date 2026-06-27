#!/usr/bin/env python3
"""case_link_map.py — 本文 mention を正典 alo_edges candidate に写す決定関数 (DD-CASELINK-001 v0.2)。

雑誌・文献の本文から取り出した「(記事中の判例参照, 役割)」を、35_link_layer 正典の
edge_type / assertion_mode / stance / evidence へ **決定的に** 割り当てる。設計を実行可能化し
ドリフトを止めるための fixture レベル参照実装。**識別(merge)はしない・実データに触れない・read-only。**

正典整合(self-consistency):
- edge_type は case_vocab.COMMENTARY_TO_CASE_EDGE_TYPES のみ (evaluates/review_chain/compares)。
- assertion_mode は vendor_explicit / vendor_implicit のみ。**llm_inferred は emit しない**(PoC DB制約)。
- stance は supporting/contrasting/neutral。strength は本文由来のとき 'implicit'。
- 自動確定(route=auto)は **masthead由来(vendor_explicit) かつ 決定的 bind** のときだけ。
  本文由来・fuzzy・未解決はすべて review。未知シグナルは fail-closed(drop)。
"""
from __future__ import annotations
import sys
import case_vocab as V

# このモジュールが emit しうる値域(整合テストが ⊆ 正典 を検査する)
EMITTABLE_EDGE_TYPES = frozenset({"evaluates", "review_chain", "compares"})
EMITTABLE_ASSERTION_MODES = frozenset({"vendor_explicit", "vendor_implicit"})
EMITTABLE_STANCES = frozenset({"supporting", "contrasting", "neutral"})

# 記事タイプ(§3)
ARTICLE_TYPES = frozenset({"commentary", "note", "article"})
# 役割シグナル(§1)
ROLE_SIGNALS = frozenset({"primary", "supporting", "contrasting", "incidental"})

# role(従) → (edge_type, stance, weight)。主は別処理(評釈対象=evaluates/review_chain)
_SECONDARY_MAP = {
    "supporting":  ("compares", "supporting", 0.5),
    "contrasting": ("compares", "contrasting", 0.5),
    "incidental":  ("compares", "neutral", 0.25),
}


def _drop(reason: str) -> dict:
    return {"edge_type": None, "stance": None, "assertion_mode": None,
            "strength": None, "weight": None, "evidence_role": None,
            "route": "drop", "central_case_hint": False, "reason": reason}


def map_mention(m: dict) -> dict:
    """mention → alo_edges candidate(1件)。

    m: {article_type, source('masthead'|'body'), role, resolved('deterministic'|'fuzzy'|None),
        is_formal_review(optional bool)}
    返り値: edge_type/stance/assertion_mode/strength/weight/evidence_role/route/central_case_hint/reason。
    route: 'auto'(自動エッジ可) | 'review'(人手) | 'drop'(非エッジ)。**merge は決して返さない**。
    """
    article_type = m.get("article_type")
    source = m.get("source")
    role = m.get("role")
    resolved = m.get("resolved")  # bind guard の解決結果

    # fail-closed: 未知の入力は非エッジ化
    if article_type not in ARTICLE_TYPES:
        return _drop(f"unknown_article_type:{article_type}")
    if source not in ("masthead", "body"):
        return _drop(f"unknown_source:{source}")
    if role not in ROLE_SIGNALS:
        return _drop(f"unknown_role:{role}")

    # 引用が canonical case に解決できない → エッジを作れない。人手解決へ
    if resolved not in ("deterministic", "fuzzy"):
        return {**_drop("unresolved_citation"), "route": "review"}

    # 確信度(§2): 由来で assertion_mode が決まる。masthead=構造由来 / body=本文推定
    if source == "masthead":
        assertion_mode, strength, evidence_role = "vendor_explicit", None, "source_field"
    else:
        assertion_mode, strength, evidence_role = "vendor_implicit", "implicit", "quote"

    central_hint = False

    if role == "primary":
        # 論文(article)は評釈対象を持たない(§3)。主指定でも evaluates にせず compares 降格 + 中心判例ヒント
        if article_type == "article":
            edge_type, stance, weight = "compares", "neutral", 0.5
            central_hint = True
        else:
            # 評釈対象(主): 正式評釈シリーズは review_chain、通常は evaluates
            edge_type = "review_chain" if m.get("is_formal_review") else "evaluates"
            stance, weight = None, 1.0
    else:
        edge_type, stance, weight = _SECONDARY_MAP[role]

    # route(§2/§5): 自動確定は masthead由来(vendor_explicit) かつ 決定的 bind のときだけ
    if assertion_mode == "vendor_explicit" and resolved == "deterministic":
        route = "auto"
    else:
        route = "review"

    return {"edge_type": edge_type, "stance": stance, "assertion_mode": assertion_mode,
            "strength": strength, "weight": weight, "evidence_role": evidence_role,
            "route": route, "central_case_hint": central_hint,
            "reason": f"{article_type}/{source}/{role}/{resolved}"}


def map_article(mentions: list[dict]) -> list[dict]:
    """1記事の mention 群を写す。1記事:N判例を **同格に潰さず** 各々を型付けする。"""
    return [map_mention(m) for m in mentions]


def _selfcheck() -> int:
    """emit 値域が正典(case_vocab)の部分集合であることを軽く自己確認。"""
    ok = (EMITTABLE_EDGE_TYPES <= V.COMMENTARY_TO_CASE_EDGE_TYPES <= V.LINK_EDGE_TYPES
          and EMITTABLE_ASSERTION_MODES <= V.ASSERTION_MODES_POC_ALLOWED
          and EMITTABLE_STANCES == V.LINK_STANCES
          and "llm_inferred" not in EMITTABLE_ASSERTION_MODES)
    print("OK" if ok else "DRIFT", "case_link_map emit ⊆ case_vocab 正典")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_selfcheck())
