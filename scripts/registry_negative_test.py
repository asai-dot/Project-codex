#!/usr/bin/env python3
"""registry_negative_test.py — DD-CASE-001 出口軸(A3)ガードの否定テスト【v0.2-recon】

recon_status: reconstructed_from_residual_materials
原本 (registry_negative_test.py, 9 assertion) は前セッションのローカル散逸で回収不能。
本ファイルは Box 残存材料 (準司法REQUEST RP-01〜06, DD-CASE-001 recon §1/§4) から
*意味* を再構成したもの。逐語ではない。

v0.2 変更 (DDCASESOURCE_PASS_WITH_NOTES 2026-06-19 の must_fix #3〜#6 反映):
  - confidentiality(matter軸) と redistribution(ライセンス軸) を独立入力化。
    global egress は「open かつ public」を要求 (must_fix#3)。
  - commercial_licensed / restricted / manual / matter_confirmed の出口禁止を assertion 化 (must_fix#4)。
  - same_matter 許可を mcp_serve に限定。export / claim_support は same_matter でも別gate (must_fix#5)。
  - source-record-level override を引数化。override が source/class 既定に勝つ (must_fix#6)。

参照:
  RP-01/06 値域 = open / matter_scoped_only / matter_confirmed / lawyer_client_confidential
  RP-02    matter_scoped_only は5点シンクへ当該matter外で出さない
  RP-03    global_content_index への backfill は open かつ public のみ
  RP-04    jufu 由来は identity evidence 限定。global embedding 禁止

実行: python3 registry_negative_test.py  (終了コード0=全PASS)。依存なし。
"""
from __future__ import annotations

CONFIDENTIALITY_CLASSES = {
    "open", "matter_scoped_only", "matter_confirmed", "lawyer_client_confidential",
}
REDISTRIBUTION_CLASSES = {"public", "commercial_licensed", "restricted"}
GLOBAL_SINKS = ("global_content_index", "embedding", "mcp_serve", "export", "claim_support")
# same_matter で許可してよい限定シンク (export/claim_support は含めない; must_fix#5)
SAME_MATTER_ALLOWED_SINKS = ("mcp_serve",)


def is_valid_class(c: str) -> bool:
    return c in CONFIDENTIALITY_CLASSES


def is_valid_redistribution(r: str) -> bool:
    return r in REDISTRIBUTION_CLASSES


def allow_global_sink(confidentiality_class: str, sink: str, *,
                      redistribution: str = "public", source: str = "",
                      same_matter: bool = False, record_override=None) -> bool:
    """ノードを global(matter横断/公開) シンクへ出してよいか。

    record_override: dict[sink->bool] | None。record-level の出口可否上書き(must_fix#6)。
                     与えられた sink については source/class 既定より override が勝つ。
    """
    if not is_valid_class(confidentiality_class):
        raise ValueError(f"unknown confidentiality_class: {confidentiality_class!r}")
    if not is_valid_redistribution(redistribution):
        raise ValueError(f"unknown redistribution: {redistribution!r}")
    if sink not in GLOBAL_SINKS:
        raise ValueError(f"unknown sink: {sink!r}")

    # must_fix#6: record-level override が最優先
    if record_override is not None and sink in record_override:
        return bool(record_override[sink])

    # RP-04: jufu 由来は global embedding 禁止 (クラス/再配布に関わらず)
    if source == "jufu" and sink == "embedding":
        return False

    # RP-03: global_content_index は open かつ public のみ
    if sink == "global_content_index":
        return confidentiality_class == "open" and redistribution == "public"

    # その他 global egress (embedding/mcp_serve/export/claim_support)
    if confidentiality_class == "open" and redistribution == "public":
        return True
    # matter_scoped_only は当該matter内の限定シンクのみ (export/claim_support不可)
    if confidentiality_class == "matter_scoped_only" and same_matter:
        return sink in SAME_MATTER_ALLOWED_SINKS
    # matter_confirmed / lawyer_client_confidential / 非public は全不可
    return False


