#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
purchase_recommender.py — 購入レコメンドエンジン（アイデアD / Fork 3）

未所蔵で詳細TOCを持つ書籍（defer_new 群）を、事務所の現業テーマとの
関連度でランキングし、購入候補を提案する。さらに「すでに持っている本を
2度買わない」ための重複アラートを出力する。

データソースは2系統（--source）:
  - json     : ローカル/Box同期のJSONを直読み（既定。gap_recommender.py と同流儀）
  - supabase : private `bookdx` schema を SQL で読む（大容量JSONを実行環境に
               持ち込めない場合の実走経路。read-only role で接続）

------------------------------------------------------------------------
設計（番頭目検で上位が現業テーマと合致することを検収基準とする）
------------------------------------------------------------------------
① 所蔵の主題分布 × 未所蔵候補のTOC主題 で関連度（fit）スコア
   - 所蔵カタログ books.json の genre / ndc を domain_l1 へ写像して
     「所蔵の主題分布（= 現業テーマの強さ）」を作る。母数は2系統:
       demand_share_all      … 全 domain（参考）
       demand_share_in_scope … 候補軸8 domain のみ（ランキング既定）       [監査F5]
   - 未所蔵候補は book_coverage_by_domain.json（primary_domain / domain_hits）と
     tag→domain 写像から主題プロファイル profile[domain] を作る。
     併せて profile_source / profile_confidence を付与（tag fallback の過信回避）[監査F3]
   - score = Σ_domain ( demand_share[domain] ** weight_power ) * profile[domain]
     weight_power=1.0（既定）で「現業テーマ整合」、<1 で空白補完寄りに振れる。

② 旗艦級（高ノード数 = コンメンタール・大系・注釈・講座 等）に重み
   - flagship_weight = 1 + alpha * log1p(toc_nodes) ＋ 旗艦キーワードでブースト。

③ Top-N 提案表（txt / json / csv）。

「2度買い防止」アラート（強弱2レーン）:                                    [監査F2]
   - 強一致（自動「所蔵済み＝買うな」）: 正規化ISBN / bencomId 一致
   - ソフト一致（レビュー候補。自動除外しない）: 正規化タイトル（＋著者/出版社）一致

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

Supabase（--source supabase）:
   接続は env BOOKDX_DB_URL（read-only role 推奨）。private `bookdx` schema を読む。
   books.json は依然 SoT。bookdx.* はそこからの一方向リードレプリカで write-back しない。

Usage:
    python purchase_recommender.py --base "C:/Users/Asai/Box/.../事務所内本棚DX化計画"
    python purchase_recommender.py --source supabase --db-url "postgresql://...:5432/postgres"

    from purchase_recommender import PurchaseRecommender
    pr = PurchaseRecommender(base=...); pr.load()
    recs = pr.recommend(top_n=50); alerts = pr.dedup_alert()
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Iterable, Optional


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
# 候補軸 = IN_SCOPE_DOMAINS。それ以外（other/information/international/medical）は
# 所蔵分布(all)には載るが in_scope では除外（ランキングは in_scope を使う）。 [監査F5]
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
    # ── 軸外（所蔵分布(all)の母数には入るが候補とは整合しにくい）──
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

# 候補側 domain_l1 軸（ランキングで使う in_scope 母数）。bookdx.candidates の
# primary_domain CHECK 制約とも一致させる（unclassified/unknown は除外）。
IN_SCOPE_DOMAINS = (
    "commercial", "civil", "administrative", "labor",
    "procedure", "criminal", "ip", "tax",
)
NON_DOMAIN = ("unclassified", "unknown")

# 旗艦級（基幹書）を示す書名/シリーズのキーワード。
FLAGSHIP_KEYWORDS = (
    "コンメンタール", "大系", "注釈", "注解", "講座", "体系",
    "全書", "実務大系", "争点", "判例体系", "総覧",
)

DEFAULT_MIN_TOC_NODES = 40   # 「詳細TOC有り」の閾値（office実データで defer_new≈616 の目安）
DEFAULT_FLAGSHIP_ALPHA = 0.20

# 候補プロファイルの confidence 固定閾値（監査F3: 実装者が後で恣意調整しないよう固定）。
# term_dict 照合は疎（matched_toc は小さく、coverage 中央値 ~0.02-0.03）なので、
# high は「明確に TOC が辞書と当たっている」少数に限定する保守的な値。
CONF_HIGH_MATCHED_TOC = 5     # high: matched_toc >= 5 かつ
CONF_HIGH_COVERAGE = 0.05     #       coverage >= 0.05
PROFILE_SOURCES = ("toc_term_dict", "tag_domain_fallback", "mixed", "unclassified")
PROFILE_CONFIDENCES = ("high", "medium", "low")


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
        core = "978" + digits[:9]
        s = sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(core))
        check = (10 - s % 10) % 10
        return core + str(check)
    return ""


