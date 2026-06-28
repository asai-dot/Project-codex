#!/usr/bin/env python3
"""
scan_queue.py — L0_DETERMINISTIC: queue 走査(Claudeに探索させない)

入力: queue_root (例: artifacts/periodical/, または .claude-orch/triggers/)
出力: queue_snapshot.json
     [
       {request_id, title, source, gate, status, ctime, mtime, sha256, size}
     ]

不変条件:
- LLM を呼ばない (HD3_no_llm_for_l0)
- 判断しない・分類しない
- 探索範囲を引数で固定する
"""
import argparse, hashlib, json, os, sys, time
from pathlib import Path


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(root: Path, patterns):
    items = []
    for pat in patterns:
        for p in sorted(root.rglob(pat)):
            if not p.is_file():
                continue
            st = p.stat()
            items.append({
                "request_id": str(p.relative_to(root)),
                "title": p.name,
                "source": str(p),
                "gate": None,
                "status": "queued",
                "ctime": int(st.st_ctime),
                "mtime": int(st.st_mtime),
                "sha256": sha256_file(p),
                "size": st.st_size,
            })
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--pattern", action="append", default=["ORCH-*.md", "*.trigger"])
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    if not args.root.exists():
        print(f"[scan_queue] root not found: {args.root}", file=sys.stderr)
        sys.exit(2)

    items = scan(args.root, args.pattern)
    snapshot = {
        "version": "v0.1",
        "scanned_at": int(time.time()),
        "root": str(args.root),
        "patterns": args.pattern,
        "items": items,
        "count": len(items),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f"[scan_queue] wrote {args.out} ({len(items)} items)")


if __name__ == "__main__":
    main()
