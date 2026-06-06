"""寛容な front-matter パーサ (stdlib only)。

実ファイルは PyYAML を前提にできない環境(Mac CC / Box Drive)で読み書きされるため、
本パッカは外部依存なしで「先頭の `---` フェンスに挟まれた YAML 風スカラ」だけを取り出す。

実データの癖を吸収する:
- 値に ` # ...` のインラインコメントが付く  (例: ``status: blocked   # ← targets 不在``)
- 値自体にコロンを含む                       (例: ``source_hash: sha1:fb37e5...``)
- ネストした list / map は無視する           (本ツールが使うのは top-level スカラのみ)
"""

from __future__ import annotations

from typing import Dict, Tuple

_FENCE = "---"


def split_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
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

    meta = _parse_scalars(lines[1:end])
    body = "\n".join(lines[end + 1 :])
    return meta, body


def _strip_inline_comment(value: str) -> str:
    """空白に続く ``#`` 以降をインラインコメントとして落とす。

    値先頭の ``#`` (= コメント行) は呼び出し側で除外済み。``sha1:...`` のような
    ``#`` を含まない値は素通しする。
    """
    idx = value.find(" #")
    if idx != -1:
        value = value[:idx]
    return value.strip()


def _parse_scalars(fm_lines) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for raw in fm_lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # 先頭がインデント/リスト記号の行は nested とみなしスキップ
        if raw[:1] in (" ", "\t", "-"):
            continue
        if ":" not in raw:
            continue
        key, _, val = raw.partition(":")
        key = key.strip()
        if not key:
            continue
        val = _strip_inline_comment(val)
        val = val.strip().strip('"').strip("'")
        meta[key] = val
    return meta
