#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_purchase_recommender.py — 合成データによる購入レコメンドエンジンの検証

Box/実データ無しで CI 上で動く。pytest でも `python tests/test_purchase_recommender.py`
でも実行可能（stdlib のみ）。

検証観点:
  1. 所蔵の主題分布（demand_share）が genre / ndc から正しく作られる
  2. defer_new 選定 = 未所蔵 × 詳細TOC（min_toc_nodes）
  3. 現業テーマ整合スコア: 所蔵が厚いドメインの候補が上位
  4. 旗艦級（高TOCノード / コンメンタール）が重み付けされる
  5. 2度買い防止アラート: 所蔵済み(ISBN/bencomId/タイトル)を検出
  6. ユーティリティ（ISBN正規化, TOCフラット化, NDC→domain）
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "term_dict", "scripts"))

from purchase_recommender import (  # noqa: E402
    PurchaseRecommender,
    normalize_isbn,
    normalize_title,
    flatten_toc,
    ndc_to_domain,
)


# ---------------------------------------------------------------------------
# Fixtures（合成）
# ---------------------------------------------------------------------------
def make_holdings():
    """所蔵カタログ: commercial に厚く、civil 少々、labor わずか。"""
    h = []
    # commercial を 6 冊（現業の主力テーマ）
    for i in range(6):
        h.append({
            "id": f"isbn_97840000000{i:02d}",
            "isbn": f"97840000000{i:02d}",
            "title": f"会社法実務マニュアル 第{i+1}巻",
            "genre": ["商法・会社法"],
            "status": {"physical": True},
            "bencomId": f"bc_owned_{i}",
        })
    # civil を 2 冊
    for i in range(2):
        h.append({
            "id": f"isbn_97840001000{i:02d}",
            "isbn": f"97840001000{i:02d}",
            "title": f"民事実務ハンドブック {i+1}",
            "genre": ["民事実務"],
            "status": {"physical": True},
        })
    # labor を 1 冊（ndc 経由でドメイン付与を検証）
    h.append({
        "id": "isbn_9784000200000",
        "isbn": "9784000200000",
        "title": "労働事件の実務",
        "genre": [],            # genre 無し → ndc で labor になること
        "ndc": ["366.14"],
        "status": {"physical": True},
    })
    return h


def make_bencom():
    """候補プール。"""
    return [
        # 所蔵済み（bencomId 一致）→ defer_new から除外 & dedup で検出
        {"id": "bc_owned_0", "isbn": "9784000000000",
         "title": "会社法実務マニュアル 第1巻", "tags": ["category:商法・会社法"],
         "toc": [{"t": f"第{i}章"} for i in range(50)]},
        # commercial・詳細TOC・通常 → 上位に来るはず
        {"id": "bc_comm_a", "isbn": "9784111111111",
         "title": "企業買収の法務", "tags": ["category:企業法務"],
         "toc": [{"t": f"第{i}節"} for i in range(60)]},
        # commercial・旗艦（コンメンタール, 超高TOC）→ 旗艦重みで最上位候補
        {"id": "bc_comm_flag", "isbn": "9784222222222",
         "title": "大コンメンタール会社法", "tags": ["category:商法・会社法"],
         "toc": [{"t": f"第{i}条解説", "children": [{"t": f"{i}-{j}"} for j in range(3)]}
                 for i in range(80)]},  # 80 + 240 = 320 ノード
        # civil・詳細TOC → 中位（所蔵が薄い）
        {"id": "bc_civil_a", "isbn": "9784333333333",
         "title": "交通事故損害賠償の実務", "tags": ["category:交通事故"],
         "toc": [{"t": f"事例{i}"} for i in range(70)]},
        # labor・詳細TOC → 所蔵わずかなので下位寄り
        {"id": "bc_labor_a", "isbn": "9784444444444",
         "title": "解雇紛争の実務", "tags": ["series:ビジネスガイド"],
         "toc": [{"t": f"論点{i}"} for i in range(55)]},
        # TOC が薄い（未所蔵だが defer_new に入らない）
        {"id": "bc_thin", "isbn": "9784555555555",
         "title": "会社法入門", "tags": ["category:商法・会社法"],
         "toc": [{"t": "第1章"}, {"t": "第2章"}]},
        # 主題が取れない（tags/coverage 無し）→ スキップされる
        {"id": "bc_nodomain", "isbn": "9784666666666",
         "title": "謎の書", "tags": [],
         "toc": [{"t": f"x{i}"} for i in range(80)]},
    ]


