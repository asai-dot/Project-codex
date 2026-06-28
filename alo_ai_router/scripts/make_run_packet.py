#!/usr/bin/env python3
"""
make_run_packet.py — head/controller が confirmed_run_packet.yaml を作る。
1件だけ・max_items=1 強制・mutation_power は draft_write 上限。
"""
import argparse, hashlib, json, sys, uuid, yaml
from pathlib import Path


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decision", required=True, type=Path, help="route_decision.json")
    ap.add_argument("--queue-item", required=True, type=Path)
    ap.add_argument("--input", action="append", default=[], help="path:role 形式 (最大5本)")
    ap.add_argument("--expected-output", action="append", required=True, help="path:type")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    if len(args.input) > 5:
        print("[make_run_packet] inputs max 5", file=sys.stderr)
        sys.exit(2)

    decision = json.loads(args.decision.read_text())
    item = json.loads(args.queue_item.read_text())
    if decision.get("status") != "routed":
        print(f"[make_run_packet] decision not routed: {decision.get('status')}", file=sys.stderr)
        sys.exit(3)

    inputs = []
    for spec in args.input:
        path_s, _, role = spec.partition(":")
        p = Path(path_s)
        if not p.exists():
            print(f"[make_run_packet] input not found: {p}", file=sys.stderr)
            sys.exit(4)
        inputs.append({"path": str(p), "sha256": sha256_file(p), "role": role or "input"})

    expected = []
    for spec in args.expected_output:
        path_s, _, typ = spec.partition(":")
        expected.append({"path": path_s, "type": typ or "RESULT_CANDIDATE"})

    packet = {
        "packet_id": str(uuid.uuid4()),
        "request_id": item["request_id"],
        "executor_role": decision["model_role"],
        "executor_model": decision.get("selected_model"),
        "mutation_power": decision.get("granted_mutation_power", "draft_write"),
        "max_items": 1,
        "inputs": inputs,
        "constraints": {
            "allow_packet_extra_search": False,
            "no_finalization": True,
            "no_processed_mark": True,
            "external_timeout_seconds": 900,
            "data_zone": item["data"].get("data_zone"),
            "no_external_send": item["data"].get("data_zone") in ("scan_raw", "signy_first_pub", "legal_thought_raw", "client_privileged", "credentials", "passwords"),
        },
        "expected_outputs": expected,
        "forbidden_outputs": item.get("outputs", {}).get("forbidden", []),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(yaml.safe_dump(packet, allow_unicode=True, sort_keys=False))
    print(f"[make_run_packet] wrote {args.out}  role={packet['executor_role']} inputs={len(inputs)}")


if __name__ == "__main__":
    main()
