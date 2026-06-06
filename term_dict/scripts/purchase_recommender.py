#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
purchase_recommender.py — 購入レコメンドエンジン（アイデアD / Fork 3）

未所蔵で詳細TOCを持つ書籍（defer_new 群）を、事務所の現業テーマとの
関連度でランキングし、購入候補を提案する。さらに「すでに持っている本を
2度買わない」ための重複アラートを出力する。

接合不要・単体成立（gap_recommender.py と同様にローカル/Box同期のデータを直読み）。

------------------------------------------------------------------------
設計（番頭目検で上位が現業テーマと合致することを検収基準とする）
------------------------------------------------------------------------
① 所蔵の主題分布 × 未所蔵候補のTOC主題 で関連度（gap/fit）スコア
   - 所蔵カタログ books.json の genre / ndc を domain_l1 へ写像して
     「所蔵の主題分布（= 現業テーマの強さ）」demand_share[domain] を作る。
   - 未所蔵候補は book_coverage_by_domain.json（TOCをterm_dictへ照合した
     primary_domain）と tag→domain 写像から主題プロファイル profile[domain]
     を作る。
   - score = Σ_domain ( demand_share[domain] ** weight_power ) * profile[domain]
     weight_power=1.0（既定）で「現業テーマ整合」、<1 で空白補完寄りに振れる。

② 旗艦級（高ノード数 = コンメンタール・大系・注釈・講座 等）に重み
   - flagship_weight = 1 + alpha * log1p(toc_nodes)、加えてシリーズ/書名の
     旗艦キーワードでブースト。詳細TOCほど（＝引きやすい基幹書ほど）優遇。

③ Top-N 提案表（txt / json / csv）。

「2度買い防止」アラート:
   - 候補（または任意の買い物リスト）を所蔵カタログに突き合わせ、ISBN /
     bencomId / 正規化タイトルが一致するものを「購入不要（所蔵済み）」として
     列挙。別版（near-duplicate）も注記する。

------------------------------------------------------------------------
入力（既定パスは Box 同期を想定。BOOKDX_BASE 環境変数 / --base で上書き可）
------------------------------------------------------------------------
  HOLDINGS   app/data/books.json                               所蔵カタログ(SoT)
  BENCOM     archive/data_imports/bencom_clean.json            候補プール(TOC付き)
  COVERAGE   term_dict/analysis/book_coverage_by_domain.json   候補のprimary_domain/TOC数
  TAG_DOMAIN term_dict/analysis/bencom_tag_domain_mapping.json tag→domain_l1

  （任意）DEFER_IDS  term_dict/analysis/defer_new_ids.json
     明示の defer_new id リストがあれば優先採用。無ければ
     「未所蔵 × TOCノード数>=min_toc_nodes」で動的に算出する。

Usage:
    # 実データに対して全出力を生成
    python purchase_recommender.py --base "C:/Users/Asai/Box/浅井/claude/事務所内本棚DX化計画"

    # ライブラリとして
    from purchase_recommender import PurchaseRecommender
    pr = PurchaseRecommender(base=...)
    pr.load()
    recs = pr.recommend(top_n=50)
    alerts = pr.dedup_alert()
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable, Optional


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DEFAULT_BASE = Path(
    os.environ.get(
        "BOOKDX_BASE",
        r"C:/Users/Asai/Box/浅井/claude/事務所内本棚DX化計画",
    )
)

