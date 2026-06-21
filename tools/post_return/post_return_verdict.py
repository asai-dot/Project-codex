#!/usr/bin/env python3
"""post-return-verdict — 501 帰り後の GO/CONDITIONAL/NO-GO 判定ハーネス

依存ゼロ (Python 3.9+)。GPT Pro 監査レーンの「帰り便」処理 (alo-gpt-audit) が
回り、ビルド/監査 run (本ツールでは "501" と総称) が `summary.md` と
`metrics.json` を返したら、本ツールが**上から走らせる**チェックリストを実体化する。

設計原則 (alo-gpt-audit と不変):
  - **fail-closed。** 必須メトリクスが欠ける／読めない → その項目は FAIL 扱い。
    判定不能を GO にはしない。
  - **このツールは owner-gated 操作を一切実行しない。** GO になっても DDL 適用・
    backfill・本番 DB 投入はしない。GO 時に出すのは *プラン草案 (draft)* だけで、
    適用は Owner ratify / 所定 T2 ゲートを経る (RUNBOOK §6)。
  - 判定は決定的 (同じ summary.md + metrics.json → 同じ verdict)。

7 ゲート → 12 チェック → verdict:
  G1 接地100%        : (1) grounded==total かつ ungrounded=0  (2) 接地カバレッジ計上が total と整合
  G2 false-merge≈0   : (3) false_merge.rate==0  (4) サンプル数が下限以上 (統計的に≈0 を主張できる)
  G3 provenance二重計上防止 : (5) double_counted=0  (6) distinct_sources が sources を水増ししていない
  G4 決定性          : (7) 再走ハッシュ一致  (8) 再走が実際に2回実行されている (両ハッシュ存在)
  G5 rights          : (9) blocked=0 (権利未クリアなし)  (10) rights 評価カバレッジが items と整合
  G6 work遅延        : (11) actual<=budget かつ SLA 違反なし
  G7 HOLD            : (12) hold.flags が空

verdict 規則:
  NO-GO  : ハードゲート (G1 G2 G3 G4 G5 G7) のいずれかが FAIL
  CONDITIONAL : ハードゲート全通過だが ソフト項目 (G6 work遅延 / サンプル下限 / provenance 注記要) が WARN
  GO     : 12 項目すべて PASS
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

# G2 で「≈0」を統計的に主張するために要求する最低サンプル件数 (既定)。
DEFAULT_MIN_FALSE_MERGE_SAMPLE = 200

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


@dataclass
class Check:
    item: int
    gate: str
    name: str
    status: str          # PASS / WARN / FAIL
    detail: str
    hard: bool           # ハードゲート (FAIL なら即 NO-GO)


@dataclass
class Verdict:
    verdict: str                       # GO / CONDITIONAL / NO-GO
    checks: list = field(default_factory=list)
    reasons: list = field(default_factory=list)   # NO-GO/CONDITIONAL の決定理由

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "summary": {
                "pass": sum(c.status == PASS for c in self.checks),
                "warn": sum(c.status == WARN for c in self.checks),
                "fail": sum(c.status == FAIL for c in self.checks),
                "total": len(self.checks),
            },
            "reasons": self.reasons,
            "checks": [
                {"item": c.item, "gate": c.gate, "name": c.name,
                 "status": c.status, "detail": c.detail, "hard": c.hard}
                for c in self.checks
            ],
        }


def _num(d: dict, *path, default=None):
    """ネストした dict から数値/値を安全に取り出す。欠落は default。"""
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def evaluate(metrics: dict, *, min_sample: int = DEFAULT_MIN_FALSE_MERGE_SAMPLE) -> Verdict:
    """metrics.json を 12 項目で評価して Verdict を返す。fail-closed。"""
    checks: list = []

    def add(item, gate, name, status, detail, hard):
        checks.append(Check(item, gate, name, status, detail, hard))

    # ---- G1 接地100% ----------------------------------------------------
    g_total = _num(metrics, "grounding", "total")
    g_grounded = _num(metrics, "grounding", "grounded")
    g_ungrounded = _num(metrics, "grounding", "ungrounded_ids")
    if g_total is None or g_grounded is None:
        add(1, "G1", "接地率100%", FAIL, "grounding.total/grounded 欠落 (fail-closed)", True)
    elif g_total == 0:
        add(1, "G1", "接地率100%", FAIL, "grounding.total==0 (接地対象が空＝判定不能)", True)
    elif g_grounded == g_total:
        add(1, "G1", "接地率100%", PASS, f"{g_grounded}/{g_total} 接地", True)
    else:
        add(1, "G1", "接地率100%", FAIL, f"{g_grounded}/{g_total} 接地 (未接地 {g_total - g_grounded})", True)

    n_ungrounded = len(g_ungrounded) if isinstance(g_ungrounded, list) else None
    if n_ungrounded is None:
        add(2, "G1", "未接地ID列挙が空", FAIL, "grounding.ungrounded_ids 欠落 (fail-closed)", True)
    elif n_ungrounded == 0:
        add(2, "G1", "未接地ID列挙が空", PASS, "未接地 0 件", True)
    else:
        add(2, "G1", "未接地ID列挙が空", FAIL,
            f"未接地 {n_ungrounded} 件: {g_ungrounded[:5]}{'…' if n_ungrounded > 5 else ''}", True)

    # ---- G2 false-merge≈0 ----------------------------------------------
    fm_rate = _num(metrics, "false_merge", "rate")
    fm_count = _num(metrics, "false_merge", "false_merges")
    fm_sampled = _num(metrics, "false_merge", "sampled")
    if fm_rate is None and fm_count is None:
        add(3, "G2", "false-merge率==0", FAIL, "false_merge.rate/false_merges 欠落 (fail-closed)", True)
    else:
        bad = (fm_rate or 0) > 0 or (fm_count or 0) > 0
        if not bad:
            add(3, "G2", "false-merge率==0", PASS, "false-merge 0 件", True)
        else:
            add(3, "G2", "false-merge率==0", FAIL,
                f"false-merge {fm_count} 件 / rate={fm_rate}", True)

    if fm_sampled is None:
        add(4, "G2", "サンプル数が下限以上", WARN, "false_merge.sampled 欠落 → ≈0 を主張不可", False)
    elif fm_sampled >= min_sample:
        add(4, "G2", "サンプル数が下限以上", PASS, f"サンプル {fm_sampled} >= {min_sample}", False)
    else:
        add(4, "G2", "サンプル数が下限以上", WARN,
            f"サンプル {fm_sampled} < 下限 {min_sample} (≈0 の確信不足)", False)

    # ---- G3 provenance 二重計上防止 ------------------------------------
    dbl = _num(metrics, "provenance", "double_counted_ids")
    p_sources = _num(metrics, "provenance", "sources")
    p_distinct = _num(metrics, "provenance", "distinct_sources")
    n_dbl = len(dbl) if isinstance(dbl, list) else None
    if n_dbl is None:
        add(5, "G3", "二重計上ID列挙が空", FAIL, "provenance.double_counted_ids 欠落 (fail-closed)", True)
    elif n_dbl == 0:
        add(5, "G3", "二重計上ID列挙が空", PASS, "二重計上 0 件", True)
    else:
        add(5, "G3", "二重計上ID列挙が空", FAIL, f"二重計上 {n_dbl} 件: {dbl[:5]}", True)

    if p_sources is None or p_distinct is None:
        add(6, "G3", "distinct/総数の整合", WARN, "provenance.sources/distinct_sources 欠落 → 注記要", False)
    elif p_distinct <= p_sources:
        add(6, "G3", "distinct/総数の整合", PASS, f"distinct {p_distinct} <= sources {p_sources}", False)
    else:
        add(6, "G3", "distinct/総数の整合", WARN,
            f"distinct {p_distinct} > sources {p_sources} (水増し疑い・注記要)", False)

    # ---- G4 決定性 ------------------------------------------------------
    ha = _num(metrics, "determinism", "run_a_hash")
    hb = _num(metrics, "determinism", "run_b_hash")
    if ha is None or hb is None:
        add(7, "G4", "再走ハッシュ一致", FAIL, "determinism.run_a_hash/run_b_hash 欠落 (fail-closed)", True)
        add(8, "G4", "再走が2回実行された", FAIL, "両ハッシュが揃わない＝再走未実施扱い", True)
    else:
        if ha == hb:
            add(7, "G4", "再走ハッシュ一致", PASS, f"hash 一致 ({str(ha)[:12]}…)", True)
        else:
            add(7, "G4", "再走ハッシュ一致", FAIL, f"hash 不一致 ({str(ha)[:8]}… != {str(hb)[:8]}…)", True)
        add(8, "G4", "再走が2回実行された", PASS, "run_a / run_b 両方存在", True)

    # ---- G5 rights ------------------------------------------------------
    r_items = _num(metrics, "rights", "items")
    r_cleared = _num(metrics, "rights", "cleared")
    blocked = _num(metrics, "rights", "blocked_ids")
    n_blocked = len(blocked) if isinstance(blocked, list) else None
    if n_blocked is None:
        add(9, "G5", "権利ブロック0件", FAIL, "rights.blocked_ids 欠落 (fail-closed)", True)
    elif n_blocked == 0:
        add(9, "G5", "権利ブロック0件", PASS, "権利未クリア 0 件", True)
    else:
        add(9, "G5", "権利ブロック0件", FAIL, f"権利未クリア {n_blocked} 件: {blocked[:5]}", True)

    if r_items is None or r_cleared is None:
        add(10, "G5", "権利評価カバレッジ完全", FAIL, "rights.items/cleared 欠落 (fail-closed)", True)
    elif r_items > 0 and r_cleared + (n_blocked or 0) >= r_items:
        add(10, "G5", "権利評価カバレッジ完全", PASS, f"評価 {r_cleared}+{n_blocked or 0} >= items {r_items}", True)
    elif r_items == 0:
        add(10, "G5", "権利評価カバレッジ完全", FAIL, "rights.items==0 (権利対象が空＝判定不能)", True)
    else:
        add(10, "G5", "権利評価カバレッジ完全", FAIL,
            f"評価漏れ: cleared+blocked < items ({r_cleared}+{n_blocked or 0} < {r_items})", True)

    # ---- G6 work遅延 (ソフト) -------------------------------------------
    budget = _num(metrics, "work_delay", "budget_min")
    actual = _num(metrics, "work_delay", "actual_min")
    sla = _num(metrics, "work_delay", "sla_breaches", default=[])
    n_sla = len(sla) if isinstance(sla, list) else 0
    if budget is None or actual is None:
        add(11, "G6", "work遅延が予算内", WARN, "work_delay.budget_min/actual_min 欠落 → 確認要", False)
    elif actual <= budget and n_sla == 0:
        add(11, "G6", "work遅延が予算内", PASS, f"actual {actual}min <= budget {budget}min, SLA違反0", False)
    else:
        add(11, "G6", "work遅延が予算内", WARN,
            f"actual {actual}min vs budget {budget}min / SLA違反 {n_sla} 件", False)

    # ---- G7 HOLD --------------------------------------------------------
    flags = _num(metrics, "hold", "flags", default=None)
    if flags is None:
        add(12, "G7", "HOLDフラグ無し", FAIL, "hold.flags 欠落 (fail-closed: HOLD 不明は止める)", True)
    elif isinstance(flags, list) and len(flags) == 0:
        add(12, "G7", "HOLDフラグ無し", PASS, "HOLD フラグ 0", True)
    else:
        add(12, "G7", "HOLDフラグ無し", FAIL, f"HOLD: {flags}", True)

    # ---- verdict --------------------------------------------------------
    hard_fail = [c for c in checks if c.hard and c.status == FAIL]
    soft_warn = [c for c in checks if c.status == WARN]
    if hard_fail:
        v = Verdict("NO-GO", checks,
                    [f"[item {c.item} {c.gate}] {c.name}: {c.detail}" for c in hard_fail])
    elif soft_warn:
        v = Verdict("CONDITIONAL", checks,
                    [f"[item {c.item} {c.gate}] {c.name}: {c.detail}" for c in soft_warn])
    else:
        v = Verdict("GO", checks, [])
    return v


# ----------------------------------------------------------------------------
# GO 経路: DDL / backfill プラン草案 (適用しない。owner-gated)
# ----------------------------------------------------------------------------
DDL_BACKFILL_DRAFT = """\
# 501 GO → DDL / backfill 計画 (草案 / DRAFT)

