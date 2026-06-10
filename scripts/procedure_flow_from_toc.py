"""会社法実務スケジュール等の詳細TOC → 手続フロー雛形を生成 (stdlib のみ).

段取り本の **詳細目次(TOC)** は「業務(章) → その段取り(節)」の順序を既に持つ。本スクリプトは
TOC を読み、上位レベル(章)を **業務=手続** とし、その配下(節)を**順序付き局面(node)**に落として
``pipeline/procedure_flow/<id>.json`` の雛形を吐く。各 node の source は「<書名> p<頁>」。

honest な限界: TOC は**順序**は持つが**分岐**は持たない → 生成物は線形 stub(``status:toc_stub``)。
分岐(公開/非公開・同時廃止/管財 等)は本文の日程表/フローチャートからの抽出＋監査で後付けする。
つまり本スクリプトは「巨人(本)の目次を機械可読な手続骨格に持ち上げる」第一段。

入力TOC: jsonl/json。各レコードのキーは緩く受ける:
  title: title|t|l|label|name   page: page|p|pg   level: level|depth|d|lv (小さいほど上位)
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _get(rec: dict, keys: list[str], default=None):
    for k in keys:
        if rec.get(k) not in (None, ""):
            return rec[k]
    return default


def _title(rec: dict) -> str:
    return str(_get(rec, ["title", "t", "l", "label", "name"], "")).strip()


def _page(rec: dict):
    return _get(rec, ["page", "p", "pg", "start_page"], None)


def _level(rec: dict) -> int:
    return int(_get(rec, ["level", "depth", "d", "lv"], 0) or 0)


def load_toc(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        recs = [json.loads(ln) for ln in text.splitlines() if ln.strip()]
    else:
        data = json.loads(text)
        recs = data if isinstance(data, list) else data.get("toc") or data.get("nodes") or []
    return [r for r in recs if _title(r)]


def _slug(s: str, idx: int) -> str:
    base = re.sub(r"[^0-9A-Za-z]+", "", s) or "proc"
    return f"{base[:16]}_{idx:03d}" if base.isascii() else f"proc_{idx:03d}"


def build_flows(toc: list[dict], book: str, isbn: str | None,
                proc_level: int | None = None) -> list[dict]:
    levels = [_level(r) for r in toc]
    top = min(levels) if levels else 0
    plevel = top if proc_level is None else proc_level

    groups: list[dict] = []
    cur: dict | None = None
    for r in toc:
        if _level(r) <= plevel:
            cur = {"title": _title(r), "page": _page(r), "steps": []}
            groups.append(cur)
        elif cur is not None:
            cur["steps"].append(r)
        else:  # 上位章の前にぶら下がる節 → 単独業務に退避
            cur = {"title": _title(r), "page": _page(r), "steps": []}
            groups.append(cur)

    flows = []
    src_book = f"{book}（{isbn}）" if isbn else book
    for gi, g in enumerate(groups, 1):
        pid = _slug(g["title"], gi)
        steps = g["steps"] or [{"_self": True, "title": g["title"], "page": g["page"]}]
        nodes = []
        for si, s in enumerate(steps, 1):
            nid = f"n{si:03d}"
            pg = _page(s) if not s.get("_self") else g["page"]
            node = {"id": nid, "局面": _title(s) if not s.get("_self") else g["title"],
                    "source": f"{src_book} p{pg}" if pg is not None else f"{src_book}（頁要記入）",
                    "次": ([{"to": f"n{si + 1:03d}"}] if si < len(steps) else [])}
            nodes.append(node)
        flows.append({
            "procedure_id": pid, "title": g["title"], "spine_ref": "",
            "status": "toc_stub",
            "_comment": "TOC から生成した線形 stub。分岐(公開/非公開 等)・根拠条文・期限・必要書類は"
                        "本文の日程表＋条文(e-Gov)から抽出し owner/GPT 監査で確定する。",
            "source_books": [src_book],
            "entry": nodes[0]["id"], "terminal": [nodes[-1]["id"]],
            "nodes": nodes,
        })
    return flows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="詳細TOC → 手続フロー雛形")
    ap.add_argument("--toc", required=True, help="書籍の詳細TOC (jsonl/json)")
    ap.add_argument("--book", default="会社法実務スケジュール", help="書名 (source 用)")
    ap.add_argument("--isbn", default=None)
    ap.add_argument("--proc-level", type=int, default=None,
                    help="この level 以下を業務(手続)とする (既定: 最上位)")
    ap.add_argument("--out-dir", default="pipeline/procedure_flow",
                    help="雛形 JSON の出力先 (空なら業務一覧のみ表示)")
    ap.add_argument("--write", action="store_true", help="雛形 JSON を書き出す")
    args = ap.parse_args(argv)

    toc = load_toc(Path(args.toc))
    flows = build_flows(toc, args.book, args.isbn, args.proc_level)

    print(f"{args.book}: 業務(手続) {len(flows)} 件を検出")
    for f in flows:
        print(f"  - {f['title']}  ({len(f['nodes'])} 局面)  [{f['procedure_id']}]")
    if args.write:
        out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
        for f in flows:
            (out / f"{f['procedure_id']}.json").write_text(
                json.dumps(f, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"→ {len(flows)} 件を {out} へ書き出し (status: toc_stub)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
