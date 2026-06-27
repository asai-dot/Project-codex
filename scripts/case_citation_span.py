#!/usr/bin/env python3
"""case_citation_span.py — 本文/記事レコード→ citation-span 検出 (DD-CASELINK-001 §9 残件の規則ベース第一版)。

`case_link_extract.extract_mentions` の上流境界(§5(c))を埋める実体。
記事レコード → masthead 引用 + 本文中の判例引用 span を規則ベース(正規表現+符号正規化)で取り出し、
`extract_mentions` が消費する article dict を組む。**統計的手法は将来の選択肢**(DD §9 open)。
規則ベースは第一版(再現率は corpus で計測)。read-only・実データ非依存(合成 fixture で検証)。

入力 record(D1-LIC 形状を想定・最小):
  {"article_type": "commentary"|"note"|"article",
   "masthead_citation": <raw str> | None,   # 構造化された表示判例(あれば)
   "is_formal_review": bool(optional),
   "body_text": <記事本文 str>}
出力: case_link_extract.extract_mentions が受ける article dict。
"""
from __future__ import annotations
import re
import sys

# 判例引用 span: 元号年+(事件記号)号 / 元号年月日(裁判所略称・最判等の接頭辞 optional)
# 接頭辞の地名は **漢字のみ**([一-龥])。かな(「これに対し」等の cue 語)を引用に飲み込ませない。
_COURT = (r"(?:最高裁判所|最高裁|最大判|最大決|最判|最決|"
          r"[一-龥]{2,5}(?:地方裁判所|高等裁判所|家庭裁判所|簡易裁判所|高判|地判|家判|簡判|高決|地決|高裁|地裁|家裁|簡裁))?")
_ERA = r"(?:令和|平成|昭和|大正|明治)\s*\d+\s*年"
_DOCKET = r"[(（][^)）]{1,10}[)）]\s*第?\s*\d+\s*号"   # (ワ)第123号
_DATE = r"\d+\s*月\s*\d+\s*日"
CITATION_RE = re.compile(_COURT + _ERA + r"(?:\s*" + _DOCKET + r"|\s*" + _DATE + r")")

_CUE_WINDOW = 14  # 引用直前の語彙手掛かり(同旨/これに対し 等)を拾う窓


def find_body_citations(text: str) -> list[dict]:
    """本文から判例引用 span を検出し、各々に直前の cue 窓を付ける(役割分類用)。"""
    out = []
    for m in CITATION_RE.finditer(text or ""):
        start = m.start()
        cue = text[max(0, start - _CUE_WINDOW):start]
        out.append({"citation": m.group(0).strip(), "cue": cue})
    return out


def masthead_citation(record: dict) -> str | None:
    """構造化された表示判例(masthead)。無ければ None(本文採掘のみになる)。"""
    c = record.get("masthead_citation")
    return c.strip() if isinstance(c, str) and c.strip() else None


def build_article(record: dict) -> dict:
    """record → extract_mentions が受ける article dict。1記事:N判例をそのまま展開。"""
    art = {"article_type": record.get("article_type"), "masthead": None, "body": []}
    mh = masthead_citation(record)
    if mh:
        art["masthead"] = {"citation": mh, "is_formal_review": bool(record.get("is_formal_review"))}
    art["body"] = find_body_citations(record.get("body_text", ""))
    return art


def _selfcheck() -> int:
    rec = {"article_type": "commentary", "masthead_citation": "令和3年(ワ)第123号",
           "body_text": "本判決の結論は妥当である。同旨、最判平成20年3月10日。"
                        "これに対し東京高判令和2年5月1日は異なる立場を採る。"}
    art = build_article(rec)
    ok = (art["masthead"]["citation"] == "令和3年(ワ)第123号"
          and len(art["body"]) == 2
          and "同旨" in art["body"][0]["cue"]
          and "これに対し" in art["body"][1]["cue"])
    print("OK" if ok else "DRIFT", "case_citation_span 規則ベース第一版")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_selfcheck())
