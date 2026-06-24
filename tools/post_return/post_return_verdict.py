#!/usr/bin/env python3
"""post-return-verdict — 属性観測層 501 dry-run 帰り後の GO/CONDITIONAL/NO-GO 判定

対象 run "501" = 「属性観測層 501 report-only dry-run」(DD-LITID-001-ATTR)。
Mac CC ワーカーが Box `_claude_dispatch/from_worker/attr_layer_501_dryrun_20260615/`
へ summary.md / metrics.json / attr_observations_sim.jsonl / attr_canonical_sim.jsonl
/ disputed_after_triage.csv を返したら、本ツールが**上から走らせる**チェックリスト。

メトリクス契約は WO `WO_attrlayer501_dryrun_20260615_1740.md` §4-§5 と L1 self-verify
に準拠 (当て推量ではなく実 WO 由来):
  metrics.json:
    adopted_value_coverage / single_authority_rate /
    disputed_rate_after_triage (+ raw_disagreement_rate 対比) /
    rights_blocked_rate / ungrounded_value_count (=0 であるべき) /
    provenance_collapse_count
  L1 self-verify (summary.md / evidence で証跡):
    501処理(欠損/重複列挙) / ungrounded=0 / 2回流して出力hash一致(決定性) /
    classification が scheme併存・multi で潰れていない /
    provenance_family畳みが効いている(弁コム×legallib 同一familyを独立計上しない) /
    biblio・DBに一切書いていない(書込ゼロ証跡) / access系が書誌合議に混入していない

設計原則:
  - **fail-closed。** 必須メトリクス/証跡が欠けたら FAIL。判定不能を GO にしない。
  - **owner-gated を一切実行しない。** GO でも biblio/authority 投影・DDL・backfill は
    しない。GO 時に出すのは *投影(projection) 計画の草案* だけ (WO「やらない」厳守)。
  - 決定的 (同じ metrics.json → 同じ verdict)。

7 ゲート → 12 項目 → verdict:
  G1 接地100%   : (1) ungrounded_value_count==0  (2) 501処理・欠損/重複なし
  G2 false-merge≈0 : (3) classification multi 未潰し  (4) disputed_rate が triage で生不一致率以下
  G3 provenance二重計上防止 : (5) family畳みが効く  (6) provenance_collapse_count>0 の証跡
  G4 決定性     : (7) 2回流して hash 一致  (8) inputs_sha256 証跡あり
  G5 rights     : (9) rights_profile カバレッジ100%  (10) rights_blocked_rate 閾値内
  G6 work遅延   : (11) 成果物5点 揃い・dry-run 完走・coverage 閾値以上
  G7 HOLD       : (12) 書込ゼロ証跡 + access非混入 + hold_flags 空

verdict 規則:
  NO-GO       : ハードゲート (G1 G2 G3 G4 G5 G7) のいずれか FAIL
  CONDITIONAL : ハード全通過だが ソフト (G2-#4 / G3-#6 / G5-#10 / G6-#11) が WARN
  GO          : 12 項目すべて PASS
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

# 既定閾値
EXPECTED_COHORT = 501            # 3サイト共通 501 冊
MAX_RIGHTS_BLOCKED_RATE = 0.20   # これ超で WARN (権利ブロック多→人手確認)
MIN_ADOPTED_COVERAGE = 0.95      # 採用値カバレッジ下限 (これ未満で WARN)
DELIVERABLES = [
    "attr_observations_sim.jsonl", "attr_canonical_sim.jsonl",
    "disputed_after_triage.csv", "metrics.json", "summary.md",
]

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


@dataclass
class Check:
    item: int
    gate: str
    name: str
    status: str
    detail: str
    hard: bool


@dataclass
class Verdict:
    verdict: str
    checks: list = field(default_factory=list)
    reasons: list = field(default_factory=list)

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


def _get(d: dict, *path, default=None):
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _is_true(v) -> Optional[bool]:
    return v if isinstance(v, bool) else None


def evaluate(m: dict, *, expected_cohort: int = EXPECTED_COHORT,
             max_rights_blocked: float = MAX_RIGHTS_BLOCKED_RATE,
             min_coverage: float = MIN_ADOPTED_COVERAGE) -> Verdict:
    checks: list = []

    def add(item, gate, name, status, detail, hard):
        checks.append(Check(item, gate, name, status, detail, hard))

    # ---- G1 接地100% ----------------------------------------------------
    ungrounded = _get(m, "ungrounded_value_count")
    if ungrounded is None:
        add(1, "G1", "ungrounded_value_count==0", FAIL, "ungrounded_value_count 欠落 (fail-closed)", True)
    elif ungrounded == 0:
        add(1, "G1", "ungrounded_value_count==0", PASS, "未接地 採用値 0 (接地100%)", True)
    else:
        add(1, "G1", "ungrounded_value_count==0", FAIL, f"未接地 採用値 {ungrounded} 件 (出所なし)", True)

    processed = _get(m, "cohort", "processed")
    expected = _get(m, "cohort", "expected", default=expected_cohort)
    missing = _get(m, "cohort", "missing_ids", default=None)
    dup = _get(m, "cohort", "duplicate_ids", default=None)
    if processed is None or missing is None or dup is None:
        add(2, "G1", "501処理・欠損/重複なし", FAIL, "cohort.processed/missing_ids/duplicate_ids 欠落 (fail-closed)", True)
    elif processed == expected and len(missing) == 0 and len(dup) == 0:
        add(2, "G1", "501処理・欠損/重複なし", PASS, f"{processed}/{expected} 処理・欠損0・重複0", True)
    else:
        add(2, "G1", "501処理・欠損/重複なし", FAIL,
            f"processed {processed}/{expected} 欠損{len(missing)} 重複{len(dup)}", True)

    # ---- G2 false-merge≈0 ----------------------------------------------
    multi = _is_true(_get(m, "classification_multi_preserved"))
    if multi is None:
        add(3, "G2", "classification multi 未潰し", FAIL, "classification_multi_preserved 欠落 (fail-closed)", True)
    elif multi:
        add(3, "G2", "classification multi 未潰し", PASS, "scheme併存・multi 保持 (誤統合なし)", True)
    else:
        add(3, "G2", "classification multi 未潰し", FAIL, "classification が単一化されている (誤マージ)", True)

    dr = _get(m, "disputed_rate_after_triage")
    raw = _get(m, "raw_disagreement_rate")
    only_tc = _is_true(_get(m, "disputed_all_true_conflict"))
    if dr is None or raw is None:
        add(4, "G2", "disputed率 triage で低減", WARN, "disputed_rate_after_triage/raw_disagreement_rate 欠落 → 確認要", False)
    elif dr <= raw and only_tc is not False:
        add(4, "G2", "disputed率 triage で低減", PASS, f"disputed {dr} <= 生不一致 {raw} (true_conflictのみ)", False)
    else:
        add(4, "G2", "disputed率 triage で低減", WARN,
            f"disputed {dr} vs 生不一致 {raw} / true_conflict限定={only_tc}", False)

    # ---- G3 provenance 二重計上防止 ------------------------------------
    family = _is_true(_get(m, "provenance_family_collapse_effective"))
    if family is None:
        add(5, "G3", "provenance family畳みが効く", FAIL, "provenance_family_collapse_effective 欠落 (fail-closed)", True)
    elif family:
        add(5, "G3", "provenance family畳みが効く", PASS, "弁コム×legallib 同一familyを独立計上せず", True)
    else:
        add(5, "G3", "provenance family畳みが効く", FAIL, "family畳み無効 (同一source二重計上の恐れ)", True)

    collapse = _get(m, "provenance_collapse_count")
    if collapse is None:
        add(6, "G3", "畳み発生の証跡", WARN, "provenance_collapse_count 欠落 → 確認要", False)
    elif collapse > 0:
        add(6, "G3", "畳み発生の証跡", PASS, f"provenance_collapse {collapse} 件 (二重計上の芽を畳んだ)", False)
    else:
        add(6, "G3", "畳み発生の証跡", WARN, "provenance_collapse_count==0 (畳み未発生＝要確認)", False)

    # ---- G4 決定性 ------------------------------------------------------
    ha = _get(m, "determinism", "run_a_hash")
    hb = _get(m, "determinism", "run_b_hash")
    if ha is None or hb is None:
        add(7, "G4", "2回流して hash 一致", FAIL, "determinism.run_a_hash/run_b_hash 欠落 (fail-closed)", True)
    elif ha == hb:
        add(7, "G4", "2回流して hash 一致", PASS, f"再現hash 一致 ({str(ha)[:12]}…)", True)
    else:
        add(7, "G4", "2回流して hash 一致", FAIL, f"hash 不一致 ({str(ha)[:8]}… != {str(hb)[:8]}…)", True)

    sha = _is_true(_get(m, "determinism", "inputs_sha256_present"))
    if sha is None:
        add(8, "G4", "inputs_sha256 証跡あり", FAIL, "determinism.inputs_sha256_present 欠落 (fail-closed)", True)
    elif sha:
        add(8, "G4", "inputs_sha256 証跡あり", PASS, "inputs_sha256.txt 存在 (入力固定)", True)
    else:
        add(8, "G4", "inputs_sha256 証跡あり", FAIL, "inputs_sha256 証跡なし (再現性の土台欠如)", True)

    # ---- G5 rights ------------------------------------------------------
    rcov = _get(m, "rights_profile_coverage")
    if rcov is None:
        add(9, "G5", "rights_profile カバレッジ100%", FAIL, "rights_profile_coverage 欠落 (fail-closed)", True)
    elif rcov >= 1.0:
        add(9, "G5", "rights_profile カバレッジ100%", PASS, "全観測に rights_profile 付与", True)
    else:
        add(9, "G5", "rights_profile カバレッジ100%", FAIL, f"rights_profile 付与 {rcov:.3f} < 1.0 (権利不明値あり)", True)

    rbr = _get(m, "rights_blocked_rate")
    if rbr is None:
        add(10, "G5", "rights_blocked_rate 閾値内", WARN, "rights_blocked_rate 欠落 → 確認要", False)
    elif rbr <= max_rights_blocked:
        add(10, "G5", "rights_blocked_rate 閾値内", PASS, f"rights_blocked {rbr:.3f} <= {max_rights_blocked}", False)
    else:
        add(10, "G5", "rights_blocked_rate 閾値内", WARN,
            f"rights_blocked {rbr:.3f} > {max_rights_blocked} (権利ブロック多→人手確認)", False)

    # ---- G6 work遅延 (ソフト): 成果物揃い・完走・coverage ----------------
    deliv = _get(m, "deliverables", default=None)
    cov = _get(m, "adopted_value_coverage")
    missing_deliv = [d for d in DELIVERABLES if not (isinstance(deliv, dict) and deliv.get(d))]
    if deliv is None or cov is None:
        add(11, "G6", "成果物5点・完走・coverage", WARN, "deliverables/adopted_value_coverage 欠落 → 完走未確認", False)
    elif not missing_deliv and cov >= min_coverage:
        add(11, "G6", "成果物5点・完走・coverage", PASS, f"成果物5点揃い・coverage {cov:.3f} >= {min_coverage}", False)
    else:
        why = []
        if missing_deliv:
            why.append(f"欠落成果物 {missing_deliv}")
        if cov < min_coverage:
            why.append(f"coverage {cov:.3f} < {min_coverage}")
        add(11, "G6", "成果物5点・完走・coverage", WARN, " / ".join(why), False)

    # ---- G7 HOLD: report-only 厳守 (書込ゼロ + access非混入 + hold無) -----
    we = _get(m, "write_evidence", default=None)
    access_ok = _is_true(_get(m, "access_not_in_biblio_consensus"))
    holds = _get(m, "hold_flags", default=None)
    if we is None or access_ok is None or holds is None:
        add(12, "G7", "report-only厳守(書込0/access非混入/hold無)", FAIL,
            "write_evidence/access_not_in_biblio_consensus/hold_flags 欠落 (fail-closed)", True)
    else:
        nonzero = {k: v for k, v in we.items() if v}
        if not nonzero and access_ok and len(holds) == 0:
            add(12, "G7", "report-only厳守(書込0/access非混入/hold無)", PASS,
                "DB/DDL/backfill/biblio/embedding/外部送信=0・access非混入・HOLD無", True)
        else:
            why = []
            if nonzero:
                why.append(f"スコープ外書込 {nonzero}")
            if not access_ok:
                why.append("access系が書誌合議に混入")
            if len(holds) > 0:
                why.append(f"HOLD: {holds}")
            add(12, "G7", "report-only厳守(書込0/access非混入/hold無)", FAIL, " / ".join(why), True)

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
# GO 経路: 属性層 投影(projection) 計画草案 (適用しない。owner-gated)
# ----------------------------------------------------------------------------
PROJECTION_DRAFT = """\
# 501 GO → 属性層 biblio/authority 投影 + DDL/backfill 計画 (草案 / DRAFT)