def allow_identity_evidence(confidentiality_class: str, source: str = "") -> bool:
    """同一性 evidence(A1) 利用可否。AN-3/RP-04: 機密・jufu でも A1 利用は可(出口ではない)。"""
    is_valid_class(confidentiality_class)
    return True


def run() -> int:
    failures = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            failures.append(name)

    # --- 原 9 assertion (RP-01〜06) ---
    check("A1_value_domain_rejects_unknown",
          (not is_valid_class("confirmed_private")) and (not is_valid_class("no_export"))
          and is_valid_class("matter_confirmed"))
    check("A2_open_public_passes_global_index",
          allow_global_sink("open", "global_content_index") is True)
    check("A3_matter_confirmed_blocked_from_global_index",
          allow_global_sink("matter_confirmed", "global_content_index") is False)
    check("A4_privileged_blocked_from_global_index",
          allow_global_sink("lawyer_client_confidential", "global_content_index") is False)
    check("A5_scoped_blocked_global_index",
          allow_global_sink("matter_scoped_only", "global_content_index", same_matter=False) is False)
    check("A6_scoped_blocked_embedding_global",
          allow_global_sink("matter_scoped_only", "embedding", same_matter=False) is False)
    check("A7_scoped_blocked_mcp_serve_global",
          allow_global_sink("matter_scoped_only", "mcp_serve", same_matter=False) is False)
    check("A8_scoped_blocked_export_and_claim_support_global",
          (allow_global_sink("matter_scoped_only", "export", same_matter=False) is False)
          and (allow_global_sink("matter_scoped_only", "claim_support", same_matter=False) is False))
    check("A9_jufu_global_embedding_banned_but_identity_evidence_ok",
          (allow_global_sink("open", "embedding", source="jufu") is False)
          and (allow_identity_evidence("lawyer_client_confidential", source="jufu") is True))

    # --- v0.2 追加 (must_fix #3〜#6) ---
    # B1 (must_fix#3): open でも redistribution!=public なら global_content_index 不可
    check("B1_open_but_nonpublic_blocked_from_global_index",
          (allow_global_sink("open", "global_content_index", redistribution="commercial_licensed") is False)
          and (allow_global_sink("open", "global_content_index", redistribution="restricted") is False))
    # B2 (must_fix#4): commercial_licensed(open) は embedding/export/global_index 禁止
    check("B2_commercial_licensed_blocked_from_egress",
          all(allow_global_sink("open", s, redistribution="commercial_licensed") is False
              for s in ("global_content_index", "embedding", "export")))
    # B3 (must_fix#4): matter_confirmed は global_index/export/claim_support 禁止
    check("B3_matter_confirmed_blocked_from_index_export_claim",
          all(allow_global_sink("matter_confirmed", s) is False
              for s in ("global_content_index", "export", "claim_support")))
    # B4 (must_fix#4): restricted(saikousai-db 等) は open でも egress 禁止
    check("B4_restricted_open_blocked_from_egress",
          all(allow_global_sink("open", s, redistribution="restricted") is False
              for s in ("global_content_index", "embedding", "export", "claim_support")))
    # B5 (must_fix#5): same_matter でも export/claim_support は不可、mcp_serve のみ可
    check("B5_same_matter_narrowed_to_mcp_serve_only",
          (allow_global_sink("matter_scoped_only", "mcp_serve", same_matter=True) is True)
          and (allow_global_sink("matter_scoped_only", "export", same_matter=True) is False)
          and (allow_global_sink("matter_scoped_only", "claim_support", same_matter=True) is False))
    # B6 (must_fix#6): record-level override が source/class 既定に勝つ (deny上書き / allow上書き両方向)
    check("B6_record_override_wins",
          (allow_global_sink("open", "export", record_override={"export": False}) is False)
          and (allow_global_sink("matter_confirmed", "mcp_serve",
                                 record_override={"mcp_serve": True}) is True))

    print()
    if failures:
        print(f"RESULT: FAIL ({len(failures)}): {failures}")
        return 1
    print("RESULT: PASS (all assertions green)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(run())
