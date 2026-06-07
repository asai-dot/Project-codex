"""legal_links 抽出結果を ALO link layer (35_link_layer.md) 準拠の
alo_edges / alo_edge_evidence / alo_pointers レコードへ変換する producer (v0.2).

⚠ エクスポート整形のみ。DB 書込みなし。

v0.2 (GPT お目付け役 DDTOCLEGALREF_MODIFY_REQUIRED 反映):
  R-01 edge_type 強すぎ → `interprets`/`evaluates` は維持しつつ
       `edge_semantics_status=candidate` で隔離（link layer 本体は無改変）。
  R-02 assertion_mode → 既存 `implicit` + `extraction_method=vendor_rule`。
       `weight` は relevance/strength であり truth confidence ではない旨を明記。
  R-03 DD-LAWTIME 依存遮断 → pub_year は coarse_proxy。`valid_from` に流用せず
       (null)、`resolved_law_revision_id`/`temporal_status` は書かない、
       `claim_support_eligible=false`。
  R-04 src_uri provisional 明示（canonical と呼ばない）。
  #5  medium は rollout_status=quarantine（初回 backfill は high のみ）。
  #7  evidence 再現性: bib_toc_node_key + payload_hash + parser_version + char span。
  #8  case candidate に candidate_status/ambiguity_count/review_required/source_text。
  #9  冪等 dedup_key を明示。
"""

from __future__ import annotations

import hashlib
import unicodedata

EXTRACTOR_VERSION = "legal_links@0.2"
PARSER_VERSION = "alo_edges@0.2"

_TIER_WEIGHT = {"high": 1.000, "medium": 0.700}
_TIER_ROLLOUT = {"high": "initial", "medium": "quarantine_sample_required"}

EDGE_TYPE_STATUTE = "interprets"   # commentary → statute（candidate 隔離）
EDGE_TYPE_CASE = "evaluates"       # commentary → case
ASSERTION_MODE = "implicit"        # 既存許容値（vendor_implicit を新設しない）
EXTRACTION_METHOD = "vendor_rule"
SRC_TYPE = "commentary"
SOURCE_SYSTEM = "bencom-library"
SOURCE_ROLE = "toc_signal"


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def _sha1(s: str) -> str:
    return hashlib.sha1(_nfc(s).encode("utf-8")).hexdigest()


def work_uri_for_bib(bib_id: str) -> str:
    bib_id = bib_id or ""
    if bib_id.startswith("alo:"):
        return _nfc(bib_id)
    return _nfc(f"alo:work:bencom:{bib_id}")


def pointer_uri_for_span(bib_id, ordinal, char_start, char_end) -> str:
    return _nfc(f"alo:pointer:bencom:{bib_id}:toc:{ordinal}:{char_start}-{char_end}")


def _provenance(tier: str, ordinal, extra: dict) -> str:
    parts = [f"extractor={EXTRACTOR_VERSION}", "source=bencom-library:biblio.bib_toc",
             f"toc_ordinal={ordinal}", f"confidence_tier={tier}"]
    parts += [f"{k}={v}" for k, v in extra.items()]
    return "; ".join(parts)


