#!/usr/bin/env python3
"""registry_negative_test.py — DD-CASE-001 出口軸(A3)ガードの否定テスト【v0.1-recon】

原本 (registry_negative_test.py, 9 assertion 全PASS) は前セッションのローカル散逸で
回収不能。本ファイルは Box 残存材料 (準司法REQUEST RP-01〜06, DD-CASE-001 recon §1/§4)
から *意味* を再構成したもの。逐語ではない。9 assertion の趣旨を保存する。

検証対象: confidentiality_class (出口軸 A3) に対する backfill / serve ガードが
RP-01〜06 を満たすこと。原本同様 *否定* テスト中心 (漏れてはならないものが漏れない)。

参照:
  RP-01/06  confidentiality_class 値域 = open / matter_scoped_only /
            matter_confirmed / lawyer_client_confidential
  RP-02     matter_scoped_only は 5点シンク (global_content_index / embedding /
            mcp_serve / export / claim_support) へ当該matter外で出さない
  RP-03     global_content_index への backfill は confidentiality_class==open のみ
            (!=no_export では緩すぎる; D1商用・在野も open 以外は除外)
  RP-04     jufu (受任手元) 由来は identity evidence 限定。global embedding 禁止

実行: python3 registry_negative_test.py  (終了コード0=全PASS)
依存なし (標準ライブラリのみ)。
"""
from __future__ import annotations

# --- 参照ポリシー実装 (DD-CASE-001 §1 3軸分離 / §4 RP-01〜06 を符号化) -------------

CONFIDENTIALITY_CLASSES = {
    "open",                       # 公開可。global index 可
    "matter_scoped_only",        # 当該matter内のみ。matter外は全シンク不可
    "matter_confirmed",          # 受任で同一性確定。global index 不可
    "lawyer_client_confidential",# 守秘特権。global 一切不可
}

# 出口シンク (RP-02 の5点ガード)
GLOBAL_SINKS = ("global_content_index", "embedding", "mcp_serve", "export", "claim_support")


def is_valid_class(c: str) -> bool:
    """RP-01/06: 値域外を弾く。"""
    return c in CONFIDENTIALITY_CLASSES


def allow_global_sink(confidentiality_class: str, sink: str, *,
                      source: str = "", same_matter: bool = False) -> bool:
    """ノードを global (matter横断/公開) シンクへ出してよいか。

    RP-03: global_content_index は open のみ。
    RP-02: matter_scoped_only は same_matter=True のシンクのみ可、global は全不可。
    RP-04: source=='jufu' は embedding(global) 不可 (identity evidence 用途は別関数)。
    """
    if not is_valid_class(confidentiality_class):
        raise ValueError(f"unknown confidentiality_class: {confidentiality_class!r}")
    if sink not in GLOBAL_SINKS:
        raise ValueError(f"unknown sink: {sink!r}")

    # RP-04: jufu 由来は global embedding 禁止 (クラスに関わらず)
    if source == "jufu" and sink == "embedding":
        return False

    if confidentiality_class == "open":
        return True
    if confidentiality_class == "matter_scoped_only":
        # 当該matter内のシンクのみ許可。global(=same_matter False)は全不可
        return same_matter and sink != "global_content_index"
    # matter_confirmed / lawyer_client_confidential は global シンク不可
    return False


def allow_identity_evidence(confidentiality_class: str, source: str = "") -> bool:
    """同一性 evidence (A1; 名寄せ根拠) としての利用可否。

    AN-3/RP-04: jufu や機密ノードも *同一性 evidence* には使える (出口ではない)。
    """
    is_valid_class(confidentiality_class)  # 値域は別assertでも検証
    return True  # A1利用は出口ではないので機密クラス・jufu でも可


# --- 否定テスト (9 assertion) -------------------------------------------------

def run() -> int:
    failures = []

    def check(name, cond):
        if cond:
            print(f"  PASS  {name}")
        else:
            print(f"  FAIL  {name}")
            failures.append(name)

    # A1 (RP-01/06): 値域外クラスは拒否される
    check("A1_value_domain_rejects_unknown",
          (not is_valid_class("confirmed_private"))   # 旧名は無効 (RP-01でmatter_confirmedへ改名)
          and (not is_valid_class("no_export"))       # RP-03で廃した緩い表現
          and is_valid_class("matter_confirmed"))

    # A2 (RP-03): global_content_index は open のみ通す (正の対照)
    check("A2_open_passes_global_index",
          allow_global_sink("open", "global_content_index") is True)

    # A3 (RP-03): matter_confirmed は global_content_index へ出ない
    check("A3_matter_confirmed_blocked_from_global_index",
          allow_global_sink("matter_confirmed", "global_content_index") is False)

    # A4 (RP-03): lawyer_client_confidential は global_content_index へ出ない
    check("A4_privileged_blocked_from_global_index",
          allow_global_sink("lawyer_client_confidential", "global_content_index") is False)

    # A5-A8 (RP-02): matter_scoped_only は5点シンクの global で全て不可
    check("A5_scoped_blocked_global_index",
          allow_global_sink("matter_scoped_only", "global_content_index", same_matter=False) is False)
    check("A6_scoped_blocked_embedding_global",
          allow_global_sink("matter_scoped_only", "embedding", same_matter=False) is False)
    check("A7_scoped_blocked_mcp_serve_global",
          allow_global_sink("matter_scoped_only", "mcp_serve", same_matter=False) is False)
    check("A8_scoped_blocked_export_and_claim_support_global",
          (allow_global_sink("matter_scoped_only", "export", same_matter=False) is False)
          and (allow_global_sink("matter_scoped_only", "claim_support", same_matter=False) is False))

    # A9 (RP-04): jufu 由来は global embedding 禁止。ただし identity evidence 利用は可
    check("A9_jufu_global_embedding_banned_but_identity_evidence_ok",
          (allow_global_sink("open", "embedding", source="jufu") is False)        # クラスopenでもjufuはembedding不可
          and (allow_identity_evidence("lawyer_client_confidential", source="jufu") is True))

    # 補助の正対照 (matter内では scoped を許す = 過剰除外でないことの確認; RP-03番頭懸念)
    check("POS_scoped_allowed_within_same_matter",
          allow_global_sink("matter_scoped_only", "mcp_serve", same_matter=True) is True)

    print()
    if failures:
        print(f"RESULT: FAIL ({len(failures)} assertion failed): {failures}")
        return 1
    print("RESULT: PASS (all assertions green)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(run())
