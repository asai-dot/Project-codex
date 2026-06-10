"""legallib 詳細TOC → canonical TOC ノード変換器 (Fork 1 / 最初の一歩 ①).

legallib STEP A の取得物 (``~/alo-ai/work/legallib_dl/*.json``) に入っている
雑誌・書籍の目次ノード ``{l, p, t, level}`` を、本番 BookDX が
``app/data/toc/isbn_*.json`` で採用しているノード schema に変換する。

本番ノード schema (実データで確認済み)::

    {
      "l": 1,
      "p": null,
      "t": "第一章 ...",
      "toc_node_id": "alo:book:isbn:9784000616072:toc:001",
      "depth": 1,
      "parent_toc_node_id": "",
      "toc_path_id": "c01",
      "page_start": null,
      "toc_source": "legallib",
      "toc_status": "legallib"
    }

このモジュールの責務は **変換のみ**。本番ファイルへの書き込み・上書き判定は
``legallib_join_policy`` / ``legallib_join_dryrun`` が担う (関心の分離)。

設計上の確定事項:
  * ``parent_toc_node_id`` は legallib の ``level`` 入れ子から再構築する
    (近接祖先 = 自分より浅い直近ノード)。
  * legallib の level がいきなり 1→3 のように飛んだ場合は depth を
    ``親 depth + 1`` にクランプし、木を常に妥当に保つ (飛びは
    ``conversion warning`` として呼び出し側に返せるよう記録)。
  * 生成ノードの ``toc_status`` は ``"legallib"`` (= **非 simple**)。これにより
    一度入った legallib TOC は以降のフラット系ソース (openbd 等) から
    上書きされなくなる (検収「非simple を劣化させない」と整合)。
"""

from __future__ import annotations

from typing import Any, Iterable

# 生成ノードの既定 source / status。
DEFAULT_SOURCE = "legallib"
DEFAULT_STATUS = "legallib"

# 入力ノードでタイトル / level / ページとして許容するキー (legallib 由来の
# 表記揺れを吸収する。最初に見つかった非空の値を採用)。
_TITLE_KEYS = ("t", "title", "label", "name", "text")
_LEVEL_KEYS = ("level", "l", "depth")
_PAGE_KEYS = ("page_start", "print_page", "pdf_page", "page", "p")


def _first_present(node: dict, keys: Iterable[str]) -> Any:
    for key in keys:
        if key in node and node[key] not in (None, ""):
            return node[key]
    return None


def flatten_nodes(raw_nodes: list[dict]) -> list[dict]:
    """ネストした legallib TOC (``children`` 木) を pre-order で平坦化する。

    実 legallib STEP A の TOC は ``{level, label, pdf_page, children:[...]}`` の
    **木構造**。フラットな列ではない。子を ``children`` から再帰収集し、各ノードの
    ``level`` を保ったまま出現順に並べる。フラット入力 (children 無し) はそのまま。
    """
    out: list[dict] = []

    def walk(nodes: list) -> None:
        for n in nodes:
            if not isinstance(n, dict):
                continue
            out.append(n)
            kids = n.get("children")
            if isinstance(kids, list) and kids:
                walk(kids)

    walk(raw_nodes)
    return out



def _coerce_title(node: dict) -> str:
    value = _first_present(node, _TITLE_KEYS)
    if value is None:
        return ""
    return str(value).strip()


def _coerce_level(node: dict) -> int:
    value = _first_present(node, _LEVEL_KEYS)
    try:
        level = int(value)
    except (TypeError, ValueError):
        return 1
    return level if level >= 1 else 1


def _coerce_page(node: dict) -> int | None:
    value = _first_present(node, _PAGE_KEYS)
    if value is None:
        return None
    try:
        page = int(value)
    except (TypeError, ValueError):
        return None
    return page if page > 0 else None


