#!/usr/bin/env python3
"""D1文献編 誌名ラベル付与 v0.2（後処理・非破壊・冪等）

背景:
  パーサ v0.1 の出力 article_meta_all.jsonl は、綺麗な誌名フィールド `掲載誌名` が
  全体の約2%(5,830/282,761)にしか無く、誌別集計が ~98% 「?」になっていた。
  ただし全レコードに `_source_file`(取得元RTFの絶対パス)があり、その親フォルダ名＝誌名。
  → 本スクリプトは _source_file の親フォルダから誌名を 100% 復元し、正規化＋別名解決して
     canonical 誌名を付与する。件数(unique_articles)は一切変えない（純粋にメタ列を足すだけ）。

使い方:
  python3 label_journals_v0.2.py <article_meta_all.jsonl> [priority.json]

出力（入力と同じ build ディレクトリ配下に新規作成・元は触らない）:
  <build>/labeled_v0.2/article_meta_labeled.jsonl   … 元レコード + 下記ラベル列
  <build>/labeled_v0.2/summary_labeled.json         … canonical 誌別件数ほか

付与する列:
  journal_raw       … _source_file の親フォルダ名（証跡, 無加工）
  journal_norm      … 正規化後（接尾辞/検索語ゴミ除去・NFKC・空白畳み）
  journal_canonical … フォルダ群の正式名（掲載誌名が在ればそれを正に採用）
  journal_source    … 'folder+meishi' / 'folder'
  match_status      … 'meishi_match' / 'meishi_conflict' / 'folder_only'
                       （priority.json 指定時は canonical の在不在で 'in_priority'/'unmapped' も付与）
"""
import json
import sys
import os
import re
import unicodedata
import collections

# 末尾に付く取得由来のラベルノイズ（実データ由来）
_SUFFIX_NOISE = ["雑誌記事メタデータ"]

# 正規化フォルダ名 → canonical の明示エイリアス。
# 正規化だけでは吸収できない少数ケース（主に ASCII の '&' がファイル名で '_' 化）を、
# 掲載誌名側の正式表記へ寄せる。実データの match_status=meishi_conflict から育てる。
# 注意: ここに入れるのは「同じ誌の表記ゆれ」だけ。より具体的な別誌
# （例: 論究ジュリスト≠ジュリスト）は決して統合しない。
_ALIAS = {
    "Law Technology": "Law & Technology",
    "Law Practice": "Law & Practice",
    "Patents Licensing": "Patents & Licensing",
}


def normalize(name: str) -> str:
    """フォルダ名/掲載誌名を比較可能な正規形へ。

    - NFKC（全角数字・全角空白・全角括弧→半角化）
    - 最初の括弧以降を切る（"銀行法務21(1～60回分)発行年月日昇順" → "銀行法務21"）
    - 既知の接尾辞ノイズ（" 雑誌記事メタデータ"）除去
    - ファイル名セーフ化された区切り（_ / ___）を空白へ
    - 連続空白を1つに畳み、前後trim
    """
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", name)
    s = re.split(r"[(]", s, 1)[0]          # NFKC後は全角括弧も半角'('
    for suf in _SUFFIX_NOISE:
        s = s.replace(suf, "")
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def journal_from_path(source_file: str) -> str:
    """取得元RTFの絶対パスから親フォルダ名（＝誌名）を取り出す。"""
    if not source_file:
        return ""
    parts = [p for p in source_file.split("/") if p]
    return parts[-2] if len(parts) >= 2 else ""


def load_priority_names(path: str) -> set:
    """優先JSONを構造に依存せず走査し、含まれる文字列を正規化して集合化。

    厳密な誌名⇔IDマッピングは構造確認後に拡張する。当面は canonical が
    優先キューに存在するか（in_priority/unmapped）の判定にのみ使う。
    """
    names = set()

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str):
            n = normalize(o)
            if n:
                names.add(n)

    with open(path, encoding="utf-8") as f:
        walk(json.load(f))
    return names


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python3 label_journals_v0.2.py <article_meta_all.jsonl> [priority.json]")
    src = sys.argv[1]
    priority = sys.argv[2] if len(sys.argv) > 2 else None
    priority_names = load_priority_names(priority) if priority else None

    out_dir = os.path.join(os.path.dirname(src), "labeled_v0.2")
    os.makedirs(out_dir, exist_ok=True)
    out_jsonl = os.path.join(out_dir, "article_meta_labeled.jsonl")

    by_canonical = collections.Counter()
    status_counter = collections.Counter()
    unmapped = collections.Counter()
    # 掲載誌名と canonical が食い違う組（エイリアス育成・要目視の素材）
    conflicts = collections.Counter()
    n = 0
    with open(src, encoding="utf-8") as f, open(out_jsonl, "w", encoding="utf-8") as w:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            raw = journal_from_path(r.get("_source_file", ""))
            norm = normalize(raw)
            # canonical = 正規化フォルダ名（一次ソース）。少数の表記ゆれのみエイリアスで吸収。
            canonical = _ALIAS.get(norm, norm)
            meishi_norm = normalize(r.get("掲載誌名") or "")
            if meishi_norm:
                source = "folder+meishi"
                if meishi_norm == canonical:
                    status = "meishi_match"
                else:
                    status = "meishi_conflict"
                    conflicts[(canonical, meishi_norm)] += 1
            else:
                source = "folder"
                status = "folder_only"
            r["journal_raw"] = raw
            r["journal_norm"] = norm
            r["journal_canonical"] = canonical
            r["journal_source"] = source
            r["match_status"] = status
            if priority_names is not None:
                in_pri = canonical in priority_names
                r["in_priority"] = in_pri
                if not in_pri:
                    unmapped[canonical] += 1
            w.write(json.dumps(r, ensure_ascii=False) + "\n")
            by_canonical[canonical] += 1
            status_counter[status] += 1
            n += 1

    q = by_canonical.get("", 0)
    summary = {
        "input": src,
        "records": n,
        "journals_canonical": len(by_canonical),
        "empty_journal": q,
        "by_status": dict(status_counter),
        "by_journal_canonical_top50": by_canonical.most_common(50),
        "meishi_conflicts_top30": [
            {"canonical": c, "meishi": m, "n": v} for (c, m), v in conflicts.most_common(30)
        ],
    }
    if priority_names is not None:
        summary["unmapped_vs_priority_top30"] = unmapped.most_common(30)

    out_summary = os.path.join(out_dir, "summary_labeled.json")
    with open(out_summary, "w", encoding="utf-8") as w:
        json.dump(summary, w, ensure_ascii=False, indent=1)

    # コンソール要約（受け入れ基準の即時確認）
    print(f"records              : {n}")
    print(f"empty journal (?)    : {q}   <-- 0 が目標")
    print(f"canonical 誌数        : {len(by_canonical)}")
    print(f"status               : {dict(status_counter)}")
    print("--- by_journal_canonical TOP30 ---")
    for k, v in by_canonical.most_common(30):
        print(f"  {v:>7}  {k}")
    if conflicts:
        print("--- 掲載誌名≠canonical（エイリアス育成・要目視 上位）---")
        for (c, m), v in conflicts.most_common(15):
            print(f"  {v:>6}  canonical「{c}」 ≠ 掲載誌名「{m}」")
    if priority_names is not None:
        print("--- canonical が優先JSONに無い(上位) ---")
        for k, v in unmapped.most_common(15):
            print(f"  {v:>6}  {k}")
    print(f"\nwrote: {out_jsonl}")
    print(f"wrote: {out_summary}")


if __name__ == "__main__":
    main()
