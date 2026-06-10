#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_supabase_source.py — SupabaseDataSource / loader transforms の検証（実DB不要）

監査(PASS_WITH_NOTES)で要求されたテスト観点を合成データで検証:
  - JSONソース同等性（同一データなら recommend()/dedup_alert() が一致）
  - No write-back（engine の Supabase 読取りは SELECT のみ＝書込みSQLを発行しない）
  - profile confidence（high/medium/low の固定閾値）
  - dedup strong/soft 分離
  - demand 母数 all / in_scope 分離

stdlib のみ。`python tests/test_supabase_source.py` でも pytest でも動く。
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "term_dict", "scripts"))

from purchase_recommender import (  # noqa: E402
    PurchaseRecommender,
    SupabaseDataSource,
    compute_candidate_profile,
    CONF_HIGH_MATCHED_TOC,
    CONF_HIGH_COVERAGE,
)
import load_to_supabase as L  # noqa: E402
from test_purchase_recommender import (  # noqa: E402
    make_holdings, make_bencom, make_coverage, make_tag_domain,
)


# ---------------------------------------------------------------------------
# Fake DB: loader transforms でDB行を作り、SELECT だけ応答する query_runner
# ---------------------------------------------------------------------------
class FakeDB:
    def __init__(self):
        holdings = make_holdings()
        bencom = make_bencom()
        cov = {c["book_id"]: c for c in make_coverage()}
        tagmap = make_tag_domain()
        tagmap_norm = {t: (e.get("domain_l1") if isinstance(e, dict) else e)
                       for t, e in tagmap.items()}
        self.h = [L.holding_row(b, "run1") for b in holdings]
        self.c = [L.candidate_row(b, cov.get(str(b.get("id", "")), {}), tagmap_norm, "run1")
                  for b in bencom]
        self.t = L.tag_domain_rows(tagmap)
        self.seen: list[str] = []

    def __call__(self, sql: str) -> list:
        self.seen.append(sql)
        low = sql.strip().lower()
        assert low.startswith("select"), f"read-only違反: {sql[:40]}"
        if "from bookdx.holdings" in low:
            return self.h
        if "from bookdx.candidates" in low:
            return self.c
        if "from bookdx.tag_domain" in low:
            return self.t
        raise AssertionError(f"想定外SQL: {sql}")


def _json_recommender(**kw) -> PurchaseRecommender:
    pr = PurchaseRecommender(min_toc_nodes=40, **kw)
    pr.load_from_memory(make_holdings(), make_bencom(), make_coverage(), make_tag_domain())
    return pr


def _supabase_recommender(fake: FakeDB, **kw) -> PurchaseRecommender:
    pr = PurchaseRecommender(min_toc_nodes=40, **kw)
    pr.load_supabase(fake)
    return pr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_supabase_matches_json_ranking():
    """同一データなら Supabase ソースと JSON ソースで recommend() が一致。"""
    fake = FakeDB()
    j = _json_recommender().recommend(top_n=10)
    s = _supabase_recommender(fake).recommend(top_n=10)
    jt = [(r.book_id, r.rank, r.score, r.profile_source, r.profile_confidence) for r in j]
    st = [(r.book_id, r.rank, r.score, r.profile_source, r.profile_confidence) for r in s]
    assert jt == st, f"\nJSON={jt}\nSUP ={st}"
    print("✓ test_supabase_matches_json_ranking", st[:3])


def test_supabase_readonly_no_writeback():
    """engine の Supabase 読取りは SELECT のみ（books.json への write-back 経路なし）。"""
    fake = FakeDB()
    pr = _supabase_recommender(fake)
    pr.recommend(top_n=5)
    pr.dedup_alert()
    assert fake.seen, "SQLが発行されていない"
    assert all(s.strip().lower().startswith("select") for s in fake.seen)
    assert not any(w in s.lower() for s in fake.seen
                   for w in ("insert", "update", "delete", "drop", "alter"))
    print("✓ test_supabase_readonly_no_writeback", f"{len(fake.seen)} SELECTs")


def test_supabase_dedup_matches_json():
    fake = FakeDB()
    jh = {(h.book_id, h.match_strength, h.match_reason) for h in _json_recommender().dedup_alert()}
    sh = {(h.book_id, h.match_strength, h.match_reason) for h in _supabase_recommender(fake).dedup_alert()}
    assert jh == sh, f"\nJSON={jh}\nSUP ={sh}"
    print("✓ test_supabase_dedup_matches_json", sh)


