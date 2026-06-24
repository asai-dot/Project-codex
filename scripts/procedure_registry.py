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
MEMBER_KINDS = {"procedure", "procedure_variant"}  # family の member になれる kind
# owner_ratified の根拠類型(MF-3)。証拠と判断を区別して監査可能にする。
RATIFICATION_BASIS_TYPES = ["owner_legal_judgment", "statutory_plus_practice", "multi_source"]
# owner_ratified に non-empty 必須の根拠フィールド(MF-3 v0.3)。証拠と判断を完全に固定する。
RATIFY_REQUIRED_SCALARS = ["ratified_by", "ratified_at", "ratification_basis_type", "ratification_note"]
RATIFY_REQUIRED_LISTS = ["ratification_basis_refs", "statutory_or_official_refs",
                         "source_family_refs", "legal_basis_refs"]
MATERIALIZATION = ["noncanonical", "canonical"]  # production loader は canonical のみ受理

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
    # canonical 境界(§5.4): 機械可読な materialization フラグ。production loader は canonical のみ受理。
    mat = registry.get("materialization_status")
    if mat not in MATERIALIZATION:
        errs.append(f"materialization_status は {MATERIALIZATION} のいずれか必須 (現値 {mat!r})")
    ids = {e.get("id") for e in registry.get("entries", [])}
    for e in registry.get("entries", []):
        eid = e.get("id", "<no-id>")
        if not e.get("id") or not e.get("name"):
            errs.append(f"{eid}: id/name 必須")
        if e.get("status") not in STATUS:
            errs.append(f"{eid}: status 不正 ({e.get('status')!r})")
        if e.get("kind") not in KIND_ENUM:
            errs.append(f"{eid}: kind 不正 ({e.get('kind')!r})")
        if e.get("status") == "owner_ratified":
            # MF-3 v0.3: 全根拠フィールドを non-empty で要求(証拠と判断を完全固定)。
            for k in RATIFY_REQUIRED_SCALARS:
                if not e.get(k):
                    errs.append(f"{eid}: owner_ratified には {k} が必須")
            if e.get("ratification_basis_type") and e["ratification_basis_type"] not in RATIFICATION_BASIS_TYPES:
                errs.append(f"{eid}: ratification_basis_type 不正 "
                            f"({'/'.join(RATIFICATION_BASIS_TYPES)})")
            for k in RATIFY_REQUIRED_LISTS:
                v = e.get(k)
                if not (isinstance(v, list) and len(v) > 0):
                    errs.append(f"{eid}: owner_ratified には {k}(非空リスト) が必須")
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

    errs += validate_family_membership(registry)
    errs += _check_rollup_semantics(registry, spine_ids)
    return errs


def validate_family_membership(registry: dict) -> list[str]:
    """MF-1: family membership crosswalk の規範検査。

    参照先存在 / kind 整合(family=procedure_family, member=procedure|variant) / 自己参照 /
    重複 / status 妥当。kind が排他なので循環は構造上生じないが、念のため kind を厳格化する。
    """
    errs: list[str] = []
    by_id = {e.get("id"): e for e in registry.get("entries", []) if e.get("id")}
    seen: set[tuple] = set()
    for m in registry.get("family_membership", []):
        fid, pid = m.get("family_id"), m.get("procedure_id")
        if not fid or not pid:
            errs.append(f"family_membership: family_id/procedure_id 必須 ({m})")
            continue
        if fid == pid:
            errs.append(f"family_membership: 自己参照 {fid}")
        if fid not in by_id:
            errs.append(f"family_membership: family_id={fid} が registry に無い")
        elif by_id[fid].get("kind") != "procedure_family":
            errs.append(f"family_membership: family_id={fid} は procedure_family でない")
        if pid not in by_id:
            errs.append(f"family_membership: procedure_id={pid} が registry に無い")
        elif by_id[pid].get("kind") not in MEMBER_KINDS:
            errs.append(f"family_membership: procedure_id={pid} は procedure/variant でない")
        if m.get("status") and m["status"] not in STATUS:
            errs.append(f"family_membership: status 不正 ({m.get('status')!r})")
        # MF-1 v0.3: validity / source_basis の整合(CLOSED WITH NOTES の補強)。
        vf, vt = m.get("valid_from"), m.get("valid_to")
        if not vf:
            errs.append(f"family_membership({fid},{pid}): valid_from 必須")
        if vt is not None and vf and not (str(vt) > str(vf)):
            errs.append(f"family_membership({fid},{pid}): valid_to は valid_from より後 か null")
        if not (m.get("source_basis") or "").strip():
            errs.append(f"family_membership({fid},{pid}): source_basis 必須(空不可)")
        if (fid, pid) in seen:
            errs.append(f"family_membership: 重複 ({fid},{pid})")
        seen.add((fid, pid))
    return errs


def is_production_loadable(registry: dict) -> bool:
    """production loader が受理してよいか(§5.4 canonical 境界)。design fixture は弾く。"""
    return registry.get("materialization_status") == "canonical"


def _check_rollup_semantics(registry: dict, spine_ids: set[str] | None) -> list[str]:
    """MF-2: stable-ID の silent な意味変更を防ぐ。

    rollup_notes で扱いが宣言された rollup_id は spine(L2) に存在すべき。意味を狭める(narrow/split/
    deprecate)宣言には supersession 記録を要求する(keep_unchanged は不要)。説明文だけの暗黙縮小を弾く。
    """
    errs: list[str] = []
    superseded = {s.get("rollup_id") or s.get("from") for s in registry.get("supersession", [])}
    for n in registry.get("rollup_notes", []):
        rid, action = n.get("rollup_id"), n.get("action")
        if rid and spine_ids is not None and rid not in spine_ids:
            errs.append(f"rollup_notes: rollup_id={rid} が spine(L2) に無い")
        if action in {"narrow", "split", "deprecate"} and rid not in superseded:
            errs.append(f"rollup_notes: {rid} の action={action} には supersession 記録が必須"
                        f"(silent narrowing 禁止=MF-2)")
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
    entries = registry.get("entries", [])
    n_ratified = sum(1 for e in entries if e.get("status") == "owner_ratified")
    n_cand = sum(1 for e in entries if e.get("status") == "candidate")
    print(f"registry(L1 v{registry.get('version','?')}): entries {len(entries)}件 "
          f"(candidate {n_cand} / owner_ratified {n_ratified}) "
          + ("✅健全" if not errs else f"❌不変条件 {len(errs)}件"))
    for m in errs:
        print(f"    ! {m}")

    # family membership(MF-1)の要約。
    fams = [e for e in entries if e.get("kind") == "procedure_family"]
    for f in fams:
        members = [m["procedure_id"] for m in registry.get("family_membership", [])
                   if m.get("family_id") == f["id"]]
        print(f"■ family {f['id']}({f['name']}) ← {len(members)}手続: {', '.join(members)}")

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
