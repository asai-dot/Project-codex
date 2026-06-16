"""toc_adopt — DD-TOCADOPT-001 統一TOC採用ルールの実装 (5 ステップ・report-only)。

owner ratify 済み設計 (`20260615_DD-TOCADOPT-001_v0.2_ACCEPTED.md`) を実装契約
`data/toc_merge_policy_unified_DRAFT.json` に沿って実行する。原則:

  源の優劣でなく、本/ノード単位で最良の中身を **出所記録つきで合成採用**する。
  priority ラダーは tie-break 専用。

Step1 同一性ゲート → Step2 基底選択 → Step3 ノード補完 → Step4 保護合議 → Step5 記録。
**投影 (projection) を返すだけ**で canonical / source snapshot / policy 本番には一切書かない。

DD-TOCADOPT-001-IMPL の GPT 監査 (MODIFY_REQUIRED) を反映:
  A1 全ペア connected component で合議集合 / A2 anchor は node 持ち源優先 /
  B1 粒度=depth・node_count・page_coverage 複合 / B2 simple_only 張替え意味論 /
  C1 source_hash 欠落時は捏造せず snapshot_missing(非採用) / C2 toc_node_id に lineage /
  C3 offset は検証済本に限定し metadata 付与 / C4 partinfo_kind_filter 実装 /
  D1 非合議/欠落ノードを accepted から pending lane へ分離 /
  D2 adoptable = identity ∧ consensus ∧ authority≠HR ∧ provenance。
stdlib のみ・決定的。
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _toc_text import normalize_title  # noqa: E402
from authority_resolver import AUTH_HUMAN_REVIEW, resolve_authority  # noqa: E402
from edition_identity import APPLY_OK_STATUS  # noqa: E402
from edition_identity_v2 import classify_edition_identity_v2  # noqa: E402
from page_basis import normalize_page_basis, to_print_page  # noqa: E402

TOC_ADOPT_VERSION = "0.2.0"

_DEFAULT_POLICY = Path(__file__).resolve().parents[1] / "data" / "toc_merge_policy_unified_DRAFT.json"

# C4: partinfo の kind フィルタが効く source。
_PARTINFO_SOURCES = {"ndl_partinfo"}


def load_policy(path: str | Path | None = None) -> dict:
    return json.loads(Path(path or _DEFAULT_POLICY).read_text(encoding="utf-8"))


def _sha(obj) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _priority_index(policy: dict, src: str) -> int:
    pr = policy.get("priority", [])
    return pr.index(src) if src in pr else len(pr)


def _node_kind(raw: dict) -> str | None:
    return raw.get("kind") or raw.get("partinfo_kind")


def _norm_nodes(book: dict, src: str) -> list[dict]:
    """1 source の生ノードを (idx 保持で) 正規化。title_norm 空は落とす。"""
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
                    "depth": depth, "page": page, "page_is_pdf": page_is_pdf,
                    "kind": _node_kind(n)})
    return out


def _page_coverage(nodes: list[dict]) -> float:
    return sum(1 for n in nodes if n["page"] is not None) / (len(nodes) or 1)


def _granularity(nodes: list[dict]) -> tuple[int, int, float]:
    """B1: 粒度 = (最大深さ, ノード数, ページ被覆) の複合指標。"""
    if not nodes:
        return (0, 0, 0.0)
    return (max(n["depth"] for n in nodes), len(nodes), round(_page_coverage(nodes), 4))


def _is_simple(nodes: list[dict]) -> bool:
    """既存 base が "simple"(浅い章リスト) か。max depth<=1 を simple とみなす。"""
    return bool(nodes) and max((n["depth"] for n in nodes), default=1) <= 1


# ---- Step 1: 同一性ゲート (A1 全ペア connected component) -------------------

def step1_identity_gate(book: dict, policy: dict, *, year_tolerance: int = 1) -> dict:
    """同一 manifestation の connected component だけを合議対象にする。

    A1: 基準1点 pairwise でなく、全ペア判定で同版エッジを張り、anchor を含む連結成分を採る。
    A2: anchor は **node を持つ源**を優先 (bib のみ源を基準にしない)。
    """
    cfg = policy.get("step1_identity_gate", {})
    ok_status = set(cfg.get("cluster_only_status", list(APPLY_OK_STATUS)))
    meta = book.get("source_meta", {})
    bibs = {s: m for s, m in meta.items() if isinstance(m, dict)}
    if not bibs:
        return {"anchor": None, "clustered": [], "clustered_with_nodes": [],
                "human_review": [], "status": "insufficient_evidence", "reason": "no bib"}

    srcs = sorted(bibs)
    adj: dict[str, set] = {s: set() for s in srcs}
    pair_reason: dict[tuple, dict] = {}
    for a, b in combinations(srcs, 2):
        res = classify_edition_identity_v2([bibs[a], bibs[b]], year_tolerance=year_tolerance)
        pair_reason[(a, b)] = res
        if res["status"] in ok_status:
            adj[a].add(b)
            adj[b].add(a)

    # anchor = node を持つ源のうち priority 最上位 (無ければ bib priority 最上位)。
    node_srcs = [s for s in srcs if book.get("sources", {}).get(s)]
    anchor = min(node_srcs or srcs, key=lambda s: _priority_index(policy, s))

    # anchor の連結成分 (BFS)。
    comp, stack = {anchor}, [anchor]
    while stack:
        cur = stack.pop()
        for nb in adj[cur]:
            if nb not in comp:
                comp.add(nb)
                stack.append(nb)

    clustered = sorted(comp)
    human_review = []
    for s in srcs:
        if s in comp:
            continue
        # anchor から見た理由 (直接ペアがあればそれ、無ければ非連結)。
        key = tuple(sorted((anchor, s)))
        r = pair_reason.get(key, {"status": "insufficient_evidence", "reason": "not connected to anchor"})
        human_review.append({"source": s, "status": r["status"], "reason": r["reason"]})

    overall = classify_edition_identity_v2(list(bibs.values()), year_tolerance=year_tolerance)
    clustered_with_nodes = [s for s in clustered if book.get("sources", {}).get(s)]
    return {"anchor": anchor, "clustered": clustered,
            "clustered_with_nodes": sorted(clustered_with_nodes),
            "human_review": human_review, "status": overall["status"],
            "reason": overall["reason"]}


# ---- Step 2: 基底選択 (B1 複合粒度 + B2 simple_only 張替え) -----------------

def step2_base_selection(book: dict, policy: dict, clustered: list[str]) -> dict:
    cfg = policy.get("step2_base_selection", {})
    guard = cfg.get("granularity_guard", {})
    default_ratio = guard.get("min_node_ratio_vs_richest_default", 0.2)
    per_source = guard.get("min_node_ratio_vs_richest_per_source", {})
    protected = set(policy.get("protected_sources", []))

    norm = {s: _norm_nodes(book, s) for s in clustered}
    norm = {s: ns for s, ns in norm.items() if ns}
    if not norm:
        return {"base": None, "richest": None, "richest_count": 0, "richest_depth": 0,
                "guard_blocked": [], "candidates": {}, "reason": "no nodes in cluster"}

    counts = {s: len(ns) for s, ns in norm.items()}
    gran = {s: _granularity(ns) for s, ns in norm.items()}
    richest = max(gran, key=lambda s: (gran[s], -_priority_index(policy, s)))
    richest_count = counts[richest]
    richest_depth = gran[richest][0]

    # B1 guard: 最富源比 ratio 未満 **または** 最富源より浅い源は base 不可 (詳細→浅い劣化防止)。
    eligible, blocked = [], []
    for s in norm:
        ratio = per_source.get(s, default_ratio)
        ok_count = counts[s] >= ratio * richest_count
        ok_depth = gran[s][0] >= richest_depth
        if ok_count and ok_depth:
            eligible.append(s)
        else:
            blocked.append({"source": s, "nodes": counts[s], "depth": gran[s][0],
                            "min_nodes": round(ratio * richest_count, 1), "min_depth": richest_depth})
    if not eligible:               # 退避: 全滅時は最富源を base に。
        eligible = [richest]

    # 候補 = guard 通過源の複合粒度ベスト。
    candidate = max(eligible, key=lambda s: (gran[s], -_priority_index(policy, s)))
    # incumbent = clustered(node持ち) の priority 最上位 = 既存 attach 相当。
    incumbent = min(norm, key=lambda s: _priority_index(policy, s))

    # B2 simple_only 張替え意味論:
    #   - protected が既に rich (非simple) なら壊さない (never_overwrite_protected)。
    #   - incumbent が simple のときだけ詳細候補で張替え。
    #   - incumbent が既に rich (非protected) なら張替えない (良い既存を壊さない / skip)。
    if incumbent in protected and not _is_simple(norm[incumbent]):
        base, reason = incumbent, "protected incumbent kept (never overwrite)"
    elif _is_simple(norm[incumbent]) and candidate != incumbent:
        base, reason = candidate, "simple incumbent replaced by detailed candidate"
    else:
        base = incumbent if incumbent in eligible else candidate
        reason = "rich incumbent kept (skip replace)" if base == incumbent else "fallback to candidate"
    if base not in eligible:        # guard を満たさない base は採れない。
        base, reason = candidate, reason + " → guard fallback to candidate"

    return {"base": base, "richest": richest, "richest_count": richest_count,
            "richest_depth": richest_depth, "incumbent": incumbent, "candidate": candidate,
            "guard_blocked": blocked, "candidates": counts,
            "granularity": {s: list(g) for s, g in gran.items()},
            "page_coverage": {s: round(_page_coverage(norm[s]), 3) for s in norm},
            "reason": reason}


# ---- Step 3: ノード補完 (C1/C2/C3/C4) -------------------------------------

def _book_offset(book: dict):
    po = book.get("page_offset")
    if isinstance(po, dict) and po.get("validated") and float(po.get("confidence", 0)) >= 1.0:
        try:
            return int(po["offset"])
        except (TypeError, ValueError, KeyError):
            return None
    return None


def step3_node_completion(book: dict, policy: dict, clustered: list[str], base: str) -> dict:
    """base に無い title_norm を他源から append。各ノードに provenance を必ず付す。

    C1: source_hash 欠落は捏造せず snapshot_missing。C3: pdf→print は検証済 offset のみ。
    C4: partinfo の volume_structure は reject、mixed_small は review。
    """
    meta = book.get("source_meta", {})
    norm = {s: _norm_nodes(book, s) for s in clustered if book.get("sources", {}).get(s)}
    if base not in norm:
        return {"nodes": [], "rejected": [], "base_count": 0, "appended_count": 0}

    offset = _book_offset(book)
    kf = policy.get("partinfo_kind_filter", {})
    attach_kinds = set(kf.get("attach_kinds", ["contents"]))
    reject_kinds = set(kf.get("reject_kinds", ["volume_structure"]))
    review_kinds = set(kf.get("review_kinds", ["mixed_small"]))

    def make_node(n: dict, appended_from: str | None) -> dict | None:
        m = meta.get(n["src"], {})
        # C4: partinfo kind フィルタ。
        kind_status = "n/a"
        if n["src"] in _PARTINFO_SOURCES and n["kind"] is not None:
            if n["kind"] in reject_kinds:
                return {"_rejected": True, "locator": f"{n['src']}#{n['idx']}",
                        "title_norm": n["title_norm"], "reason": f"partinfo_kind={n['kind']}"}
            kind_status = "review" if n["kind"] in review_kinds else (
                "attach" if n["kind"] in attach_kinds else "review")

        page, basis = n["page"], normalize_page_basis(m.get("page_basis"))
        page_converted = False
        if n["page_is_pdf"] and page is not None:
            if offset is not None:
                page, basis, page_converted = to_print_page(int(page), offset), "print_page", True
            else:
                basis = "pdf_page"  # 変換不能 → pdf のまま (needs_offset)

        # C1: source_hash 欠落は捏造しない。
        raw_hash = m.get("source_sha256")
        snapshot_missing = not (raw_hash and str(raw_hash).strip())

        # C2: toc_node_id に lineage (isbn/origin/locator/title) を入れ衝突回避。
        origin = m.get("provenance_origin", n["src"])
        locator = f"{n['src']}#{n['idx']}"
        node = {
            "title": n["title"], "title_norm": n["title_norm"], "depth": n["depth"],
            "page": page, "page_start": page, "page_end": None, "page_basis": basis,
            "page_converted_from_pdf": page_converted,
            "needs_offset": bool(n["page_is_pdf"] and offset is None),
            "source_system": n["src"], "provenance_origin": origin, "locator": locator,
            "source_hash": (raw_hash if not snapshot_missing else None),
            "snapshot_missing": snapshot_missing,
            "kind_status": kind_status,
            "toc_node_id": _sha([book.get("isbn", ""), origin, locator, n["title_norm"]])[:23],
        }
        if appended_from:
            node["appended_from"] = appended_from
        return node

    nodes: list[dict] = []
    rejected: list[dict] = []
    seen: set[str] = set()

    def add_from(src: str, appended_from: str | None):
        for n in norm[src]:
            if n["title_norm"] in seen:
                continue
            mk = make_node(n, appended_from)
            if mk is None:
                continue
            if mk.get("_rejected"):
                rejected.append(mk)
                continue
            nodes.append(mk)
            seen.add(n["title_norm"])

    add_from(base, None)
    base_count = len(nodes)
    for s in sorted(norm, key=lambda x: _priority_index(policy, x)):
        if s != base:
            add_from(s, s)

    # 章執筆者: ndl_partinfo contents から付与。
    for a in policy.get("step3_node_completion", {}).get("chapter_author_from", []):
        for n in norm.get(a, []):
            raw = book["sources"][a][n["idx"]]
            who = (raw.get("author") or raw.get("creator")) if isinstance(raw, dict) else None
            if not who:
                continue
            for node in nodes:
                if node["title_norm"] == n["title_norm"]:
                    node["chapter_author"] = who

    return {"nodes": nodes, "rejected": rejected,
            "base_count": base_count, "appended_count": len(nodes) - base_count}


# ---- Step 4: 保護と合議 (D1 lane 分離 / votes=provenance_origin) -----------

def step4_protect_and_consensus(book: dict, policy: dict, clustered: list[str],
                                nodes: list[dict], edition_status: str) -> dict:
    cfg = policy.get("step4_protect_and_consensus", {})
    min_origins = cfg.get("consensus_min_independent_origins", 3)
    meta = book.get("source_meta", {})
    norm = {s: _norm_nodes(book, s) for s in clustered if book.get("sources", {}).get(s)}
    origins_by_title: dict[str, set] = {}
    for s, ns in norm.items():
        origin = meta.get(s, {}).get("provenance_origin", s)
        for n in ns:
            origins_by_title.setdefault(n["title_norm"], set()).add(origin)

    accepted, pending = [], []
    for node in nodes:
        votes = len(origins_by_title.get(node["title_norm"], set()))
        node["votes_by_provenance_origin"] = votes
        node["consensus"] = votes >= min_origins
        # D1: accepted = consensus かつ provenance 健全かつ kind が review でない。
        reasons = []
        if not node["consensus"]:
            reasons.append("non_consensus")
        if node.get("snapshot_missing"):
            reasons.append("source_snapshot_missing")
        if node.get("kind_status") == "review":
            reasons.append("partinfo_mixed_small_review")
        if node.get("needs_offset"):
            reasons.append("needs_offset")
        if reasons:
            node["pending_reasons"] = reasons
            pending.append(node)
        else:
            accepted.append(node)

    authority = resolve_authority(meta, edition_status=edition_status)
    return {"authority": authority["authority"], "authority_reason": authority["reason"],
            "accepted": accepted, "pending": pending,
            "consensus_nodes": len(accepted), "pending_nodes": len(pending),
            "min_origins": min_origins}


# ---- 親子リンク (F2 baseline 用) + 統合 ------------------------------------

def _link_parents(ordered: list[dict]) -> None:
    """深さスタックで parent_id を付与 (flat→tree の近似・accepted 順序内)。"""
    stack: list[dict] = []
    for n in ordered:
        while stack and stack[-1]["depth"] >= n["depth"]:
            stack.pop()
        n["parent_id"] = stack[-1]["toc_node_id"] if stack else None
        stack.append(n)


def adopt_book(book: dict, policy: dict | None = None) -> dict:
    """1 冊に 5 ステップを適用し、採用 projection を返す (report-only)。"""
    p = policy or load_policy()
    s1 = step1_identity_gate(book, p)
    clustered = s1["clustered_with_nodes"]
    s2 = step2_base_selection(book, p, clustered)
    base = s2["base"]
    identity_ok = s1["status"] in APPLY_OK_STATUS
    if base is None:
        return {"isbn": book.get("isbn", ""), "title": book.get("title", ""),
                "step1": s1, "step2": s2, "step3": {"nodes": [], "rejected": []},
                "step4": {}, "base_source": None, "accepted": [], "pending": [], "rejected": [],
                "projection": [], "projection_node_count": 0, "projection_sha": _sha([]),
                "base_source_distribution": {}, "adoptable": False, "adoptable_blockers": ["no_base"],
                "report_only": True}
    s3 = step3_node_completion(book, p, clustered, base)
    s4 = step4_protect_and_consensus(book, p, clustered, s3["nodes"], s1["status"])

    accepted = s4["accepted"]
    _link_parents(accepted)
    pending = s4["pending"]

    # D2: adoptable = identity ∧ consensus ∧ authority≠HR ∧ provenance(欠落なし)。
    authority_ok = s4["authority"] != AUTH_HUMAN_REVIEW
    consensus_ok = bool(accepted) and not pending
    provenance_ok = all(n.get("source_hash") for n in accepted)
    blockers = []
    if not identity_ok:
        blockers.append("identity_unresolved")
    if not consensus_ok:
        blockers.append("non_consensus_or_pending")
    if not authority_ok:
        blockers.append("authority_human_review")
    if not provenance_ok:
        blockers.append("provenance_incomplete")
    adoptable = not blockers

    return {
        "isbn": book.get("isbn", ""), "title": book.get("title", ""),
        "step1": s1, "step2": s2, "step3": s3, "step4": s4,
        "base_source": base,
        "accepted": accepted, "pending": pending, "rejected": s3["rejected"],
        "projection": accepted,                 # accepted のみが採用 projection (D1)
        "projection_node_count": len(accepted),
        "pending_node_count": len(pending),
        "projection_sha": _sha(sorted(
            (n["toc_node_id"], n["title_norm"], n.get("page"), n.get("parent_id"),
             n["provenance_origin"]) for n in accepted)),  # 入力順非依存
        "base_source_distribution": _base_dist(accepted, base),
        "adoptable": adoptable, "adoptable_blockers": blockers,
        "report_only": True,
    }


def _base_dist(projection: list[dict], base: str) -> dict:
    d: dict[str, int] = {}
    for n in projection:
        s = n.get("appended_from", base)
        d[s] = d.get(s, 0) + 1
    return dict(sorted(d.items()))


def export_baseline(adoptions: list[dict]) -> dict:
    """F2: ALOBookDX baseline と突合するための reproduction 用 export。

    sha だけでなくノード集合・親子・ページ・base 分布の同値検査ができる粒度で出す。
    """
    out = {}
    for a in adoptions:
        out[a["isbn"]] = {
            "book_cluster_id": a["isbn"],
            "base_source": a["base_source"],
            "projection_sha": a["projection_sha"],
            "base_source_distribution": a["base_source_distribution"],
            "nodes": [{
                "toc_node_id": n["toc_node_id"], "parent_id": n.get("parent_id"),
                "title_norm": n["title_norm"], "page_start": n.get("page_start"),
                "page_end": n.get("page_end"), "provenance_origin": n["provenance_origin"],
                "source_snapshot_hash": n.get("source_hash"),
                "chapter_author": n.get("chapter_author"),
            } for n in a["accepted"]],
        }
    return out


def adopt_corpus(books: list[dict], policy: dict | None = None) -> dict:
    p = policy or load_policy()
    rows = [adopt_book(b, p) for b in books]
    return {
        "policy_version": p.get("policy_version"),
        "adopt_version": TOC_ADOPT_VERSION,
        "books": len(rows),
        "adoptable_count": sum(1 for r in rows if r["adoptable"]),
        "total_accepted_nodes": sum(r["projection_node_count"] for r in rows),
        "total_pending_nodes": sum(r["pending_node_count"] for r in rows),
        "rows": rows,
        "report_only": True,
    }


__all__ = ["TOC_ADOPT_VERSION", "load_policy", "adopt_book", "adopt_corpus", "export_baseline",
           "step1_identity_gate", "step2_base_selection", "step3_node_completion",
           "step4_protect_and_consensus"]
