#!/usr/bin/env python3
"""jufu_intake.py — 受任案件 手元判決(jufu)の取込境界 (DD-CASEID-005)。

jufu = 事務所が受任案件で保有する手元判決(非公開・lawyer_client_confidential)。
原則: *identity evidence には使えるが出口(global)には出さない*。
  - A1 同一性 evidence(case_key の存在確認・自然キー補強)        → 許可
  - 出口5点(global_content_index/embedding/mcp_serve/export/claim_support) → global は全拒否
  - matter 内(当該受任案件の認可者)への display/mcp_serve         → 認可時のみ許可
  - embedding は global 禁止(RP-04)。export/claim_support は matter 内でも global へ出さない

reconcile: case_key(判例) ≠ alo_matter_id(受任案件)=別オブジェクト(N-1)。
出口可否は DDCASESOURCE が一次所有(N-3)。本境界はその適用。read-only。
"""
from __future__ import annotations

GLOBAL_SINKS = ("global_content_index", "embedding", "mcp_serve", "export", "claim_support")
# matter 内で認可者に許してよい用途(閲覧系のみ。matter 外へ出す用途は含めない)
MATTER_INTERNAL_ALLOWED = ("mcp_serve", "display")


def allow_jufu_use(use: str, *, scope: str = "global",
                   requester_matters: set | None = None, matter_id: str | None = None) -> bool:
    """jufu observation を `use` 用途で使ってよいか。

    use: 'identity_evidence' | 'display' | 'global_content_index' | 'embedding' |
         'mcp_serve' | 'export' | 'claim_support'
    scope: 'global' | 'matter'
    """
    # A1 同一性 evidence は出口ではない → 常に許可(jufu でも identity 補強に使える)
    if use == "identity_evidence":
        return True
    # RP-04: jufu 由来 embedding は global 禁止(matter 内でも global index 連動は不可)
    if use == "embedding":
        return False
    # global scope: lawyer_client_confidential は出口5点すべて不可
    if scope == "global":
        return False
    # matter scope: 当該受任案件の認可者にのみ閲覧系を許可
    if scope == "matter":
        authorized = requester_matters is not None and matter_id in requester_matters
        if not authorized:
            return False
        # matter 外へ持ち出す用途(export/claim_support/global index)は matter 内でも不可
        if use in ("export", "claim_support", "global_content_index"):
            return False
        return use in MATTER_INTERNAL_ALLOWED
    return False


def classify_jufu_observation(obs: dict) -> dict:
    """jufu observation の取込分類。

    returns {role, confidentiality_class, redistribution, can_global_index,
             matter_link_required, identity_use_allowed}。
    """
    return {
        "role": "identity_evidence_only",
        "confidentiality_class": "lawyer_client_confidential",
        "redistribution": "restricted",
        "can_global_index": False,
        "matter_link_required": True,   # alo_matter_id への link 必須(N-1: case_key とは別)
        "identity_use_allowed": True,
        "global_egress_allowed": False,
    }
