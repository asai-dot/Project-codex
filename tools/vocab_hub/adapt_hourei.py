#!/usr/bin/env python3
"""学陽『法令用語辞典 第11次改訂版』entries -> 語彙Hub用 Term JSONL アダプタ (read-only).

入力: hourei_all_entries_v0.2_20260612.jsonl
  各行: {"scheme_id","entry_id","headword","reading","definition","flags",...}
  (phase1_5_parse_md_v0.2_calibrated.py 出力. 定義はインライン)

出力: build_hub_dryrun.py の Term スキーマ:
  {"stg_term_key","scheme_id","authority_rank":102,"term_tier":1,
   "pref_label","normalized_pref","reading","definition"}

クリーニング (adapt() 内で完結):
  1. ゴミエントリ除去: 書籍メタ情報ページ / 記号箇条書き見出し
  2. 括弧内別表記の剥離: 「当たる(あたる,該る)」→ normalized_pref=「当たる」
  3. reading 補完: ①元データ ②ひらがな/カタカナ見出し ③有斐閣 pref 引き継ぎ ④pykakasi
  4. 重複除去: 同 normalized_pref + 同定義 → 先勝ち (同 pref + 別定義は保持)

normalized_pref は build_hub_dryrun.norm_pref と同一ロジック(有斐閣と揃える).
pykakasi は optional (無くても動作, reading="" のまま残る).
DBに書かない.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, Optional

try:
    import pykakasi as _pykakasi
    _kks = _pykakasi.kakasi()
    def _kakasi_reading(s: str) -> str:
        return "".join(x["hira"] for x in _kks.convert(s))
except ImportError:
    _kakasi_reading = None  # type: ignore

_FW_ALNUM = str.maketrans(
    "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")

# 書籍メタ情報ページ / 記号ゴミ の正規表現
_TRASH_HW = re.compile(
    r'^(?:法令用語辞典|[ぁ-んァ-ヴa-zA-Z０-９A-Z]+(?:第\d+次改訂版)?'  # 書籍名
    r'|[ア-オカ-コ]行$'          # 索引見出し「ア行」等
    r'|[イロハニホヘト][\)）]$'   # イ) ロ) 等の箇条書き記号
    r'|[㋐-㋾①-⑳]$'            # 丸数字
    r')$'
)
# 定義が書籍情報（はしがき・奥付）を含む
_TRASH_DEF = re.compile(r'共編|はしがき|学陽書房|第\d+次改訂版|奥付')

_BRACKET = re.compile(r'[（(][^）)]*[）)]')  # 全角・半角括弧


def norm_pref(s: str) -> str:
    return unicodedata.normalize("NFC", str(s or "")).strip().translate(_FW_ALNUM)


def _kata_to_hira(s: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヴ" else c for c in s)


def _strip_brackets(hw: str) -> str:
    """括弧内別表記を除去して主見出しだけ返す."""
    return _BRACKET.sub("", hw).strip()


def _infer_reading(stripped: str) -> Optional[str]:
    """stripped pref から reading を推定できる場合に返す."""
    core = stripped.replace(" ", "").replace("　", "").replace("・", "").replace("ー", "")
    if not core:
        return None
    if re.fullmatch(r"[ぁ-ん]+", core):
        return core
    if re.fullmatch(r"[ァ-ヴｦ-ﾟー]+", core):
        return _kata_to_hira(core)
    return None


def _is_trash(hw: str, definition: str) -> bool:
    """書籍メタ情報や記号ゴミの判定."""
    if _TRASH_HW.match(hw):
        return True
    if definition and _TRASH_DEF.search(definition[:100]):
        return True
    return False


def _enrich_readings(terms: list, yuhikaku_reading_map: Dict[str, str]) -> None:
    """reading が空の term に有斐閣読み引き継ぎ → pykakasi の順で補完 (in-place)."""
    for t in terms:
        if t.get("reading"):
            continue
        np = t.get("normalized_pref", "")
        # ③ 有斐閣 pref match → reading 引き継ぎ
        if np in yuhikaku_reading_map:
            t["reading"] = yuhikaku_reading_map[np]
            t["reading_source"] = "yuhikaku_pref_match"
            continue
        # ④ pykakasi fallback
        if _kakasi_reading:
            r = _kakasi_reading(np)
            if r:
                t["reading"] = r
                t["reading_source"] = "pykakasi"


def adapt(entries, scheme_id: str, authority_rank: int,
          yuhikaku_reading_map: Optional[Dict[str, str]] = None):
    """
    yuhikaku_reading_map: {normalized_pref -> reading} を渡すと reading 補完③に使う.
    run_2dict.py などから渡す. None の場合は ③ をスキップ.
    """
    out = []
    seen: dict = {}  # normalized_pref -> set of def_fingerprint (重複除去)
    for e in entries:
        hw = (e.get("headword") or "").strip()
        if not hw:
            continue
        definition = (e.get("definition") or "").strip()

        # ゴミ除去
        if _is_trash(hw, definition):
            continue

        # 括弧剥ぎ
        stripped = _strip_brackets(hw)
        if not stripped:
            stripped = hw

        sid = e.get("scheme_id") or scheme_id
        eid = e.get("entry_id") or f"{sid}__{len(out) + 1:05d}"

        # reading: ① 元データ → ② ひらがな/カタカナ推定 (③④は後段 _enrich_readings で)
        reading = e.get("reading") or None
        if not reading:
            reading = _infer_reading(stripped)

        np = norm_pref(stripped)
        if not np:
            continue

        # 重複除去: 同 normalized_pref + 同定義 (先勝ち)
        def_fp = definition[:80]
        if (np, def_fp) in seen:
            continue
        seen[(np, def_fp)] = True

        out.append({
            "stg_term_key": f"hstg_{eid}",
            "scheme_id": sid,
            "authority_rank": authority_rank,
            "term_tier": 1,
            "pref_label": hw,
            "normalized_pref": np,
            "reading": reading,
            "definition": definition,
            "source_item_key": eid,
        })

    # ③④ reading 補完
    _enrich_readings(out, yuhikaku_reading_map or {})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="学陽 entries -> Hub用 Term JSONL (read-only)")
    ap.add_argument("--entries", required=True, type=Path)
    ap.add_argument("--scheme", default="hourei_yougo_jiten_11")
    ap.add_argument("--authority-rank", type=int, default=102)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)

    entries = []
    with a.entries.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    terms = adapt(entries, a.scheme, a.authority_rank)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8") as fh:
        for t in terms:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"[adapt-hourei] entries={len(entries)} -> terms={len(terms)} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
