#!/usr/bin/env python3
"""D1文献編 誌名ラベル付与 v0.2.1（catch-all フォルダの掲載誌等ベース分割）

v0.2 の課題:
  取得時に広すぎる検索語で落としたフォルダ（例: フォルダ「法学」46,279件）は、中身が
  法学セミナー/月刊法学教室/法学協会雑誌(評釈4位)/立命館法学… と多数の別誌の寄せ集め。
  v0.2 は「フォルダ名＝誌名」なので、これらが全部「法学」に潰れて埋もれていた。

v0.2.1 の方針:
  - 各 canonical フォルダについて、配下レコードの `掲載誌等` 先頭(=記事ごとの実誌名)が
    フォルダ名とどれだけ一致するか(agreement)を測る。
  - agreement が低い大きめフォルダ＝catch-all と判定し、そのフォルダのレコードだけ
    `掲載誌等` 先頭で誌名を割り直す。純粋フォルダ(ジュリスト等)は v0.2 のまま不変。
  - 非破壊・冪等: 入力 jsonl は読むだけ。<build>/labeled_v0.2.1/ に新規出力。件数不変。

使い方:
  python3 label_journals_v0.2.1.py <article_meta_all.jsonl> [priority.json]
"""
import json
import sys
import os
import re
import unicodedata
import collections

_SUFFIX_NOISE = ["雑誌記事メタデータ"]
_ALIAS = {
    "Law Technology": "Law & Technology",
    "Law Practice": "Law & Practice",
    "Patents Licensing": "Patents & Licensing",
}

# 同一誌が複数の正式名で出るものの統合（最終 canonical に対して適用）。
# 例: 法学教室の本体は catch-all 法学から「月刊法学教室」として救出されるが、
# 独立フォルダ「法学教室」も存在するため、両者を1誌に寄せる。
_MERGE = {
    "月刊法学教室": "法学教室",
}

# catch-all 判定: フォルダ件数がこの値以上で、配下レコードの掲載誌等先頭(=実誌名)が
# 「最頻誌のシェア < _MAX_DOMINANT」かつ「実質_MIN_DISTINCT誌以上に散る」場合のみ寄せ集めとみなす。
# 単一誌が表記ゆれで複数名になっているだけ（最頻誌が支配的）のフォルダは分割しない。
_CATCHALL_MIN_SIZE = 300
_CATCHALL_MAX_DOMINANT = 0.5
_CATCHALL_MIN_DISTINCT = 4
_CATCHALL_MIN_CONSTITUENT = 20


def normalize(name: str) -> str:
    """フォルダ名/掲載誌名を比較可能な正規形へ（NFKC・括弧以降切り・接尾辞除去・空白畳み）。"""
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", name)
    s = re.split(r"[(]", s, 1)[0]
    for suf in _SUFFIX_NOISE:
        s = s.replace(suf, "")
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def journal_from_path(source_file: str) -> str:
    if not source_file:
        return ""
    parts = [p for p in source_file.split("/") if p]
    return parts[-2] if len(parts) >= 2 else ""


def journal_from_etc(etc: str) -> str:
    """`掲載誌等`（例 "法学研究（慶応義塾大学）83巻,p1"）の先頭＝記事の実誌名を取り出す。

    巻号(数字)の手前までを誌名とみなす。大学名などの括弧修飾は残す（誌の区別に効く）。
    """
    if not etc:
        return ""
    s = unicodedata.normalize("NFKC", etc)
    s = s.lstrip("『「（(")            # 先頭の括弧・引用記号を除去
    s = re.split(r"[0-9]", s, 1)[0]   # 最初の数字(巻号)で切る
    s = s.strip(" 　,，、。.・（(「『")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def folder_canonical_of(source_file: str) -> str:
    norm = normalize(journal_from_path(source_file))
    return _ALIAS.get(norm, norm)


