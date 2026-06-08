"""パイプライン進捗ダッシュボード (manifest + snapshot → Markdown / HTML).

各ステージの status を probe 結果と依存から導出して可視化する:
  * done        ✅ 全 probe 完了。
  * waiting     ⏳ GPT/OCR 等の戻り待ち (roundtrip に pending あり)。
  * in_progress 🔄 一部進行。
  * blocked     ⛔ 依存ステージが未完 (入れない)。
  * todo        ⬜ 未着手。
  * error       ❗ probe エラー。

「どこが詰まっているか (blocked/waiting)」「どこが終わったか (done)」
「どこから入るか (todo かつ依存 done)」が一目で分かる。
roundtrip の pending/stale で「GPT 数が戻ってない/待ってる」を表示。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_probe import (  # noqa: E402
    ManifestError, collect, load_manifest, parse_roots, print_manifest_error,
)


def _roots_str(snapshot: dict) -> str:
    roots = snapshot.get("roots") or ({"default": snapshot["root"]} if snapshot.get("root") else {})
    return ", ".join(f"{k}=`{v}`" for k, v in roots.items()) or "?"

_ICON = {"done": "✅", "waiting": "⏳", "in_progress": "🔄",
         "blocked": "⛔", "todo": "⬜", "error": "❗"}
_COLOR = {"done": "#2e7d32", "in_progress": "#1565c0", "waiting": "#ef6c00",
          "blocked": "#c62828", "todo": "#9e9e9e", "error": "#6a1b9a"}


def _rollup(rows_by_id: dict, stage_ids: list[str]) -> dict | None:
    """構造オブジェクトに紐づくステージ群の runtime 状態を 1 つに集約 (無ければ None)。"""
    rs = [rows_by_id[s] for s in stage_ids if s in rows_by_id]
    if not rs:
        return None
    total = len(rs)
    done = sum(1 for r in rs if r["status"] == "done")
    if any(r["status"] == "error" for r in rs):
        st = "error"
    elif done == total:
        st = "done"
    elif any(r["status"] == "waiting" for r in rs):
        st = "waiting"
    elif any(r["status"] in ("in_progress", "done") for r in rs):
        st = "in_progress"
    elif all(r["status"] == "blocked" for r in rs):
        st = "blocked"
    else:
        st = "todo"
    return {"status": st, "done": done, "total": total}


def render_structure_md(manifest: dict, rows: list[dict]) -> list[str]:
    """DD 全体構造 (docs/dd_index.md の 7×6×4) を最上部に描く。live があれば roll-up。"""
    structure = manifest.get("structure")
    if not structure:
        return []
    rows_by_id = {r["id"]: r for r in rows}
    out = ["## 🗺 全体構造（静的7 / 動的6 / 横断）", "",
           "> DD 全体の正本構造 (`docs/dd_index.md`)。進捗は live 測定のあるオブジェクトのみ "
           "roll-up（`—` は外部ワークストリーム / 未起票で本パイプライン未測定）。", ""]
    groups = [("■ 静的データベース（7オブジェクト）", structure.get("static_objects", [])),
              ("■ 動的データベース（6ソース系統）", structure.get("dynamic_sources", [])),
              ("■ 横断層", structure.get("crosscutting", []))]
    for title, entries in groups:
        if not entries:
            continue
        out += [f"**{title}**", "", "| | 区分 | 進捗 | メモ |", "|---|---|---|---|"]
        for e in entries:
            ru = _rollup(rows_by_id, e.get("stages", []))
            icon = _ICON[ru["status"]] if ru else "·"
            prog = f"{ru['done']}/{ru['total']} done" if ru else "—"
            out.append(f"| {icon} | {e.get('label', e.get('id', '?'))} | {prog} | {e.get('note', '')} |")
            for s in e.get("subs", []):
                sru = _rollup(rows_by_id, s.get("stages", []))
                sicon = _ICON[sru["status"]] if sru else "·"
                sprog = f"{sru['done']}/{sru['total']} done" if sru else "—"
                out.append(f"| {sicon} | 　└ {s.get('label', s.get('id', '?'))} | {sprog} | {s.get('note', '')} |")
        out.append("")
    return out


def render_structure_html(manifest: dict, rows: list[dict]) -> str:
    structure = manifest.get("structure")
    if not structure:
        return ""
    rows_by_id = {r["id"]: r for r in rows}

    def chip(e: dict, cls: str = "schip") -> str:
        ru = _rollup(rows_by_id, e.get("stages", []))
        c = _COLOR[ru["status"]] if ru else "#bdbdbd"
        prog = f"{ru['done']}/{ru['total']}" if ru else "—"
        note = (e.get("note", "") or "").replace('"', "'")
        return (f'<span class="{cls}" title="{note}" style="border-left:4px solid {c}">'
                f'{e.get("label", "?")} <b>{prog}</b></span>')

    def block(entries: list[dict], with_subs: bool = False) -> str:
        parts = []
        for e in entries:
            parts.append(chip(e))
            if with_subs and e.get("subs"):
                parts.append('<div class="subs">'
                             + "".join(chip(s, "subchip") for s in e["subs"]) + '</div>')
        return "".join(parts)

    return (
        '<div class="struct"><h2>🗺 全体構造（静的7 / 動的6 / 横断）</h2>'
        '<div class="sgrp"><div class="sttl">静的DB（7オブジェクト）</div>'
        + block(structure.get("static_objects", []), with_subs=True) + '</div>'
        '<div class="sgrp"><div class="sttl">動的DB（6ソース系統）</div>'
        + block(structure.get("dynamic_sources", [])) + '</div>'
        '<div class="sgrp"><div class="sttl">横断層</div>'
        + block(structure.get("crosscutting", [])) + '</div></div>'
    )


def _probe_ratio(results: list[dict]) -> float:
    if not results:
        return 0.0
    total = 0.0
    for r in results:
        if r.get("type") == "count":
            total += r.get("ratio", 0.0)
        else:
            total += 1.0 if r.get("done") else 0.0
    return total / len(results)


def _has_waiting(results: list[dict], now: int) -> tuple[bool, int]:
    """roundtrip に未戻りがあるか。stale (古い未戻り) 件数も返す。"""
    waiting = False
    stale = 0
    for r in results:
        if r.get("type") == "roundtrip" and r.get("pending_count", 0) > 0:
            waiting = True
            max_age = r.get("max_age_hours", 24) * 3600
            for p in r.get("pending", []):
                basis = p.get("sent_epoch", p.get("sent_mtime", now))  # v0.2: front-matter優先
                if now - basis > max_age:
                    stale += 1
    return waiting, stale


def _has_count(results: list[dict]) -> bool:
    return any(r.get("type") == "count" for r in results)


def _progress_cell(row: dict) -> str:
    """exists-only/roundtrip は誤誘導する % を出さず present/待ち表示 (GPT 指摘#5)。"""
    results = row["probes"]
    if _has_count(results):
        return f"`{_bar(row['ratio'])}` {int(row['ratio']*100)}%"
    kinds = {r.get("type") for r in results}
    if kinds <= {"exists", "orphan"} and results:
        done = sum(1 for r in results if r.get("done"))
        return "有" if done == len(results) else ("一部" if done else "無")
    if "roundtrip" in kinds:
        return "完" if row["status"] == "done" else "待ち"
    return "—"


def derive(manifest: dict, snapshot: dict, now: int | None = None) -> list[dict]:
    now = now or int(time.time())
    snap_stages = snapshot.get("stages", {})
    done: dict[str, bool] = {}
    rows: list[dict] = []

    # manifest 順に評価 (依存は基本的に前方で定義される想定。done_map を逐次更新)。
    for stage in manifest.get("stages", []):
        sid = stage["id"]
        results = snap_stages.get(sid, {}).get("probes", [])
        ratio = _probe_ratio(results)
        all_done = bool(results) and all(r.get("done") for r in results)
        has_err = any("error" in r for r in results)
        waiting, stale = _has_waiting(results, now)

        deps = stage.get("depends_on", [])
        unmet = [d for d in deps if not done.get(d, False)]

        if has_err:
            status = "error"
        elif unmet:
            status = "blocked"
        elif all_done:
            status = "done"
        elif waiting:
            status = "waiting"
        elif ratio > 0:
            status = "in_progress"
        else:
            status = "todo"

        done[sid] = (status == "done")
        rows.append({
            "id": sid, "title": stage.get("title", sid),
            "track": stage.get("track", "other"), "owner": stage.get("owner", ""),
            "status": status, "ratio": round(ratio, 3), "deps": deps,
            "unmet_deps": unmet, "stale": stale, "note": stage.get("note", ""),
            "probes": results,
        })
    return rows


def _bar(ratio: float, width: int = 12) -> str:
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled)


