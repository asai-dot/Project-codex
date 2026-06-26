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

# 法令の接続詞・係り受けを語境界として除去(「資本金及び資本準備金」→ 資本金 / 資本準備金)。
_CONJ = re.compile(r"及び|並びに|又は|若しくは|その他の|その他|に関する事項|に関する|に係る"
                   r"|における|に掲げる事項|に掲げる|に規定する|に定める|についての")
# 単独では情報の薄い汎用語(錨にしない)。
_STOP = {"事項", "場合", "当該", "前項", "各号", "以下", "同じ", "規定", "内容", "とき",
         "もの", "その", "これ", "次に", "前条", "前各号", "定める", "前号", "方法"}
_KANJI = re.compile(r"[一-龥]+")


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", str(s or ""))


def _clean_chunks(text: str) -> list[str]:
    """名称/aliasを接続詞で割り、漢字名詞句(>=2字)のチャンクへ。接続詞漢字は端から剥ぐ。"""
    t = _CONJ.sub("、", _norm(text))
    out = []
    for raw in _KANJI.findall(t):
        c = raw.strip("及又並若其他")  # 端に残った接続詞漢字を除去
        if len(c) >= 2 and c not in _STOP:
            out.append(c)
    return out


def _terms(item: dict) -> set[str]:
    """1号の名称/aliasesから綺麗な名詞句チャンク集合。"""
    out: set[str] = set()
    for s in [item.get("名称", "")] + list(item.get("aliases", [])):
        out.update(_clean_chunks(s))
    return out


def _shared_concepts(ta: set[str], tb: set[str], minlen: int = 2) -> set[str]:
    """2号のチャンク集合から共有概念(包含関係・最小minlen字)を返す。代表は短い(汎用な)方。"""
    shared: set[str] = set()
    for a in ta:
        for b in tb:
            if a == b and len(a) >= minlen:
                shared.add(a)
            elif a in b and len(a) >= minlen:
                shared.add(a)
            elif b in a and len(b) >= minlen:
                shared.add(b)
    return shared


def link(procs: list[dict]) -> list[dict]:
    """床ペアごとに、共通概念を共有する号の組を返す。"""
    floor_terms = [[(it["号"], _terms(it)) for it in p["items"]] for p in procs]
    links: list[dict] = []
    for (ai, a), (bi, b) in combinations(enumerate(floor_terms), 2):
        for (ga, ta) in a:
            for (gb, tb) in b:
                for concept in _shared_concepts(ta, tb):
                    links.append({"floor_a": procs[ai]["label"], "号_a": ga,
                                  "floor_b": procs[bi]["label"], "号_b": gb,
                                  "concept": concept})
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