def load_priority_names(path: str) -> set:
    names = set()

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str):
            nm = normalize(o)
            if nm:
                names.add(nm)

    with open(path, encoding="utf-8") as f:
        walk(json.load(f))
    return names


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python3 label_journals_v0.2.1.py <article_meta_all.jsonl> [priority.json]")
    src = sys.argv[1]
    priority = sys.argv[2] if len(sys.argv) > 2 else None
    priority_names = load_priority_names(priority) if priority else None

    # ---- pass1: フォルダ canonical ごとに、配下レコードの掲載誌等先頭(=実誌名)の分布を集計 ----
    folder_total = collections.Counter()
    folder_etc = collections.defaultdict(collections.Counter)
    with open(src, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            fc = folder_canonical_of(r.get("_source_file", ""))
            folder_total[fc] += 1
            etc_j = journal_from_etc(r.get("掲載誌等", ""))
            if etc_j:
                folder_etc[fc][etc_j] += 1

    # 寄せ集め判定: 最頻誌のシェアが低く(<_MAX_DOMINANT)、かつ実質_MIN_DISTINCT誌以上に散る。
    # 単一誌の表記ゆれ（最頻誌が支配的）は分割しない＝金融法務事情↔旬刊金融法務事情の誤分裂を防ぐ。
    catchall = set()
    catchall_report = []
    for fc, total in folder_total.items():
        if not fc or total < _CATCHALL_MIN_SIZE:
            continue
        etcc = folder_etc.get(fc)
        if not etcc:
            continue
        dom, dom_n = etcc.most_common(1)[0]
        dom_share = dom_n / total
        distinct = sum(1 for v in etcc.values() if v >= _CATCHALL_MIN_CONSTITUENT)
        if dom_share < _CATCHALL_MAX_DOMINANT and distinct >= _CATCHALL_MIN_DISTINCT:
            catchall.add(fc)
            catchall_report.append({
                "folder": fc, "size": total,
                "dominant": dom, "dominant_share": round(dom_share, 3),
                "distinct_journals": distinct,
            })
    catchall_report.sort(key=lambda d: -d["size"])

    # ---- pass2: 出力。catch-all フォルダは掲載誌等で誌名を割り直す ----
    out_dir = os.path.join(os.path.dirname(src), "labeled_v0.2.1")
    os.makedirs(out_dir, exist_ok=True)
    out_jsonl = os.path.join(out_dir, "article_meta_labeled.jsonl")

    by_canonical = collections.Counter()
    source_counter = collections.Counter()
    unmapped = collections.Counter()
    n = 0
    with open(src, encoding="utf-8") as f, open(out_jsonl, "w", encoding="utf-8") as w:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            raw = journal_from_path(r.get("_source_file", ""))
            norm = normalize(raw)
            fc = _ALIAS.get(norm, norm)
            etc_j = journal_from_etc(r.get("掲載誌等", ""))
            if fc in catchall:
                canonical = etc_j or fc           # 掲載誌等が空なら従来のフォルダ名へ退避
                source = "etc_catchall" if etc_j else "folder_fallback"
            else:
                canonical = fc
                source = "folder"
            canonical = _MERGE.get(canonical, canonical)   # 同一誌の別名統合
            meishi_norm = normalize(r.get("掲載誌名") or "")
            if meishi_norm:
                source = source + "+meishi"
            r["journal_raw"] = raw
            r["journal_norm"] = norm
            r["journal_canonical"] = canonical
            r["journal_source"] = source
            if priority_names is not None:
                in_pri = canonical in priority_names
                r["in_priority"] = in_pri
                if not in_pri:
                    unmapped[canonical] += 1
            w.write(json.dumps(r, ensure_ascii=False) + "\n")
            by_canonical[canonical] += 1
            source_counter[source] += 1
            n += 1

    q = by_canonical.get("", 0)
    summary = {
        "input": src,
        "records": n,
        "journals_canonical": len(by_canonical),
        "empty_journal": q,
        "catchall_folders": catchall_report,
        "by_source": dict(source_counter),
        "by_journal_canonical_top50": by_canonical.most_common(50),
    }
    if priority_names is not None:
        summary["unmapped_vs_priority_top30"] = unmapped.most_common(30)

    with open(os.path.join(out_dir, "summary_labeled.json"), "w", encoding="utf-8") as w:
        json.dump(summary, w, ensure_ascii=False, indent=1)

    print(f"records              : {n}")
    print(f"empty journal (?)    : {q}   <-- 0 が目標")
    print(f"canonical 誌数        : {len(by_canonical)}")
    print(f"catch-all フォルダ     : {[d['folder'] for d in catchall_report]}")
    for d in catchall_report:
        print(f"    {d['folder']}  size={d['size']} 最頻={d['dominant']}({d['dominant_share']}) 実質{d['distinct_journals']}誌 → 掲載誌等で分割")
    print(f"source               : {dict(source_counter)}")
    print("--- by_journal_canonical TOP35 ---")
    for k, v in by_canonical.most_common(35):
        print(f"  {v:>7}  {k}")
    if priority_names is not None:
        print("--- canonical が優先JSONに無い(上位) ---")
        for k, v in unmapped.most_common(15):
            print(f"  {v:>6}  {k}")
    print(f"\nwrote: {out_jsonl}")


if __name__ == "__main__":
    main()