REL = {
    "holdings": "app/data/books.json",
    "bencom": "archive/data_imports/bencom_clean.json",
    "coverage": "term_dict/analysis/book_coverage_by_domain.json",
    "tag_domain": "term_dict/analysis/bencom_tag_domain_mapping.json",
    "defer_ids": "term_dict/analysis/defer_new_ids.json",  # optional
    "out_report": "term_dict/output/purchase_recommendations.txt",
    "out_json": "term_dict/output/purchase_recommendations.json",
    "out_csv": "term_dict/output/purchase_recommendations.csv",
    "out_alert": "term_dict/output/purchase_dedup_alert.json",
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# 所蔵カタログ books.json の genre（classify_genre / NDC バックフィル由来）を
# term_dict の domain_l1 へ写像する。候補側 (book_coverage_by_domain.json) の
# domain_l1 と同じ軸に揃えることで「所蔵 × 候補」の内積が取れる。
#
# 語彙は2系統の和集合:
#   (1) booklib.py の GENRE_RULES（キーワード分類。「〜実務」「〜法務」系）
#   (2) app/data/ndc_genre_mapping.json（NDCバックフィル。「民法」「刑法」等）
# 候補軸 = {commercial, civil, administrative, labor, procedure, criminal, ip, tax}
# それ以外（other/information/international/medical）は所蔵分布には載るが候補とは
# 整合しない（内積0）。これは仕様どおり（該当候補が無いだけ）。
GENRE_TO_DOMAIN: dict[str, str] = {
    # ── commercial（商事・企業法務系）──
    "M&A": "commercial",
    "事業承継": "commercial",
    "経済法": "commercial",
    "商法・会社法": "commercial",
    "コーポレート": "commercial",
    "ファイナンス": "commercial",
    "ベンチャー・IPO": "commercial",
    "コンプライアンス": "commercial",
    "渉外法務": "commercial",
    "企業法務": "commercial",
    "登記実務": "commercial",
    "経済・経営": "commercial",
    "経営": "commercial",
    "経営管理": "commercial",
    "会計・財務": "commercial",
    # ── civil（民事系）──
    "民事実務": "civil",
    "民法": "civil",
    "家族法・相続": "civil",
    "家事実務": "civil",
    "不動産": "civil",
    "不動産法": "civil",
    "交通事故": "civil",
    "消費者法": "civil",
    "倒産法": "civil",
    # ── procedure（民事手続）──
    "訴訟実務": "procedure",
    "訴訟法": "procedure",
    "民事訴訟法": "procedure",
    # ── criminal（刑事。刑事訴訟法を含む）──
    "刑事実務": "criminal",
    "刑法": "criminal",
    "刑事訴訟法": "criminal",
    # ── administrative（公法・行政・社会保障・環境）──
    "公法実務": "administrative",
    "憲法": "administrative",
    "行政法": "administrative",
    "社会保障": "administrative",
    "環境法": "administrative",
    # ── labor（労働）──
    "労働法務": "labor",
    "労働法": "labor",
    # ── ip（知財）──
    "知的財産": "ip",
    # ── tax（税務）──
    "税務・会計": "tax",
    "税法": "tax",
    # ── 軸外（所蔵分布の母数には入るが候補とは整合しにくい）──
    "情報法": "information",
    "国際法務": "international",
    "国際法": "international",
    "医事・薬事": "medical",
    "医事法": "medical",
    "法学一般": "other",
    "法制史": "other",
    "産業一般": "other",
    "その他": "other",
}

# NDC 分類（先頭一致・最長優先）→ domain_l1。books.json の `ndc` を補助シグナルに。
# app/data/ndc_genre_mapping.json の ndc_prefix_fallback を domain へ写像したもの。
NDC_PREFIX_TO_DOMAIN: list[tuple[str, str]] = [
    ("320", "other"),         # 法学一般
    ("321", "other"),
    ("322", "other"),         # 法制史
    ("323", "administrative"),# 憲法・行政法
    ("324.6", "civil"),       # 家族法・相続
    ("324.8", "civil"),       # 不動産法
    ("324", "civil"),         # 民法
    ("325", "commercial"),    # 商法・会社法
    ("326", "criminal"),      # 刑法
    ("327.4", "civil"),       # 倒産法
    ("327.6", "criminal"),    # 刑事訴訟法
    ("327.2", "procedure"),   # 民事訴訟法
    ("327.3", "procedure"),
    ("327.5", "procedure"),
    ("327", "procedure"),     # 訴訟法（民訴系）
    ("328", "administrative"),# 行政法
    ("329", "international"),  # 国際法
    ("330", "commercial"),    # 経済・経営
    ("335", "commercial"),    # 経営
    ("336", "commercial"),    # 経営管理
    ("338", "commercial"),    # ファイナンス
    ("345", "tax"),           # 税法
    ("364", "administrative"),# 社会保障
    ("366", "labor"),         # 労働
    ("498", "medical"),       # 医事法
    ("507.2", "ip"),          # 工業所有権
    ("519", "administrative"),# 環境法
    ("007", "information"),   # 情報法
    ("673", "civil"),         # 不動産法
]

# 旗艦級（基幹書）を示す書名/シリーズのキーワード。
FLAGSHIP_KEYWORDS = (
    "コンメンタール", "大系", "注釈", "注解", "講座", "体系",
    "全書", "実務大系", "争点", "判例体系", "総覧",
)

DEFAULT_MIN_TOC_NODES = 40   # 「詳細TOC有り」の閾値（office実データで defer_new≈616 になる目安）
DEFAULT_FLAGSHIP_ALPHA = 0.20


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def _nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "")