> ⚠️ **owner-gated。** 本草案は post-return-verdict が GO を出したことで自動生成された
> *叩き台* に過ぎない。DDL 適用・backfill・本番 DB 投入は **Owner ratify / T2 ゲート**
> を経るまで実行しない (RUNBOOK §6 / APPROVAL_RULE)。本ツールは一切 DB を触らない。

- run_id: {run_id}
- verdict: GO ({passed}/{total} 項目 PASS)
- generated_from: summary.md + metrics.json (決定的判定)

## 1. 前提 (GO の根拠)
- 接地 100% / false-merge 0 / provenance 二重計上なし / 決定性一致 / rights クリア / HOLD なし。
- 上記がメトリクス上で満たされているため、正本化 (accepted/canonical) と Generated Index
  への backfill を **計画してよい段階** に入った (実行はまだ)。

## 2. DDL 草案 (要レビュー)
- [ ] 対象テーブル / カラムを確定 (canonical id, provenance ref, grounding ref, rights flag)。
- [ ] stable_anchor_id の mint 規則を明記 (決定性ハッシュを再利用)。
- [ ] 一意制約: provenance 二重計上を DB レベルでも防ぐ unique 制約。
- [ ] NOT NULL: grounding ref を必須に (接地100%をスキーマで担保)。
- [ ] migration は前方互換 (既存 index を壊さない) で起票。