def transform_node_links(node: dict, links: list[dict]) -> dict:
    bib_id = node["bib_id"]
    ordinal = node.get("ordinal")
    pub_year = node.get("pub_year")
    as_of = f"{pub_year}-01-01" if pub_year else None
    src_uri = work_uri_for_bib(bib_id)
    node_key = f"{bib_id}:{ordinal}"
    payload_hash = _sha1(node.get("text") or "")

    edges, evidence, pointers, case_cands = [], [], [], []
    skipped_low = 0
    seen_edges: set = set()

    for lk in links:
        cs = lk.get("char_start")
        match = lk.get("match_text") or ""
        ce = (cs + len(match)) if cs is not None else None
        span_hash = _sha1(f"{cs}:{ce}:{match}")
        ptr_uri = pointer_uri_for_span(bib_id, ordinal, cs, ce)

        if lk["scheme"] == "jp_statute_ref":
            tier = lk.get("confidence")
            if tier not in _TIER_WEIGHT:           # low / None は除外（誤検出隔離）
                skipped_low += 1
                continue
            dst_uri = _nfc(lk["uri"])
            dedup_key = "|".join([bib_id, dst_uri, EDGE_TYPE_STATUTE, node_key,
                                  span_hash, EXTRACTOR_VERSION])
            if dedup_key in seen_edges:
                continue
            seen_edges.add(dedup_key)

            edges.append({
                # --- src（provisional 明示, R-04）---
                "src_uri": src_uri, "src_type": SRC_TYPE,
                "src_uri_status": "provisional",
                "source_record_key": bib_id, "canonical_work_uri": None,
                "src_resolution_status": "unresolved",
                # --- dst ---
                "dst_uri": dst_uri, "dst_type": "statute",
                # --- semantics（R-01: candidate 隔離）---
                "edge_type": EDGE_TYPE_STATUTE,
                "edge_semantics_status": "candidate",
                # --- assertion（R-02）---
                "assertion_mode": ASSERTION_MODE,
                "extraction_method": EXTRACTION_METHOD,
                "assertion_confidence": None,
                "weight": _TIER_WEIGHT[tier],
                "weight_basis": "relevance_strength_not_truth_confidence",
                "rollout_status": _TIER_ROLLOUT[tier],   # #5
                # --- temporal（R-03: DD-LAWTIME 遮断）---
                "valid_from": None, "valid_to": "9999-12-31", "invalidated_by": None,
                "as_of_value": as_of, "as_of_basis": "pub_year",
                "as_of_precision": "year", "as_of_status": "coarse_proxy",
                "resolved_law_revision_id": None, "temporal_status": None,
                "claim_support_eligible": False,
                # --- provenance / source ---
                "source_system": SOURCE_SYSTEM, "source_role": SOURCE_ROLE,
                "extractor_version": EXTRACTOR_VERSION,
                "dedup_key": _sha1(dedup_key),
                "provenance": _provenance(tier, ordinal, {
                    "law_id": lk.get("law_id"), "article": lk.get("article"),
                    "article_in_egov": lk.get("article_in_egov"),
                    "as_of_status": "coarse_proxy",
                }),
                "_evidence_pointer_uri": ptr_uri,
            })
            pointers.append(_pointer(ptr_uri, src_uri, node_key, payload_hash, cs, ce,
                                     node.get("text")))
            evidence.append({
                "_src_uri": src_uri, "_dst_uri": dst_uri,
                "_edge_type": EDGE_TYPE_STATUTE, "_dedup_key": _sha1(dedup_key),
                "pointer_uri": ptr_uri, "role": "source_field", "ordinal": 1,
            })

        elif lk["scheme"] == "jp_case_citation":
            case_cands.append({
                "src_uri": src_uri, "src_uri_status": "provisional",
                "source_record_key": bib_id, "src_type": SRC_TYPE,
                "intended_edge_type": EDGE_TYPE_CASE,
                "assertion_mode": ASSERTION_MODE, "extraction_method": EXTRACTION_METHOD,
                # --- 解決キュー設計（#8）---
                "candidate_status": "unresolved",
                "resolution_basis": "court+era+date（事件番号なし）",
                "matched_case_uri": None, "ambiguity_count": None,
                "review_required": True,
                "cite_raw": lk.get("match_text"), "source_text": node.get("text"),
                "court": lk.get("court"), "era": lk.get("era"),
                "cite_key": lk.get("cite_key"),
                "as_of_value": as_of, "as_of_status": "coarse_proxy",
                "evidence_pointer_uri": ptr_uri,
                "extractor_version": EXTRACTOR_VERSION,
                "provenance": _provenance("case", ordinal, {"cite_key": lk.get("cite_key")}),
            })
            pointers.append(_pointer(ptr_uri, src_uri, node_key, payload_hash, cs, ce,
                                     node.get("text")))

    return {"edges": edges, "edge_evidence": evidence, "pointers": pointers,
            "case_candidates": case_cands, "skipped_low": skipped_low}


def _pointer(ptr_uri, src_uri, node_key, payload_hash, cs, ce, text):
    return {
        "pointer_uri": ptr_uri, "entity_type": "work", "entity_uri": src_uri,
        "storage_type": "external",
        "bib_toc_node_key": node_key, "payload_hash": payload_hash,   # 再現性（#7）
        "parser_version": PARSER_VERSION,
        "range_type": "char", "range_start": cs, "range_end": ce,
        "_node_text": text,
    }
