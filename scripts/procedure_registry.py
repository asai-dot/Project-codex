"""procedure registry (L1) — 観測(L0)と roll-up(L2)の間に置く正準レジストリの器とゲート (stdlib のみ).

GPT お目付け 20260619 DDPROGRESS_PASS_WITH_NOTES Q1/§5 の三層化を実装:

    L0 observation : TOC/法令/公式案内由来の生観測   (procedure_inventory.json)
    L1 registry    : owner ratify された procedure/family/variant ← 本ツールの対象
    L2 roll-up     : 旧24類型 navigation・系統・facet (procedure_spine.json)

本ツールの境界(HOLD 厳守):
  - **自動昇格しない**: observation → candidate は「候補提示」だけ。owner_ratified への昇格は
    owner ratify(ratified_by/ratified_at)のみ。番頭はゲート検算と候補提示に徹する。
  - **正本を書き換えない**: spine 置換・DB write なし。registry への owner_ratified 追記は owner の手。

提供する3機能:
  1. promotion_report : L0 観測を昇格ルールで判定し candidate 候補を**提示**(mutation なし)。
  2. validate_registry: status lifecycle / ratify メタ / supersession グラフ の不変条件検査。
  3. crosswalk        : L1 entry → L2 roll-up(legacy_rollup_id) の被覆レポート。
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path

STATUS = ["observed", "candidate", "owner_ratified", "superseded", "deprecated"]
KIND_ENUM = ["procedure", "procedure_family", "procedure_variant"]

# status lifecycle の許可遷移。owner_ratified は ratify を経た時だけ。終端は superseded/deprecated。
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "observed": {"candidate", "deprecated"},
    "candidate": {"owner_ratified", "deprecated"},
    "owner_ratified": {"superseded", "deprecated"},
    "superseded": set(),
    "deprecated": set(),
}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", str(s or "")).replace(" ", "").replace("　", "")


def validate_transition(old: str, new: str) -> bool:
    """status 遷移が lifecycle 上許されるか。"""
    return new in ALLOWED_TRANSITIONS.get(old, set())


def _family(o: dict) -> str | None:
    """観測の独立源キー。source_family が無ければ source_book で代替(同一上流は1族)。"""
    return o.get("source_family") or o.get("source_book")


def _registry_index(registry: dict) -> dict[str, str]:
    """registry の name/aliases を正規化キー → entry id に。"""
    idx: dict[str, str] = {}
    for e in registry.get("entries", []):
        for term in [e.get("name", "")] + list(e.get("aliases", [])):
            if term:
                idx[_norm(term)] = e["id"]
    return idx


def promotion_report(observations: list[dict], registry: dict | None = None) -> list[dict]:
    """L0 観測を昇格ルールで判定し candidate 候補を提示(**mutation しない**)。

    昇格ルール: 独立2 source_family、または 法令/公式1 + 実務書1。
    現実の数冊サンプルでは単一 source が多く、その場合は eligible=False(1冊1章 auto-accept しない)。
    """
    known = _registry_index(registry or {})
    groups: dict[str, dict] = {}
    for o in observations:
        if o.get("kind") != "procedure":  # facet/局面は registry の手続候補にしない
            continue
        key = _norm(o["name"])
        groups.setdefault(key, {"name": o["name"], "obs": []})["obs"].append(o)

    rows: list[dict] = []
    for key, g in sorted(groups.items()):
        fams = {f for o in g["obs"] if (f := _family(o))}
        skinds = {o.get("source_kind", "practice") for o in g["obs"]}
        has_authority = bool({"statutory", "official"} & skinds)
        eligible = len(fams) >= 2 or (has_authority and "practice" in skinds)
        if eligible and len(fams) >= 2:
            reason = f"独立 {len(fams)} source_family"
        elif eligible:
            reason = "法令/公式 + 実務書 の2源"
        else:
            reason = "単一 source(1冊1章 auto-accept しない)"
        rows.append({
            "name": g["name"], "n_obs": len(g["obs"]),
            "source_families": sorted(fams), "source_kinds": sorted(skinds),
            "eligible_for_candidate": eligible,
            "in_registry": key in known, "registry_id": known.get(key),
            "reason": reason,
        })
    return rows


def validate_registry(registry: dict, spine_ids: set[str] | None = None) -> list[str]:
    """registry の不変条件を検査。違反メッセージのリストを返す(空=健全)。"""
    errs: list[str] = []
    ids = {e.get("id") for e in registry.get("entries", [])}
    for e in registry.get("entries", []):
        eid = e.get("id", "<no-id>")
        if not e.get("id") or not e.get("name"):
            errs.append(f"{eid}: id/name 必須")
        if e.get("status") not in STATUS:
            errs.append(f"{eid}: status 不正 ({e.get('status')!r})")
        if e.get("kind") not in KIND_ENUM:
            errs.append(f"{eid}: kind 不正 ({e.get('kind')!r})")
        if e.get("status") == "owner_ratified" and not (e.get("ratified_by") and e.get("ratified_at")):
            errs.append(f"{eid}: owner_ratified には ratified_by/ratified_at が必須(自動昇格禁止)")
        if e.get("status") == "superseded":
            tgt = e.get("superseded_by")
            if not tgt:
                errs.append(f"{eid}: superseded には superseded_by が必須")
            elif tgt not in ids:
                errs.append(f"{eid}: superseded_by={tgt} が registry に無い")
        rid = e.get("legacy_rollup_id")
        if rid and spine_ids is not None and rid not in spine_ids:
            errs.append(f"{eid}: legacy_rollup_id={rid} が spine(L2) に無い")

    # supersession グラフ: 参照先存在 + 循環なし。
    graph = {e["id"]: e.get("superseded_by") for e in registry.get("entries", [])
             if e.get("id") and e.get("superseded_by")}
    for start in list(graph):
        seen, cur = set(), start
        while cur in graph:
            if cur in seen:
                errs.append(f"supersession に循環: {start}")
                break
            seen.add(cur)
            cur = graph[cur]
    return errs


def crosswalk(registry: dict, spine: dict) -> dict:
    """L1 entry → L2 roll-up(legacy_rollup_id) の被覆。"""
    spine_ids = {t["id"] for t in spine.get("procedure_types", [])}
    entries = registry.get("entries", [])
    mapped = [e for e in entries if e.get("legacy_rollup_id") in spine_ids]
    unmapped = [e["id"] for e in entries if e.get("legacy_rollup_id") not in spine_ids]
    used = {e["legacy_rollup_id"] for e in mapped}
    return {"n_entries": len(entries), "mapped": len(mapped),
            "unmapped_entries": unmapped, "rollups_used": sorted(used),
            "rollups_unused": sorted(spine_ids - used)}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="procedure registry(L1) ゲート検算 / 昇格候補提示")
    ap.add_argument("--registry", default=str(here / "pipeline" / "procedure_registry.json"))
    ap.add_argument("--inventory", default=str(here / "pipeline" / "procedure_inventory.json"))
    ap.add_argument("--spine", default=str(here / "pipeline" / "procedure_spine.json"))
    args = ap.parse_args(argv)

    registry = _load(Path(args.registry))
    inventory = _load(Path(args.inventory))
    spine = _load(Path(args.spine))
    spine_ids = {t["id"] for t in spine.get("procedure_types", [])}

    errs = validate_registry(registry, spine_ids)
    n_ratified = sum(1 for e in registry.get("entries", []) if e.get("status") == "owner_ratified")
    print(f"registry(L1): entries {len(registry.get('entries', []))}件 / owner_ratified {n_ratified}件 "
          + ("✅健全" if not errs else f"❌不変条件 {len(errs)}件"))
    for m in errs:
        print(f"    ! {m}")

    rep = promotion_report(inventory.get("procedures", []), registry)
    elig = [r for r in rep if r["eligible_for_candidate"]]
    print(f"■ 昇格候補(候補提示のみ・自動昇格しない): {len(elig)}/{len(rep)} 手続が candidate 適格")
    for r in rep:
        mark = "→candidate可" if r["eligible_for_candidate"] else "—"
        print(f"    [{mark}] {r['name']}: {r['reason']} (源 {len(r['source_families'])}族)")
    if not elig:
        print("    (現サンプル=単一source中心。owner ratify か独立source追加までは昇格しない)")

    cw = crosswalk(registry, spine)
    print(f"■ L1→L2 crosswalk: {cw['mapped']}/{cw['n_entries']} が roll-up に対応 "
          f"(roll-up 未使用 {len(cw['rollups_unused'])}/{len(spine_ids)})")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