## 3. backfill 草案 (要レビュー)
- [ ] dry-run backfill (件数・衝突・既存 index との差分を観測、書込なし)。
- [ ] 冪等性: 再実行で二重 insert しない upsert キーを定義。
- [ ] provenance 二重計上ガード: 投入前に distinct_sources を再検証。
- [ ] ロールバック手順 (migration down / 投入分の限定削除キー) を用意。

## 4. owner ratify チェックポイント
- [ ] Owner に 5 行サマリで GO 根拠を提示。
- [ ] T2 ゲート (DD accepted/canonical 昇格) を Owner 承認で通す。
- [ ] 承認後にのみ DDL apply → backfill --apply (本ツール外・別手順)。
"""


def render_plan(run_id: str, v: Verdict) -> str:
    p = sum(c.status == PASS for c in v.checks)
    return DDL_BACKFILL_DRAFT.format(
        run_id=run_id, passed=p, total=len(v.checks),
    )


# ----------------------------------------------------------------------------
# 出力
# ----------------------------------------------------------------------------
def render_report(run_id: str, v: Verdict) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append(f"# post-return-verdict — run {run_id}")
    s = v.to_dict()["summary"]
    lines.append(f"VERDICT: {v.verdict}   (PASS {s['pass']} / WARN {s['warn']} / FAIL {s['fail']} / {s['total']})")
    lines.append("-" * 60)
    for c in v.checks:
        mark = {"PASS": "✓", "WARN": "▲", "FAIL": "✗"}[c.status]
        hard = "H" if c.hard else "s"
        lines.append(f"  {mark} [{c.item:>2}|{c.gate}|{hard}] {c.name}: {c.detail}")
    if v.reasons:
        lines.append("-" * 60)
        head = "NO-GO 理由 (ハードゲート FAIL):" if v.verdict == "NO-GO" else "CONDITIONAL 要対応 (ソフト WARN):"
        lines.append(head)
        for r in v.reasons:
            lines.append(f"  - {r}")
    lines.append("-" * 60)
    if v.verdict == "GO":
        lines.append("→ 次成果物: DDL/backfill 計画草案を出力可 (--emit-plan)。適用は owner-gated。")
    elif v.verdict == "CONDITIONAL":
        lines.append("→ ソフト項目を解消するか、Owner が条件付き許可するまで GO にしない。")
    else:
        lines.append("→ ハードゲート FAIL。再ビルド/再監査して 501 を返し直す。DDL/backfill は起票しない。")
    return "\n".join(lines)


def load_metrics(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(prog="post-return-verdict",
                                 description="501 帰り後 GO/CONDITIONAL/NO-GO 判定")
    ap.add_argument("--metrics", required=True, help="metrics.json のパス")
    ap.add_argument("--summary", help="summary.md のパス (記録用・任意)")
    ap.add_argument("--run-id", default="501", help="run 識別子 (既定: 501)")
    ap.add_argument("--min-sample", type=int, default=DEFAULT_MIN_FALSE_MERGE_SAMPLE,
                    help="false-merge ≈0 を主張する最低サンプル数")
    ap.add_argument("--json", action="store_true", help="JSON で出力")
    ap.add_argument("--emit-plan", action="store_true",
                    help="GO の場合に DDL/backfill 計画草案を stdout へ (適用はしない)")
    args = ap.parse_args(argv)

    try:
        metrics = load_metrics(args.metrics)
    except FileNotFoundError:
        print(f"metrics.json が見つからない: {args.metrics} (fail-closed → NO-GO)", file=sys.stderr)
        print("NO-GO")
        return 2
    except json.JSONDecodeError as e:
        print(f"metrics.json が壊れている: {e} (fail-closed → NO-GO)", file=sys.stderr)
        print("NO-GO")
        return 2

    v = evaluate(metrics, min_sample=args.min_sample)

    if args.emit_plan:
        if v.verdict == "GO":
            print(render_plan(args.run_id, v))
        else:
            print(f"# 計画草案は出さない。verdict={v.verdict} (GO 限定)。", file=sys.stderr)
            print(render_report(args.run_id, v), file=sys.stderr)
        return 0 if v.verdict == "GO" else 1

    if args.json:
        out = v.to_dict()
        out["run_id"] = args.run_id
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(render_report(args.run_id, v))

    # exit code: GO=0, CONDITIONAL=1, NO-GO=2
    return {"GO": 0, "CONDITIONAL": 1, "NO-GO": 2}[v.verdict]


if __name__ == "__main__":
    raise SystemExit(main())