def normalize_title(s: str) -> str:
    """照合用の正規化キー（NFKC・小文字・空白/記号除去）。著者/出版社にも流用。"""
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
        for k in ("t", "title", "label", "text", "heading"):
            v = item.get(k)
            if v:
                out.append(str(v).strip())
                break
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


def compute_candidate_profile(
    primary_domain: Optional[str],
    domain_hits: Optional[dict],
    tags: Optional[list],
    tag_domain: dict,
    matched_toc: int = 0,
    coverage: float = 0.0,
) -> tuple[dict[str, float], str, str]:
    """候補の (profile, profile_source, profile_confidence) を計算する純関数。 [監査F3]

    engine（_candidate_signal）と loader（load_to_supabase）で共有し、写像/閾値の
    ドリフトを防ぐ。confidence 閾値は CONF_HIGH_* に固定。
    """
    prof: Counter = Counter()
    toc_signal = False
    tag_signal = False

    if primary_domain and primary_domain not in NON_DOMAIN:
        prof[primary_domain] += 2.0
        toc_signal = True
    if isinstance(domain_hits, dict):
        for d, c in domain_hits.items():
            if d and d not in NON_DOMAIN:
                prof[d] += float(c)
                toc_signal = True
    for tag in _as_list(tags):
        d = tag_domain.get(tag)
        if d and d not in NON_DOMAIN:
            prof[d] += 1.0
            tag_signal = True

    total = sum(prof.values())
    if total <= 0:
        return {}, "unclassified", "low"
    profile = {d: c / total for d, c in prof.items()}

    if toc_signal and tag_signal:
        source = "mixed"
    elif toc_signal:
        source = "toc_term_dict"
    else:
        source = "tag_domain_fallback"

    if toc_signal and int(matched_toc or 0) >= CONF_HIGH_MATCHED_TOC \
            and float(coverage or 0.0) >= CONF_HIGH_COVERAGE:
        confidence = "high"
    elif toc_signal:
        confidence = "medium"
    else:
        confidence = "low"
    return profile, source, confidence


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Recommendation:
    """購入候補1件。"""
    rank: int
    score: float                 # 0-100 に正規化した最終スコア
    raw_score: float
    relevance: float
    flagship_weight: float
    is_flagship: bool
    book_id: str
    isbn: str
    title: str
    author: str
    publisher: str
    toc_nodes: int
    primary_domain: str
    profile_source: str = "unclassified"      # [監査F3]
    profile_confidence: str = "low"           # high/medium/low [監査F3]
    demand_scope: str = "in_scope"            # スコアに使った母数 [監査F5]
    top_domains: list = field(default_factory=list)   # [(domain, weight), ...]
    sample_headings: list = field(default_factory=list)
    bencom_url: str = ""
    dup_alert: str = ""          # ソフト一致（別版所蔵の可能性）注記。空なら無し