def _probe_summary(results: list[dict]) -> str:
    parts = []
    for r in results:
        if r["type"] == "count":
            exp = r.get("expected")
            parts.append(f"{r['label']} {r['count']}/{exp if exp else '?'}")
        elif r["type"] == "exists":
            parts.append(f"{r['label']} {'有' if r['done'] else '無'}")
        elif r["type"] == "roundtrip":
            orphan = f" 孤{r['orphan_count']}" if r.get("orphan_count") else ""
            dup = f" 重{r['duplicate_count']}" if r.get("duplicate_count") else ""
            parts.append(f"{r['label']} 戻{r['returned']}/送{r['sent']}"
                         f"(未{r['pending_count']}){orphan}{dup}")
        elif r["type"] == "orphan":
            parts.append(f"{r['label']} 未宣言{r['orphan_count']}/{r['scan_count']}")
        elif "error" in r:
            parts.append(f"{r.get('label', '?')} ❗{r['error']}")
    return ", ".join(parts)


def render_markdown(manifest: dict, rows: list[dict], snapshot: dict) -> str:
    from collections import Counter

    counts = Counter(r["status"] for r in rows)
    blocked = [r for r in rows if r["status"] == "blocked"]
    waiting = [r for r in rows if r["status"] == "waiting"]
    ready = [r for r in rows if r["status"] == "todo" and not r["unmet_deps"]]

    when = snapshot.get("generated_at_jst") or snapshot.get("collected_at", "?")
    mhash = (snapshot.get("manifest_hash") or "")[:18]
    out = [
        f"# {manifest.get('title', 'パイプライン進捗')}",
        "",
        f"_収集: {when} / probe v{snapshot.get('probe_version', '?')} / "
        f"manifest {mhash} / roots: {_roots_str(snapshot)}_",
        "",
        "> 状態は **runtime_status（実行・運用状態）**。DD-STATUS-REGISTRY の "
        "artifact lifecycle（draft/candidate/accepted/canonical…）とは別軸。",
        "",
    ]
    out += render_structure_md(manifest, rows)
    errs = snapshot.get("manifest_errors") or []
    if errs:
        out.append("## ⚠ manifest エラー（描画は参考値）")
        out.append("")
        out.extend(f"- {e}" for e in errs)
        out.append("")
    out += [
        "## サマリ",
        "",
        "  ".join(f"{_ICON[s]}{s} {counts.get(s, 0)}"
                 for s in ["done", "in_progress", "waiting", "blocked", "todo", "error"]),
        "",
    ]
    if blocked or waiting or ready:
        out.append("## 要注目")
        out.append("")
        if waiting:
            out.append("**⏳ 戻り待ち (GPT/OCR 等):**")
            for r in waiting:
                stale = f" — ⚠stale {r['stale']}" if r["stale"] else ""
                out.append(f"- {r['title']} ({_probe_summary(r['probes'])}){stale}")
            out.append("")
        if blocked:
            out.append("**⛔ 依存待ちで入れない:**")
            for r in blocked:
                out.append(f"- {r['title']} ← 未完: {', '.join(r['unmet_deps'])}")
            out.append("")
        if ready:
            out.append("**▶ いま入れる (依存 done・未着手):**")
            for r in ready:
                out.append(f"- {r['title']}" + (f" ({r['owner']})" if r["owner"] else ""))
            out.append("")

    tracks = manifest.get("tracks", {})
    by_track: dict[str, list[dict]] = {}
    for r in rows:
        by_track.setdefault(r["track"], []).append(r)

    for tk, rs in by_track.items():
        out.append(f"## {tracks.get(tk, tk)}")
        out.append("")
        out.append("| | ステージ | 進捗 | 状態詳細 | 依存 | 担当 |")
        out.append("|---|---|---|---|---|---|")
        for r in rs:
            icon = _ICON[r["status"]]
            deps = ", ".join(r["deps"]) if r["deps"] else "—"
            out.append(f"| {icon} | {r['title']} | {_progress_cell(r)} | "
                       f"{_probe_summary(r['probes']) or '—'} | {deps} | {r['owner']} |")
        out.append("")

    # roundtrip の未戻り明細。
    pend_lines = []
    for sid, sdata in snapshot.get("stages", {}).items():
        for pr in sdata.get("probes", []):
            if pr.get("type") == "roundtrip" and pr.get("pending"):
                for p in pr["pending"]:
                    pend_lines.append(f"- [{sid}] {p['key']} (送信: {p['sent_file']})")
    if pend_lines:
        out.append("## 未戻り明細 (to_gpt → from_gpt)")
        out.append("")
        out.extend(pend_lines)
        out.append("")

    # N2: 同一 request_id の重複送信 (silent dedupe させず明示)。
    dup_lines = []
    for sid, sdata in snapshot.get("stages", {}).items():
        for pr in sdata.get("probes", []):
            if pr.get("type") == "roundtrip":
                for d in pr.get("duplicate", []):
                    dup_lines.append(f"- [{sid}] {d['key']} ← {', '.join(d['files'])}")
    if dup_lines:
        out.append("## ⚠ 重複 request_id (要 handoff 衛生)")
        out.append("")
        out.extend(dup_lines)
        out.append("")

    return "\n".join(out) + "\n"


