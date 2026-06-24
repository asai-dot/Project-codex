#!/usr/bin/env python3
"""
DD-FORMOBJ-001 S1: 式 → toc_node アドレスリゾルバ（参照実装 v0.1）

役割: 書式(式)を、その書籍のTOCノード(toc_nodes)へ対応付け、anchorのnull
      (toc_node_id / page_span_print / span_kind / match_*)を埋める。
方式: norm_title_v1(誤謬クラス吸収) → 親パス修飾スコープ → ladder → ordinalタイブレーク
      → 一致無し(解説埋込型)は内包セクションへフォールバック(review)。

toc_nodes未投入でも動くよう、入力はノード配列(辞書)。本ファイルは __main__ で自己テスト。
DD-TOCATTACH-001 §1.2/1.3 準拠。ノード発明はしない(gate_no_node_invention)。
"""
from __future__ import annotations
import re, unicodedata
from dataclasses import dataclass, field
from typing import Optional

NORM_VERSION = "norm_title_v1"

# 確定誤謬クラス(語単位置換)。LB系統OCR誤字「廷→延」を吸収(意味のある誤り=表示は別途corrected snapshot)。
# 正規化キー上だけで吸収し、過剰マージ(延期/順延の正当な"延")は起こさない語単位設計。
ERROR_CLASSES: list[tuple[str, str]] = [
    ("公判延", "公判廷"), ("開延", "開廷"), ("閉延", "閉廷"),
    ("法延", "法廷"), ("出延", "出廷"), ("退延", "退廷"),
]

_PUA = re.compile(r"[-]")
_SYM = str.maketrans({"‐":"-","―":"-","—":"-","－":"-","〜":"~","～":"~","・":"","､":"","、":"","，":"",})
_DROP = re.compile(r"[\s　:：。.／/_~()（）〈〉<>\[\]【】「」『』〔〕#＃!！?？*＊・]")

