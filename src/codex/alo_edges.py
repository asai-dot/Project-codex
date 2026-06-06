"""legal_links 抽出結果を ALO knowledge-db の link layer (35_link_layer.md) に
準拠した alo_edges / alo_edge_evidence / alo_pointers レコードへ変換する producer.

⚠ これは **エクスポート整形のみ**。DB への書込みは一切しない（Phase 0）。
最終投入は DD-TOCLEGALREF 承認 + 法令/リンク層実装後に governance 経由で行う。

設計図書からの拘束（厳守）:
  - edge_type は固定 10 値。文献→条文 = `interprets`、文献→判例 = `evaluates`。
  - assertion_mode = `vendor_implicit`（ルール抽出。`llm_inferred` は DB 禁止）。
  - `assertion_confidence` は llm_inferred 専用 → 規則抽出では **NULL**。
    確信度は `weight`(0–1) と provenance に載せる。
  - Gate-5: cites/applies 等のエッジは alo_edge_evidence(→alo_pointers) 必須。
  - URI は NFC。
  - 判例は cases.canonical_uri が事件番号を要求 → TOC からは作れない
    → 判例引用は「解決候補」として別出力（dst 未解決フラグ）。
"""

from __future__ import annotations

import unicodedata

# tier(高/中/低) → weight。low は誤検出が集中するため edge 化しない（除外）。
_TIER_WEIGHT = {"high": 1.000, "medium": 0.700}

# 文献(commentary) を起点にした法令/判例参照の edge_type（35_link_layer §2.2）
EDGE_TYPE_STATUTE = "interprets"   # commentary → statute
EDGE_TYPE_CASE = "evaluates"       # commentary → case

ASSERTION_MODE = "vendor_implicit"
SRC_TYPE = "commentary"
SOURCE_SYSTEM = "bencom-library"   # ※ alo_source_priority への登録は DD で要請（未登録）


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def work_uri_for_bib(bib_id: str) -> str:
    """書誌 → 文献(work) URI。bib_id が既に alo: 形式ならそのまま、
    NOBN_ 等は暫定 work URI を付す（最終は 32_literature_layer の work URI に解決）。"""
    bib_id = bib_id or ""
    if bib_id.startswith("alo:"):
        return _nfc(bib_id)
    return _nfc(f"alo:work:bencom:{bib_id}")


def pointer_uri_for_span(bib_id: str, ordinal, char_start, char_end) -> str:
    return _nfc(f"alo:pointer:bencom:{bib_id}:toc:{ordinal}:{char_start}-{char_end}")


def _provenance(tier: str, ordinal, extra: dict) -> str:
    parts = [
        "extractor=legal_links@0.1",
        "source=bencom-library:biblio.bib_toc",
        f"toc_ordinal={ordinal}",
        f"confidence_tier={tier}",
    ]
    for k, v in extra.items():
        parts.append(f"{k}={v}")
    return "; ".join(parts)


def transform_node_links(node: dict, links: list[dict]) -> dict:
    """1 ノード分の legal_links を alo_edges 群へ変換。

    node: {bib_id, ordinal, pub_year, page, text, ...}
    links: legal_links.extract_links(...) の出力
    返り値: {"edges": [...], "edge_evidence": [...], "pointers": [...],
             "case_candidates": [...], "skipped_low": int}
    """
    bib_id = node["bib_id"]
    ordinal = node.get("ordinal")
    pub_year = node.get("pub_year")
    as_of = f"{pub_year}-01-01" if pub_year else None  # DD-LAWTIME 用（粒度=年）
    src_uri = work_uri_for_bib(bib_id)

    edges, evidence, pointers, case_cands = [], [], [], []
    skipped_low = 0
    seen_edges: set[tuple] = set()

    for lk in links:
        cs = lk.get("char_start")
        # span end: マッチ文字列長から算出（legal_links は char_start を持つ）
        match = lk.get("match_text") or ""
        ce = (cs + len(match)) if cs is not None else None
        ptr_uri = pointer_uri_for_span(bib_id, ordinal, cs, ce)

        if lk["scheme"] == "jp_statute_ref":
            tier = lk.get("confidence")
            if tier not in _TIER_WEIGHT:      # low / None は edge 化しない
                skipped_low += 1
                continue
            dst_uri = _nfc(lk["uri"])         # egov:law_id[:art:N]
            valid_from = as_of                # interprets は valid_from 任意（pub 日を proxy）
            key = (src_uri, dst_uri, EDGE_TYPE_STATUTE, ASSERTION_MODE, valid_from)
            if key in seen_edges:
                continue
            seen_edges.add(key)

            edges.append({
                "src_uri": src_uri, "src_type": SRC_TYPE,
                "dst_uri": dst_uri, "dst_type": "statute",
                "edge_type": EDGE_TYPE_STATUTE,
                "assertion_mode": ASSERTION_MODE,
                "weight": _TIER_WEIGHT[tier],
                "assertion_confidence": None,     # llm_inferred 専用 → NULL
                "valid_from": valid_from,
                "valid_to": "9999-12-31",
                "invalidated_by": None,
                "provenance": _provenance(tier, ordinal, {
                    "law_id": lk.get("law_id"),
                    "article": lk.get("article"),
                    "article_in_egov": lk.get("article_in_egov"),
                    "as_of_date": as_of,           # DD-LAWTIME 準備（active schema 外）
                }),
                "source_system": SOURCE_SYSTEM,
                "_evidence_pointer_uri": ptr_uri,
            })
            pointers.append({
                "pointer_uri": ptr_uri, "entity_type": "work",
                "entity_uri": src_uri, "storage_type": "external",
                "range_type": "char", "range_start": cs, "range_end": ce,
                "_node_text": node.get("text"),
            })
            evidence.append({
                "_src_uri": src_uri, "_dst_uri": dst_uri,
                "_edge_type": EDGE_TYPE_STATUTE, "_valid_from": valid_from,
                "pointer_uri": ptr_uri, "role": "source_field", "ordinal": 1,
            })

        elif lk["scheme"] == "jp_case_citation":
            # 判例は事件番号が無く canonical case URI を作れない → 解決候補として保留
            case_cands.append({
                "src_uri": src_uri, "src_type": SRC_TYPE,
                "intended_edge_type": EDGE_TYPE_CASE,
                "assertion_mode": ASSERTION_MODE,
                "cite_raw": lk.get("match_text"),
                "court": lk.get("court"), "era": lk.get("era"),
                "cite_key": lk.get("cite_key"),
                "as_of_date": as_of,
                "resolution_status": "needs_case_uri",   # cases 表(court+date+事件番号)へ要照合
                "evidence_pointer_uri": ptr_uri,
                "provenance": _provenance("case", ordinal, {"cite_key": lk.get("cite_key")}),
            })
            pointers.append({
                "pointer_uri": ptr_uri, "entity_type": "work",
                "entity_uri": src_uri, "storage_type": "external",
                "range_type": "char", "range_start": cs, "range_end": ce,
                "_node_text": node.get("text"),
            })

    return {"edges": edges, "edge_evidence": evidence, "pointers": pointers,
            "case_candidates": case_cands, "skipped_low": skipped_low}
