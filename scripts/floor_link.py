"""床リンカ — 複数の法定床(記載事項/登記事項/定款事項)に共通する項目を炙り出す (stdlib のみ).

owner 着想: 1書式の slot構造 = 適用される複数の法定床の合成。複数床に共通して現れる項目
(資本金・発行可能株式総数 等)は、書面間の整合チェックの錨であり、書式構造化(⑦)のヒント。

本ツールは `pipeline/floor/statute_floor_extract.json` の各床の名称/aliases から、全角漢字の
共通語(>=3字)を機械抽出し、どの床のどの号がそれを共有するかを出す。決定的・stdlib のみ。
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRACT = ROOT / "pipeline" / "floor" / "statute_floor_extract.json"

_KANJI_RUN = re.compile(r"[一-龥]{3,8}")
# 単独では情報が薄い語を除外(汎用すぎる共通語)。
_STOP = {"事項", "関する", "とするとき", "するもの", "に関する事", "関する事項",
         "その他", "場合", "とき", "もの", "及びそ"}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", str(s or ""))


def _terms(item: dict) -> set[str]:
    """1号の名称/aliasesから漢字連続(>=3字)の語候補を集める。"""
    out: set[str] = set()
    for s in [item.get("名称", "")] + list(item.get("aliases", [])):
        for m in _KANJI_RUN.findall(_norm(s)):
            for L in range(3, len(m) + 1):
                for i in range(len(m) - L + 1):
                    g = m[i:i + L]
                    if g not in _STOP:
                        out.add(g)
    return out


def link(procs: list[dict]) -> list[dict]:
    """床ペアごとに、共通語を共有する号の組を返す(最長一致を代表に)。"""
    # 各床: 号 -> 語集合
    floor_terms = []
    for p in procs:
        floor_terms.append([(it["号"], _terms(it)) for it in p["items"]])

    links: list[dict] = []
    for (ai, a), (bi, b) in combinations(enumerate(floor_terms), 2):
        for (ga, ta) in a:
            for (gb, tb) in b:
                shared = ta & tb
                if not shared:
                    continue
                rep = max(shared, key=len)  # 最長の共通語を代表に
                links.append({"floor_a": procs[ai]["label"], "号_a": ga,
                              "floor_b": procs[bi]["label"], "号_b": gb,
                              "concept": rep})
    return links


def main() -> int:
    data = json.loads(EXTRACT.read_text(encoding="utf-8"))
    procs = data["procedures"]
    pick = sys.argv[1:] or ["27", "199", "911"]
    procs = [p for p in procs if p["article"] in pick]
    links = link(procs)
    # concept ごとに集約。
    by_concept: dict[str, list] = {}
    for ln in links:
        by_concept.setdefault(ln["concept"], []).append(ln)
    # 2床以上にまたがる concept を「整合の錨」として表示(長い語優先)。
    print(f"=== 床横断の共通項目(整合の錨) : {', '.join(p['label'] for p in procs)} ===")
    shown = 0
    for concept in sorted(by_concept, key=lambda c: (-len(c), c)):
        lns = by_concept[concept]
        floors = {(ln["floor_a"]) for ln in lns} | {(ln["floor_b"]) for ln in lns}
        if len(floors) < 2:
            continue
        pairs = sorted({f"{ln['floor_a'][:8]}{ln['号_a']}号↔{ln['floor_b'][:8]}{ln['号_b']}号" for ln in lns})
        print(f"  【{concept}】 {len(floors)}床: " + " / ".join(pairs[:4]))
        shown += 1
    if not shown:
        print("  (共通項目なし)")
    print("\n読み方: 同一 concept が複数の書面(議事録/登記/定款)に現れる = その値は書面間で一致すべき"
          "整合チェックの錨。書式構造化(⑦)の共通 slot 候補。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