@dataclass
class DedupHit:
    """所蔵済み候補（2度買い）。強一致＝買うな / ソフト一致＝要レビュー。 [監査F2]"""
    book_id: str
    isbn: str
    title: str
    match_strength: str          # "strong" | "soft"
    match_reason: str            # isbn / bencom_id / title / title_author / title_publisher
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
        demand_scope: str = "in_scope",   # "in_scope"（既定・ランキング用）| "all"
    ):
        self.base = Path(base) if base else DEFAULT_BASE
        self.min_toc_nodes = min_toc_nodes
        self.weight_power = weight_power
        self.flagship_alpha = flagship_alpha
        self.present_only = present_only
        self.demand_scope = demand_scope

        # loaded data
        self.holdings: list[dict] = []
        self.bencom: list[dict] = []
        self.coverage: dict[str, dict] = {}
        self.tag_domain: dict[str, Optional[str]] = {}
        self.explicit_defer_ids: Optional[set] = None

        # derived demand（所蔵主題分布）
        self.demand_all: Counter = Counter()
        self.demand_in: Counter = Counter()
        self.demand_share_all: dict[str, float] = {}
        self.demand_share_in_scope: dict[str, float] = {}
        self.unmapped_genres: Counter = Counter()

        # dedup indices: strong（isbn/bencom_id） & soft（title / title|author / title|publisher）
        self.held_isbn: dict[str, tuple] = {}        # isbn -> (held_id, held_title)
        self.held_bencom_id: dict[str, tuple] = {}
        self.held_title: dict[str, tuple] = {}
        self.held_title_author: dict[str, tuple] = {}
        self.held_title_pub: dict[str, tuple] = {}
        self._loaded = False

    # active demand share（ランキングで使う母数）
    @property
    def demand_share(self) -> dict[str, float]:
        return self.demand_share_all if self.demand_scope == "all" else self.demand_share_in_scope

    # -------------------------------------------------------------------
    # Loading
    # -------------------------------------------------------------------
    def _path(self, key: str) -> Path:
        return self.base / REL[key]

    @staticmethod
    def _normalize_tag_domain(raw: dict) -> dict:
        """tag→domain 写像を {tag: domain_l1|None} へ正規化。"""
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
        """テスト用 / SupabaseDataSource 用: in-memory データを注入。"""
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

    def load_supabase(self, query_runner: Callable[[str], list], schema: str = "bookdx"):
        """private `bookdx` schema から読み込む（read-only role 接続を想定）。
        query_runner(sql)->list[dict] を注入（本番=psycopg / テスト=フェイク）。"""
        ds = SupabaseDataSource(query_runner, schema=schema)
        holdings, bencom, coverage, tag_domain = ds.fetch()
        self.load_from_memory(holdings, bencom, coverage, tag_domain)

    # -------------------------------------------------------------------
    # Indices / demand distribution（所蔵の主題分布）
    # -------------------------------------------------------------------
    def build_indices(self):
        self.demand_all = Counter()
        self.held_isbn = {}
        self.held_bencom_id = {}
        self.held_title = {}
        self.held_title_author = {}
        self.held_title_pub = {}

        for b in self.holdings:
            if self.present_only and not self._is_present(b):
                continue
            hid = str(b.get("id", ""))
            title = b.get("title", "")
            # dedup インデックス（強/ソフト）
            isbn = normalize_isbn(b.get("isbn") or (b.get("external_refs") or {}).get("isbn"))
            if isbn:
                self.held_isbn[isbn] = (hid, title)
            bcid = str(b.get("bencomId") or "").strip()
            if bcid:
                self.held_bencom_id[bcid] = (hid, title)
            tkey = normalize_title(title)
            if tkey:
                self.held_title[tkey] = (hid, title)
                akey = normalize_title(b.get("author", ""))
                if akey:
                    self.held_title_author[tkey + "|" + akey] = (hid, title)
                pkey = normalize_title(b.get("publisher", ""))
                if pkey:
                    self.held_title_pub[tkey + "|" + pkey] = (hid, title)

            # 主題分布
            domains = self._holding_domains(b)
            if not domains:
                continue
            w = 1.0 / len(domains)
            for d in domains:
                self.demand_all[d] += w

        total_all = sum(self.demand_all.values()) or 1.0
        self.demand_share_all = {d: c / total_all for d, c in self.demand_all.items()}
        self.demand_in = Counter(
            {d: c for d, c in self.demand_all.items() if d in IN_SCOPE_DOMAINS}
        )
        total_in = sum(self.demand_in.values()) or 1.0
        self.demand_share_in_scope = {d: c / total_in for d, c in self.demand_in.items()}

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
                for key in unmapped:
                    self.unmapped_genres[key] += 1
        seen = set()
        uniq = []
        for d in domains:
            if d not in seen:
                seen.add(d)
                uniq.append(d)
        return uniq

    # -------------------------------------------------------------------
    # Candidate profile（未所蔵候補のTOC主題）+ source/confidence [監査F3]
    # -------------------------------------------------------------------
    def _candidate_profile(self, book: dict) -> dict[str, float]:
        """候補1冊の主題プロファイル profile[domain]（合計1へ正規化）。"""
        return self._candidate_signal(book)[0]

    def _candidate_signal(self, book: dict) -> tuple[dict[str, float], str, str]:
        """(profile, profile_source, profile_confidence) を返す。共有純関数へ委譲。"""
        cov = self.coverage.get(str(book.get("id", "")), {})
        dist = cov.get("domain_hits") or cov.get("domain_distribution") or cov.get("domains")
        return compute_candidate_profile(
            primary_domain=cov.get("primary_domain"),
            domain_hits=dist if isinstance(dist, dict) else None,
            tags=book.get("tags"),
            tag_domain=self.tag_domain,
            matched_toc=cov.get("matched_toc") or 0,
            coverage=cov.get("coverage") or 0.0,
        )

    # -------------------------------------------------------------------
    # Scoring
    # -------------------------------------------------------------------
    def _relevance(self, profile: dict[str, float]) -> float:
        """所蔵分布(active母数)との整合度。weight_power で現業整合↔空白補完を制御。"""
        s = 0.0
        share = self.demand_share
        for d, w in profile.items():
            s += (share.get(d, 0.0) ** self.weight_power) * w
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
    # Held / dedup（強=自動ブロック / ソフト=レビュー） [監査F2]
    # -------------------------------------------------------------------
    def _held_match(self, book: dict) -> tuple[str, str, tuple]:
        """(strength, reason, (held_id, held_title))。未一致なら ("","",("",""))。
        strength: "strong"（isbn/bencom_id）| "soft"（title系）| ""。"""
        isbn = normalize_isbn(book.get("isbn"))
        if isbn and isbn in self.held_isbn:
            return "strong", "isbn", self.held_isbn[isbn]
        bid = str(book.get("id") or book.get("bencomId") or "").strip()
        if bid and bid in self.held_bencom_id:
            return "strong", "bencom_id", self.held_bencom_id[bid]
        tkey = normalize_title(book.get("title", ""))
        if tkey:
            akey = normalize_title(book.get("author", ""))
            if akey and (tkey + "|" + akey) in self.held_title_author:
                return "soft", "title_author", self.held_title_author[tkey + "|" + akey]
            pkey = normalize_title(book.get("publisher", ""))
            if pkey and (tkey + "|" + pkey) in self.held_title_pub:
                return "soft", "title_publisher", self.held_title_pub[tkey + "|" + pkey]
            if tkey in self.held_title:
                return "soft", "title", self.held_title[tkey]
        return "", "", ("", "")

    # -------------------------------------------------------------------
    # defer_new selection（未所蔵＝強一致のみ除外。ソフトは候補に残し注記） [監査F2]
    # -------------------------------------------------------------------
    def select_defer_new(self) -> list[dict]:
        out = []
        for book in self.bencom:
            bid = str(book.get("id", ""))
            if self.explicit_defer_ids is not None:
                if bid not in self.explicit_defer_ids:
                    continue
            else:
                strength, _, _ = self._held_match(book)
                if strength == "strong":
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
            profile, source, confidence = self._candidate_signal(book)
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
            strength, reason, _ = self._held_match(book)
            dup = ""
            if strength == "soft":
                dup = f"別版/類似を所蔵の可能性（{reason}）"
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
                profile_source=source,
                profile_confidence=confidence,
                demand_scope=self.demand_scope,
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
    # Dedup alert（2度買い防止・強/ソフト2レーン） [監査F2]
    # -------------------------------------------------------------------
    def dedup_alert(self, candidates: Optional[list[dict]] = None) -> list[DedupHit]:
        """候補（既定: bencom 全体）のうち所蔵済みのものを列挙。
        買い物リスト(dict list)を渡せば、その2度買いチェックにも使える。"""
        self.load()
        pool = candidates if candidates is not None else self.bencom
        hits: list[DedupHit] = []
        for book in pool:
            strength, reason, (held_id, held_title) = self._held_match(book)
            if strength:
                hits.append(DedupHit(
                    book_id=str(book.get("id", "")),
                    isbn=normalize_isbn(book.get("isbn")),
                    title=book.get("title", ""),
                    match_strength=strength,
                    match_reason=reason,
                    held_title=held_title,
                    held_id=str(held_id),
                ))
        # 強一致を先に
        hits.sort(key=lambda h: 0 if h.match_strength == "strong" else 1)
        return hits

    # -------------------------------------------------------------------
    # Reporting
    # -------------------------------------------------------------------
    def demand_summary(self, scope: Optional[str] = None) -> list[tuple[str, float, float]]:
        """所蔵の主題分布 [(domain, weight, share), ...]（share降順）。"""
        scope = scope or self.demand_scope
        if scope == "all":
            counter, share = self.demand_all, self.demand_share_all
        else:
            counter, share = self.demand_in, self.demand_share_in_scope
        rows = [(d, counter[d], share[d]) for d in counter]
        rows.sort(key=lambda x: -x[2])
        return rows

    def full_report(self, top_n: int = 50) -> str:
        self.load()
        recs = self.recommend(top_n=top_n)
        alerts = self.dedup_alert()
        defer = self.select_defer_new()
        strong = [h for h in alerts if h.match_strength == "strong"]
        soft = [h for h in alerts if h.match_strength == "soft"]
        oos = sum(s for d, s in self.demand_share_all.items() if d not in IN_SCOPE_DOMAINS)

        L = []
        L.append("=" * 76)
        L.append("購入レコメンド（アイデアD / Fork 3）")
        L.append("=" * 76)
        L.append("")
        L.append("■ サマリ")
        L.append(f"  所蔵カタログ件数 : {len(self.holdings):,}")
        L.append(f"  候補プール(bencom): {len(self.bencom):,}")
        L.append(f"  defer_new（未所蔵×詳細TOC, min_toc_nodes={self.min_toc_nodes}）: {len(defer):,}")
        L.append(f"  weight_power={self.weight_power}  flagship_alpha={self.flagship_alpha}"
                 f"  demand_scope={self.demand_scope}")
        L.append("")
        L.append(f"■ 所蔵の主題分布（= 現業テーマの強さ・母数={self.demand_scope}）")
        for d, w, share in self.demand_summary():
            L.append(f"    {d:<14} {share*100:5.1f}%  ({w:.1f})")
        L.append(f"  （参考）軸外ドメインの所蔵シェア(all母数): {oos*100:.1f}%")
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
            conf = "" if r.profile_confidence == "high" else f" ⟨{r.profile_confidence}"
            if r.profile_source == "tag_domain_fallback":
                conf = " ⟨tag fallback"
            conf = (conf + "⟩") if conf else ""
            doms = ", ".join(f"{d}:{w:.2f}" for d, w in r.top_domains)
            L.append(f"  {r.rank:3d}. [{r.score:5.1f}] {r.title[:54]}{flag}{conf}")
            L.append(f"        著者={r.author[:30]}  出版={r.publisher[:24]}")
            L.append(f"        TOCノード={r.toc_nodes}  主題[{doms}]  ISBN={r.isbn}")
            if r.dup_alert:
                L.append(f"        ⚠ {r.dup_alert}")
        L.append("")
        L.append("-" * 76)
        L.append(f"■ 2度買い防止アラート: 強一致(所蔵済み)={len(strong)} / ソフト(要レビュー)={len(soft)}")
        L.append("-" * 76)
        for h in strong[:40]:
            L.append(f"    ✗強 {h.title[:50]}  ←所蔵済み({h.match_reason}: {h.held_title[:28]})")
        for h in soft[:20]:
            L.append(f"    ?軟 {h.title[:50]}  ←別版の可能性({h.match_reason}: {h.held_title[:28]})")
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
                        "primary_domain", "profile_source", "profile_confidence",
                        "toc_nodes", "is_flagship", "isbn",
                        "top_domains", "dup_alert", "bencom_url"])
            for r in recs:
                w.writerow([
                    r.rank, r.score, r.title, r.author, r.publisher,
                    r.primary_domain, r.profile_source, r.profile_confidence,
                    r.toc_nodes, int(r.is_flagship), r.isbn,
                    ";".join(f"{d}:{wt:.2f}" for d, wt in r.top_domains),
                    r.dup_alert, r.bencom_url,
                ])

        self._path("out_alert").write_text(
            json.dumps([asdict(h) for h in alerts], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        n_strong = sum(1 for h in alerts if h.match_strength == "strong")
        print(f"Report  : {self._path('out_report')}")
        print(f"JSON    : {self._path('out_json')}")
        print(f"CSV     : {self._path('out_csv')}")
        print(f"Alert   : {self._path('out_alert')}  (強={n_strong} / ソフト={len(alerts)-n_strong})")
        print()
        print("Top 5 購入提案:")
        for r in recs[:5]:
            print(f"  {r.rank}. [{r.score}] {r.title[:50]} "
                  f"(TOC={r.toc_nodes}, {'旗艦' if r.is_flagship else '通常'}, conf={r.profile_confidence})")


# ---------------------------------------------------------------------------
# Supabase data source（private bookdx schema を read-only で読む） [監査F1]
# ---------------------------------------------------------------------------
class SupabaseDataSource:
    """`bookdx` schema の行を JSON ソースと同形の in-memory 構造へ変換する。
    query_runner(sql)->list[dict] を注入（本番=psycopg / テスト=フェイク）。
    toc/raw は引かない（ペイロード最小・total_toc は coverage 列を使用）。"""

    def __init__(self, query_runner: Callable[[str], list], schema: str = "bookdx"):
        self.q = query_runner
        self.schema = schema

    def fetch(self) -> tuple[list[dict], list[dict], list[dict], dict]:
        s = self.schema
        h_rows = self.q(
            f"SELECT internal_id, isbn, bencom_id, title, author, publisher, "
            f"genre, ndc, physical, cut, scanned FROM {s}.holdings"
        )
        holdings = [{
            "id": r.get("internal_id"),
            "isbn": r.get("isbn"),
            "bencomId": r.get("bencom_id"),
            "title": r.get("title") or "",
            "author": r.get("author") or "",
            "publisher": r.get("publisher") or "",
            "genre": r.get("genre"),
            "ndc": r.get("ndc"),
            "status": {"physical": r.get("physical"), "cut": r.get("cut"),
                       "scanned": r.get("scanned")},
        } for r in h_rows]

        c_rows = self.q(
            f"SELECT book_id, isbn, title, author, publisher, tags, bencom_url, "
            f"primary_domain, domain_hits, total_toc, matched_toc, coverage "
            f"FROM {s}.candidates"
        )
        bencom, coverage = [], []
        for r in c_rows:
            bencom.append({
                "id": r.get("book_id"),
                "isbn": r.get("isbn"),
                "title": r.get("title") or "",
                "author": r.get("author") or "",
                "publisher": r.get("publisher") or "",
                "tags": r.get("tags") or [],
                "bencomUrl": r.get("bencom_url") or "",
                "toc": [],   # 本文は引かない。total_toc を coverage で渡す
            })
            coverage.append({
                "book_id": r.get("book_id"),
                "primary_domain": r.get("primary_domain"),
                "domain_hits": r.get("domain_hits") or {},
                "total_toc": r.get("total_toc") or 0,
                "matched_toc": r.get("matched_toc") or 0,
                "coverage": float(r.get("coverage") or 0.0),
            })

        t_rows = self.q(f"SELECT tag, domain_l1 FROM {s}.tag_domain")
        tag_domain = {r.get("tag"): r.get("domain_l1") for r in t_rows if r.get("tag")}
        return holdings, bencom, coverage, tag_domain


def make_psycopg_runner(db_url: str) -> Callable[[str], list]:
    """psycopg(v3) を遅延importして read-only クエリランナを返す。
    通常実行は read-only role の接続文字列を渡すこと（監査: service_role常用を避ける）。"""
    try:
        import psycopg                      # noqa: F401  (遅延import)
        from psycopg.rows import dict_row
    except ImportError as e:                # pragma: no cover - 環境依存
        raise RuntimeError(
            "Supabase ソースには psycopg(v3) が必要です: pip install 'psycopg[binary]'"
        ) from e

    def run(sql: str) -> list:
        with psycopg.connect(db_url, row_factory=dict_row) as conn:
            conn.read_only = True           # 防御的に read-only を宣言
            with conn.cursor() as cur:
                cur.execute(sql)
                return list(cur.fetchall())
    return run


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="購入レコメンド（アイデアD）")
    ap.add_argument("--source", choices=["json", "supabase"], default="json",
                    help="データソース（既定 json）")
    ap.add_argument("--base", default=str(DEFAULT_BASE),
                    help="json ソース時の 事務所内本棚DX化計画 ベースディレクトリ")
    ap.add_argument("--db-url", default=os.environ.get("BOOKDX_DB_URL", ""),
                    help="supabase ソース時の接続文字列（read-only role 推奨）")
    ap.add_argument("--top-n", type=int, default=100)
    ap.add_argument("--min-toc-nodes", type=int, default=DEFAULT_MIN_TOC_NODES)
    ap.add_argument("--weight-power", type=float, default=1.0,
                    help="1.0=現業テーマ整合, <1.0=空白補完寄り")
    ap.add_argument("--flagship-alpha", type=float, default=DEFAULT_FLAGSHIP_ALPHA)
    ap.add_argument("--demand-scope", choices=["in_scope", "all"], default="in_scope",
                    help="所蔵分布の母数（既定 in_scope=候補軸8 domain）")
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
        demand_scope=args.demand_scope,
    )
    if args.source == "supabase":
        if not args.db_url:
            ap.error("--source supabase には --db-url か env BOOKDX_DB_URL が必要です")
        pr.load_supabase(make_psycopg_runner(args.db_url))

    if args.do_print:
        print(pr.full_report(top_n=args.top_n))
    else:
        pr.generate_all_outputs(top_n=args.top_n)


if __name__ == "__main__":
    main()