def test_profile_confidence_tiers():
    """固定閾値で high/medium/low が出る。"""
    td = {"category:商法・会社法": "commercial"}
    # high: 強いTOC照合
    _, src_h, conf_h = compute_candidate_profile(
        "commercial", {"commercial": 9}, [], td,
        matched_toc=CONF_HIGH_MATCHED_TOC, coverage=CONF_HIGH_COVERAGE)
    assert src_h == "toc_term_dict" and conf_h == "high"
    # medium: TOC照合あるが閾値未満
    _, src_m, conf_m = compute_candidate_profile(
        "commercial", {"commercial": 1}, [], td, matched_toc=1, coverage=0.0)
    assert src_m == "toc_term_dict" and conf_m == "medium"
    # low: tagsのみ（tag fallback）
    _, src_l, conf_l = compute_candidate_profile(
        None, {}, ["category:商法・会社法"], td, matched_toc=0, coverage=0.0)
    assert src_l == "tag_domain_fallback" and conf_l == "low"
    # mixed: 両方
    _, src_x, _ = compute_candidate_profile(
        "commercial", {"commercial": 1}, ["category:商法・会社法"], td)
    assert src_x == "mixed"
    # unclassified: 信号なし
    prof, src_u, _ = compute_candidate_profile(None, {}, [], td)
    assert prof == {} and src_u == "unclassified"
    print("✓ test_profile_confidence_tiers", conf_h, conf_m, conf_l, src_x)


def test_demand_scope_all_vs_in_scope():
    """軸外ドメイン(information)は in_scope 母数から外れ、all には載る。"""
    holdings = [
        {"id": "a", "isbn": "9784000000001", "title": "会社法", "genre": ["商法・会社法"]},
        {"id": "b", "isbn": "9784000000002", "title": "情報法本", "genre": ["情報法"]},  # 軸外
    ]
    pr = PurchaseRecommender()
    pr.load_from_memory(holdings=holdings, bencom=[], coverage=[], tag_domain={})
    # all: commercial と information の2軸
    assert set(pr.demand_share_all) == {"commercial", "information"}
    # in_scope: information は除外 → commercial のみ（=1.0）
    assert set(pr.demand_share_in_scope) == {"commercial"}
    assert abs(pr.demand_share_in_scope["commercial"] - 1.0) < 1e-9
    # 既定の母数は in_scope
    assert pr.demand_scope == "in_scope"
    assert pr.demand_share is pr.demand_share_in_scope
    print("✓ test_demand_scope_all_vs_in_scope",
          {k: round(v, 2) for k, v in pr.demand_share_all.items()})


def test_dedup_strong_soft_split():
    """強一致(isbn/bencom_id)とソフト一致(title系)が分離される。"""
    holdings = [
        {"id": "h1", "isbn": "9784111111111", "title": "会社法コンメンタール 第1巻",
         "author": "田中", "genre": ["商法・会社法"]},
    ]
    shopping = [
        {"id": "s1", "isbn": "9784111111111", "title": "別タイトル"},          # 強(isbn)
        {"id": "s2", "title": "会社法コンメンタール 第1巻", "author": "田中"},   # 軟(title+author)
        {"id": "s3", "title": "会社法コンメンタール 第1巻"},                    # 軟(title)
        {"id": "s4", "title": "無関係な本"},                                   # なし
    ]
    pr = PurchaseRecommender()
    pr.load_from_memory(holdings=holdings, bencom=[], coverage=[], tag_domain={})
    hits = {h.book_id: (h.match_strength, h.match_reason) for h in pr.dedup_alert(shopping)}
    assert hits["s1"] == ("strong", "isbn")
    assert hits["s2"] == ("soft", "title_author")
    assert hits["s3"] == ("soft", "title")
    assert "s4" not in hits
    print("✓ test_dedup_strong_soft_split", hits)


def test_loader_rows_shape():
    """loader transforms が schema 列に必要なキーを作る。"""
    h = L.holding_row({"id": "x", "isbn": "978-4-00-000000-0", "title": "T",
                       "genre": "商法・会社法", "status": {"physical": True}}, "run1")
    assert h["internal_id"] == "x" and h["isbn"] == "9784000000000"
    assert h["genre"] == ["商法・会社法"] and h["physical"] is True
    assert h["load_run_id"] == "run1" and h["source_record_hash"]
    c = L.candidate_row(
        {"id": "y", "isbn": "9784222222222", "title": "C", "tags": ["category:商法・会社法"]},
        {"primary_domain": "commercial", "domain_hits": {"commercial": 2},
         "total_toc": 60, "matched_toc": 6, "coverage": 0.06},
        {"category:商法・会社法": "commercial"}, "run1")
    assert c["book_id"] == "y" and c["primary_domain"] == "commercial"
    assert c["profile_source"] == "mixed"
    assert c["profile_confidence"] == "high"   # matched_toc6>=5 & coverage0.06>=0.05
    print("✓ test_loader_rows_shape", c["profile_source"], c["profile_confidence"])


# ---------------------------------------------------------------------------
def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"\nAll {len(fns)} supabase-source tests passed.")


if __name__ == "__main__":
    _run_all()