def convert_legallib_nodes(
    raw_nodes: list[dict],
    isbn: str,
    *,
    source: str = DEFAULT_SOURCE,
    status: str = DEFAULT_STATUS,
    warnings: list[str] | None = None,
) -> list[dict]:
    """legallib の生ノード列 → 本番 canonical ノード列。

    Args:
        raw_nodes: legallib 1冊分の toc ノード (``{l,p,t,level}`` 系) の列。
        isbn: 接合先 canonical 書籍の ISBN-13 (``toc_node_id`` の名前空間)。
        source: 生成ノードの ``toc_source``。
        status: 生成ノードの ``toc_status`` (既定 ``"legallib"`` = 非simple)。
        warnings: None でなければ level 飛び等の警告を追記する。

    Returns:
        本番ノード schema の dict のリスト (冪等・決定的)。

    変換は決定的: 同じ入力からは常に同じ出力 (順序保存、連番固定)。
    """
    # 0) ネスト (children 木) を pre-order で平坦化してから処理。
    raw_nodes = flatten_nodes(raw_nodes)

    # 1) タイトルが取れないノードは捨てる (空ノードは木を壊す)。
    parsed: list[tuple[int, str, int | None]] = []
    for raw in raw_nodes:
        if not isinstance(raw, dict):
            continue
        title = _coerce_title(raw)
        if not title:
            continue
        parsed.append((_coerce_level(raw), title, _coerce_page(raw)))

    if not parsed:
        return []

    # 2) level の絶対値ではなく相対 (最小 level を depth=1 に正規化)。
    min_level = min(level for level, _, _ in parsed)

    out: list[dict] = []
    # stack = 現在の祖先チェーン。各要素は
    # {"depth", "node_id", "path", "child_count"}。
    stack: list[dict] = []
    root_children = 0
    seq = 0

    for level, title, page in parsed:
        depth = level - min_level + 1

        # level 飛びのクランプ: depth は「親 depth + 1」を超えられない。
        max_allowed = (stack[-1]["depth"] + 1) if stack else 1
        if depth > max_allowed:
            if warnings is not None:
                warnings.append(
                    f"level jump clamped: isbn={isbn} seq={seq + 1} "
                    f"raw_depth={depth} -> {max_allowed} (title={title!r})"
                )
            depth = max_allowed

        # 自分以上の深さの祖先を pop して親を確定。
        while stack and stack[-1]["depth"] >= depth:
            stack.pop()
        parent = stack[-1] if stack else None

        seq += 1
        node_id = f"alo:book:isbn:{isbn}:toc:{seq:03d}"

        if parent is not None:
            parent["child_count"] += 1
            path = f"{parent['path']}.{parent['child_count']:02d}"
            parent_id = parent["node_id"]
        else:
            root_children += 1
            path = f"c{root_children:02d}"
            parent_id = ""

        node = {
            "l": depth,
            "p": page,
            "t": title,
            "toc_node_id": node_id,
            "depth": depth,
            "parent_toc_node_id": parent_id,
            "toc_path_id": path,
            "page_start": page,
            "toc_source": source,
            "toc_status": status,
        }
        out.append(node)
        stack.append(
            {"depth": depth, "node_id": node_id, "path": path, "child_count": 0}
        )

    return out


def to_canonical_bib_extra_toc(nodes: list[dict]) -> list[dict]:
    """本番ノード列 → canonical schema ``bib_extra.toc`` 形式へ射影。

    ``bookdx_canonical_schema_v1.json`` の ``bib_extra.toc`` は
    ``{depth(1-6), label, page}`` のフラット配列。本番ノードからの
    可逆でない簡約 (books.json / Sheet ビュー用)。
    """
    projected = []
    for node in nodes:
        depth = node.get("depth") or node.get("l") or 1
        depth = max(1, min(6, int(depth)))  # schema 制約: 1..6
        projected.append(
            {
                "depth": depth,
                "label": node.get("t", ""),
                "page": node.get("page_start"),
            }
        )
    return projected


__all__ = [
    "DEFAULT_SOURCE",
    "DEFAULT_STATUS",
    "flatten_nodes",
    "convert_legallib_nodes",
    "to_canonical_bib_extra_toc",
]
