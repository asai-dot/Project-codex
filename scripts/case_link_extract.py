#!/usr/bin/env python3
"""case_link_extract.py — 記事レコード→mention 抽出の *契約と決定部* (DD-CASELINK-001 v0.2)。

`case_link_map` の上流。記事から「(判例参照, 役割, 解決度)」= mention を作る。
本モジュールが担うのは **決定的に書ける部分**:
  - 役割分類(masthead=主 / 本文=語彙手掛かりで supporting|contrasting|incidental)
  - 引用解決(case_number_norm で 完全事件番号→deterministic / 日付のみ→fuzzy / それ以外→None)
生テキストからの **citation-span 検出は境界(注入入力)** とし、ここでは扱わない
(規則 vs 統計の実体は corpus 段階=Mac CC)。これにより抽出器を実データ無しで検証可能にする。

入力 article:
  {"article_type": "commentary"|"note"|"article",
   "masthead": {"citation": <raw str>} | None,
   "body": [{"citation": <raw str>, "cue": <周辺語 str>}, ...]}
出力: case_link_map.map_mention が消費する mention dict のリスト。read-only。
"""
from __future__ import annotations
import re
import sys
import case_number_norm as N

# 本文の語彙手掛かり → 従の役割(§1)。優先順: contrasting を supporting より先に見る
ROLE_CUES = (
    ("contrasting", ("これに対し", "反対", "対比", "異なり", "に対して", "cf")),
    ("supporting",  ("同旨", "同趣旨", "参照", "同様", "accord")),
)
# 元号/和暦 日付の存在(部分引用=fuzzy の判定に使う)
_DATE_RE = re.compile(r"(令和|平成|昭和|大正|明治)\s*\d+\s*年|\d+\s*年\s*\d+\s*月\s*\d+\s*日")


def classify_role(source: str, cue: str = "") -> str:
    """masthead→primary。body→語彙手掛かりで supporting/contrasting、無ければ incidental(弱)。"""
    if source == "masthead":
        return "primary"
    for role, cues in ROLE_CUES:
        if any(c in cue for c in cues):
            return role
    return "incidental"


def resolve_citation(raw: str) -> str | None:
    """引用の解決度。完全事件番号→'deterministic' / 日付のみ→'fuzzy' / それ以外→None(未解決)。"""
    if raw and N.normalize(raw):
        return "deterministic"
    if raw and _DATE_RE.search(raw):
        return "fuzzy"
    return None


def extract_mentions(article: dict) -> list[dict]:
    """記事 → mention リスト。1記事:N判例 をそのまま N 件の型付き候補にする(潰さない)。"""
    atype = article.get("article_type")
    mentions: list[dict] = []

    mh = article.get("masthead")
    if mh and mh.get("citation"):
        mentions.append({
            "article_type": atype, "source": "masthead", "role": "primary",
            "resolved": resolve_citation(mh["citation"]),
            "is_formal_review": bool(mh.get("is_formal_review")),
            "citation": mh["citation"],
        })

    for b in article.get("body", []) or []:
        cit = b.get("citation", "")
        mentions.append({
            "article_type": atype, "source": "body",
            "role": classify_role("body", b.get("cue", "")),
            "resolved": resolve_citation(cit),
            "citation": cit,
        })
    return mentions


def _selfcheck() -> int:
    a = {"article_type": "commentary",
         "masthead": {"citation": "令和3年(ワ)第123号"},
         "body": [{"citation": "最判平成20年3月10日", "cue": "同旨"},
                  {"citation": "東京地裁", "cue": "これに対し"}]}
    ms = extract_mentions(a)
    ok = (ms[0]["role"] == "primary" and ms[0]["resolved"] == "deterministic"
          and ms[1]["role"] == "supporting" and ms[1]["resolved"] == "fuzzy"
          and ms[2]["role"] == "contrasting" and ms[2]["resolved"] is None)
    print("OK" if ok else "DRIFT", "case_link_extract 決定部")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_selfcheck())
