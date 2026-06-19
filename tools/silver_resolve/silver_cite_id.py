#!/usr/bin/env python3
"""silver-1: 掲載位置文字列 -> source-record 候補リンクの suggestion (read-only dry-run).

WO-SILVER-CITEID-001 の実装. 依存ゼロ (Python 3.9+).
**SILVER-RESOLUTION-KICKOFF v0.1.1 (GPT audit SILVERKICKOFF_ADOPT_AS_PLAN) 整合版.**

監査整合の要点:
  - 出力は machine_suggested_*_unreviewed 等の **未レビュー候補**. strong/accepted/resolved は使わない.
  - 解決先は **source-record URI**(d1hanrei:{id}) であって canonical case ID ではない
    (identity_scope=source_record_crosswalk_not_canonical_case).
  - 非選択 sibling を non_selection_reason 付きで保存 (畳まない).
  - blocker_code: db_unbuilt / index_absent / policy_blocked / insufficient_signal /
    authority_snapshot_missing / source_registry_unratified.
  - authority_snapshot 必須 (gate8). 無ければ全行 blocked_by_policy_or_provenance.
  - 商用本文は出さない. 出すのは ID/hash/正規化キー/短い構造ラベルのみ.

入力 (read-only, 既取得データのみ):
  --lic-edges   lic 解説引用エッジ JSONL (via_journal / by_date)
  --pub-index   hanrei_published_in 索引 JSONL {"hanrei_id","journal","issue","page"}
  --canon-index (任意) court+date 索引 JSONL {"hanrei_id","court","date"}
  --norm-dict   (任意) 誌名正規化辞書 JSON. 雑誌レーン ALIAS+journal_issn_map から生成 (再発明禁止)
  --authority-snapshot (必須) authority_snapshot_manifest JSON
                  {"authority_dataset_version","authority_hash","rule_version",...}

出力 (candidate のみ. 本番 write なし):
  <out>/silver_cite_resolution_candidates.jsonl
  <out>/silver_cite_resolution_report.md

tier (kickoff v0.1.1 §6):
  A machine_suggested_source_record_match_unreviewed          (正規化 誌+号+頁 exact・単一)
  B machine_suggested_source_record_match_high_density_qa_required (誌名alias経由の exact 等・要高密度QA)
  C needs_human_review                                        (号レベル一意 / 頁欠だが court+date 手掛り)
  D ambiguous_or_unresolved                                   (多候補・衝突・index無)
  X blocked_by_policy_or_provenance                           (authority欠/ポリシー/provenance)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

_FW_DIGITS = {ord("０") + i: ord("0") + i for i in range(10)}
IDENTITY_SCOPE = "source_record_crosswalk_not_canonical_case"
SOURCE_RECORD_PREFIX = "d1hanrei:"

# tier status 語彙 (kickoff v0.1.1 §6)
ST_A = "machine_suggested_source_record_match_unreviewed"
ST_B = "machine_suggested_source_record_match_high_density_qa_required"
ST_C = "needs_human_review"
ST_D = "ambiguous_or_unresolved"
ST_X = "blocked_by_policy_or_provenance"


def read_jsonl(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def remap_records(records: Iterable[dict], field_map: Optional[Dict[str, str]]) -> Iterable[dict]:
    """実データのフィールド名を期待スキーマへ写像. field_map = {expected_key: actual_key}."""
    if not field_map:
        yield from records
        return
    for r in records:
        for expected, actual in field_map.items():
            if expected not in r and actual in r:
                r[expected] = r[actual]
        yield r


def normalize_journal(raw: str, norm_dict: Optional[Dict[str, str]] = None) -> str:
    if raw is None:
        return ""
    s = raw.translate(_FW_DIGITS).replace("　", "").replace(" ", "").strip()
    if norm_dict and s in norm_dict:
        return norm_dict[s]
    return s


def parse_locator(locator: str) -> Optional[Tuple[str, str, str]]:
    """'journal_article:労働判例:1060:5' -> (journal, issue, page). 解析不能は None."""
    if not locator:
        return None
    parts = locator.split(":")
    if parts and parts[0] == "journal_article":
        parts = parts[1:]
    if len(parts) < 3:
        return None
    journal, issue, page = parts[0], parts[1], parts[2]
    if not journal or not issue:
        return None
    return journal, issue, page


def _src_uri(hid: str) -> str:
    return f"{SOURCE_RECORD_PREFIX}{hid}"


def _sha(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()[:16]


def build_pub_indexes(pub_records: Iterable[dict], norm_dict: Optional[Dict[str, str]]):
    by_jip: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
    by_ji: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for r in pub_records:
        hid = str(r.get("hanrei_id", ""))
        if not hid:
            continue
        j = normalize_journal(r.get("journal", ""), norm_dict)
        issue = str(r.get("issue", "")).translate(_FW_DIGITS)
        page = str(r.get("page", "")).translate(_FW_DIGITS)
        by_jip[(j, issue, page)].append(hid)
        by_ji[(j, issue)].append(hid)
    return by_jip, by_ji


def build_canon_index(canon_records: Iterable[dict]):
    by_cd: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for r in canon_records:
        hid = str(r.get("hanrei_id", ""))
        if not hid:
            continue
        by_cd[(str(r.get("court", "")).strip(), str(r.get("date", "")).strip())].append(hid)
    return by_cd


def _base(edge: dict, authority: Optional[dict]) -> dict:
    return {
        "lic_edge_id": edge.get("edge_id", ""),
        "edge_type": edge.get("edge_type", ""),
        "source_ref_hash": None,
        "normalized_position_key": None,
        "target_source_record_uri": [],          # source record, NOT canonical case
        "identity_scope": IDENTITY_SCOPE,
        "match_basis": None,
        "score": 0.0,
        "sibling_count": 0,
        "non_selection_reason": None,
        "suggestion_status": None,
        "blocker_code": None,
        "evidence_tier": None,
        "authority_dataset_version": (authority or {}).get("authority_dataset_version"),
        "authority_hash": (authority or {}).get("authority_hash"),
    }


def resolve_edge(edge: dict, by_jip, by_ji, by_cd, norm_dict, authority: Optional[dict] = None) -> dict:
    """1 エッジを source-record 候補へ. authority 無ければ blocked (gate8)."""
    c = _base(edge, authority)
    if authority is None:
        c.update(suggestion_status=ST_X, evidence_tier="X", blocker_code="authority_snapshot_missing")
        return c

    etype = edge.get("edge_type", "")
    if etype == "cites_judgment_via_journal":
        locator = edge.get("source_locator", "")
        c["source_ref_hash"] = _sha(locator)
        parsed = parse_locator(locator)
        if parsed is None:
            c.update(suggestion_status=ST_D, evidence_tier="D", blocker_code="insufficient_signal")
            return c
        journal, issue, page = parsed
        nj = normalize_journal(journal, norm_dict)
        page = str(page).translate(_FW_DIGITS)
        c["normalized_position_key"] = f"jp:{nj}#{issue}#{page}"
        alias_applied = (nj != journal)
        hits = by_jip.get((nj, issue, page), [])
        if len(hits) == 1:
            tier_b = alias_applied  # 誌名alias経由の exact は高密度QA対象 (kickoff §6 B)
            c.update(target_source_record_uri=[_src_uri(hits[0])], sibling_count=1,
                     match_basis="normalized_journal_issue_page_exact_alias" if alias_applied
                     else "normalized_journal_issue_page_exact",
                     score=0.90 if tier_b else 0.95,
                     suggestion_status=ST_B if tier_b else ST_A,
                     evidence_tier="B" if tier_b else "A")
            return c
        if len(hits) > 1:  # 同頁多候補 = 衝突 -> ambiguous, siblings 全保存
            c.update(target_source_record_uri=[_src_uri(h) for h in sorted(set(hits))],
                     sibling_count=len(set(hits)), match_basis="issue_page_collision",
                     score=0.60, suggestion_status=ST_D, evidence_tier="D",
                     non_selection_reason="multiple_targets_same_issue_page")
            return c
        fb = by_ji.get((nj, issue), [])
        if len(fb) == 1:  # 号レベル一意 (頁欠/不一致) -> needs_human_review
            c.update(target_source_record_uri=[_src_uri(fb[0])], sibling_count=1,
                     match_basis="issue_level_unique_page_lost", score=0.50,
                     suggestion_status=ST_C, evidence_tier="C")
            return c
        if len(fb) > 1:
            c.update(target_source_record_uri=[_src_uri(h) for h in sorted(set(fb))],
                     sibling_count=len(set(fb)), match_basis="issue_level_multi", score=0.40,
                     suggestion_status=ST_D, evidence_tier="D",
                     non_selection_reason="multiple_targets_same_issue")
            return c
        c.update(suggestion_status=ST_D, evidence_tier="D", blocker_code="index_absent")
        return c

    if etype == "cites_judgment_by_date":
        court = str(edge.get("court", "")).strip()
        date = str(edge.get("date", "")).strip()
        c["source_ref_hash"] = _sha(f"{court}/{date}")
        c["normalized_position_key"] = f"cd:{court}#{date}"
        hits = by_cd.get((court, date), [])
        if len(hits) == 1:  # court+date 手掛りは強いが頁なし -> needs_human_review (auto選択しない)
            c.update(target_source_record_uri=[_src_uri(hits[0])], sibling_count=1,
                     match_basis="court_date_unique", score=0.60,
                     suggestion_status=ST_C, evidence_tier="C")
            return c
        if len(hits) > 1:
            c.update(target_source_record_uri=[_src_uri(h) for h in sorted(set(hits))],
                     sibling_count=len(set(hits)), match_basis="court_date_multi", score=0.45,
                     suggestion_status=ST_D, evidence_tier="D",
                     non_selection_reason="multiple_targets_same_court_date")
            return c
        c.update(suggestion_status=ST_D, evidence_tier="D", blocker_code="index_absent")
        return c

    c.update(suggestion_status=ST_X, evidence_tier="X", blocker_code="policy_blocked")
    return c


def resolve_all(edges, by_jip, by_ji, by_cd, norm_dict, authority: Optional[dict] = None) -> List[dict]:
    return [resolve_edge(e, by_jip, by_ji, by_cd, norm_dict, authority) for e in edges]


def build_report(cands: List[dict], authority: Optional[dict]) -> str:
    total = len(cands)
    by_tier = Counter(c["evidence_tier"] or "(none)" for c in cands)
    by_status = Counter(c["suggestion_status"] for c in cands)
    blockers = Counter(c["blocker_code"] for c in cands if c["blocker_code"])
    suggested = by_status.get(ST_A, 0) + by_status.get(ST_B, 0)
    rate = (suggested / total * 100) if total else 0.0
    av = (authority or {}).get("authority_dataset_version", "MISSING")
    lines = [
        "# silver-1 掲載位置→source-record 候補レポート (dry-run / read-only)",
        "",
        "> SILVER-RESOLUTION-KICKOFF v0.1.1 整合. 出力は未レビュー候補. reviewed/canonical 化なし.",
        f"> authority_dataset_version: {av}",
        "",
        f"- 入力エッジ総数: **{total}**",
        f"- machine_suggested (tier A+B, 未レビュー): **{suggested}** ({rate:.1f}%)  ※基準 概算24%",
        f"  - A 単一exact: **{by_status.get(ST_A, 0)}** / B alias要高密度QA: **{by_status.get(ST_B, 0)}**",
        f"- needs_human_review (C): **{by_status.get(ST_C, 0)}**",
        f"- ambiguous_or_unresolved (D): **{by_status.get(ST_D, 0)}**",
        f"- blocked_by_policy_or_provenance (X): **{by_status.get(ST_X, 0)}**",
        "",
        "## evidence_tier 別",
        "| tier | 件数 |",
        "|---|---|",
    ]
    for t in ["A", "B", "C", "D", "X"]:
        if by_tier.get(t):
            lines.append(f"| {t} | {by_tier[t]} |")
    lines += ["", "## blocker_code", "| code | 件数 |", "|---|---|"]
    for r, n in blockers.most_common():
        lines.append(f"| {r} | {n} |")
    lines += [
        "",
        "## 監査整合の確認",
        "- 解決先は source-record URI (d1hanrei:) = canonical case ではない (identity_scope).",
        "- tier A/B も未レビュー候補. reviewed=true / claim_support / alo_edges に昇格しない.",
        "- 非選択 sibling は target に保存し non_selection_reason 付与 (畳まない).",
        "- authority_snapshot 無しは全行 blocked (gate8).",
        "",
        "_dry-run. candidate staging 出力のみ. 本番 write なし. 商用本文は出力しない._",
    ]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="silver-1 掲載位置→source-record 候補 (read-only dry-run)")
    ap.add_argument("--lic-edges", required=True, type=Path)
    ap.add_argument("--pub-index", required=True, type=Path)
    ap.add_argument("--canon-index", type=Path, default=None)
    ap.add_argument("--norm-dict", type=Path, default=None)
    ap.add_argument("--authority-snapshot", type=Path, default=None,
                    help="authority_snapshot_manifest JSON (gate8: 無いと全行 blocked)")
    ap.add_argument("--field-map", type=Path, default=None)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    norm_dict = json.loads(args.norm_dict.read_text(encoding="utf-8")) if args.norm_dict else None
    fmap = json.loads(args.field_map.read_text(encoding="utf-8")) if args.field_map else None
    authority = json.loads(args.authority_snapshot.read_text(encoding="utf-8")) if args.authority_snapshot else None
    by_jip, by_ji = build_pub_indexes(remap_records(read_jsonl(args.pub_index), fmap), norm_dict)
    by_cd = build_canon_index(remap_records(read_jsonl(args.canon_index), fmap)) if args.canon_index else {}
    cands = resolve_all(remap_records(read_jsonl(args.lic_edges), fmap), by_jip, by_ji, by_cd, norm_dict, authority)

    args.out.mkdir(parents=True, exist_ok=True)
    cpath = args.out / "silver_cite_resolution_candidates.jsonl"
    with cpath.open("w", encoding="utf-8") as fh:
        for c in cands:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    rpath = args.out / "silver_cite_resolution_report.md"
    rpath.write_text(build_report(cands, authority), encoding="utf-8")
    if authority is None:
        print("[silver-1] WARNING: --authority-snapshot 無し -> 全行 blocked (gate8)")
    print(f"[silver-1] candidates={len(cands)} -> {cpath}")
    print(f"[silver-1] report -> {rpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
