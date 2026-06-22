#!/usr/bin/env python3
"""R1: NDL ダンプの inventory / schema / hash を read-only で検証する。

機械処理（front-loaded）。ローカルちゃんは `python3 r1_probe.py <DUMP_DIR>` を実行するだけ。
出力 out/ :
  R1_inventory.json   : ファイル一覧・サイズ・sha256（ストリーミング計算）
  R1_schema_map.json  : 各CSVの encoding/delimiter/列マッピング自動判定（★人が1回だけ目視）
  R1_probe_report.md  : 人間向けサマリ

source file は一切変更しない（read-only）。
"""
import sys, os, json, csv, glob, hashlib, re, argparse, datetime
from isbn_util import normalize_to_isbn13

ENCODINGS = ["utf-8-sig", "utf-8", "cp932", "shift_jis", "euc_jp"]
HDR = {
    "isbn":      ["isbn", "ＩＳＢＮ"],
    "ndl_bib_id":["書誌id", "bibid", "bib_id", "ndlbibid", "jpno", "jp番号", "レコードid", "永続的識別子", "識別子"],
    "title":     ["タイトル", "title", "本タイトル", "標題"],
    "publisher": ["出版者", "出版社", "publisher", "頒布者"],
    "pub_year":  ["出版年", "発行年", "出版日付", "issued", "date", "年"],
    "edition":   ["版", "edition", "版表示"],
}


def sha256_stream(path, limit_bytes=None):
    h = hashlib.sha256(); read = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk); read += len(chunk)
            if limit_bytes and read >= limit_bytes:
                break
    return h.hexdigest(), read


def sniff_text(path):
    """encoding を試行し、先頭数KBをデコードして返す。"""
    raw = open(path, "rb").read(65536)
    for enc in ENCODINGS:
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace"), "utf-8(replace)"


def guess_delim(sample):
    counts = {d: sample.count(d) for d in [",", "\t", "|"]}
    return max(counts, key=counts.get)


def map_columns(header_cells, data_rows):
    """ヘッダ語 → 役割。ヘッダ語で当たらない列は内容ヒューリスティックで ISBN/bibid を推定。"""
    norm = [re.sub(r"[\s_\-]", "", (c or "").strip().lower()) for c in header_cells]
    role = {}
    for role_name, keys in HDR.items():
        for idx, h in enumerate(norm):
            if any(k in h for k in keys):
                role.setdefault(role_name, idx); break
    # 内容ヒューリスティック（ヘッダ判定の補強）
    ncol = len(header_cells)
    isbn_hit = [0] * ncol; bibid_like = [0] * ncol
    for r in data_rows:
        for i in range(min(ncol, len(r))):
            v = (r[i] or "").strip()
            if normalize_to_isbn13(v):
                isbn_hit[i] += 1
            elif re.fullmatch(r"[0-9]{8,12}", re.sub(r"\D", "", v) or "x") and v:
                bibid_like[i] += 1
    if "isbn" not in role and any(isbn_hit):
        role["isbn"] = isbn_hit.index(max(isbn_hit))
    if "ndl_bib_id" not in role and any(bibid_like):
        cand = bibid_like.index(max(bibid_like))
        if cand != role.get("isbn"):
            role["ndl_bib_id"] = cand
    return role


def probe_csv(path):
    text, enc = sniff_text(path)
    lines = text.splitlines()
    delim = guess_delim(lines[0] if lines else "")
    rdr = list(csv.reader(lines[:50], delimiter=delim))
    header, data = (rdr[0], rdr[1:]) if rdr else ([], [])
    # ヘッダらしさ: 1行目に数字主体のISBNが無く、既知語があるか
    looks_header = any(any(k in re.sub(r"[\s_\-]", "", (c or "").lower()) for ks in HDR.values() for k in ks) for c in header)
    if not looks_header:  # ヘッダ無しデータ → 役割は内容のみで推定
        data = rdr; header = [f"col{i}" for i in range(len(rdr[0]) if rdr else 0)]
    role = map_columns(header, data)
    return {"encoding": enc, "delimiter": delim, "has_header": looks_header,
            "header": header, "column_roles": role,
            "roles_found": sorted(role.keys()),
            "sample_row": (data[0] if data else [])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump_dir", help="NDLダンプのフォルダ（Box Drive 同期パス）")
    ap.add_argument("--out", default="out")
    ap.add_argument("--full-hash", action="store_true", help="全バイトでsha256（既定は先頭16MBのみで高速）")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    csvs = sorted(glob.glob(os.path.join(a.dump_dir, "ndl_all_records_*.csv")))
    extra = [p for p in glob.glob(os.path.join(a.dump_dir, "*")) if os.path.isfile(p) and not p.endswith(".csv")]
    if not csvs:
        print("!! ndl_all_records_*.csv が見つかりません。dump_dir を確認してください:", a.dump_dir); sys.exit(2)

    inv = []
    for p in csvs + extra:
        digest, read = sha256_stream(p, None if a.full_hash else 16 << 20)
        inv.append({"file": os.path.basename(p), "bytes": os.path.getsize(p),
                    "sha256": digest, "sha256_scope": "full" if a.full_hash else "first16MB"})
    schema = {}
    for p in csvs[:3]:  # 先頭3分割でスキーマ判定（全件同形と仮定。違えば report に出る）
        schema[os.path.basename(p)] = probe_csv(p)
    law = next((p for p in extra if "law_isbn" in os.path.basename(p)), None)
    law_probe = None
    if law:
        t, enc = sniff_text(law)
        law_probe = {"encoding": enc, "first_lines": t.splitlines()[:5]}

    json.dump({"generated_at": datetime.datetime.now().isoformat(), "dump_dir": a.dump_dir,
               "file_count": len(csvs), "files": inv}, open(f"{a.out}/R1_inventory.json", "w"), ensure_ascii=False, indent=2)
    json.dump({"csv_schema": schema, "ndl_law_isbn": law_probe}, open(f"{a.out}/R1_schema_map.json", "w"), ensure_ascii=False, indent=2)

    with open(f"{a.out}/R1_probe_report.md", "w", encoding="utf-8") as f:
        f.write("# R1 probe report\n\n")
        f.write(f"- dump_dir: {a.dump_dir}\n- csv files: {len(csvs)}\n- 付随ファイル: {[os.path.basename(p) for p in extra]}\n\n")
        f.write("## スキーマ自動判定（要・人間の目視確認）\n")
        for name, s in schema.items():
            f.write(f"\n### {name}\n- encoding: {s['encoding']} / delimiter: {repr(s['delimiter'])} / header: {s['has_header']}\n")
            f.write(f"- 検出列: {s['roles_found']}\n- column_roles: {s['column_roles']}\n- header: {s['header']}\n")
            miss = [r for r in ("isbn", "ndl_bib_id") if r not in s["column_roles"]]
            if miss:
                f.write(f"- ⚠ 未検出の重要列: {miss} → R1_schema_map.json を手で補ってから r2 を実行\n")
        if law_probe:
            f.write(f"\n## ndl_law_isbn.txt 先頭\n```\n" + "\n".join(law_probe["first_lines"]) + "\n```\n")
    print("OK: out/R1_inventory.json, out/R1_schema_map.json, out/R1_probe_report.md")
    print("→ 次: out/R1_schema_map.json の column_roles を目視確認（isbn/ndl_bib_id が正しいか）してから r2_build_index.py")


if __name__ == "__main__":
    main()
