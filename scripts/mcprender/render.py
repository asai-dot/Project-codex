"""Render resolved assertions + disputes into safe MCP payloads.

Two outputs per provision target:
- a structured `provision_view` dict (for MCP/JSON consumers), and
- a `markdown` block (for human/LLM display), both-sides, hedged.

The renderer is pure formatting over already-safe assembler output; it adds NO
new judgement. It refuses to emit an assertive sentence: every substantive line
is attributed and qualified.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from . import RENDERER_VERSION

# Japanese labels for source tiers / types (display only)
SOURCE_LABEL = {
    "official_legal_data": "公式法令データ",
    "legislative_drafter": "立案担当者解説",
    "ministry_commentary": "所管庁解説",
    "legislative_record": "国会審議",
    "court": "裁判例",
    "scholar": "学説",
    "treatise": "体系書",
    "practitioner": "実務書",
    "alo_internal": "ALO実務観測",
}
STANCE_LABEL = {
    "continues": "意味は継続（変更なし）",
    "changed": "意味が変わった",
    "qualified": "限定・部分的変更",
    "neutral": "中立的言及",
    "disputed": "係争（出典自体が対立を報告）",
    "unknown": "未確認",
}
VALUE_LABEL = {
    "no_substantive_change": "実質変更なし",
    "wording_clarification": "文言の明確化",
    "scope_expansion": "適用範囲の拡大",
    "scope_reduction": "適用範囲の縮小",
    "requirement_added": "要件の追加",
    "requirement_removed": "要件の削除",
    "requirement_changed": "要件の変更",
    "effect_changed": "効果の変更",
    "subject_changed": "主体の変更",
    "procedure_changed": "手続の変更",
    "efficacy_change": "効力の変動",
    "substantive_change_unspecified": "実質変更あり（類型未特定）",
    "interpretation_continues": "旧解釈は継続",
    "interpretation_discontinued": "旧解釈は不継続",
    "interpretation_modified": "解釈の修正",
    "interpretation_newly_established": "新たな解釈の確立",
    "followed": "踏襲", "applied": "適用", "approved": "是認",
    "relied_upon": "依拠", "distinguished": "区別", "limited": "限定",
    "questioned": "疑問視", "criticized": "批判", "called_into_doubt": "疑義",
    "overruled": "判例変更", "abrogated": "廃棄", "disapproved": "否認",
    "superseded_by_statute": "立法により前提喪失",
    "disputed": "係争", "unknown": "未確認",
}


def _src(a: dict) -> str:
    lab = SOURCE_LABEL.get(a["asserted_by_source_type"], a["asserted_by_source_type"])
    return f"{lab}(T{a['source_tier']})"


def _claim_word(a: dict) -> str:
    # claim_support_eligible is the ONLY thing that licenses relied-upon framing
    return "参考提示可" if a.get("claim_support_eligible") else "参考（要確認・断定不可）"


def render_provision(target_key: str, members: List[dict],
                     dispute: Optional[dict],
                     formal_note: Optional[str] = None) -> dict:
    """Build a structured, safe provision view."""
    is_disputed = dispute is not None
    claims = []
    for a in sorted(members, key=lambda x: (x["source_tier"], x["assertion_key"])):
        claims.append({
            "source": _src(a),
            "source_type": a["asserted_by_source_type"],
            "tier": a["source_tier"],
            "value": a["value"],
            "value_label": VALUE_LABEL.get(a["value"], a["value"]),
            "stance": a["stance"],
            "stance_label": STANCE_LABEL.get(a["stance"], a["stance"]),
            "confidence": a.get("confidence"),
            "status": a["current_status"],
            "evidence_key": a.get("evidence_key"),
            "usage": _claim_word(a),
        })
    return {
        "target": target_key,
        "formal_note": formal_note,            # DD-LAWTIME fact, may be stated plainly
        "disposition": "disputed" if is_disputed else "candidate",
        "both_sides_required": is_disputed,
        "claims": claims,
        "dispute_basis": dispute["basis"] if dispute else None,
        "safe_summary": _safe_summary(target_key, claims, is_disputed, formal_note),
        "renderer_version": RENDERER_VERSION,
        # hard invariant surfaced to consumers:
        "assertive_output_allowed": False,
    }


def _safe_summary(target_key, claims, is_disputed, formal_note) -> str:
    """One hedged sentence. Never asserts a substantive conclusion."""
    head = formal_note + " " if formal_note else ""
    if not claims:
        return head + f"{target_key} について実質的変更に関する出典付き主張は未収集です。"
    if is_disputed:
        return (head + f"{target_key} の実質的意味については出典間で評価が分かれています"
                "（下記の両論を参照。いずれも断定はできません）。")
    # non-disputed: still candidates, not a verdict
    vals = "／".join(sorted({c["value_label"] for c in claims}))
    return (head + f"{target_key} について、出典は「{vals}」と述べています"
            "（出典付き候補。確定見解ではありません）。")


def render_markdown(view: dict) -> str:
    lines = [f"### {view['target']}"]
    if view.get("formal_note"):
        lines.append(f"- 形式（DD-LAWTIME）: {view['formal_note']}")
    lines.append(f"- 実質評価の扱い: **{'両論併記（係争）' if view['both_sides_required'] else '出典付き候補'}** "
                 f"／ 断定不可")
    lines.append(f"- 要約: {view['safe_summary']}")
    if view["claims"]:
        lines.append("")
        lines.append("| 出典 | 評価 | stance | 確度 | 状態 | 利用 | 証拠 |")
        lines.append("|---|---|---|---|---|---|---|")
        for c in view["claims"]:
            ev = c["evidence_key"][:10] + "…" if c.get("evidence_key") else "—"
            lines.append(f"| {c['source']} | {c['value_label']} | {c['stance_label']} "
                         f"| {c['confidence'] or '—'} | {c['status']} | {c['usage']} | {ev} |")
    if view["dispute_basis"]:
        lines.append("")
        lines.append(f"> 係争の根拠: `{view['dispute_basis']}`")
    return "\n".join(lines)


def render_all(resolved: List[dict], disputes: List[dict],
               formal_notes: Optional[Dict[str, str]] = None) -> List[dict]:
    formal_notes = formal_notes or {}
    disp_by_target = {d["target_key"]: d for d in disputes}
    by_target: Dict[str, List[dict]] = {}
    for r in resolved:
        by_target.setdefault(r["target_key"], []).append(r)
    out = []
    for target in sorted(by_target):
        view = render_provision(target, by_target[target],
                                disp_by_target.get(target),
                                formal_notes.get(target))
        view["markdown"] = render_markdown(view)
        out.append(view)
    return out