> ⚠️ **owner-gated。** WO「やらない」: final_toc apply / biblio・authority への書込 /
> DDL / backfill / scalar上書き / work rollup / embedding / 外部送信。本草案は GO を受けた
> *叩き台* で、適用は **Owner ratify / T2 ゲート**を経るまで実行しない。本ツールは DB を触らない。

- run_id: {run_id}
- verdict: GO ({passed}/{total} 項目 PASS)
- 根拠: ungrounded=0 (接地100%) / classification multi保持 / family畳み有効 / 決定性hash一致 /
  rights_profile 100% / report-only 厳守(書込ゼロ)。

## 1. DDL 草案 (attr_canonical_sim → 正本スキーマ)
- [ ] `attr_canonical` テーブル: item_id, attr_key, attr_scheme, canonical_value,
      adopted_status, rollup_status(=item_only), agreement_count, projection_version,
      rights_profile, provenance_group。
- [ ] 一意制約 (item_id, attr_key, attr_scheme) で **二重計上を DB レベルで再防止**。
- [ ] NOT NULL: provenance_group / rights_profile (接地100%・権利付与をスキーマで担保)。
- [ ] classification は multi 保持できる行設計 (scheme併存を 1 行に潰さない)。
- [ ] access 系 (held_by_office/shelf_locator/fulltext_access) は **fact_class=access** で
      別系統に隔離 (書誌合議に混ぜない)。

