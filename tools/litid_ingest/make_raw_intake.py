#!/usr/bin/env python3
"""make_raw_intake.py — raw_intake スケルトン + manifest テンプレ生成 (GO: 監査 recommended_next_steps #1).

INGEST_SPEC v0.2 のレーン構成に沿って raw_intake/<source>/<date>/ を作り,
各フォルダに §2 manifest の **TODO テンプレ** と DROP_HERE.md を置く. データは入れない (骨組みだけ).
TODO テンプレは意図的に manifest_gate を通らない (人が埋めて初めて投入可).

使い方:
  python3 make_raw_intake.py --root /path/to/raw_intake --date 20260618
  python3 make_raw_intake.py --root ./raw_intake --date 20260618 --sources legallib

read-only ではない (フォルダ/テンプレを作る) が, canonical/DDL/突合には一切触れない.
"""
from __future__ import annotations

import argparse
import json
import os

# INGEST_SPEC v0.2 §0/§7-B のルート別期待形 (手当ての手掛かりとしてテンプレに埋める)
ROUTE_HINTS = {
    "lionbolt": {"route_local_id": "book_id", "key_field": "isbn",
                 "toc_origin": "own_ocr", "medium_origin": "digital",
                 "rights_class": "owned", "lane": "isbn_ndl_lane"},
    "bengo4":   {"route_local_id": "content_id", "key_field": "content_id",
                 "toc_origin": "publisher_html", "medium_origin": "digital",
                 "rights_class": "subscription_access", "lane": "bengo4_noisbn_shadow"},
    "legallib": {"route_local_id": "legallib_book_id", "key_field": "isbn",
                 "toc_origin": "unknown", "medium_origin": "digital",
                 "rights_class": "subscription_access", "lane": "isbn_ndl_lane"},
    "self_scan": {"route_local_id": "scan_id", "key_field": "isbn",
                  "toc_origin": "own_ocr", "medium_origin": "paper_scan",
                  "rights_class": "owned", "lane": "isbn_ndl_lane"},
}

REQUIRED = [
    "source", "source_system", "fetched_at", "account", "fetch_method",
    "acquisition_path", "source_location", "rights_class", "medium_origin",
    "route_local_id", "key_field", "toc_origin", "extractor_version",
    "record_count", "files", "evidence_locator",
]


def manifest_template(source: str) -> dict:
    """全必須フィールドを持つ TODO テンプレ. ヒントのある箇所は既定値, 残りは TODO."""
    h = ROUTE_HINTS[source]
    t: dict = {}
    for f in REQUIRED:
        if f == "source":
            t[f] = source
        elif f in h:
            t[f] = h[f]
        elif f == "record_count":
            t[f] = 0  # 投入前は 0。field_profile が実数で上書きする
        elif f == "files":
            t[f] = [{"name": "TODO_dropped_filename", "sha256": "TODO_sha256", "bytes": None}]
        else:
            t[f] = f"TODO_{f}"
    t["_note"] = ("INGEST_SPEC v0.2 §7-A template. 推奨: field_profile.py --manifest-stub で"
                  "データ由来の下書きを作り直し、TODO/record_count/files を埋め、manifest_gate.py を"
                  f"PASS させてから投入。lane={h['lane']}")
    return t


def drop_readme(source: str, date: str) -> str:
    h = ROUTE_HINTS[source]
    return f"""# DROP HERE — {source} / {date}

INGEST_SPEC v0.2 のレーン: **{h['lane']}**

## 手順
1. このフォルダに raw データ (JSONL/NDJSON) をドロップ。
2. プロファイル + manifest 下書き:
   ```
   python3 tools/litid_ingest/field_profile.py <dropped>.jsonl --source {source} \\
       --out-md profile.md --manifest-stub manifest.json
   ```
3. `manifest.json` の TODO を埋める (取得時メタ: account/fetched_at/source_location/
   acquisition_path/extractor_version/evidence_locator)。
4. ゲート通過を確認 (PASS しないと投入不可):
   ```
   python3 tools/litid_ingest/manifest_gate.py manifest.json
   ```

## このルートの期待形 (ヒント)
- route_local_id: `{h['route_local_id']}` / key_field: `{h['key_field']}`
- toc_origin: `{h['toc_origin']}` / medium: `{h['medium_origin']}` / rights: `{h['rights_class']}`

データ本体はリポジトリに入れない (容量・権利)。self_scan は PDF 本体ではなく奥付メタのみ。
"""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, help="raw_intake ルート (Box同期パス等)")
    ap.add_argument("--date", required=True, help="バッチ日付 YYYYMMDD")
    ap.add_argument("--sources", nargs="*", default=list(ROUTE_HINTS),
                    choices=list(ROUTE_HINTS))
    ap.add_argument("--force", action="store_true", help="既存テンプレを上書き")
    args = ap.parse_args(argv)

    made = []
    for source in args.sources:
        d = os.path.join(args.root, source, args.date)
        os.makedirs(d, exist_ok=True)

        mpath = os.path.join(d, "manifest.template.json")
        if args.force or not os.path.exists(mpath):
            with open(mpath, "w", encoding="utf-8") as fh:
                json.dump(manifest_template(source), fh, ensure_ascii=False, indent=2)

        rpath = os.path.join(d, "DROP_HERE.md")
        if args.force or not os.path.exists(rpath):
            with open(rpath, "w", encoding="utf-8") as fh:
                fh.write(drop_readme(source, args.date))

        made.append(d)

    print("created raw_intake skeleton:")
    for d in made:
        print(f"  {d}/  (manifest.template.json, DROP_HERE.md)")
    print("\nテンプレは TODO のまま = manifest_gate を通らない (設計どおり). "
          "データ投下後に field_profile --manifest-stub で作り直して埋める。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