def normalize_isbn(raw) -> str:
    """ISBN を13桁数字へ正規化。取れなければ空文字。"""
    if not raw:
        return ""
    digits = re.sub(r"[^0-9Xx]", "", str(raw))
    if len(digits) == 13 and digits.isdigit():
        return digits
    if len(digits) == 10:
        # ISBN-10 → 13 へ（978 プレフィックス + チェックディジット再計算）
        core = "978" + digits[:9]
        s = sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(core))
        check = (10 - s % 10) % 10
        return core + str(check)
    return ""


def normalize_title(s: str) -> str:
    """タイトル照合用の正規化キー（NFKC・小文字・空白/記号除去）。"""
    s = _nfkc(s).lower()
    s = re.sub(r"[\s　・,.:;！!？?（）()\[\]【】「」『』~〜\-—_/\\]+", "", s)
    return s


def flatten_toc(toc) -> list[str]:
    """TOC（入れ子可）を見出し文字列のフラットなリストへ。ノード数 = len(...)。"""
    out: list[str] = []
    if not isinstance(toc, (list, tuple)):
        return out
    for item in toc:
        if isinstance(item, str):
            t = item.strip()
            if t:
                out.append(t)
            continue
        if not isinstance(item, dict):
            continue
        # 見出しテキストの候補キー
        for k in ("t", "title", "label", "text", "heading"):
            v = item.get(k)
            if v:
                out.append(str(v).strip())
                break
        # 子ノードの候補キー
        for ck in ("children", "c", "sub", "items", "nodes"):
            if isinstance(item.get(ck), (list, tuple)):
                out.extend(flatten_toc(item[ck]))
    return out


def _as_list(value) -> list[str]:
    """str | list | None を list[str] へ。"""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple)):
        out = []
        for v in value:
            if isinstance(v, str) and v.strip():
                out.append(v.strip())
            elif v:
                out.append(str(v))
        return out
    return [str(value)]


def ndc_to_domain(ndc_value) -> Optional[str]:
    """NDC（"324.5" 等、複数可）を domain_l1 へ。最長一致を優先。"""
    best = None
    best_len = -1
    for ndc in _as_list(ndc_value):
        code = _nfkc(ndc).strip()
        for prefix, domain in NDC_PREFIX_TO_DOMAIN:
            if code.startswith(prefix) and len(prefix) > best_len:
                best, best_len = domain, len(prefix)
    return best


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Recommendation:
    """購入候補1件。"""
    rank: int
    score: float                 # 0-100 に正規化した最終スコア
    raw_score: float             # 正規化前
    relevance: float             # 所蔵分布との整合（旗艦重み前）
    flagship_weight: float
    is_flagship: bool
    book_id: str
    isbn: str
    title: str
    author: str
    publisher: str
    toc_nodes: int
    primary_domain: str
    top_domains: list = field(default_factory=list)   # [(domain, weight), ...]
    sample_headings: list = field(default_factory=list)
    bencom_url: str = ""
    dup_alert: str = ""          # 別版所蔵などの注記（空なら無し）


