"""publisher_norm — 出版社名の alias 正規化 (DD-EDIDENT-001-IMPL R1)。

監査是正 R1: edition_identity_v2 は publisher を `normalize_title` で **完全一致**比較していたため、
「有斐閣」↔「株式会社有斐閣」↔「(株)有斐閣」が mismatch 扱いとなり過剰 review (recall 低下) を招く。
本モジュールは法人格トークン (株式会社/(株)/㈱ 等) と記号を畳んで別表記を同一キーに寄せる。

`normalize_publisher(s) -> str`。stdlib のみ・決定的・NFKC ベース。
"""

from __future__ import annotations

import re
import unicodedata

# 法人格表記 (NFKC 後)。㈱→(株)・㈲→(有) 等は NFKC が括弧形へ畳む。
_CORP = re.compile(
    r"(独立行政法人|一般財団法人|一般社団法人|公益財団法人|公益社団法人"
    r"|株式会社|有限会社|合同会社|合名会社|合資会社|財団法人|社団法人"
    r"|\(株\)|\(有\)|\(財\)|\(社\)|\(同\)|\(資\)|\(名\))")

_PUNCT = re.compile(
    r"[\s　・･:：,，、_\-\(\)\[\]【】「」『』“”\"'./&＆ー―−‐‑‒–—]+")


def normalize_publisher(text: str) -> str:
    """法人格トークン・記号・全半角差を畳んだ出版社キーを返す ('' = 空)。"""
    s = unicodedata.normalize("NFKC", text or "").lower()
    s = _CORP.sub("", s)        # 法人格を先に除去 ((株) の括弧を _PUNCT より前に処理)。
    s = _PUNCT.sub("", s)
    return s


__all__ = ["normalize_publisher"]