def norm_title_v1(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKC", s)
    s = _PUA.sub("", s)
    for wrong, right in ERROR_CLASSES:
        s = s.replace(wrong, right)
    s = s.lower().translate(_SYM)
    s = _DROP.sub("", s)
    return s

@dataclass
class TocNode:
    toc_node_id: str
    parent_toc_node_id: Optional[str]
    ordinal: int
    level: int
    title: str
    page: Optional[int] = None
    end_page: Optional[int] = None

@dataclass
class Resolution:
    toc_node_id: Optional[str]
    match_kind: str            # exact_title_page|normalized_title|title_only|embedded_parent|unmatched
    match_score: float
    decision_status: str       # auto|review|unmatched
    page_span_print: Optional[list] = None
    span_kind: str = "single_node"   # single_node|subtree|embedded|multi_node
    norm_version: str = NORM_VERSION
    note: str = ""
    candidates: list = field(default_factory=list)

def _parent_path(nodes: dict, nid: Optional[str]) -> tuple:
    path=[]
    while nid and nid in nodes:
        path.append(nid); nid=nodes[nid].parent_toc_node_id
    return tuple(reversed(path))

def _page_span(node: TocNode, ordered: list[TocNode]) -> Optional[list]:
    if node.page is None: return None
    if node.end_page is not None: return [node.page, node.end_page]
    # 次の同階層以上(level<=)ノードの page-1 を終端に
    start=node.page; idx=ordered.index(node)
    for nxt in ordered[idx+1:]:
        if nxt.level <= node.level and nxt.page and nxt.page > start:
            return [start, nxt.page-1]
    return [start, start]

def resolve_form(form_title: str, nodes: list[TocNode],
                 form_page_hint: Optional[int]=None,
                 parent_scope_id: Optional[str]=None) -> Resolution:
    """式名 → ノード対応。parent_scope_id 指定時はその部分木に絞る(衝突回避)。"""
    nd = {n.toc_node_id: n for n in nodes}
    ordered = sorted(nodes, key=lambda n: n.ordinal)
    ft = norm_title_v1(form_title)

    # スコープ: parent_scope指定があれば部分木に限定
    def in_scope(n: TocNode) -> bool:
        if not parent_scope_id: return True
        return parent_scope_id in _parent_path(nd, n.toc_node_id)
    pool = [n for n in ordered if in_scope(n)]

    # ladder 1: 正規化タイトル一致(+頁ヒントがあれば exact_title_page)
    norm_hits = [n for n in pool if norm_title_v1(n.title) == ft and ft]
    if not norm_hits:
        # 包含一致(式名がノード見出しに含まれる/その逆) — 書式集の「巻末資料1〔型〕式名」対策
        norm_hits = [n for n in pool if ft and (ft in norm_title_v1(n.title) or norm_title_v1(n.title) in ft)
                     and min(len(ft), len(norm_title_v1(n.title))) >= 6]
    if norm_hits:
        if len(norm_hits) == 1:
            n = norm_hits[0]
            return Resolution(n.toc_node_id, "normalized_title", 0.95, "auto",
                              _page_span(n, ordered),
                              "subtree" if any(c.parent_toc_node_id==n.toc_node_id for c in nodes) else "single_node")
        # 複数 → ordinal近接(頁ヒント)でタイブレーク、決まらねば review
        if form_page_hint is not None:
            n = min(norm_hits, key=lambda x: abs((x.page or 10**9) - form_page_hint))
            return Resolution(n.toc_node_id, "normalized_title", 0.8, "review",
                              _page_span(n, ordered), "single_node",
                              note=f"{len(norm_hits)}候補をページ近接で選択")
        return Resolution(None, "title_only", 0.6, "review", None, "single_node",
                          note=f"{len(norm_hits)}候補(親パス修飾/頁ヒント要)",
                          candidates=[n.toc_node_id for n in norm_hits])

    # ladder 2: 一致無し → 解説埋込型。頁ヒントから内包セクションへフォールバック
    if form_page_hint is not None:
        enclosing = [n for n in ordered if n.page is not None and n.page <= form_page_hint]
        if enclosing:
            # 同頁なら最も具体的(ordinal大=直前の最深セクション)を内包親に
            n = max(enclosing, key=lambda x: (x.page, x.ordinal))
            return Resolution(n.toc_node_id, "embedded_parent", 0.5, "review",
                              _page_span(n, ordered), "embedded",
                              note="式は独立ノード無し(埋込)。内包セクションへ係留→vision再分割対象")
    return Resolution(None, "unmatched", 0.0, "unmatched", None, "embedded",
                      note="ノード対応なし・頁ヒントなし → 要手当")

# ----------------------- 自己テスト(toc_nodes投入前の検証) -----------------------
if __name__ == "__main__":
    ok = 0; total = 0
    def check(name, cond):
        global ok, total; total += 1
        print(("PASS" if cond else "FAIL"), name); ok += bool(cond)

    # norm: 誤謬クラス吸収(公判延=公判廷) / 記号・空白除去
    check("norm 延→廷吸収", norm_title_v1("第282条〔公判延〕") == norm_title_v1("第282条〔公判廷〕"))
    check("norm 順延は不変(過剰マージ無し)", "延" in norm_title_v1("支払の順延について"))

    # 書式集(業務委託): 巻末資料見出しに式名包含 → auto
    book_a = [
        TocNode("a1", None, 134, 1, "巻末資料１〔製造委託型〕 製造委託基本契約書（サンプル）", 216, 233),
        TocNode("a2", None, 135, 1, "巻末資料２〔役務提供型〕 業務委託契約書（サンプル）", 234, 249),
    ]
    r = resolve_form("製造委託基本契約書（サンプル）", book_a)
    check("書式集 包含一致=auto", r.decision_status=="auto" and r.toc_node_id=="a1")
    check("書式集 page_span", r.page_span_print==[216,233])

    # 衝突(逐条 "Ⅰ 趣旨" が複数親下) → 親スコープで一意化
    book_b = [
        TocNode("p282", None, 0, 3, "第282条〔公判廷〕", 1),
        TocNode("p282_1", "p282", 1, 4, "Ⅰ 趣旨", 1),
        TocNode("p283", None, 5, 3, "第283条", 8),
        TocNode("p283_1", "p283", 6, 4, "Ⅰ 趣旨", 8),
    ]
    r_amb = resolve_form("Ⅰ 趣旨", book_b)
    check("衝突=review(スコープ無し)", r_amb.decision_status=="review")
    r_scoped = resolve_form("Ⅰ 趣旨", book_b, parent_scope_id="p283")
    check("親スコープで一意=auto", r_scoped.decision_status=="auto" and r_scoped.toc_node_id=="p283_1")

    # 解説埋込(契約解消): 式名に対応ノード無し→頁ヒントで内包セクションへ係留(embedded/review)
    book_c = [
        TocNode("s_kihon", None, 28, 3, "２．解除通知作成のポイント", 60),
        TocNode("s_rei", "s_kihon", 29, 4, "⑴ はじめに―解除通知の例", 60),
        TocNode("s_letter", "s_kihon", 30, 4, "⑵ レターヘッド", 63),
    ]
    r_emb = resolve_form("解除通知書（英文文例）", book_c, form_page_hint=61)
    check("埋込=embedded/review", r_emb.span_kind=="embedded" and r_emb.decision_status=="review" and r_emb.toc_node_id=="s_rei")

    print(f"\n{ok}/{total} passed")
