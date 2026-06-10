"""⑥手続 フローモデル: スケジュール本/段取り本の手続構造を保持・検証・描画 (stdlib のみ).

設計: docs/dd_procedure_design.md §8。**手続フローは手作りしない**——「会社法スケジュール」等の
段取り本（専門家が分岐つき段取りを構造化済み＝巨人の肩）から抽出した構造を、機械可読な
有向グラフ (局面 node ＋ 条件付き遷移 edge) として保持する。

本モジュールは「持てること」を担保する3機能:
  * load   : procedure_flow JSON を読む
  * validate: 構造健全性 ＋ **各 node の出典(source) 必須**(捏造防止・三点測量の監査前提)を検査
  * render : 分岐つきフロー図をテキスト描画 (どこで道が割れるか可視化)

実際の手順内容は本からの抽出＋owner/GPT 監査で埋める。本モジュールは内容を作らない。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_flow(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_flow(flow: dict) -> list[str]:
    """構造＋出典の健全性を検査。空 list なら健全。"""
    errors: list[str] = []
    nodes = flow.get("nodes", [])
    ids = [n.get("id") for n in nodes]

    seen: set[str] = set()
    for nid in ids:
        if not nid:
            errors.append("id の無い node がある")
        elif nid in seen:
            errors.append(f"duplicate node id: {nid}")
        seen.add(nid)

    idset = set(ids)
    for n in nodes:
        nid = n.get("id")
        # 出典必須: どの本の何ページ / どの条文 由来か (捏造防止)。
        if not n.get("source"):
            errors.append(f"node に source(出典) が無い: {nid}")
        for e in n.get("次", []):
            to = e.get("to")
            if to not in idset:
                errors.append(f"unknown 遷移先: {nid} -> {to}")

    entry = flow.get("entry")
    if entry and entry not in idset:
        errors.append(f"entry が node に無い: {entry}")
    for t in flow.get("terminal", []):
        if t not in idset:
            errors.append(f"terminal が node に無い: {t}")

    # 到達性 (entry から届かない node を警告)。
    if entry in idset:
        reach: set[str] = set()
        stack = [entry]
        nmap = {n["id"]: n for n in nodes if n.get("id")}
        while stack:
            cur = stack.pop()
            if cur in reach:
                continue
            reach.add(cur)
            for e in nmap.get(cur, {}).get("次", []):
                if e.get("to"):
                    stack.append(e["to"])
        for nid in idset - reach:
            errors.append(f"entry から到達できない node: {nid}")
    return errors


def render_text(flow: dict) -> str:
    """分岐つきフローをインデント描画。分岐(複数の次)は条件付きで枝表示。"""
    nmap = {n["id"]: n for n in flow.get("nodes", []) if n.get("id")}
    out = [f"# {flow.get('title', flow.get('procedure_id', '手続'))}"
           f"  [{flow.get('status', '?')}]"]
    if flow.get("source_books"):
        out.append("出典本: " + ", ".join(flow["source_books"]))
    out.append("")

    seen: set[str] = set()

    def line(n: dict) -> str:
        bits = [n.get("局面", n["id"])]
        if n.get("機関"):
            bits.append(f"〔{n['機関']}〕")
        if n.get("根拠条文"):
            bits.append("(" + "・".join(n["根拠条文"]) + ")")
        if n.get("期限"):
            bits.append(f"⏱{n['期限']}")
        if n.get("必要書類"):
            bits.append("📄" + "・".join(n["必要書類"]))
        if n.get("書式"):
            forms = [f.get("名称", str(f)) if isinstance(f, dict) else str(f)
                     for f in n["書式"]]
            bits.append("📝書式:" + "・".join(forms))
        return " ".join(bits)

    def walk(nid: str, depth: int, cond: str | None) -> None:
        n = nmap.get(nid)
        prefix = "  " * depth + ("└ " if depth else "")
        label = (f"[{cond}] " if cond else "") + (line(n) if n else f"?{nid}")
        if nid in seen:
            out.append(prefix + label + "  …(既出へ合流)")
            return
        seen.add(nid)
        out.append(prefix + label)
        nxt = n.get("次", []) if n else []
        if len(nxt) == 1:
            walk(nxt[0]["to"], depth, nxt[0].get("条件"))
        else:
            for e in nxt:  # 分岐: 深さを下げて枝分かれを見せる
                walk(e["to"], depth + 1, e.get("条件"))

    if flow.get("entry"):
        walk(flow["entry"], 0, None)
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="手続フロー 検証/描画")
    ap.add_argument("flow", help="procedure_flow JSON")
    ap.add_argument("--render", action="store_true", help="フロー図を描画")
    args = ap.parse_args(argv)

    flow = load_flow(Path(args.flow))
    errors = validate_flow(flow)
    if errors:
        for e in errors:
            print(f"  ❌ {e}")
        print(f"validate FAILED ({len(errors)})")
        return 1
    print(f"✓ validate OK: {flow.get('procedure_id')} "
          f"({len(flow.get('nodes', []))} 局面)")
    if args.render:
        print()
        print(render_text(flow), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
