#!/usr/bin/env python3
"""
DD-FORMOBJ-001 完成ドライバ: S2 snapshot(anchor確定) → 完成 form_object

手順: S2スナップショット群 → form_canonical_merge(S3) → form_uid発番 → form_object出力。
form_uid: 現状はDB登録前なので anchor 由来の決定的・暫定ID(再現可能・sticky)。
          正式 sticky ULID は S5(DB persist)で発番、resolution_logで対応。
"""
from __future__ import annotations
import json, sys, os, hashlib, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from form_canonical_merge import Snapshot, merge_snapshots

def provisional_form_uid(canonical_book_id: str, toc_node_id: str) -> str:
    h = hashlib.sha1(f"{canonical_book_id}|{toc_node_id}".encode()).hexdigest()[:16]
    return f"alo:form:prov:{h}"

def complete(snapshot_files: list[str], out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for f in snapshot_files:
        snap = json.load(open(f, encoding="utf-8"))
        a = snap["anchor"]
        blocks = snap["content"]["blocks"]
        canon = merge_snapshots([Snapshot(snap["source"]["source_system"], blocks,
                                          snap["source"].get("provenance_group"))])
        anchored = bool(a.get("toc_node_id") and a.get("canonical_book_id"))
        fuid = provisional_form_uid(a.get("canonical_book_id") or "?", a.get("toc_node_id") or "?") if anchored else None
        content = {"blocks": canon.blocks, "blanks_total": canon.blanks_total,
                   "block_count": canon.block_count,
                   "clause_count": snap["content"].get("clause_count"),
                   "item_count": snap["content"].get("item_count")}
        fo = {
            "schema": "form_object.v1",
            "form_uid": fuid,
            "form_uid_kind": "provisional_deterministic (DB登録前; 正式ULIDはS5)",
            "anchor": {k: a.get(k) for k in
                       ("canonical_book_id","toc_node_id","page_span_print","page_span_pdf","span_kind","anchor_status")},
            "book_ref": a.get("book_ref"),
            "form_title": snap["form_title"], "form_kind": snap.get("form_kind"),
            "language": snap.get("language"),
            "content": content,
            "canonical_source": canon.canonical_source,
            "provenance": {"sources_used": canon.sources_used, "agreement": canon.agreement,
                           "discrepancies": canon.discrepancies},
            "quality": {"ocr_error_classes": canon.ocr_error_classes, "corrections": canon.corrections,
                        "notes": snap.get("quality",{}).get("notes")},
            "confidence": canon.confidence,
            "content_coverage": snap.get("anchor",{}).get("toc_ref",{}).get("scope_note") or "full",
            "content_sha1": hashlib.sha1(json.dumps(content, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12],
            "established_at": datetime.date.today().isoformat(),
            "established_by": "remote-claude (S0-S3 reference impl)",
        }
        name = os.path.splitext(os.path.basename(f))[0].replace(".s2","")
        outp = f"{out_dir}/{name}.formobj.json"
        json.dump(fo, open(outp, "w"), ensure_ascii=False, indent=2)
        results.append((name, fuid, canon.canonical_source, canon.confidence["final"],
                        content["block_count"], content["blanks_total"], anchored))
        print(f"{name}: uid={fuid} src={canon.canonical_source} conf={canon.confidence['final']} "
              f"blocks={content['block_count']} blanks={content['blanks_total']} anchored={anchored}")
    return results

if __name__ == "__main__":
    base = os.path.join(os.path.dirname(__file__), "..", "docs/tmplstruct/s2_snapshots")
    files = [os.path.join(base, x) for x in
             ("keiyakukaisho_kaijo_tsuchi.s2.json", "gyomu_seizo_kihon_keiyaku.s2.json")]
    complete(files, os.path.join(os.path.dirname(__file__), "..", "docs/tmplstruct/form_objects"))
