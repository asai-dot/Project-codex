"""パイプライン進捗の probe ランナー + 状態コレクタ.

実ファイルシステム (Box 同期 / ~/alo-ai 等) を走査し、各ステージの「実状態」を
小さな snapshot.json に落とす。重い走査は Mac 側で実行し、snapshot だけを
本リポジトリへ戻せば web 側でダッシュボード描画・差分追跡ができる。

probe 種別:
  * count     : glob 件数 vs expected (取得率)。「出せてない/未取得」を見る。
  * exists    : glob にマッチが 1 つでもあるか (成果物の有無)。
  * roundtrip : 送信 (例 to_gpt/*REQUEST) と 戻り (from_gpt/*RESULT) を
                キーで突合。pending(戻ってない) / orphan(送信なしの戻り) /
                stale(古いまま戻らない=詰まり) を出す。「GPT数が戻ってない/
                待ってる」を見る。

snapshot は純データ (status 判定は dashboard 側)。冪等・stdlib のみ。
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

# roundtrip のキー化: 末尾の役割サフィックスを落として送信/戻りを同一キーに。
_RT_SUFFIX = re.compile(
    r"[_\-]?(request|result|response|reply|answer|req|res|out|in|送信|戻り|依頼|回答)$",
    re.IGNORECASE,
)


def _glob(root: Path, pattern: str) -> list[Path]:
    # pathlib.glob は ** もサポート。隠し対策は不要。
    return sorted(p for p in root.glob(pattern) if p.is_file())


def _roundtrip_key(stem: str, key_pattern: str | None) -> str:
    if key_pattern:
        m = re.search(key_pattern, stem)
        return m.group(1) if m else stem
    return _RT_SUFFIX.sub("", stem)


def run_probe(root: Path, probe: dict) -> dict:
    ptype = probe.get("type")
    label = probe.get("label", ptype)

    if ptype == "count":
        files = _glob(root, probe["path"])
        expected = probe.get("expected")
        count = len(files)
        ratio = (min(count / expected, 1.0) if expected else (1.0 if count else 0.0))
        return {
            "type": "count", "label": label, "path": probe["path"],
            "count": count, "expected": expected, "ratio": round(ratio, 4),
            "done": (count >= expected) if expected else bool(count),
        }

    if ptype == "exists":
        files = _glob(root, probe["path"])
        return {
            "type": "exists", "label": label, "path": probe["path"],
            "match_count": len(files), "done": bool(files),
        }

    if ptype == "roundtrip":
        kp = probe.get("key_pattern")
        sent = _glob(root, probe["sent"])
        returned = _glob(root, probe["returned"])
        sent_keys: dict[str, Path] = {}
        for p in sent:
            sent_keys.setdefault(_roundtrip_key(p.stem, kp), p)
        ret_keys = {_roundtrip_key(p.stem, kp) for p in returned}

        pending = []
        for key, p in sent_keys.items():
            if key not in ret_keys:
                pending.append({"key": key, "sent_file": p.name,
                                "sent_mtime": int(p.stat().st_mtime)})
        orphan = sorted(ret_keys - set(sent_keys))
        # snapshot を小さく保つため pending は古い順に上限件数だけ詳細保持。
        pending.sort(key=lambda x: x["sent_mtime"])
        cap = probe.get("detail_cap", 50)
        return {
            "type": "roundtrip", "label": label,
            "sent": len(sent_keys), "returned": len(ret_keys),
            "pending_count": len(pending), "pending": pending[:cap],
            "orphan_count": len(orphan), "orphan": orphan[:cap],
            "max_age_hours": probe.get("max_age_hours", 24),
            "done": len(pending) == 0 and len(sent_keys) > 0,
        }

    return {"type": ptype, "label": label, "error": f"unknown probe type: {ptype}"}


def collect(roots: dict[str, Path] | Path, manifest: dict) -> dict:
    # 単一 Path も許容 (default ルートとして扱う)。
    if isinstance(roots, Path):
        roots = {"default": roots}

    def resolve(probe: dict) -> Path:
        rk = probe.get("root", "default")
        return roots.get(rk) or roots.get("default") or next(iter(roots.values()))

    stages_out = {}
    for stage in manifest.get("stages", []):
        results = [run_probe(resolve(pr), pr) for pr in stage.get("probes", [])]
        stages_out[stage["id"]] = {"probes": results}
    return {
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "collected_epoch": int(time.time()),
        "roots": {k: str(v) for k, v in roots.items()},
        "manifest_version": manifest.get("version"),
        "stages": stages_out,
    }


def parse_roots(values: list[str]) -> dict[str, Path]:
    """``--root name=path`` を複数、または ``--root path`` 単体を dict 化。"""
    roots: dict[str, Path] = {}
    for v in values:
        if "=" in v:
            name, _, path = v.partition("=")
            roots[name.strip()] = Path(path).expanduser()
        else:
            roots["default"] = Path(v).expanduser()
    return roots


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="パイプライン状態コレクタ")
    ap.add_argument("--root", action="append", default=[], metavar="[NAME=]PATH",
                    help="走査ルート。複数可 (例: --root bookdx=/Box/... --root alo=~/alo-ai)")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True, help="snapshot.json 出力先")
    args = ap.parse_args(argv)

    if not args.root:
        ap.error("--root を最低 1 つ指定 (例: --root /path または --root alo=/path)")
    roots = parse_roots(args.root)
    manifest = load_manifest(Path(args.manifest))
    snap = collect(roots, manifest)
    Path(args.out).write_text(json.dumps(snap, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    print(f"collected {len(snap['stages'])} stages, roots={list(roots)} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