def make_coverage():
    """book_coverage_by_domain.json 相当。primary_domain と total_toc。"""
    return [
        {"book_id": "bc_owned_0", "primary_domain": "commercial", "total_toc": 50},
        {"book_id": "bc_comm_a", "primary_domain": "commercial", "total_toc": 60},
        {"book_id": "bc_comm_flag", "primary_domain": "commercial", "total_toc": 320},
        {"book_id": "bc_civil_a", "primary_domain": "civil", "total_toc": 70},
        {"book_id": "bc_labor_a", "primary_domain": "labor", "total_toc": 55},
        {"book_id": "bc_thin", "primary_domain": "commercial", "total_toc": 2},
        {"book_id": "bc_nodomain", "primary_domain": "unclassified", "total_toc": 80},
    ]


def make_tag_domain():
    return {
        "category:商法・会社法": {"domain_l1": "commercial"},
        "category:企業法務": {"domain_l1": "commercial"},
        "category:交通事故": {"domain_l1": "civil"},
        "series:ビジネスガイド": {"domain_l1": "labor"},
    }


def build(**kwargs) -> PurchaseRecommender:
    pr = PurchaseRecommender(min_toc_nodes=40, **kwargs)
    pr.load_from_memory(
        holdings=make_holdings(),
        bencom=make_bencom(),
        coverage=make_coverage(),
        tag_domain=make_tag_domain(),
    )
    return pr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_utilities():
    assert normalize_isbn("978-4-00-000000-0") == "9784000000000"
    assert normalize_isbn("4063897753") == normalize_isbn("9784063897753")
    assert normalize_isbn("garbage") == ""
    assert normalize_title("会社法　実務マニュアル（第3版）") == normalize_title("会社法実務マニュアル第3版")
    assert len(flatten_toc([{"t": "a", "children": [{"t": "b"}, {"t": "c"}]}])) == 3
    assert ndc_to_domain(["366.14"]) == "labor"
    assert ndc_to_domain("324.5") == "civil"
    print("✓ test_utilities")


def test_demand_distribution():
    pr = build()
    share = pr.demand_share
    # commercial が最大シェア（6冊）
    assert share.get("commercial", 0) > share.get("civil", 0) > 0
    assert "labor" in share          # ndc 経由で付与されている
    assert abs(sum(share.values()) - 1.0) < 1e-9
    # commercial 6 / (6+2+1) = 0.666...
    assert abs(share["commercial"] - 6 / 9) < 1e-6
    print("✓ test_demand_distribution", {k: round(v, 3) for k, v in share.items()})


def test_defer_new_selection():
    pr = build()
    ids = {b["id"] for b in pr.select_defer_new()}
    # 所蔵済み(bc_owned_0)・薄TOC(bc_thin)は除外、未所蔵×詳細TOCのみ
    assert "bc_owned_0" not in ids
    assert "bc_thin" not in ids
    assert {"bc_comm_a", "bc_comm_flag", "bc_civil_a", "bc_labor_a"} <= ids
    print("✓ test_defer_new_selection", sorted(ids))


def test_alignment_ranking():
    """現業テーマ整合: commercial 候補が civil/labor より上位。"""
    pr = build()
    recs = pr.recommend(top_n=10)
    rank = {r.book_id: r.rank for r in recs}
    # 主題が取れない bc_nodomain は除外
    assert "bc_nodomain" not in rank
    # commercial 勢が civil/labor より上
    assert rank["bc_comm_flag"] < rank["bc_civil_a"]
    assert rank["bc_comm_a"] < rank["bc_labor_a"]
    # トップは旗艦コンメンタール
    assert recs[0].book_id == "bc_comm_flag"
    assert recs[0].is_flagship is True
    assert recs[0].score == 100.0
    print("✓ test_alignment_ranking", [(r.book_id, r.score) for r in recs])


