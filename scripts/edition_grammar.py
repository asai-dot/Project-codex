"""edition_grammar — 版表示の文法トークナイザ (DD-EDIDENT-001-IMPL H4 再設計)。

旧 `phase0_inventory.edition_signature` は非番号版を一律 `rev` に潰し、`改訂` の末尾 `版` を
core に残すことがあり false merge / false split の双方を起こした (監査 H4)。本モジュールは:

  * 番号版 (第N版 / N版 / 初版)、訂版 (3訂版 / 補訂2版)、ラベル版 (改訂/新訂/全訂/増補/補訂/
    新装/新)、複合版 (改訂新版 / 増補改訂版) を **区別して token 化**する。
  * marker を core から Unicode-safe に **完全除去**する (prefix/suffix どちらでも core 一致)。
  * `版`-様トークンが現れたが既知文法に当たらなければ **unknown_edition_marker** として review へ。
  * 異なる revision family を一律 `rev` に潰さない。

`parse_edition(title) -> EditionParse(signature, core, has_marker, unknown)`。stdlib のみ・決定的。
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_KANJI_NUM = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}
_NUM = r"(?:\d+|[〇一二三四五六七八九十]+)"

# core から落とす記号 (NFKC 後)。版マーカ除去とは別。
_CORE_STRIP = re.compile(
    r"[\s　・･:：,，、_\-\(\)\[\]【】「」『』〔〕〈〉（）“”\"'./&＆ー―−‐‑‒–—]+")


def _kanji_to_int(s: str):
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if "十" in s:
        a, _, b = s.partition("十")
        tens = (_KANJI_NUM.get(a, 1) if a else 1) * 10
        return tens + (_KANJI_NUM.get(b, 0) if b else 0)
    return _KANJI_NUM.get(s)


def _num(tok: str):
    n = _kanji_to_int(tok)
    return n


# 適用順 = 具体的 (複合・訂・番号) → 一般ラベル。各要素 (regex, signature 化関数)。
# 括弧/隅付きは marker の一部として一緒に剥がす。
_BRACKET = r"[第\(\[〔〈【（]?\s*"
_BRACKET_CLOSE = r"\s*[\)\]〕〉】）]?"

_PATTERNS: list[tuple[re.Pattern, object]] = [
    # 複合版 (順序: 最長一致を先に)。
    (re.compile(r"増補改訂新版"), lambda m: "label:zoho_kaitei_shinpan"),
    (re.compile(r"改訂増補版"), lambda m: "label:kaitei_zoho"),
    (re.compile(r"増補改訂版"), lambda m: "label:zoho_kaitei"),
    (re.compile(r"改訂新版"), lambda m: "label:kaitei_shinpan"),
    # 補訂N版 / 増補N版 (ラベル+番号)。
    (re.compile(r"(補訂|増補|改訂|新訂|全訂)\s*(" + _NUM + r")\s*版"),
     lambda m: f"label:{_LABELS[m.group(1)]}:{_num(m.group(2))}"),
    # N訂版 (3訂版 / 三訂版)。
    (re.compile(r"(" + _NUM + r")\s*訂\s*版"), lambda m: f"tei:{_num(m.group(1))}"),
    # 番号版 (第7版 / (第4版) / 7版)。初版は num:1。
    (re.compile(_BRACKET + r"(" + _NUM + r")\s*版" + _BRACKET_CLOSE),
     lambda m: f"num:{_num(m.group(1))}"),
    (re.compile(r"初版"), lambda m: "num:1"),
    # 単独ラベル版。
    (re.compile(r"(改訂|新訂|全訂|増補|補訂|新装|新)\s*版"),
     lambda m: f"label:{_LABELS[m.group(1)]}"),
]

_LABELS = {"改訂": "kaitei", "新訂": "shintei", "全訂": "zentei", "増補": "zoho",
           "補訂": "hotei", "新装": "shinso", "新": "shin"}

# 「版」を末尾に持つトークン候補 (unknown 検出用)。直前 1-6 文字の非空白塊。
_VER_LIKE = re.compile(r"([0-9〇一二三四五六七八九十一-龥ァ-ヶ]{1,6})版")
# 巻 (volume) を title から拾う補助 (explicit volume field が無いとき)。
_VOL_RE = re.compile(r"(上巻|中巻|下巻|前巻|後巻|別巻|続巻|" + _NUM + r"\s*巻)")


@dataclass(frozen=True)
class EditionParse:
    signature: str       # "" = 版表記なし / "num:7" / "tei:3" / "label:kaitei" / "label:hotei:2"
    core: str            # 版マーカ完全除去後の核 (記号除去・小文字)
    has_marker: bool     # 版マーカが1つでもあったか
    unknown: bool        # 版様トークンがあったが既知文法に当たらなかった


def parse_edition(title: str) -> EditionParse:
    raw = unicodedata.normalize("NFKC", title or "")
    work = raw
    sigs: list[str] = []
    for rx, fn in _PATTERNS:
        m = rx.search(work)
        while m:
            sigs.append(fn(m))
            work = work[:m.start()] + work[m.end():]
            m = rx.search(work)
    has_marker = bool(sigs)

    # unknown: まだ '...版' 様トークンが残っていれば未知マーカ。
    # ただし「出版」「版権」等の一般語の '版' は誤検知しやすいので、
    # 直前が数字/訂/改/補/新/全/増/装 など版文脈の字に限る。
    unknown = False
    for vm in _VER_LIKE.finditer(work):
        frag = vm.group(1)
        if re.search(r"[0-9〇一二三四五六七八九十訂改補新全増装]", frag):
            unknown = True
            break

    core = _CORE_STRIP.sub("", work.lower())
    # 代表 signature: 複数あれば結合 (決定的順序)。
    signature = "+".join(sorted(sigs)) if sigs else ""
    return EditionParse(signature=signature, core=core, has_marker=has_marker, unknown=unknown)


def title_volume(title: str) -> str:
    """title から巻表示を拾う ('' = なし)。explicit volume field の補完用。"""
    m = _VOL_RE.search(unicodedata.normalize("NFKC", title or ""))
    return m.group(1) if m else ""


__all__ = ["EditionParse", "parse_edition", "title_volume"]
