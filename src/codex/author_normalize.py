"""著者名の正規化 (Fork 4 ステップ②).

雑誌目次の著者表記は揺れが大きい。横断検索 (著者キーで articles を引く) を
成立させるため、表記揺れを吸収した正規化キー `author_key` を生成する。

正規化の方針:
  - Unicode NFKC (全角英数 → 半角、互換文字の畳み込み)
  - 役割語/肩書 (司会・編・訳・聞き手 等) を除去し role として別管理
  - 内部空白の除去 (姓名間の全角/半角空白)
  - 末尾の敬称・括弧注記の除去

`authors_raw` の split 由来の各要素に対して 1 つの正規化結果を返す。
"""

from __future__ import annotations

import re
import unicodedata

# 著者要素から剥がす役割語 (先頭/末尾どちらでも)。除去しつつ role に記録。
ROLE_WORDS = (
    "司会", "聞き手", "聞手", "話し手", "話手",
    "編集", "編", "訳", "監修", "監訳", "構成", "取材", "文",
    "述", "談", "報告", "解説", "評者", "コーディネーター",
)

# 末尾につく敬称
HONORIFICS = ("先生", "教授", "弁護士", "判事", "氏", "さん", "君", "ほか", "他", "ら")

# 括弧注記 (所属など) を丸ごと除去: 山田太郎(東京大学) / 山田太郎（弁護士）
_PAREN_RE = re.compile(r"[（(][^）)]*[）)]")

# 役割語を「役割語：名前」「名前・役割語」両形で剥がすための前後パターン
_ROLE_PREFIX_RE = re.compile(
    r"^(?:" + "|".join(map(re.escape, ROLE_WORDS)) + r")[：:・／\s]+"
)
_ROLE_SUFFIX_RE = re.compile(
    r"[（(]?(?:" + "|".join(map(re.escape, ROLE_WORDS)) + r")[）)]?\s*$"
)


def _strip_honorifics(name: str) -> str:
    changed = True
    while changed:
        changed = False
        for h in HONORIFICS:
            if name.endswith(h) and len(name) > len(h):
                name = name[: -len(h)].strip()
                changed = True
    return name


def normalize_author(raw: str) -> dict:
    """単一著者要素を正規化。

    返り値: {
      "raw": 入力そのまま,
      "display": 表示用 (NFKC + 注記/敬称除去, 空白は保持),
      "key": 検索キー (display から内部空白も除去),
      "roles": 検出された役割語のリスト,
    }
    解釈不能 (空) の場合は display/key が "" になる。
    """
    raw = (raw or "").strip()
    roles: list[str] = []

    s = unicodedata.normalize("NFKC", raw)
    # 括弧注記を除去
    s = _PAREN_RE.sub("", s).strip()

    # 役割語 (prefix) を剥がす
    m = _ROLE_PREFIX_RE.match(s)
    if m:
        roles.append(m.group(0).rstrip("：:・／ \t"))
        s = s[m.end():].strip()

    # 役割語 (suffix) を剥がす
    m = _ROLE_SUFFIX_RE.search(s)
    if m and m.start() > 0:
        tail = m.group(0).strip("（()） ")
        if tail:
            roles.append(tail)
        s = s[: m.start()].strip()

    # 敬称除去
    s = _strip_honorifics(s).strip()

    display = s
    # 検索キー: 内部空白 (半角/全角) を除去、英字は小文字化
    key = re.sub(r"\s+", "", display).lower()

    # role 名そのものだけが残った場合 (例: 著者なしの「司会」) は名前ではない
    if display in ROLE_WORDS:
        roles.append(display)
        display = ""
        key = ""

    # 重複 role を除去 (順序保持)
    seen = set()
    roles = [r for r in roles if not (r in seen or seen.add(r))]

    return {"raw": raw, "display": display, "key": key, "roles": roles}


def normalize_authors(authors: list[str]) -> list[dict]:
    """parse 済みの authors リストを正規化リストへ。空キーは除外しない
    (role のみの要素も後段評価のため残す)。"""
    return [normalize_author(a) for a in (authors or [])]


def author_keys(authors: list[str]) -> list[str]:
    """横断検索用: 空でない正規化キーのみを (順序保持・重複排除で) 返す。"""
    out: list[str] = []
    seen: set[str] = set()
    for n in normalize_authors(authors):
        k = n["key"]
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out