def test_flagship_weight():
    pr = build()
    recs = {r.book_id: r for r in pr.recommend(top_n=10)}
    flag = recs["bc_comm_flag"]
    normal = recs["bc_comm_a"]
    # 旗艦は flagship_weight が大きい & フラグ立ち
    assert flag.is_flagship and not normal.is_flagship
    assert flag.flagship_weight > normal.flagship_weight
    # 同じ commercial でも旗艦が上位
    assert flag.rank < normal.rank
    print("✓ test_flagship_weight", flag.flagship_weight, normal.flagship_weight)


def test_weight_power_shifts_to_gapfill():
    """weight_power<1 で薄いドメイン(civil/labor)の相対評価が上がる。"""
    align = build(weight_power=1.0)
    gapfill = build(weight_power=0.3)
    a = {r.book_id: r.score for r in align.recommend(top_n=10)}
    g = {r.book_id: r.score for r in gapfill.recommend(top_n=10)}
    # civil の対 commercial 相対スコアが gapfill で上昇
    a_ratio = a["bc_civil_a"] / a["bc_comm_a"]
    g_ratio = g["bc_civil_a"] / g["bc_comm_a"]
    assert g_ratio > a_ratio
    print("✓ test_weight_power_shifts_to_gapfill", round(a_ratio, 3), "->", round(g_ratio, 3))


def test_dedup_alert():
    pr = build()
    hits = {h.book_id: h for h in pr.dedup_alert()}
    # bencomId 一致で所蔵済みを検出
    assert "bc_owned_0" in hits
    assert hits["bc_owned_0"].match_reason in ("bencom_id", "isbn", "title")
    # 未所蔵は出ない
    assert "bc_comm_a" not in hits
    print("✓ test_dedup_alert", [(h.book_id, h.match_reason) for h in hits.values()])


def test_dedup_alert_shopping_list():
    """任意の買い物リストの2度買いチェック。"""
    pr = build()
    shopping = [
        {"id": "x1", "isbn": "9784000000001", "title": "なんでも"},  # ISBN一致(所蔵)
        {"id": "x2", "isbn": "9784999999999", "title": "未所蔵の本"},
        {"id": "x3", "title": "民事実務ハンドブック 1"},            # タイトル一致(所蔵)
    ]
    hits = pr.dedup_alert(candidates=shopping)
    reasons = {h.book_id: h.match_reason for h in hits}
    assert reasons.get("x1") == "isbn"
    assert reasons.get("x3") == "title"
    assert "x2" not in reasons
    print("✓ test_dedup_alert_shopping_list", reasons)


def test_domain_hits_profile():
    """book_coverage の実フィールド domain_hits から主題プロファイルが作られる
    （tags 無し・primary_domain=unclassified でも domain_hits を拾う）。"""
    pr = PurchaseRecommender(min_toc_nodes=10)
    pr.load_from_memory(
        holdings=[{"id": "h1", "isbn": "9784000000001", "title": "労働法A",
                   "genre": ["労働法務"], "status": {"physical": True}}],
        bencom=[{"id": "x", "isbn": "9784999999999", "title": "ある実務書",
                 "tags": [], "toc": [{"t": f"n{i}"} for i in range(20)]}],
        coverage=[{"book_id": "x", "primary_domain": "unclassified",
                   "total_toc": 20, "domain_hits": {"labor": 3, "unknown": 5}}],
        tag_domain={},
    )
    prof = pr._candidate_profile(pr.bencom[0])
    assert prof.get("labor", 0) > 0      # domain_hits から labor を採用
    assert "unknown" not in prof          # unknown/unclassified は除外
    recs = pr.recommend(top_n=5)
    assert recs and recs[0].book_id == "x"
    print("✓ test_domain_hits_profile", prof)


def test_report_renders():
    pr = build()
    report = pr.full_report(top_n=10)
    assert "購入レコメンド" in report
    assert "所蔵の主題分布" in report
    assert "2度買い防止アラート" in report
    print("✓ test_report_renders (len=%d)" % len(report))


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"\nAll {len(fns)} tests passed.")


if __name__ == "__main__":
    _run_all()