def render_html(manifest: dict, rows: list[dict], snapshot: dict) -> str:
    color = _COLOR
    errs = snapshot.get("manifest_errors") or []
    cells = []
    for r in rows:
        c = color[r["status"]]
        has_count = _has_count(r["probes"])
        # exists/roundtrip は連続%にしない (binary present)。GPT 指摘#5。
        pct = int(r["ratio"] * 100) if has_count else (100 if r["status"] == "done" else 0)
        prog = _progress_cell(r)
        cells.append(
            f'<div class="card" style="border-left:6px solid {c}">'
            f'<div class="hd"><span class="ic">{_ICON[r["status"]]}</span>'
            f'<b>{r["title"]}</b> <span class="tk">{r["track"]}/{r["owner"]} · {prog}</span></div>'
            f'<div class="bar"><div class="fill" style="width:{pct}%;background:{c}"></div></div>'
            f'<div class="meta">{_probe_summary(r["probes"]) or "—"}'
            + (f' · 依存待ち: {", ".join(r["unmet_deps"])}' if r["unmet_deps"] else "")
            + (f' · ⚠stale {r["stale"]}' if r["stale"] else "")
            + "</div></div>"
        )
    err_html = ("<div class='err'>⚠ manifest エラー: "
                + "; ".join(errs) + "</div>") if errs else ""
    return (
        "<!doctype html><meta charset='utf-8'>"
        f"<title>{manifest.get('title','pipeline')}</title>"
        "<style>body{font-family:sans-serif;margin:24px;background:#fafafa}"
        ".card{background:#fff;margin:8px 0;padding:10px 14px;border-radius:6px;"
        "box-shadow:0 1px 3px rgba(0,0,0,.1)}.hd{margin-bottom:6px}.ic{margin-right:6px}"
        ".tk{color:#888;font-size:.8em;margin-left:6px}.bar{height:8px;background:#eee;"
        "border-radius:4px;overflow:hidden}.fill{height:100%}.meta{color:#555;"
        "font-size:.85em;margin-top:6px}"
        ".err{background:#fdecea;color:#c62828;padding:8px 12px;border-radius:6px;margin:8px 0}"
        ".fn{color:#888;font-size:.8em}"
        ".struct{background:#fff;border-radius:6px;padding:10px 14px;margin:8px 0;"
        "box-shadow:0 1px 3px rgba(0,0,0,.1)}.struct h2{margin:.2em 0 .4em;font-size:1.05em}"
        ".sgrp{margin:6px 0}.sttl{color:#666;font-size:.8em;margin-bottom:4px}"
        ".schip{display:inline-block;background:#fafafa;border:1px solid #eee;border-radius:4px;"
        "padding:3px 8px;margin:3px 4px 3px 0;font-size:.85em}.schip b{color:#333}"
        ".subs{margin:1px 0 5px 20px}.subchip{display:inline-block;background:#fff;"
        "border:1px solid #f0f0f0;border-radius:4px;padding:2px 7px;margin:2px 4px 2px 0;"
        "font-size:.78em;color:#666}.subchip b{color:#444}</style>"
        f"<h1>{manifest.get('title','pipeline')}</h1>"
        f"<p>収集: {snapshot.get('generated_at_jst', snapshot.get('collected_at','?'))} / "
        f"probe v{snapshot.get('probe_version','?')} / roots: {_roots_str(snapshot)}</p>"
        "<p class='fn'>状態は runtime_status（実行・運用状態）。artifact lifecycle"
        "（draft/candidate/accepted/canonical…）とは別軸。</p>"
        + render_structure_html(manifest, rows)
        + err_html
        + "".join(cells)
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="パイプライン ダッシュボード")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--snapshot", help="既存 snapshot.json (無ければ --root で収集)")
    ap.add_argument("--root", action="append", default=[], metavar="[NAME=]PATH",
                    help="snapshot が無いとき走査するルート (複数可)")
    ap.add_argument("--out-md")
    ap.add_argument("--out-html")
    args = ap.parse_args(argv)

    manifest = load_manifest(Path(args.manifest))
    if args.snapshot:
        snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    elif args.root:
        # N1: 収集+描画一発実行も collect() の検証→拒否ゲートを通す。
        # 不正 manifest はここで弾き、出力を一切書かずに exit 1。
        try:
            snapshot = collect(parse_roots(args.root), manifest)
        except ManifestError as e:
            print_manifest_error(e)
            return 1
    else:
        ap.error("--snapshot か --root のどちらかが必要")

    rows = derive(manifest, snapshot)
    md = render_markdown(manifest, rows, snapshot)
    if args.out_md:
        p = Path(args.out_md); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(md, encoding="utf-8")
    if args.out_html:
        p = Path(args.out_html); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render_html(manifest, rows, snapshot), encoding="utf-8")
    if not args.out_md and not args.out_html:
        print(md)
    else:
        from collections import Counter
        print(dict(Counter(r["status"] for r in rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
