"""ISBN 正規化（stdlib のみ）。ISBN10/13 → ISBN13 へ。

ローカルちゃん用ノート: ここは触らなくてOK。他スクリプトが import して使う。
"""
import re

_PARSER_VERSION = "isbn_util/0.1"


def digits_only(s: str) -> str:
    return re.sub(r"[^0-9Xx]", "", s or "")


def isbn13_checkdigit(body12: str) -> str:
    t = sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(body12))
    return str((10 - (t % 10)) % 10)


def isbn10_checkdigit(body9: str) -> str:
    t = sum((10 - i) * int(c) for i, c in enumerate(body9))
    r = (11 - (t % 11)) % 11
    return "X" if r == 10 else str(r)


def normalize_to_isbn13(raw: str):
    """raw 文字列 → (isbn13, valid:bool) か None。ハイフン/空白除去、10桁は13へ変換。"""
    s = digits_only(raw).upper()
    if len(s) == 13 and s.isdigit() and s[:3] in ("978", "979"):
        return s, (s[12] == isbn13_checkdigit(s[:12]))
    if len(s) == 10 and re.fullmatch(r"[0-9]{9}[0-9X]", s):
        valid10 = s[9] == isbn10_checkdigit(s[:9])
        body = "978" + s[:9]
        i13 = body + isbn13_checkdigit(body)
        return i13, valid10
    return None
