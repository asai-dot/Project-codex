#!/usr/bin/env python3
"""
finalize_result.py — controller/head 専用。candidate を final_RESULT として確定する。
worker から起動された場合は拒否(env ALO_FINALIZER 必須)。
"""
import argparse, hashlib, json, os, sys, uuid
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", required=True, type=Path)
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--out-final", required=True, type=Path)
    ap.add_argument("--out-record", required=True, type=Path)
    ap.add_argument("--decision-type", required=True, choices=["adopt", "modify_and_adopt", "reject", "hold", "canonical_promote", "external_publish"])
    ap.add_argument("--label", required=True)
    ap.add_argument("--processed-mark", action="store_true")
    ap.add_argument("--canonical-write", action="store_true")
    ap.add_argument("--rollback-plan")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    finalizer = os.environ.get("ALO_FINALIZER", "")
    if finalizer not in ("head", "controller", "human", "head_controller"):
        print("[finalize_result] BLOCK: ALO_FINALIZER env must be head|controller|human|head_controller", file=sys.stderr)
        sys.exit(2)
    if args.canonical_write and finalizer not in ("head", "controller", "human"):
        print("[finalize_result] BLOCK: canonical_write requires head|controller|human", file=sys.stderr)
        sys.exit(2)
    if args.canonical_write and not args.rollback_plan:
        print("[finalize_result] BLOCK: canonical_write requires --rollback-plan", file=sys.stderr)
        sys.exit(2)

    args.out_final.parent.mkdir(parents=True, exist_ok=True)
    args.out_final.write_bytes(args.candidate.read_bytes())

    rec = {
        "decision_id": str(uuid.uuid4()),
        "request_id": args.request.name,
        "run_id": None,
        "decision_type": args.decision_type,
        "label": args.label,
        "finalized_by": finalizer,
        "finalized_at": datetime.now(timezone.utc).isoformat(),
        "processed_mark_applied": args.processed_mark,
        "canonical_write_applied": args.canonical_write,
        "request_sha256": sha256(args.request),
        "candidate_sha256": sha256(args.candidate),
        "rollback_plan": args.rollback_plan,
        "notes": args.notes,
    }
    args.out_record.parent.mkdir(parents=True, exist_ok=True)
    args.out_record.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    print(f"[finalize_result] FINAL written: {args.out_final}  RECORD: {args.out_record}  by={finalizer}")


if __name__ == "__main__":
    main()
