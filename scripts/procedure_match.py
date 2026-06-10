"""⑥手続 wedge: 書式タイトル × 手続類型 spine の alias 突合タグ付け (stdlib のみ).

設計: docs/dd_procedure_design.md。手続シグナルは書式の archetype(A〜E=構造型) ではなく
**タイトル/件名**にある (「破産手続開始申立書」「仮差押命令申立書」…)。本スクリプトは
``pipeline/procedure_spine.json`` の各類型 alias/name を書式タイトルへ部分一致させ、
``procedure_id`` を付与する。契約等の取引文書は手続 alias に当たらず unmatched になる
(＝「契約は手続でない」がデータ上自然に出る)。

入力: 書式リスト (jsonl {id,title,...} か csv: 先頭行ヘッダに id,title)。
出力: 各書式の手続タグ(jsonl) と、手続類型ごとのカバレッジ集計 (stdout)。
決定的・冪等。これが ⑥手続の「最初の面 (書式 face)」を点灯させる最小実装。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path

# 「手続法」と判定する根拠法令キーワード (実体法=民法/会社法 は broad 突合に使わない)。
_PROC_LAW_RE = re.compile(r"訴訟|保全|執行|破産|再生|更生|調停|審判|非訟|手続|督促|労働審判")


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").replace(" ", "").replace("　", "")


def load_spine(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")).get("procedure_types", [])


def _terms(pt: dict) -> list[str]:
    """leaf 突合語＝name ＋ aliases。長い語を優先 (より具体的な一致を上に)。"""
    terms = [pt.get("name", "")] + list(pt.get("aliases", []))
    return sorted({_norm(t) for t in terms if t}, key=len, reverse=True)


def _law_terms(pt: dict) -> list[str]:
    """broad 突合語＝根拠法令名のうち「手続法」だけ (実体法は除外)。"""
    return [_norm(law) for law in pt.get("根拠法令", []) if _PROC_LAW_RE.search(law)]


def match_title(title: str, spine: list[dict]) -> list[dict]:
    """タイトルに一致した手続類型を返す (複数可。曖昧さは隠さず全部出す)。

    2段: leaf(手続名/alias) で一致を試み、無ければ broad(手続法の根拠法令名) で拾う。
    各 hit に ``tier`` (leaf/broad) を付ける。
    """
    nt = _norm(title)
    leaf = []
    for pt in spine:
        matched = next((t for t in _terms(pt) if t and t in nt), None)
        if matched:
            leaf.append({"procedure_id": pt["id"], "系統": pt.get("系統", ""),
                         "name": pt.get("name", ""), "via": matched, "tier": "leaf"})
    if leaf:
        leaf.sort(key=lambda h: len(h["via"]), reverse=True)
        return leaf
    broad = []
    for pt in spine:
        matched = next((t for t in _law_terms(pt) if t and t in nt), None)
        if matched:
            broad.append({"procedure_id": pt["id"], "系統": pt.get("系統", ""),
                          "name": pt.get("name", ""), "via": matched, "tier": "broad"})
    broad.sort(key=lambda h: len(h["via"]), reverse=True)
    return broad


def load_templates(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl" or text.lstrip().startswith("{"):
        return [json.loads(ln) for ln in text.splitlines() if ln.strip()]
    rows = list(csv.DictReader(text.splitlines()))
    return rows


def run(spine: list[dict], templates: list[dict]) -> dict:
    tagged = []
    cov: dict[str, int] = {}
    groups: dict[str, list[dict]] = {}
    ambiguous = unmatched = 0
    for t in templates:
        title = t.get("title") or t.get("name") or ""
        hits = match_title(title, spine)
        primary = hits[0]["procedure_id"] if hits else None
        if not hits:
            unmatched += 1
        else:
            if len(hits) > 1:
                ambiguous += 1
            cov[primary] = cov.get(primary, 0) + 1
            groups.setdefault(primary, []).append({"id": t.get("id"), "title": title})
        tagged.append({"id": t.get("id"), "title": title, "primary": primary,
                       "candidates": [h["procedure_id"] for h in hits],
                       "ambiguous": len(hits) > 1})
    return {"tagged": tagged, "coverage": cov, "groups": groups,
            "total": len(templates), "matched": len(templates) - unmatched,
            "unmatched": unmatched, "ambiguous": ambiguous}


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="書式タイトル×手続類型 spine 突合")
    ap.add_argument("--spine", default=str(here / "pipeline" / "procedure_spine.json"))
    ap.add_argument("--templates", required=True, help="jsonl({id,title}) か csv(id,title)")
    ap.add_argument("--out", help="タグ付け結果 jsonl の出力先")
    ap.add_argument("--label", default="書式", help="出力ラベル (例: 書式 / 文献)")
    ap.add_argument("--list", action="store_true", help="手続別に一致した書名を列挙")
    ap.add_argument("--list-cap", type=int, default=8, help="--list の1類型あたり表示上限")
    args = ap.parse_args(argv)

    spine = load_spine(Path(args.spine))
    templates = load_templates(Path(args.templates))
    res = run(spine, templates)

    if args.out:
        p = Path(args.out); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(json.dumps(t, ensure_ascii=False) for t in res["tagged"]) + "\n",
                     encoding="utf-8")

    lb = args.label
    print(f"{lb} {res['total']} 件: 手続一致 {res['matched']} / 未一致 {res['unmatched']} "
          f"/ 曖昧 {res['ambiguous']}")
    by_name = {pt["id"]: f"{pt.get('系統','')} {pt.get('name','')}" for pt in spine}
    print(f"— 手続類型 × {lb}件数 (primary) —")
    for pid, n in sorted(res["coverage"].items(), key=lambda kv: -kv[1]):
        print(f"  {n:5d}  {by_name.get(pid, pid)}")
    if args.list:
        print(f"\n— 手続別 {lb}一覧 —")
        for pid, n in sorted(res["coverage"].items(), key=lambda kv: -kv[1]):
            print(f"▶ {by_name.get(pid, pid)} ({n})")
            for it in res["groups"].get(pid, [])[:args.list_cap]:
                print(f"    - {it['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