## 2. backfill 草案 (dry-run → apply は別承認)
- [ ] dry-run backfill: 件数・衝突・既存 biblio との差分を観測 (書込なし)。
- [ ] 冪等 upsert キー = (item_id, attr_key, attr_scheme, projection_version)。
- [ ] 投入前に provenance_family 再畳みで agreement_count 水増しが無いか再検証。
- [ ] disputed (true_conflict) 行は backfill 対象外 → 人手 review 経路へ。
- [ ] ロールバック: projection_version 単位の限定削除キーを用意。

## 3. owner ratify チェックポイント
- [ ] Owner に 5 行サマリで GO 根拠を提示。
- [ ] DD-LITID-001-ATTR を accepted/canonical へ昇格 (T2 ゲート)。
- [ ] 承認後にのみ DDL apply → backfill --apply (本ツール外・別手順)。
"""


def render_plan(run_id: str, v: Verdict) -> str:
    p = sum(c.status == PASS for c in v.checks)
    return PROJECTION_DRAFT.format(run_id=run_id, passed=p, total=len(v.checks))


def render_report(run_id: str, v: Verdict) -> str:
    lines = ["=" * 64, f"# post-return-verdict — run {run_id} (属性観測層 501 dry-run)"]
    s = v.to_dict()["summary"]
    lines.append(f"VERDICT: {v.verdict}   (PASS {s['pass']} / WARN {s['warn']} / FAIL {s['fail']} / {s['total']})")
    lines.append("-" * 64)
    for c in v.checks:
        mark = {"PASS": "✓", "WARN": "▲", "FAIL": "✗"}[c.status]
        hard = "H" if c.hard else "s"
        lines.append(f"  {mark} [{c.item:>2}|{c.gate}|{hard}] {c.name}: {c.detail}")
    if v.reasons:
        lines.append("-" * 64)
        head = "NO-GO 理由 (ハードゲート FAIL):" if v.verdict == "NO-GO" else "CONDITIONAL 要対応 (ソフト WARN):"
        lines.append(head)
        for r in v.reasons:
            lines.append(f"  - {r}")
    lines.append("-" * 64)
    if v.verdict == "GO":
        lines.append("→ 次成果物: 属性層 投影/DDL/backfill 計画草案を出力可 (--emit-plan)。適用は owner-gated。")
    elif v.verdict == "CONDITIONAL":
        lines.append("→ ソフト項目を解消するか、Owner が条件付き許可するまで GO にしない。")
    else:
        lines.append("→ ハードゲート FAIL。dry-run をやり直して 501 を返し直す。投影/DDL/backfill は起票しない。")
    return "\n".join(lines)


def load_metrics(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(prog="post-return-verdict",
                                 description="属性観測層 501 dry-run 帰り後 GO/CONDITIONAL/NO-GO 判定")
    ap.add_argument("--metrics", required=True, help="metrics.json のパス")
    ap.add_argument("--summary", help="summary.md のパス (記録用・任意)")
    ap.add_argument("--run-id", default="attr_layer_501_dryrun_20260615", help="run 識別子")
    ap.add_argument("--expected-cohort", type=int, default=EXPECTED_COHORT)
    ap.add_argument("--json", action="store_true", help="JSON で出力")
    ap.add_argument("--emit-plan", action="store_true",
                    help="GO の場合に投影/DDL/backfill 計画草案を stdout へ (適用はしない)")
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

    v = evaluate(metrics, expected_cohort=args.expected_cohort)

    if args.emit_plan:
        if v.verdict == "GO":
            print(render_plan(args.run_id, v))
            return 0
        print(f"# 計画草案は出さない。verdict={v.verdict} (GO 限定)。", file=sys.stderr)
        print(render_report(args.run_id, v), file=sys.stderr)
        return 1

    if args.json:
        out = v.to_dict()
        out["run_id"] = args.run_id
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(render_report(args.run_id, v))

    return {"GO": 0, "CONDITIONAL": 1, "NO-GO": 2}[v.verdict]


if __name__ == "__main__":
    raise SystemExit(main())
