"""寛容な front-matter パーサ (stdlib only)。

worker task は PyYAML を前提にできない環境 (Claude Code / Box Drive / CI) で読み書き
されるため、外部依存なしで「先頭の ``---`` フェンスに挟まれた YAML 風」を取り出す。
gpt_audit の同名パーサを拡張し、**top-level の block list** も拾う:

    allowed_paths:
      - src/xdoc/
      - tests/xdoc/

実データの癖を吸収する:
- 値に ` # ...` のインラインコメントが付く  (例: ``status: queued   # P0``)
- 値自体にコロンを含む                       (例: ``test_command: pytest tests/xdoc -q``)
- ネストした map は無視する                  (本ツールが使うのは top-level スカラ/リストのみ)

戻り値の dict は、値が ``str`` (スカラ) か ``List[str]`` (block list) の混在。
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Union

_FENCE = "---"

Scalar = str
Value = Union[Scalar, List[str]]


def split_frontmatter(text: str) -> Tuple[Dict[str, Value], str]:
    """``(meta, body)`` を返す。front-matter が無ければ ``({}, text)``。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FENCE:
        return {}, text

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _FENCE:
            end = i
            break
    if end is None:
        # 閉じフェンス無し: front-matter として扱わない
        return {}, text

    meta = _parse(lines[1:end])
    body = "\n".join(lines[end + 1 :])
    return meta, body


def _strip_inline_comment(value: str) -> str:
    """空白に続く ``#`` 以降をインラインコメントとして落とす。

    ``pytest -q  # fast`` -> ``pytest -q``。``sha1:...`` のような ``#`` を含まない値は素通し。
    """
    idx = value.find(" #")
    if idx != -1:
        value = value[:idx]
    return value.strip().strip('"').strip("'")


def _is_indented(raw: str) -> bool:
    return raw[:1] in (" ", "\t")


def _parse(fm_lines: List[str]) -> Dict[str, Value]:
    meta: Dict[str, Value] = {}
    i = 0
    n = len(fm_lines)
    while i < n:
        raw = fm_lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        # 親キーを持たない宙ぶらりんのインデント/リスト行は無視 (耐障害性)
        if _is_indented(raw) or stripped.startswith("- "):
            i += 1
            continue
        if ":" not in raw:
            i += 1
            continue

        key, _, val = raw.partition(":")
        key = key.strip()
        if not key:
            i += 1
            continue
        val = _strip_inline_comment(val)

        if val:
            meta[key] = val
            i += 1
            continue

        # 値が空 -> block list か、ネスト map の親。次行以降を覗く。
        items: List[str] = []
        j = i + 1
        while j < n:
            nxt = fm_lines[j]
            ns = nxt.strip()
            if ns.startswith("- "):
                items.append(_strip_inline_comment(ns[2:]))
                j += 1
            elif _is_indented(nxt) and ns:
                # ネスト map (例: ``target:`` 配下の ``files:``) は読み飛ばす
                j += 1
            elif ns == "":
                # 空行: ブロック継続を許容 (Box Drive 由来の空行癖)
                j += 1
            else:
                break
        meta[key] = items if items else ""
        i = j
    return meta


def as_list(value: Value) -> List[str]:
    """スカラ/リストいずれでも ``List[str]`` に正規化する。"""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [v for v in value if v]
    return [value]
