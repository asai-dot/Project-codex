#!/usr/bin/env python3
"""case_review_packet.py — 人手レビュー第一バッチ(Q1法令参照)の worksheet 生成＋集計 (L-RV / S5)。

CASE_HUMAN_REVIEW_SAMPLE_FRAME(caserev_q1_v0) を実データに接続する配管。
- build_worksheet: Q1候補(JSONL)を frozen frame で層化抽出 → 負例control注入 →
  reviewer 記入用 worksheet 行(正規化キー＋expected_check のみ。**raw本文を出さない**)。
- tally: 記入済 worksheet → stratum別 decision分布・negative control 健全性・false-positive。
**read-only・決定的(seed)。canonical/DB/alo_edges 反映なし(HOLD)。** 検証 test_case_review_packet.py。

候補 record(Mac CC 供給, 最小):
  {"ref_id","law_name","article","d1kos_node","article_side_root","taxonomy_root",
   "flags":[...]}  # flags: p1_top_root_aligned/cross_root/multi_law_token/suffix/provisional_kos
"""
from __future__ import annotations
import csv
import random
from collections import defaultdict

FRAME_VERSION = "caserev_q1_v0_20260618"
SEED = 20260618

# 決定語彙(frame §1)。pending 以外には decision_actor 必須(§4-3)
DECISION_VOCAB = ("pending_review", "accept_d1kos_statute_ref_context",
                  "reject_not_same_statute_context", "needs_more_evidence", "defer")
# 表示する正規化キーのみ(商用本文は出さない)
DISPLAY_KEYS = ["law_name", "article", "d1kos_node", "article_side_root", "taxonomy_root"]
# 層化枠(frame §3)。all=母数全件 / n=抽出数
STRATA = [
    {"key": "S-A", "flag": "p1_top_root_aligned", "all": True, "desc": "P1 top-root-aligned(最高信頼)"},
    {"key": "S-C", "flag": "multi_law_token", "all": True, "desc": "複数法令名混在(パース誤り)"},
    {"key": "S-D", "flag": "suffix", "all": True, "desc": "suffix寄せ(金商法→商法 等)"},
    {"key": "S-B", "flag": "cross_root", "n": 10, "desc": "cross_root(分類文脈の過剰接続)"},
    {"key": "S-E", "flag": "provisional_kos", "n": 10, "desc": "暫定KOSノード接続"},
]
NOTE_REQUIRED = {"S-B", "S-C", "S-D"}   # accept に review_note 必須
N_NEGATIVE_CONTROL = 8


def derive_stratum(cand: dict) -> str:
    """flags から層を決定(優先順: 誤りやすい層を先取り。最後に S-A)。"""
    f = set(cand.get("flags", []))
    for st in ("S-C", "S-D", "S-B", "S-E"):   # multi/suffix/cross_root/provisional 優先
        flag = next(s["flag"] for s in STRATA if s["key"] == st)
        if flag in f:
            return st
    return "S-A" if "p1_top_root_aligned" in f else "S-OTHER"


def _expected_check(cand: dict, st: str) -> str:
    return {
        "S-A": "法令名×条 が D1KOS分類ノードの主題と一致するか(top-root整合)",
        "S-B": "taxonomy_root ≠ 法令 でも article側が支持しているか(過剰接続でないか)",
        "S-C": f"混在法令名のどれが正しい参照か({cand.get('law_name','')})",
        "S-D": f"suffix一致が別法令でないか({cand.get('law_name','')} が長い名称の一部でないか)",
        "S-E": "暫定KOSノードへの接続が妥当か(確定ノードに置換すべきでないか)",
    }.get(st, "正規化キー一致を目視")