@dataclass
class DedupHit:
    """すでに所蔵している（=買うと2度買い）候補。"""
    book_id: str
    isbn: str
    title: str
    match_reason: str            # "isbn" / "bencom_id" / "title" / "near_title"
    held_title: str
    held_id: str


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class PurchaseRecommender:
    """購入レコメンドエンジン。IO と純粋スコア計算を分離してテスト可能にする。"""

    def __init__(
        self,
        base: Optional[Path] = None,
        min_toc_nodes: int = DEFAULT_MIN_TOC_NODES,
        weight_power: float = 1.0,
        flagship_alpha: float = DEFAULT_FLAGSHIP_ALPHA,
        present_only: bool = False,
    ):
        self.base = Path(base) if base else DEFAULT_BASE
        self.min_toc_nodes = min_toc_nodes
        self.weight_power = weight_power
        self.flagship_alpha = flagship_alpha
        self.present_only = present_only

        # loaded data
        self.holdings: list[dict] = []
        self.bencom: list[dict] = []
        self.coverage: dict[str, dict] = {}      # book_id -> {primary_domain,total_toc,...}
        self.tag_domain: dict[str, Optional[str]] = {}
        self.explicit_defer_ids: Optional[set] = None

        # derived
        self.demand: Counter = Counter()         # domain -> weight（所蔵主題分布）
        self.demand_share: dict[str, float] = {}
        self.unmapped_genres: Counter = Counter() # 写像漏れ genre の観測（実データ点検用）
        self.held_isbn: set = set()
        self.held_bencom_id: set = set()
        self.held_title: set = set()
        self._loaded = False

    # -------------------------------------------------------------------
    # Loading
    # -------------------------------------------------------------------
    def _path(self, key: str) -> Path:
        return self.base / REL[key]

    @staticmethod
    def _normalize_tag_domain(raw: dict) -> dict:
        """tag→domain 写像を {tag: domain_l1|None} へ正規化。
        値は {"domain_l1": ...} 形式・文字列・None のいずれも許容。"""
        out: dict[str, Optional[str]] = {}
        for tag, entry in (raw or {}).items():
            if isinstance(entry, dict):
                out[tag] = entry.get("domain_l1")
            else:
                out[tag] = entry
        return out

    def load(self):
        if self._loaded:
            return
        with open(self._path("holdings"), encoding="utf-8") as f:
            self.holdings = json.load(f)
        with open(self._path("bencom"), encoding="utf-8") as f:
            self.bencom = json.load(f)
        with open(self._path("coverage"), encoding="utf-8") as f:
            cov = json.load(f)
        for bk in cov.get("books", cov if isinstance(cov, list) else []):
            bid = bk.get("book_id") or bk.get("id")
            if bid:
                self.coverage[str(bid)] = bk
        tag_path = self._path("tag_domain")
        if tag_path.exists():
            with open(tag_path, encoding="utf-8") as f:
                self.tag_domain = self._normalize_tag_domain(json.load(f))
        defer_path = self._path("defer_ids")
        if defer_path.exists():
            with open(defer_path, encoding="utf-8") as f:
                ids = json.load(f)
            self.explicit_defer_ids = set(map(str, ids))

        self.build_indices()
        self._loaded = True

    def load_from_memory(
        self,
        holdings: list[dict],
        bencom: list[dict],
        coverage: Optional[list[dict]] = None,
        tag_domain: Optional[dict] = None,
        defer_ids: Optional[Iterable] = None,
    ):
        """テスト用: ファイルを介さずに in-memory データを注入。"""
        self.holdings = holdings
        self.bencom = bencom
        self.coverage = {}
        for bk in (coverage or []):
            bid = bk.get("book_id") or bk.get("id")
            if bid:
                self.coverage[str(bid)] = bk
        self.tag_domain = self._normalize_tag_domain(tag_domain or {})
        self.explicit_defer_ids = set(map(str, defer_ids)) if defer_ids is not None else None
        self.build_indices()
        self._loaded = True

    # -------------------------------------------------------------------
    # Indices / demand distribution（所蔵の主題分布）
    # -------------------------------------------------------------------
    def build_indices(self):
        self.demand = Counter()
        self.held_isbn = set()
        self.held_bencom_id = set()
        self.held_title = set()

        for b in self.holdings:
            if self.present_only and not self._is_present(b):
                continue
            # 重複検出用インデックス
            isbn = normalize_isbn(b.get("isbn") or (b.get("external_refs") or {}).get("isbn"))
            if isbn:
                self.held_isbn.add(isbn)
            bcid = str(b.get("bencomId") or "").strip()
            if bcid:
                self.held_bencom_id.add(bcid)
            tkey = normalize_title(b.get("title", ""))
            if tkey:
                self.held_title.add(tkey)

            # 主題分布: genre（複数可）→domain、無ければ ndc→domain
            domains = self._holding_domains(b)
            if not domains:
                continue
            w = 1.0 / len(domains)
            for d in domains:
                self.demand[d] += w

        total = sum(self.demand.values()) or 1.0
        self.demand_share = {d: c / total for d, c in self.demand.items()}

    @staticmethod
    def _is_present(b: dict) -> bool:
        st = b.get("status") or {}
        return bool(
            st.get("physical") or st.get("cut") or st.get("scanned")
            or b.get("shelfLabel") or b.get("pdfFiles")
        )

    def _holding_domains(self, b: dict) -> list[str]:
        """所蔵1冊の主題（domain_l1）リスト。genre優先、補助でndc。"""
        domains: list[str] = []
        unmapped: list[str] = []
        for g in _as_list(b.get("genre")):
            key = g.strip()
            d = GENRE_TO_DOMAIN.get(key)
            if d:
                domains.append(d)
            elif key:
                unmapped.append(key)
        if not domains:
            d = ndc_to_domain(b.get("ndc"))
            if d:
                domains.append(d)
            else:
                # genre も ndc も写像できなかった → 観測（写像辞書の補正点になる）
                for key in unmapped:
                    self.unmapped_genres[key] += 1
        # 重複除去（順序保持）
        seen = set()
        uniq = []
        for d in domains:
            if d not in seen:
                seen.add(d)
                uniq.append(d)
        return uniq

    # -------------------------------------------------------------------
    # Candidate profile（未所蔵候補のTOC主題）
    # -------------------------------------------------------------------
    def _candidate_profile(self, book: dict) -> dict[str, float]:
        """候補1冊の主題プロファイル profile[domain]（合計1へ正規化）。"""
        prof: Counter = Counter()
        bid = str(book.get("id", ""))
        cov = self.coverage.get(bid, {})

        # (a) book_coverage の primary_domain（TOCをterm_dictへ照合した主結果）
        pdom = cov.get("primary_domain")
        if pdom and pdom != "unclassified":
            prof[pdom] += 2.0

        # (b) domain_hits があれば加点（book_coverage_by_domain.json の実フィールド名は
        #     domain_hits = {domain: ヒット数}。別名 domain_distribution/domains も許容）
        dist = cov.get("domain_hits") or cov.get("domain_distribution") or cov.get("domains")
        if isinstance(dist, dict):
            for d, c in dist.items():
                if d and d not in ("unclassified", "unknown"):
                    prof[d] += float(c)

        # (c) tags → domain（term_dict照合が疎なため重要なフォールバック）
        for tag in _as_list(book.get("tags")):
            d = self.tag_domain.get(tag)
            if d and d not in ("unclassified", "unknown"):
                prof[d] += 1.0

        total = sum(prof.values())
        if total <= 0:
            return {}
        return {d: c / total for d, c in prof.items()}

    # -------------------------------------------------------------------
    # Scoring
    # -------------------------------------------------------------------
    def _relevance(self, profile: dict[str, float]) -> float:
        """所蔵分布との整合度。weight_power で現業整合↔空白補完を制御。"""
        s = 0.0
        for d, w in profile.items():
            share = self.demand_share.get(d, 0.0)
            s += (share ** self.weight_power) * w
        return s

    def _toc_nodes(self, book: dict) -> int:
        bid = str(book.get("id", ""))
        cov = self.coverage.get(bid, {})
        if cov.get("total_toc"):
            return int(cov["total_toc"])
        return len(flatten_toc(book.get("toc")))

    def _flagship(self, book: dict, toc_nodes: int) -> tuple[float, bool]:
        weight = 1.0 + self.flagship_alpha * math.log1p(max(0, toc_nodes))
        text = _nfkc(book.get("title", "")) + " " + " ".join(_as_list(book.get("tags")))
        is_flag = any(kw in text for kw in FLAGSHIP_KEYWORDS) or toc_nodes >= 200
        if is_flag:
            weight *= 1.25
        return weight, is_flag

    # -------------------------------------------------------------------
    # Held / dedup
    # -------------------------------------------------------------------
    def _held_match(self, book: dict) -> tuple[bool, str]:
        """所蔵済みか。(held, reason)。reason: isbn/bencom_id/title/near_title/''"""
        isbn = normalize_isbn(book.get("isbn"))
        if isbn and isbn in self.held_isbn:
            return True, "isbn"
        bid = str(book.get("id") or book.get("bencomId") or "").strip()
        if bid and bid in self.held_bencom_id:
            return True, "bencom_id"
        tkey = normalize_title(book.get("title", ""))
        if tkey and tkey in self.held_title:
            return True, "title"
        return False, ""

    # -------------------------------------------------------------------
    # defer_new selection
    # -------------------------------------------------------------------
    def select_defer_new(self) -> list[dict]:
        """未所蔵 × 詳細TOC有り の候補（defer_new）。
        明示idリストがあればそれを採用、無ければ動的算出。"""
        out = []
        for book in self.bencom:
            bid = str(book.get("id", ""))
            if self.explicit_defer_ids is not None:
                if bid not in self.explicit_defer_ids:
                    continue
            else:
                held, _ = self._held_match(book)
                if held:
                    continue
                if self._toc_nodes(book) < self.min_toc_nodes:
                    continue
            out.append(book)
        return out

    # -------------------------------------------------------------------
    # Recommend
    # -------------------------------------------------------------------
    def recommend(self, top_n: int = 50) -> list[Recommendation]:
        self.load()
        scored: list[Recommendation] = []
        for book in self.select_defer_new():
            profile = self._candidate_profile(book)
            if not profile:
                continue  # 主題が取れない候補はスキップ（番頭目検の精度を守る）
            relevance = self._relevance(profile)
            if relevance <= 0:
                continue
            toc_nodes = self._toc_nodes(book)
            fw, is_flag = self._flagship(book, toc_nodes)
            raw = relevance * fw
            top_domains = sorted(profile.items(), key=lambda x: -x[1])[:3]
            headings = flatten_toc(book.get("toc"))[:6]
            # near-duplicate（別版所蔵）注記
            _, reason = self._held_match(book)
            dup = ""
            tkey = normalize_title(book.get("title", ""))
            if not reason and tkey and any(
                tkey in h or h in tkey for h in self.held_title if len(h) > 6 and len(tkey) > 6
            ):
                dup = "別版/類似タイトルを所蔵の可能性"
            scored.append(Recommendation(
                rank=0, score=0.0, raw_score=raw, relevance=relevance,
                flagship_weight=fw, is_flagship=is_flag,
                book_id=str(book.get("id", "")),
                isbn=normalize_isbn(book.get("isbn")),
                title=book.get("title", ""),
                author=book.get("author", ""),
                publisher=book.get("publisher", ""),
                toc_nodes=toc_nodes,
                primary_domain=self.coverage.get(str(book.get("id", "")), {}).get("primary_domain", ""),
                top_domains=top_domains,
                sample_headings=headings,
                bencom_url=book.get("bencomUrl") or book.get("url", ""),
                dup_alert=dup,
            ))

        scored.sort(key=lambda r: -r.raw_score)
        top = scored[:top_n]
        max_raw = top[0].raw_score if top else 1.0
        for i, r in enumerate(top, 1):
            r.rank = i
            r.score = round(100.0 * r.raw_score / max_raw, 2) if max_raw else 0.0
            r.raw_score = round(r.raw_score, 6)
            r.relevance = round(r.relevance, 6)
            r.flagship_weight = round(r.flagship_weight, 4)
        return top

    # -------------------------------------------------------------------
    # Dedup alert（2度買い防止）
    # -------------------------------------------------------------------
    def dedup_alert(self, candidates: Optional[list[dict]] = None) -> list[DedupHit]:
        """候補（既定: bencom 全体）のうち所蔵済みのものを列挙。
        買い物リスト(dict list)を渡せば、その2度買いチェックにも使える。"""
        self.load()
        pool = candidates if candidates is not None else self.bencom
        # held_id -> title 逆引き
        id_to_title = {}
        isbn_to_title = {}
        title_to_title = {}
        for b in self.holdings:
            t = b.get("title", "")
            bcid = str(b.get("bencomId") or "").strip()
            if bcid:
                id_to_title[bcid] = (b.get("id", ""), t)
            isbn = normalize_isbn(b.get("isbn") or (b.get("external_refs") or {}).get("isbn"))
            if isbn:
                isbn_to_title[isbn] = (b.get("id", ""), t)
            tk = normalize_title(t)
            if tk:
                title_to_title[tk] = (b.get("id", ""), t)

        hits: list[DedupHit] = []
        for book in pool:
            isbn = normalize_isbn(book.get("isbn"))
            bid = str(book.get("id") or book.get("bencomId") or "").strip()
            tkey = normalize_title(book.get("title", ""))
            held_id, held_title, reason = "", "", ""
            if isbn and isbn in isbn_to_title:
                held_id, held_title = isbn_to_title[isbn]; reason = "isbn"
            elif bid and bid in id_to_title:
                held_id, held_title = id_to_title[bid]; reason = "bencom_id"
            elif tkey and tkey in title_to_title:
                held_id, held_title = title_to_title[tkey]; reason = "title"
            if reason:
                hits.append(DedupHit(
                    book_id=str(book.get("id", "")),
                    isbn=isbn,
                    title=book.get("title", ""),
                    match_reason=reason,
                    held_title=held_title,
                    held_id=str(held_id),
                ))
        return hits

    # -------------------------------------------------------------------
    # Reporting
    # -------------------------------------------------------------------
    def demand_summary(self) -> list[tuple[str, float, float]]:
        """所蔵の主題分布 [(domain, weight, share), ...]（share降順）。"""
        rows = [(d, self.demand[d], self.demand_share[d]) for d in self.demand]
        rows.sort(key=lambda x: -x[2])
        return rows

    def full_report(self, top_n: int = 50) -> str:
        self.load()
        recs = self.recommend(top_n=top_n)
        alerts = self.dedup_alert()
        defer = self.select_defer_new()

        L = []
        L.append("=" * 76)
        L.append("購入レコメンド（アイデアD / Fork 3）")
        L.append("=" * 76)
        L.append("")
        L.append("■ サマリ")
        L.append(f"  所蔵カタログ件数 : {len(self.holdings):,}")
        L.append(f"  候補プール(bencom): {len(self.bencom):,}")
        L.append(f"  defer_new（未所蔵×詳細TOC, min_toc_nodes={self.min_toc_nodes}）: {len(defer):,}")
        L.append(f"  weight_power={self.weight_power}  flagship_alpha={self.flagship_alpha}")
        L.append("")
        L.append("■ 所蔵の主題分布（= 現業テーマの強さ）")
        for d, w, share in self.demand_summary():
            L.append(f"    {d:<14} {share*100:5.1f}%  ({w:.1f})")
        if self.unmapped_genres:
            L.append("")
            L.append("  ⚠ 未写像 genre（GENRE_TO_DOMAIN 補正候補・上位10）:")
            for g, c in self.unmapped_genres.most_common(10):
                L.append(f"      {g}  ×{c}")
        L.append("")
        L.append("-" * 76)
        L.append(f"■ Top {len(recs)} 購入提案")
        L.append("-" * 76)
        for r in recs:
            flag = " ★旗艦" if r.is_flagship else ""
            doms = ", ".join(f"{d}:{w:.2f}" for d, w in r.top_domains)
            L.append(f"  {r.rank:3d}. [{r.score:5.1f}] {r.title[:54]}{flag}")
            L.append(f"        著者={r.author[:30]}  出版={r.publisher[:24]}")
            L.append(f"        TOCノード={r.toc_nodes}  主題[{doms}]  ISBN={r.isbn}")
            if r.dup_alert:
                L.append(f"        ⚠ {r.dup_alert}")
        L.append("")
        L.append("-" * 76)
        L.append(f"■ 2度買い防止アラート（候補プール中の所蔵済み）: {len(alerts)} 件")
        L.append("-" * 76)
        for h in alerts[:50]:
            L.append(f"    ✗ {h.title[:54]}  ←所蔵済み({h.match_reason}: {h.held_title[:30]})")
        if len(alerts) > 50:
            L.append(f"    … 他 {len(alerts)-50} 件")
        L.append("")
        L.append("=" * 76)
        L.append("End of report.")
        return "\n".join(L)

    def generate_all_outputs(self, top_n: int = 100):
        self.load()
        recs = self.recommend(top_n=top_n)
        alerts = self.dedup_alert()
        report = self.full_report(top_n=top_n)

        out_report = self._path("out_report")
        out_report.parent.mkdir(parents=True, exist_ok=True)
        out_report.write_text(report, encoding="utf-8")

        self._path("out_json").write_text(
            json.dumps([asdict(r) for r in recs], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        with open(self._path("out_csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["rank", "score", "title", "author", "publisher",
                        "primary_domain", "toc_nodes", "is_flagship", "isbn",
                        "top_domains", "dup_alert", "bencom_url"])
            for r in recs:
                w.writerow([
                    r.rank, r.score, r.title, r.author, r.publisher,
                    r.primary_domain, r.toc_nodes, int(r.is_flagship), r.isbn,
                    ";".join(f"{d}:{wt:.2f}" for d, wt in r.top_domains),
                    r.dup_alert, r.bencom_url,
                ])

        self._path("out_alert").write_text(
            json.dumps([asdict(h) for h in alerts], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"Report  : {self._path('out_report')}")
        print(f"JSON    : {self._path('out_json')}")
        print(f"CSV     : {self._path('out_csv')}")
        print(f"Alert   : {self._path('out_alert')}  ({len(alerts)} 件)")
        print()
        print("Top 5 購入提案:")
        for r in recs[:5]:
            print(f"  {r.rank}. [{r.score}] {r.title[:50]} "
                  f"(TOC={r.toc_nodes}, {'旗艦' if r.is_flagship else '通常'})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="購入レコメンド（アイデアD）")
    ap.add_argument("--base", default=str(DEFAULT_BASE),
                    help="事務所内本棚DX化計画 のベースディレクトリ")
    ap.add_argument("--top-n", type=int, default=100)
    ap.add_argument("--min-toc-nodes", type=int, default=DEFAULT_MIN_TOC_NODES,
                    help="defer_new 判定: 詳細TOCとみなすノード数の下限")
    ap.add_argument("--weight-power", type=float, default=1.0,
                    help="1.0=現業テーマ整合, <1.0=空白補完寄り")
    ap.add_argument("--flagship-alpha", type=float, default=DEFAULT_FLAGSHIP_ALPHA)
    ap.add_argument("--present-only", action="store_true",
                    help="所蔵分布を物理/スキャン所持本のみで集計")
    ap.add_argument("--print", dest="do_print", action="store_true",
                    help="ファイル出力せずレポートを標準出力")
    args = ap.parse_args(argv)

    pr = PurchaseRecommender(
        base=args.base,
        min_toc_nodes=args.min_toc_nodes,
        weight_power=args.weight_power,
        flagship_alpha=args.flagship_alpha,
        present_only=args.present_only,
    )
    if args.do_print:
        print(pr.full_report(top_n=args.top_n))
    else:
        pr.generate_all_outputs(top_n=args.top_n)


if __name__ == "__main__":
    main()
