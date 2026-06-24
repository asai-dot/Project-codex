#!/usr/bin/env python3
"""case_vocab.py — 判例オブジェクトの *唯一の正本語彙* (統一性アンカー)。

時系列で別々に書いた DD/実装の語彙ドリフトを防ぐため、横断 enum をここに一元化する。
各モジュールは本書を import し、独自定義しない。整合は test_case_consistency.py が検査。

参照: DD-CASE-001(case_type/3軸) / DD-CASEID-002(forum_level/符号) /
      DD-CASEID-003(forum_type) / DDCASESOURCE(confidentiality/redistribution) /
      DD-CASEID-001(Tier) / DD-CASECITE(egress sinks)。
"""

# --- A3 出口(DDCASESOURCE 一次所有) ---
CONFIDENTIALITY_CLASSES = frozenset({
    "open", "matter_scoped_only", "matter_confirmed", "lawyer_client_confidential",
})
REDISTRIBUTION_CLASSES = frozenset({"public", "commercial_licensed", "restricted"})
# 出口5点シンク (RP-02)。global egress の検査対象
EGRESS_SINKS = ("global_content_index", "embedding", "mcp_serve", "export", "claim_support")

# --- A1 同一性: forum 種別(DD-CASEID-003 = granular 7値が正準) ---
FORUM_TYPES = frozenset({
    "court", "administrative_tribunal", "administrative_review",
    "agency", "adr", "arbitration", "other",
})

# --- A1 判断類型(DD-CASE-001 §2 が唯一定義。forum_type とは別軸・1:1束縛しない N-2) ---
CASE_TYPES = frozenset({
    "judicial", "adjudication", "administrative_review", "advisory", "adr", "conciliation",
})
# 参考: forum_type → ありうる case_type (非拘束ヒント。多対多)。
FORUM_TYPE_CASE_HINT = {
    "court": {"judicial", "conciliation", "adjudication"},
    "administrative_tribunal": {"adjudication", "administrative_review"},
    "administrative_review": {"administrative_review"},
    "agency": {"advisory", "administrative_review"},
    "adr": {"adr", "conciliation"},
    "arbitration": {"adr"},
    "other": set(CASE_TYPES),
}

# --- 符号の forum_level(DD-CASEID-002 semantics。裁判所階層。forum_type とは別概念) ---
FORUM_LEVELS = frozenset({
    "district", "summary", "high", "supreme", "family", "daishin_in",
})

# --- 名寄せ Tier(DD-CASEID-001 / DD-CASEBIND)。prov を含む完全集合 ---
BIND_TIERS = frozenset({"A", "B", "C", "prov"})
# Tier 別 precision 目標(prov は監査対象外=None)。DD-CASEREVIEW
TIER_PRECISION_TARGET = {"A": 0.99, "B": 0.95, "C": 0.90, "prov": None}
# Tier のリスク順(高いほど高リスク)。eval の per-tier 集約に使用
TIER_RISK = {"A": 0, "B": 1, "C": 2, "prov": 3}

# --- 登録 source_system(source registry seed 31 + 判例DB NII)。corroborate/gold が使う ---
# 判例DB(identity 補強に使える源)。L1 corroboration の母集合
CASELAW_SOURCES = frozenset({
    "D1-Law", "NII", "saikousai-hp", "saikousai-db", "hanrei-times", "hanrei-hisho",
    "lexdb-tkc", "westlaw-japan", "kakyu-saibansho-hp", "chizai-kosai-hp",
})
# 確定登録済 source(seed 31)。proposed_addition は確定後にここへ
REGISTERED_SOURCES = frozenset(CASELAW_SOURCES | {
    "LIC", "opac-cinii", "manual", "jufu",
    "kokuzei-fufuku-shinpan", "churoi", "jftc", "gyofuku-shinsakai", "roho-shinsakai",
    "shaho-shinsakai", "kochoi", "kainan-shinpan", "sesc", "finmac", "zenginkyo-adr",
    "nichibenren-adr", "jsaa", "jp-drp", "kokusen-hanrei", "kokusen-adr", "pmda-kyufu",
    "bpo", "retio", "denki-tsushin-funso", "soumu-johokokai-toshin", "zaiya-seihodb",
})

# --- リンク層(35_link_layer 正典のミラー)。DD-CASELINK が alo_edges へ供給する語彙 ---
# edge_type: 35_link_layer §2.2 が CHECK 強制する 10値(正典)。本 repo はこれを増やさない。
LINK_EDGE_TYPES = frozenset({
    "cites", "applies", "excludes", "relative_resolved", "crosslaw",
    "interprets", "compares", "evaluates", "doctrine", "review_chain",
})
# commentary→case で使える部分集合(評釈→判例)。DD-CASELINK はこの3つのみ emit
COMMENTARY_TO_CASE_EDGE_TYPES = frozenset({"evaluates", "review_chain", "compares"})
# assertion_mode: §2.3 の4値。llm_inferred は PoC で DB制約により投入禁止
ASSERTION_MODES = frozenset({"vendor_explicit", "vendor_implicit", "human", "llm_inferred"})
ASSERTION_MODES_POC_ALLOWED = frozenset({"vendor_explicit", "vendor_implicit", "human"})
# stance: DD-CASELINK 提案の新 qualifier(同旨/反対の保存)。正典 §2 への列追加は DDCASE 監査通過後
LINK_STANCES = frozenset({"supporting", "contrasting", "neutral"})
# alo_edge_evidence.role(§3。根拠なし edge 禁止=Gate-5)
EDGE_EVIDENCE_ROLES = frozenset({"support", "quote", "source_field"})
# link 精度目標(DD-CASEEVAL 拡張)。evaluates(評釈対象)は誤リンクが最も有害=最高精度
LINK_PRECISION_TARGET = {"evaluates": 0.97, "review_chain": 0.97, "compares": 0.90}
LINK_STANCE_ACCURACY_TARGET = 0.85  # 同旨/反対 の付け間違い許容度


# --- redistribution=public のみ global index 可(AC-3)。商用/有償は false ---
def can_global_index(confidentiality_class: str, redistribution: str, source: str = "") -> bool:
    if source == "jufu":
        return False
    return confidentiality_class == "open" and redistribution == "public"