def build_worksheet(candidates: list[dict]) -> list[dict]:
    """frozen frame で層化抽出＋負例注入 → worksheet 行(decision 空欄)。"""
    rng = random.Random(SEED)
    by_st = defaultdict(list)
    for c in candidates:
        by_st[derive_stratum(c)].append(c)

    rows: list[dict] = []
    for spec in STRATA:
        st = spec["key"]
        items = sorted(by_st.get(st, []), key=lambda x: x["ref_id"])
        if spec.get("all"):
            picked = items
        else:
            picked = items if len(items) <= spec["n"] else rng.sample(items, spec["n"])
        for c in sorted(picked, key=lambda x: x["ref_id"]):
            rows.append(_row(c, st, is_neg=False))

    # 負例control: 別root候補の d1kos を貼り替え、確実に reject になる組を N 件
    pool = [c for c in candidates if "cross_root" not in c.get("flags", [])]
    pool_sorted = sorted(pool, key=lambda x: x["ref_id"])
    if len(pool_sorted) >= 2:
        for i in range(min(N_NEGATIVE_CONTROL, len(pool_sorted))):
            base = dict(pool_sorted[i])
            donor = pool_sorted[(i + len(pool_sorted) // 2) % len(pool_sorted)]
            if donor.get("taxonomy_root") == base.get("taxonomy_root"):
                donor = pool_sorted[(i + 1) % len(pool_sorted)]
            base["d1kos_node"] = donor.get("d1kos_node", "")
            base["taxonomy_root"] = donor.get("taxonomy_root", "")
            base["ref_id"] = f"NEG-{base['ref_id']}"
            rows.append(_row(base, "S-NEG", is_neg=True))
    return rows


def _row(c: dict, st: str, is_neg: bool) -> dict:
    row = {"ref_id": c["ref_id"], "stratum": st,
           "is_negative_control": "1" if is_neg else "0",
           "frame_version": FRAME_VERSION}
    for k in DISPLAY_KEYS:
        row[k] = c.get(k, "")
    row["expected_manual_check"] = _expected_check(c, st)
    row["note_required_on_accept"] = "1" if st in NOTE_REQUIRED else "0"
    # 記入欄(reviewer)
    row["decision"] = ""          # DECISION_VOCAB のいずれか
    row["reason_code"] = ""       # reject 時必須
    row["review_note"] = ""       # note_required 層の accept で必須
    row["decision_actor"] = ""    # pending 以外で必須
    return row


WORKSHEET_COLUMNS = (["ref_id", "stratum", "is_negative_control", "frame_version"]
                     + DISPLAY_KEYS + ["expected_manual_check", "note_required_on_accept",
                                       "decision", "reason_code", "review_note", "decision_actor"])


def write_worksheet_csv(rows: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=WORKSHEET_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def read_worksheet_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def tally(filled: list[dict]) -> dict:
    """記入済 worksheet → stratum別 decision分布・負例健全性・記入不備の検出。"""
    by_st = defaultdict(lambda: defaultdict(int))
    issues = []
    neg_total = neg_reject = 0
    for r in filled:
        st = r.get("stratum", "?")
        d = (r.get("decision") or "").strip()
        if d and d not in DECISION_VOCAB:
            issues.append(f"{r.get('ref_id')}: 語彙外 decision={d}")
            continue
        by_st[st][d or "pending_review"] += 1
        # validator: pending 以外は decision_actor 必須
        if d and d != "pending_review" and not (r.get("decision_actor") or "").strip():
            issues.append(f"{r.get('ref_id')}: decision_actor 欠落")
        # reject は reason_code 必須
        if d == "reject_not_same_statute_context" and not (r.get("reason_code") or "").strip():
            issues.append(f"{r.get('ref_id')}: reason_code 欠落")
        # note_required 層の accept は review_note 必須
        if d == "accept_d1kos_statute_ref_context" and r.get("note_required_on_accept") == "1" \
           and not (r.get("review_note") or "").strip():
            issues.append(f"{r.get('ref_id')}: review_note 欠落(note必須層)")
        # 負例control: accept が出たら過剰検出バグ
        if r.get("is_negative_control") == "1":
            neg_total += 1
            if d == "reject_not_same_statute_context":
                neg_reject += 1
            elif d == "accept_d1kos_statute_ref_context":
                issues.append(f"{r.get('ref_id')}: ★負例controlにaccept=過剰検出バグ")

    def fp_rate(st_counts):
        acc = st_counts.get("accept_d1kos_statute_ref_context", 0)
        rej = st_counts.get("reject_not_same_statute_context", 0)
        dec = acc + rej
        return round(rej / dec, 4) if dec else None   # この支持文脈では reject=偽陽性扱い候補

    decided = sum(v for st in by_st for k, v in by_st[st].items() if k != "pending_review")
    return {
        "frame_version": FRAME_VERSION,
        "by_stratum": {st: dict(c) for st, c in sorted(by_st.items())},
        "stratum_reject_share": {st: fp_rate(c) for st, c in sorted(by_st.items())},
        "decisions_made": decided,           # ← これが 0→N の証拠
        "negative_control": {"total": neg_total, "rejected": neg_reject,
                             "healthy": neg_total > 0 and neg_reject == neg_total},
        "issues": issues,
        "ok": not issues,
    }


def _load_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [__import__("json").loads(l) for l in f if l.strip()]


if __name__ == "__main__":
    import json
    import sys
    args = sys.argv[1:]
    if len(args) >= 3 and args[0] == "build":
        rows = build_worksheet(_load_jsonl(args[1]))
        write_worksheet_csv(rows, args[2])
        st = defaultdict(int)
        for r in rows:
            st[r["stratum"]] += 1
        print(f"# worksheet 生成: {args[2]}  ({len(rows)}行)  frame={FRAME_VERSION}")
        print("# stratum別:", dict(sorted(st.items())))
        print("# reviewer は decision/reason_code/review_note/decision_actor を記入 → tally で集計")
    elif len(args) >= 2 and args[0] == "tally":
        print(json.dumps(tally(read_worksheet_csv(args[1])), ensure_ascii=False, indent=2))
    else:
        print("usage:\n  case_review_packet.py build <candidates.jsonl> <worksheet.csv>\n"
              "  case_review_packet.py tally <filled_worksheet.csv>")
        sys.exit(2)
