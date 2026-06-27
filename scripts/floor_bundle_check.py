"""3書面セット一括整合チェック (定款/議事録/登記) — stdlib のみ.

手続バンドル JSON を受け取り 3段のチェックを行う:
  1. 床充足チェック   : 各書面が担う法定床(各号)を満たすか
  2. 錨出現チェック   : 複数床にまたがる錨概念が各書面に出現するか
  3. 錨値照合        : 商号・本店 など抽出可能な固有名詞/数値が書面間で一致するか

Usage:
  python3 scripts/floor_bundle_check.py \\
      --bundle pipeline/floor/bundles/募集株式発行.json

オプション:
  --json    : 機械読み取り用 JSON を stdout に出す
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from requirement_floor import check_against_statute  # noqa: E402
from floor_link import link as fl_link, _clean_chunks  # noqa: E402

EXTRACT = ROOT / "pipeline" / "floor" / "statute_floor_extract.json"

# ── 値抽出パターン (ベストエフォート) ─────────────────────────────────────────

# 各概念: [(pattern, group_idx, note)]
# 複数パターンを順に試し、最初にヒットしたものを採用。
_EXTRACT_RULES: dict[str, list[tuple[re.Pattern, int, str]]] = {
    "商号": [
        (re.compile(r"(?:当会社は、|商号\s+)([^\s。\n]+(?:株式会社|合同会社|有限会社)[^\s。\n]*)"), 1, ""),
        (re.compile(r"([^\s。\n]+(?:株式会社|合同会社|有限会社)[^\s。\n]*)と称する"), 1, ""),
        (re.compile(r"商号\s+(\S+)"), 1, ""),
    ],
    "本店": [
        # 定款形式: 「本店を東京都渋谷区に置く」→ 都道府県+区市町村まで丸ごと
        (re.compile(r"本店を((?:東京都|大阪府|京都府|北海道|[^\s。\n]{2}[都道府県])[^\s。\n、]{0,30})(?=に置く)"), 1, ""),
        # 登記形式: 改行インデント 「本店\n   東京都○○」
        (re.compile(r"本店\s*\n\s+(\S[^\n]{3,40})"), 1, ""),
        # 登記形式: 同行スペース 「本店  東京都○○」
        (re.compile(r"本店\s{2,}(\S[^\n]{3,40})"), 1, ""),
    ],
    "資本金": [
        # delta パターンを先に(total パターンに誤ヒットしないよう順序重要)
        (re.compile(r"増加する資本金の額\s*金?\s*([0-9,]+)\s*円"), 1, "delta"),
        (re.compile(r"資本金の額\s*金?\s*([0-9,]+)\s*円"), 1, "total"),
        (re.compile(r"資本金\s+金([0-9,]+)円"), 1, "total"),
    ],
}

# 錨値照合の「計算的照合」が必要な概念 = 値が食い違っても自動で NG にしない
_NEEDS_HUMAN_VERIFY = {"資本金", "発行"}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", str(s or "")).strip()


def _extract_value(concept: str, text: str) -> tuple[str, str] | None:
    """concept の値を text から抽出。(value, note) or None。"""
    rules = _EXTRACT_RULES.get(concept, [])
    for pat, grp, note in rules:
        m = pat.search(text)
        if m:
            return (_norm(m.group(grp)), note)
    return None


def _values_match(a: str, b: str) -> bool:
    """正規化した値の一致判定。短い方が長い方の先頭に含まれれば OK(所在地の詳細差異を許容)。"""
    na, nb = _norm(a).replace(" ", "").replace("　", ""), _norm(b).replace(" ", "").replace("　", "")
    return na == nb or nb.startswith(na) or na.startswith(nb)


# ── 床充足チェック ─────────────────────────────────────────────────────────────

def _floor_check_doc(doc: dict, proc: dict) -> dict:
    """1書面の床充足チェック。skip_floor_check=true なら SKIPPED を返す。"""
    if doc.get("skip_floor_check"):
        return {
            "label": doc["label"], "article": proc["article"],
            "ok": True, "missing": [], "present": [],
            "conditional_skipped": [], "n_floor": len(proc["items"]),
            "n_effective": 0, "n_skipped": 0,
            "skipped": True, "skip_note": doc.get("skip_floor_note", ""),
        }
    text = doc["_text"]
    canonical = proc["items"]

    # 条件付き号の自動判定: 名称に「あるときは」を含む号はテキストに
    # 号名称の一部が出現しない限り bed として要求しない。
    effective = []
    conditional_skip = []
    for item in canonical:
        name = item.get("名称", "")
        if "あるときは" in name or "ときは" in name:
            # トリガーが canonical に明示されているか
            trigger = item.get("trigger")
            if trigger:
                if trigger not in text:
                    conditional_skip.append(item["号"])
                    continue
            else:
                # 名称から条件節前の語を簡易抽出してトリガーワードとして使う
                trigger_part = re.split(r"あるときは|であるときは|ときは", name)[0]
                trigger_chunk = _clean_chunks(trigger_part)
                if trigger_chunk and not any(c in text for c in trigger_chunk):
                    conditional_skip.append(item["号"])
                    continue
        effective.append(item)

    result = check_against_statute(text, effective)
    present = [r for r in result["rows"] if r.get("present")]
    return {
        "label": doc["label"],
        "article": proc["article"],
        "ok": result["ok"],
        "missing": result["missing"],
        "present": present,
        "conditional_skipped": conditional_skip,
        "n_floor": len(canonical),
        "n_effective": len(effective),
        "n_skipped": len(conditional_skip),
    }


# ── 錨チェック ────────────────────────────────────────────────────────────────

def _anchor_check(docs: list[dict], procs: list[dict]) -> list[dict]:
    """floor_link で取れた錨概念を 3段チェック。"""
    links = fl_link(procs)

    # concept → {floor_a, floor_b, 号_a, 号_b} 一覧
    by_concept: dict[str, list[dict]] = {}
    for ln in links:
        by_concept.setdefault(ln["concept"], []).append(ln)

    doc_by_label = {d["label"]: d for d in docs}
    label_to_proc_label = {d["label"]: p["label"] for d, p in zip(docs, procs)}

    results = []
    for concept, lns in sorted(by_concept.items(), key=lambda x: (-len(x[0]), x[0])):
        # 複数書面にまたがるか
        floors = {ln["floor_a"] for ln in lns} | {ln["floor_b"] for ln in lns}
        if len(floors) < 2:
            continue

        # どの書面ラベルが関係するか
        involved_labels = [d["label"] for d in docs
                           if label_to_proc_label[d["label"]] in floors]

        # 出現チェック: 各書面テキストに concept が含まれるか
        presence: dict[str, bool] = {}
        for lbl in involved_labels:
            text = doc_by_label[lbl]["_text"]
            presence[lbl] = concept in text

        # 値抽出 & 照合
        extracted: dict[str, tuple[str, str] | None] = {}
        for lbl in involved_labels:
            extracted[lbl] = _extract_value(concept, doc_by_label[lbl]["_text"])

        value_pairs: list[dict] = []
        needs_human = concept in _NEEDS_HUMAN_VERIFY
        for i, la in enumerate(involved_labels):
            for lb in involved_labels[i + 1:]:
                va = extracted.get(la)
                vb = extracted.get(lb)
                if va and vb:
                    match = _values_match(va[0], vb[0])
                    value_pairs.append({
                        "doc_a": la, "val_a": va[0], "note_a": va[1],
                        "doc_b": lb, "val_b": vb[0], "note_b": vb[1],
                        "match": match,
                        "needs_human": needs_human or va[1] == "delta" or vb[1] == "delta",
                    })

        results.append({
            "concept": concept,
            "involved_docs": involved_labels,
            "presence": presence,
            "value_pairs": value_pairs,
            "go_pairs": [f"{ln['floor_a'][:6]}{ln['号_a']}↔{ln['floor_b'][:6]}{ln['号_b']}"
                         for ln in lns],
        })

    return results


# ── レポート印字 ──────────────────────────────────────────────────────────────

def _print_report(手続: str, floor_results: list[dict], anchor_results: list[dict]) -> None:
    W = "=" * 60
    print(f"\n{W}")
    print(f"  手続バンドル整合チェック : {手続}")
    print(W)

    # ── 1. 床充足 ──
    print("\n【1. 床充足チェック】各書面が法定の各号を満たすか")
    all_floor_ok = True
    for r in floor_results:
        if r.get("skipped"):
            print(f"\n  ⏭️  {r['label']} (会社法{r['article']}条) — 床充足チェックスキップ")
            print(f"     理由: {r['skip_note']}")
            continue
        icon = "✅" if r["ok"] else "❌"
        cond = f"  (条件付き{r['n_skipped']}号スキップ)" if r["n_skipped"] else ""
        print(f"\n  {icon} {r['label']} (会社法{r['article']}条){cond}")
        if r["missing"]:
            for m in r["missing"]:
                print(f"     ❌ 欠落: {m['号']}号 「{m['名称'][:40]}」")
            all_floor_ok = False
        else:
            n = r["n_effective"]
            print(f"     {n}号すべて充足")

    # ── 2. 錨出現 ──
    print("\n【2. 錨概念 出現チェック】複数書面にまたがる整合の錨")
    missing_presence = []
    for ar in anchor_results:
        absent = [lbl for lbl, ok in ar["presence"].items() if not ok]
        icon = "✅" if not absent else "⚠️ "
        print(f"\n  {icon}【{ar['concept']}】 "
              f"{'→'.join(ar['involved_docs'])}")
        print(f"     条文ペア: " + " / ".join(ar["go_pairs"][:3]))
        for lbl, ok in ar["presence"].items():
            mark = "○" if ok else "×(不在)"
            print(f"     {mark}  {lbl}")
        if absent:
            missing_presence.append(ar["concept"])

    # ── 3. 錨値照合 ──
    print("\n【3. 錨値照合】抽出可能な値を書面間で比較")
    value_conflicts: list[str] = []
    value_human: list[str] = []
    checked = 0
    for ar in anchor_results:
        for vp in ar["value_pairs"]:
            checked += 1
            if vp["needs_human"]:
                icon = "🔍"
                note = "要人確認(Δ値と総額の差異)"
                value_human.append(ar["concept"])
            elif vp["match"]:
                icon = "✅"
                note = "一致"
            else:
                icon = "❌"
                note = "不一致"
                value_conflicts.append(ar["concept"])
            print(f"\n  {icon}【{ar['concept']}】 {note}")
            print(f"     {vp['doc_a']}: {vp['val_a']!r}")
            print(f"     {vp['doc_b']}: {vp['val_b']!r}")

    if checked == 0:
        print("  (値抽出できた錨なし — alias 整備後に再確認)")

    # ── サマリ ──
    print(f"\n{W}")
    f_ok = sum(1 for r in floor_results if r["ok"])
    a_ok = sum(1 for ar in anchor_results
               if not [lbl for lbl, ok in ar["presence"].items() if not ok])
    v_ok = checked - len(value_conflicts) - len(value_human)
    print(f"  床充足    : {f_ok}/{len(floor_results)} 書面")
    print(f"  錨出現    : {a_ok}/{len(anchor_results)} 概念 (不在錨: {missing_presence or 'なし'})")
    if checked:
        print(f"  値照合    : 確認{checked}件 / 一致{v_ok} / 不一致{len(value_conflicts)} "
              f"/ 要人確認{len(value_human)}")
    verdict = "✅ PASS" if all_floor_ok and not value_conflicts else "❌ FAIL"
    print(f"\n  総合: {verdict}")
    print(W)


# ── main ─────────────────────────────────────────────────────────────────────

def run_bundle(bundle_path: Path) -> dict:
    """バンドルを読んでチェック結果 dict を返す(テスト用)。"""
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    extract = json.loads(EXTRACT.read_text(encoding="utf-8"))
    proc_by_key: dict[str, dict] = {}
    for p in extract["procedures"]:
        key = (p["article"], str(p.get("paragraph") or ""))
        proc_by_key[key] = p

    docs: list[dict] = []
    procs: list[dict] = []
    for doc_def in bundle["documents"]:
        fpath = ROOT / doc_def["file"]
        text = fpath.read_text(encoding="utf-8")
        key = (doc_def["article"], str(doc_def.get("paragraph") or ""))
        proc = proc_by_key.get(key)
        if proc is None:
            raise KeyError(f"statute_floor_extract に {key} がない")

        # curated canonical が指定されていれば items を差し替え
        if doc_def.get("canonical_file"):
            canon_path = ROOT / doc_def["canonical_file"]
            canon_data = json.loads(canon_path.read_text(encoding="utf-8"))
            items = canon_data.get("items", canon_data) if isinstance(canon_data, dict) else canon_data
            proc = {**proc, "items": items}

        docs.append({**doc_def, "_text": text})
        procs.append(proc)

    floor_results = [_floor_check_doc(d, p) for d, p in zip(docs, procs)]
    anchor_results = _anchor_check(docs, procs)

    return {
        "手続": bundle["手続"],
        "floor_results": floor_results,
        "anchor_results": anchor_results,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="3書面セット一括整合チェック")
    ap.add_argument("--bundle", required=True, help="バンドル定義 JSON のパス")
    ap.add_argument("--json", action="store_true", help="JSON 出力")
    args = ap.parse_args()

    result = run_bundle(ROOT / args.bundle)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2,
                         default=lambda o: str(o)))
    else:
        _print_report(result["手続"], result["floor_results"], result["anchor_results"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
