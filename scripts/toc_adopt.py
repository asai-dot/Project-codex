"""toc_adopt — DD-TOCADOPT-001 統一TOC採用ルールの実装 (5 ステップ・report-only)。

owner ratify 済み設計 (`20260615_DD-TOCADOPT-001_v0.2_ACCEPTED.md`) を実装契約
`data/toc_merge_policy_unified_DRAFT.json` に沿って実行する。原則:

  源の優劣でなく、本/ノード単位で最良の中身を **出所記録つきで合成採用**する。
  priority ラダーは tie-break 専用。

Step1 同一性ゲート → Step2 基底選択 → Step3 ノード補完 → Step4 保護合議 → Step5 記録。
**投影 (projection) を返すだけ**で canonical / source snapshot / policy 本番には一切書かない
(release_boundary.report_only=true / HOLD は policy 参照)。stdlib のみ・決定的。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _toc_text import normalize_title  # noqa: E402
from authority_resolver import resolve_authority  # noqa: E402
from edition_identity import APPLY_OK_STATUS  # noqa: E402
from edition_identity_v2 import classify_edition_identity_v2  # noqa: E402
from page_basis import normalize_page_basis, to_print_page  # noqa: E402

TOC_ADOPT_VERSION = "0.1.0"

_DEFAULT_POLICY = Path(__file__).resolve().parents[1] / "data" / "toc_merge_policy_unified_DRAFT.json"


def load_policy(path: str | Path | None = None) -> dict:
    return json.loads(Path(path or _DEFAULT_POLICY).read_text(encoding="utf-8"))


def _sha(obj) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _priority_index(policy: dict, src: str) -> int:
    pr = policy.get("priority", [])
    sysname = src
    return pr.index(sysname) if sysname in pr else len(pr)


def _norm_nodes(book: dict, src: str) -> list[dict]:
    """1 source の生ノードを (idx 保持で) 正規化。title_norm 空は落とす (silent ではなく未採用)。"""
    out = []
    for i, n in enumerate(book.get("sources", {}).get(src, [])):
        if not isinstance(n, dict):
            continue
        raw = n.get("t") or n.get("title") or n.get("label") or ""
        tn = normalize_title(raw)
        if not tn:
            continue
        depth = n.get("depth") or n.get("l") or n.get("level") or 1
        try:
            depth = int(depth)
        except (TypeError, ValueError):
            depth = 1
        page = n.get("page_start")
        page = page if page is not None else (n.get("p") or n.get("print_page") or n.get("pdf_page"))
        page_is_pdf = (n.get("print_page") is None and n.get("pdf_page") is not None
                       and n.get("page_start") is None and n.get("p") is None)
        out.append({"src": src, "idx": i, "title": raw, "title_norm": tn,
                    "depth": depth, "page": page, "page_is_pdf": page_is_pdf})
    return out


# ---- Step 1: 同一性ゲート -------------------------------------------------

def step1_identity_gate(book: dict, policy: dict, *, year_tolerance: int = 1) -> dict:
    """同一 manifestation が確認できた source だけを合議対象に絞る (per-source 包含)。

    基準 source (priority 最上位かつ bib あり) との pairwise 判定で
    cluster_only_status のみ採用、それ以外は human_review に落とす。
    """
    cfg = policy.get("step1_identity_gate", {})
    ok_status = set(cfg.get("cluster_only_status", list(APPLY_OK_STATUS)))
    meta = book.get("source_meta", {})
    bibs = {s: m for s, m in meta.items() if isinstance(m, dict)}
    if not bibs:
        return {"clustered": [], "human_review": [], "status": "insufficient_evidence",
                "reason": "no bib", "reference": None}

    # 基準 = priority 最上位の bib source。
    ref = min(bibs, key=lambda s: _priority_index(policy, s))
    clustered = [ref]
    human_review: list[dict] = []
    reasons = {}
    for s, m in bibs.items():
        if s == ref:
            continue
        res = classify_edition_identity_v2([bibs[ref], m], year_tolerance=year_tolerance)
        reasons[s] = res
        if res["status"] in ok_status:
            clustered.append(s)
        else:
            human_review.append({"source": s, "status": res["status"], "reason": res["reason"]})

    # 合議全体の status (worst-case) も持つ。
    overall = classify_edition_identity_v2(list(bibs.values()), year_tolerance=year_tolerance)
    # node を持つ clustered source のみが実際の採用対象。
    clustered_with_nodes = [s for s in clustered if book.get("sources", {}).get(s)]
    return {"reference": ref, "clustered": sorted(clustered),
            "clustered_with_nodes": sorted(clustered_with_nodes),
            "human_review": human_review, "status": overall["status"],
            "reason": overall["reason"], "pairwise": reasons}


# ---- Step 2: 基底選択 -----------------------------------------------------

def _is_simple(nodes: list[dict]) -> bool:
    """既存 base が "simple"(浅い章リスト) か。max depth==1 を simple とみなす (Fork1 gate)。"""
    return bool(nodes) and max((n["depth"] for n in nodes), default=1) <= 1


def step2_base_selection(book: dict, policy: dict, clustered: list[str]) -> dict:
    cfg = policy.get("step2_base_selection", {})
    guard = cfg.get("granularity_guard", {})
    default_ratio = guard.get("min_node_ratio_vs_richest_default", 0.2)
    per_source = guard.get("min_node_ratio_vs_richest_per_source", {})
    protected = set(policy.get("protected_sources", []))

    norm = {s: _norm_nodes(book, s) for s in clustered}
    norm = {s: ns for s, ns in norm.items() if ns}
    if not norm:
        return {"base": None, "richest": None, "richest_count": 0,
                "guard_blocked": [], "candidates": {}, "reason": "no nodes in cluster"}

    counts = {s: len(ns) for s, ns in norm.items()}
    richest = max(counts, key=lambda s: (counts[s], -_priority_index(policy, s)))
    richest_count = counts[richest]

    # granularity_guard: 最富源比 ratio 未満は base 不可 (詳細→浅い劣化防止)。
    eligible, blocked = [], []
    for s, c in counts.items():
        ratio = per_source.get(s, default_ratio)
        if c >= ratio * richest_count:
            eligible.append(s)
        else:
            blocked.append({"source": s, "nodes": c, "min": round(ratio * richest_count, 1)})

    def page_cov(s):
        ns = norm[s]
        return sum(1 for n in ns if n["page"] is not None) / (len(ns) or 1)

    # 一次=粒度, 二次=ページ被覆, 三次=priority(tie-break)。
    base = max(eligible, key=lambda s: (counts[s], page_cov(s), -_priority_index(policy, s)))

    # legallib_simple_only: 既存 base が simple のときだけ詳細源で張替える、を解釈として:
    #   protected 源が base 候補にあり既に非 simple なら、それを壊して非 protected を base にしない。
    so = cfg.get("legallib_simple_only", {})
    if so.get("never_overwrite_protected_sources", True):
        prot_bases = [s for s in eligible if s in protected and not _is_simple(norm[s])]
        if prot_bases and base not in protected:
            # 既存の良い protected base を壊さない: protected の中で最richを base に。
            base = max(prot_bases, key=lambda s: (counts[s], -_priority_index(policy, s)))

    return {"base": base, "richest": richest, "richest_count": richest_count,
            "guard_blocked": blocked, "candidates": counts,
            "page_coverage": {s: round(page_cov(s), 3) for s in norm},
            "reason": f"granularity-first base={base} (nodes={counts[base]}/richest={richest_count})"}


# ---- Step 3: ノード補完 (append_missing_only) -----------------------------

def step3_node_completion(book: dict, policy: dict, clustered: list[str], base: str) -> dict:
    """base に無い title_norm を他源から append。各ノードに provenance を必ず付す。"""
    meta = book.get("source_meta", {})
    norm = {s: _norm_nodes(book, s) for s in clustered if book.get("sources", {}).get(s)}
    if base not in norm:
        return {"adopted": [], "base_count": 0, "appended_count": 0}

    # book 単位 offset (検証済のみ) で pdf→print を整合 (Phase0: 94.9% 本単位単一)。
    po = book.get("page_offset")
    offset = None
    if isinstance(po, dict) and po.get("validated") and float(po.get("confidence", 0)) >= 1.0:
        try:
            offset = int(po["offset"])
        except (TypeError, ValueError, KeyError):
            offset = None

    def provenance(n: dict) -> dict:
        m = meta.get(n["src"], {})
        page = n["page"]
        basis = normalize_page_basis(m.get("page_basis"))
        # pdf 基準ページは検証済 offset があれば print に整合 (raw は不変・派生のみ)。
        if n["page_is_pdf"] and offset is not None and page is not None:
            page = to_print_page(int(page), offset)
            basis = "print_page"
        return {
            "title": n["title"], "title_norm": n["title_norm"], "depth": n["depth"],
            "page": page, "page_basis": basis,
            "source_system": n["src"],
            "provenance_origin": m.get("provenance_origin", n["src"]),
            "locator": f"{n['src']}#{n['idx']}",
            "source_hash": m.get("source_sha256") or _sha(n["title_norm"]),
            "toc_node_id": _sha([book.get("isbn", ""), n["title_norm"]])[:23],
        }

    adopted = [provenance(n) for n in norm[base]]
    seen = {n["title_norm"] for n in adopted}
    appended = 0
    # 補完は priority 順で安定させる。
    for s in sorted(norm, key=lambda x: _priority_index(policy, x)):
        if s == base:
            continue
        for n in norm[s]:
            if n["title_norm"] in seen:
                continue  # append_missing_only: 既存は上書きしない
            adopted.append({**provenance(n), "appended_from": s})
            seen.add(n["title_norm"])
            appended += 1

    # 章執筆者: ndl_partinfo contents から付与 (あれば)。
    author_src = policy.get("step3_node_completion", {}).get("chapter_author_from", [])
    for a in author_src:
        for n in norm.get(a, []):
            raw = book["sources"][a][n["idx"]]
            who = raw.get("author") or raw.get("creator") if isinstance(raw, dict) else None
            if not who:
                continue
            for node in adopted:
                if node["title_norm"] == n["title_norm"]:
                    node["chapter_author"] = who
    return {"adopted": adopted, "base_count": len(norm[base]), "appended_count": appended}


# ---- Step 4: 保護と合議 ---------------------------------------------------

def step4_protect_and_consensus(book: dict, policy: dict, clustered: list[str],
                                adopted: list[dict], edition_status: str) -> dict:
    cfg = policy.get("step4_protect_and_consensus", {})
    min_origins = cfg.get("consensus_min_independent_origins", 3)
    meta = book.get("source_meta", {})

    # ノードごとに、その title_norm を含む source の provenance_origin 集合 (dedup)。
    norm = {s: _norm_nodes(book, s) for s in clustered if book.get("sources", {}).get(s)}
    origins_by_title: dict[str, set] = {}
    for s, ns in norm.items():
        origin = meta.get(s, {}).get("provenance_origin", s)
        for n in ns:
            origins_by_title.setdefault(n["title_norm"], set()).add(origin)

    consensus_nodes = human_review_nodes = 0
    for node in adopted:
        votes = len(origins_by_title.get(node["title_norm"], set()))
        node["votes_by_provenance_origin"] = votes
        node["consensus"] = votes >= min_origins
        if node["consensus"]:
            consensus_nodes += 1
        else:
            human_review_nodes += 1

    # 本単位の権威 (PDF/consensus/human_review)。
    authority = resolve_authority(meta, edition_status=edition_status)
    return {"authority": authority["authority"], "authority_reason": authority["reason"],
            "consensus_nodes": consensus_nodes, "human_review_nodes": human_review_nodes,
            "min_origins": min_origins}


# ---- 統合 ----------------------------------------------------------------

def adopt_book(book: dict, policy: dict | None = None) -> dict:
    """1 冊に 5 ステップを適用し、採用 projection を返す (report-only)。"""
    p = policy or load_policy()
    s1 = step1_identity_gate(book, p)
    clustered = s1["clustered_with_nodes"]
    s2 = step2_base_selection(book, p, clustered)
    base = s2["base"]
    if base is None:
        return {"isbn": book.get("isbn", ""), "title": book.get("title", ""),
                "step1": s1, "step2": s2, "step3": {"adopted": [], "appended_count": 0},
                "step4": {}, "projection": [], "projection_sha": _sha([]),
                "adoptable": False, "report_only": True}
    s3 = step3_node_completion(book, p, clustered, base)
    s4 = step4_protect_and_consensus(book, p, clustered, s3["adopted"], s1["status"])

    projection = s3["adopted"]
    # adoptable = 同一性が解決済 (HOLD: unresolved manifestation は合議参加させない)。
    adoptable = s1["status"] in APPLY_OK_STATUS
    return {
        "isbn": book.get("isbn", ""), "title": book.get("title", ""),
        "step1": s1, "step2": s2, "step3": s3, "step4": s4,
        "base_source": base,
        "projection": projection,
        "projection_node_count": len(projection),
        "projection_sha": _sha(sorted(
            (n["toc_node_id"], n["title_norm"], n.get("page"), n["provenance_origin"])
            for n in projection)),  # 入力順非依存
        "base_source_distribution": _base_dist(projection, base),
        "adoptable": adoptable,
        "report_only": True,
    }


def _base_dist(projection: list[dict], base: str) -> dict:
    d: dict[str, int] = {}
    for n in projection:
        s = n.get("appended_from", base)
        d[s] = d.get(s, 0) + 1
    return dict(sorted(d.items()))


def adopt_corpus(books: list[dict], policy: dict | None = None) -> dict:
    p = policy or load_policy()
    rows = [adopt_book(b, p) for b in books]
    return {
        "policy_version": p.get("policy_version"),
        "adopt_version": TOC_ADOPT_VERSION,
        "books": len(rows),
        "adoptable_count": sum(1 for r in rows if r["adoptable"]),
        "total_projection_nodes": sum(r["projection_node_count"] for r in rows),
        "rows": rows,
        "report_only": True,
    }


__all__ = ["TOC_ADOPT_VERSION", "load_policy", "adopt_book", "adopt_corpus",
           "step1_identity_gate", "step2_base_selection", "step3_node_completion",
           "step4_protect_and_consensus"]
