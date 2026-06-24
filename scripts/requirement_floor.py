"""記載事項の床 — 法定/実務必須の記載事項を抽出し、ドラフトの抜け漏れを撃つ (stdlib のみ).

設計思想: docs/dd_doctrine.md §5（記載事項の床）。GPT DDDOCTRINE 監査 F2 校正を反映。

着想:
  * **条文の各号 = 法定記載事項の正準リスト**（例 会社法199①一〜）。top-down の権威。
  * **N冊の書式の収束** = bottom-up の実務。両者を突き合わせる。
  * 全冊一致は **証明でなく強い候補（F2）**。3段で扱う:
      - statutory_floor          : 条文各号にある（= 法定。落とせば無効）
      - established_practice_floor: 全冊一致だが条文各号に無い（= 実務上不可欠。落とせば却下/恥）
      - floor_candidate          : 全冊一致のみ（弱い。要・条文照合）
  * **源の独立性（F4）**: 書式が同一上流（同テンプレ/出版系列）なら一致を割り引く。

最大の実利 = **抜け漏れ検出**: ドラフトの記載事項を床と突合し、欠落した法定/実務必須を「致命傷」
として撃つ。決定的・stdlib のみ。法定性は文脈依存（条件付）なので、必須判定は context で発火する。
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", str(s or "")).replace(" ", "").replace("　", "")


def _canon_index(canonical: list[dict]) -> dict[str, dict]:
    """法定記載事項(条文各号)を正規化キーで引けるように。name/aliases を突合語に。"""
    idx: dict[str, dict] = {}
    for c in canonical:
        terms = [c.get("名称", "")] + list(c.get("aliases", []))
        c["_terms"] = sorted({_norm(t) for t in terms if t}, key=len, reverse=True)
        idx[c["id"]] = c
    return idx


def _match_canon(item: str, canonical: list[dict]) -> str | None:
    """書式の1記載事項を、条文各号のどれか(id)へ突合 (部分一致・長語優先)。無ければ None。"""
    ni = _norm(item)
    best = None
    for c in canonical:
        for t in c.get("_terms", []):
            if t and t in ni:
                if best is None or len(t) > best[1]:
                    best = (c["id"], len(t))
    return best[0] if best else None


def analyze_floor(canonical: list[dict], forms: list[dict]) -> dict:
    """条文各号 × N書式の記載事項 → 床(法定/実務必須) と裁量帯。

    forms: [{"id":..., "記載事項":[str,...], "source_family":任意}]
    """
    _canon_index(canonical)
    n = len(forms)

    # 各書式の記載事項を、条文各号id / 条文外名称(正規化) の集合へ落とす。
    form_canon: list[set[str]] = []   # 各書式が満たした条文各号 id
    form_extra: list[set[str]] = []   # 各書式の条文外記載事項 (正規化名)
    for f in forms:
        cset, eset = set(), set()
        for it in f.get("記載事項", []):
            cid = _match_canon(it, canonical)
            (cset.add(cid) if cid else eset.add(_norm(it)))
        form_canon.append(cset)
        form_extra.append(eset)

    families = [f.get("source_family") for f in forms if f.get("source_family")]
    independent = len(set(families)) if families else n
    indep_warn = (n >= 2 and independent < n)

    # 条文各号ごとの被覆。
    statutory_floor, conditional = [], []
    for c in canonical:
        cov = sum(1 for cs in form_canon if c["id"] in cs)
        row = {"id": c["id"], "名称": c.get("名称", ""), "号": c.get("号"),
               "coverage": f"{cov}/{n}", "tier": "statutory_floor"}
        if cov == n:
            statutory_floor.append(row)
        else:
            # 条文にあるが全書式が書かない = 条件付(現物出資等) or 一部書式の欠落候補。
            row["tier"] = "statutory_conditional"
            conditional.append(row)

    # 条文外で全冊一致 = 実務上不可欠 (established-practice floor)。一部一致 = 裁量帯。
    extra_all = set.intersection(*form_extra) if form_extra else set()
    extra_union = set.union(*form_extra) if form_extra else set()
    established = [{"名称": e, "coverage": f"{n}/{n}", "tier": "established_practice_floor"}
                  for e in sorted(extra_all)]
    discretion = [{"名称": e, "coverage": f"{sum(1 for es in form_extra if e in es)}/{n}",
                   "tier": "discretion"} for e in sorted(extra_union - extra_all)]

    return {
        "n_forms": n, "independent_sources": independent, "independence_warning": indep_warn,
        "statutory_floor": statutory_floor,            # 落とせば無効
        "statutory_conditional": conditional,           # 条件付/要確認
        "established_practice_floor": established,       # 落とせば却下・恥
        "discretion": discretion,                       # 実務の幅
    }


def check_omissions(draft_items: list[dict] | list[str], canonical: list[dict],
                    floor: dict) -> dict:
    """ドラフトの記載事項を床と突合し、欠落を撃つ（最大の実利 = 致命傷防止）。"""
    _canon_index(canonical)
    items = [d if isinstance(d, str) else d.get("名称", "") for d in draft_items]
    have_canon = {cid for it in items if (cid := _match_canon(it, canonical))}
    have_extra = {_norm(it) for it in items if not _match_canon(it, canonical)}

    missing_statutory = [r for r in floor["statutory_floor"] if r["id"] not in have_canon]
    missing_practice = [r for r in floor["established_practice_floor"]
                        if r["名称"] not in have_extra]
    return {
        "missing_statutory": missing_statutory,    # ❌致命傷: 法定記載事項の欠落 → 無効
        "missing_practice": missing_practice,      # ⚠却下リスク: 実務必須の欠落
        "ok": not missing_statutory and not missing_practice,
    }


def check_against_statute(draft_text: str, canonical: list[dict]) -> dict:
    """ドラフト本文を条文各号(= top-down 正本の床)と直接突合し、抜け漏れを撃つ。

    条文を e-Gov から取得済みなので、各号がそのまま法定の床になる(N書式の収束を待たない)。
    `条件付`(例 三号=現物出資)は、`条件`語がドラフトに出た時だけ必須化する(無条件チェックリストにしない
    =法律家が信頼できる挙動)。判定は決定的・stdlib のみ・部分一致(正規化)。

    canonical: [{号, 名称, aliases, 条件付?, 条件?[...]}]
    """
    nt = _norm(draft_text)
    rows = []
    for c in canonical:
        conditional = bool(c.get("条件付"))
        triggered = (not conditional) or any(_norm(t) in nt for t in c.get("条件", []) if t)
        terms = [c.get("名称", "")] + list(c.get("aliases", []))
        present = any(_norm(t) in nt for t in terms if t)
        rows.append({"号": c.get("号"), "名称": c.get("名称", ""), "id": c.get("id"),
                     "conditional": conditional, "required": triggered, "present": present,
                     "missing": triggered and not present})
    missing = [r for r in rows if r["missing"]]
    return {"rows": rows, "missing": missing, "ok": not missing}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="記載事項の床 / 抜け漏れ検出")
    ap.add_argument("--canonical", required=True, help="条文各号 jsonl/json [{id,名称,号,aliases}]")
    ap.add_argument("--forms", required=True, help="書式 jsonl/json [{id,記載事項:[...]}]")
    ap.add_argument("--draft", help="ドラフトの記載事項 jsonl/json (抜け漏れ検出)")
    args = ap.parse_args(argv)

    canonical = _load(Path(args.canonical))
    forms = _load(Path(args.forms))
    floor = analyze_floor(canonical, forms)

    print(f"書式 {floor['n_forms']} 冊 / 独立源 {floor['independent_sources']}"
          + ("  ⚠独立性低(一致を割り引け)" if floor["independence_warning"] else ""))
    print(f"■ 法定の床(落とせば無効) {len(floor['statutory_floor'])}件:")
    for r in floor["statutory_floor"]:
        print(f"    [{r.get('号','')}] {r['名称']}  ({r['coverage']})")
    if floor["statutory_conditional"]:
        print(f"■ 条件付/要確認 {len(floor['statutory_conditional'])}件:")
        for r in floor["statutory_conditional"]:
            print(f"    [{r.get('号','')}] {r['名称']}  ({r['coverage']})")
    if floor["established_practice_floor"]:
        print(f"■ 実務必須(条文外・落とせば却下) {len(floor['established_practice_floor'])}件:")
        for r in floor["established_practice_floor"]:
            print(f"    {r['名称']}  ({r['coverage']})")
    if args.draft:
        res = check_omissions(_load(Path(args.draft)), canonical, floor)
        print("\n=== 抜け漏れ検出 ===")
        if res["ok"]:
            print("  ✅ 床を満たす")
        for r in res["missing_statutory"]:
            print(f"  ❌致命傷(無効): {r['名称']} [{r.get('号','')}] が欠落")
        for r in res["missing_practice"]:
            print(f"  ⚠却下リスク: {r['名称']}(実務必須) が欠落")
    return 0


def _load(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(l) for l in text.splitlines() if l.strip()]
    d = json.loads(text)
    return d if isinstance(d, list) else d.get("items", [])


if __name__ == "__main__":
    raise SystemExit(main())
