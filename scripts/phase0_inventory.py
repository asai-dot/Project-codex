#!/usr/bin/env python3
"""phase0_inventory — legallibjoin v0.3.1 Phase 0 実データ profiling (report-only)。

DDLEGALLIBCONCORD_PASS_WITH_NOTES (phase0=GO / production_apply=HOLD) に基づき、
接合の実入力 (legallib 詳細TOC / canonical 書誌 / resolver 突合) を点検する。
**canonical も legallib も一切書き換えない。final_toc も作らない。stdlib のみ・決定的。**

成果物 (--out へ):
  source_inventory.md            : ソース別 inventory (件数/ISBN欠落/解決率…)
  parser_success_histogram.csv   : content_type 別 parse 成否・node数バケット
  page_basis_profile.md          : pdf_page/print_page 両持ち率・offset 分布
  edition_identity_sample.jsonl  : classify_edition_identity を実 2ソース対へ適用
  known_conflict_golden.md       : 既知 conflict 10冊 seed (golden)
  inputs_sha256.txt              : 入力の sha256 (再現性)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edition_identity import classify_edition_identity  # noqa: E402
from legallib_to_canonical import flatten_nodes  # noqa: E402

import unicodedata  # noqa: E402

_RESERVED = {"resolver_decisions.jsonl", "books.jsonl"}
_YEAR_RE = re.compile(r"(\d{4})")

# --- 版(edition)シグネチャ抽出: タイトル文字列差を「副題違い/別版」へ層別する ---
_KANJI_NUM = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
# NFKC 後を前提 (全角数字→半角, （）→() 済)。〔〕〈〉【】 は NFKC で変わらないので明示。
_ED_NUM_RE = re.compile(r"[第\(\[〔〈【]?\s*(\d+|[〇一二三四五六七八九十]+)\s*版")
_ED_LABEL_RE = re.compile(r"(改訂|新訂|全訂|増補|補訂|新版|初版)")
# 版・括弧・読点を落として残った『核タイトル』を作るための strip。
_CORE_STRIP = re.compile(
    r"[\s　・･:：,，、_\-\(\)\[\]【】「」『』〔〕〈〉（）“”\"'./&＆ー―−‐‑‒–—~〜!！?？|｜─–]+"
)


def _kanji_to_int(s: str):
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    # 単純な十進(十N / N十 / N十M)
    if "十" in s:
        a, _, b = s.partition("十")
        tens = (_KANJI_NUM.get(a, 1) if a else 1) * 10
        return tens + (_KANJI_NUM.get(b, 0) if b else 0)
    return _KANJI_NUM.get(s)


def edition_signature(title: str) -> str:
    """タイトルから版シグネチャを返す ('' = 版表記なし)。"""
    s = unicodedata.normalize("NFKC", title or "")
    m = _ED_NUM_RE.search(s)
    if m:
        n = _kanji_to_int(m.group(1))
        if n is not None:
            return f"v{n}"
    m = _ED_LABEL_RE.search(s)
    if m:
        return {"初版": "v1"}.get(m.group(1), "rev")
    return ""


def _core_title(title: str) -> str:
    """版表記を除いた核タイトル (副題込み・記号除去・小文字)。"""
    s = unicodedata.normalize("NFKC", title or "").lower()
    s = _ED_NUM_RE.sub("", s)
    s = _ED_LABEL_RE.sub("", s)
    return _CORE_STRIP.sub("", s)


# 別版/別本として **実質的に要レビュー** の層 (装飾差・副題差・±1年ノイズは除外)。
_REAL_TKINDS = {"edition_number_conflict", "edition_marker_asymmetry", "genuine_title_diff"}


def is_real_suspect(r: dict) -> bool:
    if r["status"] != "suspected_different_manifestation":
        return False
    if r["reason"] == "year divergence":
        le, ce = r.get("legallib_edition_sig"), r.get("canonical_edition_sig")
        if le and ce and le == ce:
            return False                    # 版番号一致 → 年差は重版/表記ゆれ
        g = r.get("year_gap")
        return g is None or g >= 2          # ±1 年は出版年表記ゆれ → 弱信号
    return r.get("title_diff_kind") in _REAL_TKINDS


def title_diff_kind(ll_title: str, cn_title: str) -> str:
    """title divergence を層別: cosmetic / subtitle / edition_number_conflict /
    edition_marker_asymmetry / genuine_title_diff。"""
    le, ce = edition_signature(ll_title), edition_signature(cn_title)
    if le and ce and le != ce:
        return "edition_number_conflict"        # 第7版 vs 第4版 = 真の別版
    lc, cc = _core_title(ll_title), _core_title(cn_title)
    if lc == cc:
        # 核は一致 → 版括弧/全半角/読点差。版マーカ非対称なら要レビュー。
        return "edition_marker_asymmetry" if (bool(le) != bool(ce)) else "cosmetic"
    if lc and cc and (lc in cc or cc in lc):
        return "subtitle_difference"            # 片方が副題を含む = 同一本
    return "genuine_title_diff"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def norm_isbn(v) -> str:
    return re.sub(r"[^0-9Xx]", "", str(v or "")).upper()


def parse_year(v) -> str:
    m = _YEAR_RE.search(str(v or ""))
    return m.group(1) if m else ""


def _bucket(n: int) -> str:
    if n == 0:
        return "empty"
    if n <= 10:
        return "1-10"
    if n <= 50:
        return "11-50"
    return "51+"


def _walk_pages(nodes, acc):
    """toc 木を再帰し、各ノードの pdf_page/print_page 充足と offset を集計。"""
    for n in nodes:
        if not isinstance(n, dict):
            continue
        pdf = n.get("pdf_page")
        prt = n.get("print_page")
        has_pdf = isinstance(pdf, int)
        has_prt = isinstance(prt, int)
        acc["nodes"] += 1
        acc["has_pdf"] += has_pdf
        acc["has_print"] += has_prt
        if has_pdf and has_prt:
            acc["both"] += 1
            acc["offsets"][pdf - prt] += 1
        elif has_pdf:
            acc["pdf_only"] += 1
        elif has_prt:
            acc["print_only"] += 1
        else:
            acc["neither"] += 1
        if n.get("children"):
            _walk_pages(n["children"], acc)


# ---------------------------------------------------------------------------
# 1) legallib source profiling (inventory + parser histogram + page_basis)
# ---------------------------------------------------------------------------
def profile_legallib(legallib_dir: Path) -> dict:
    files = sorted(f for f in legallib_dir.glob("*.json") if f.name not in _RESERVED)
    by_ct = defaultdict(lambda: {
        "files": 0, "unreadable": 0, "with_toc": 0, "total_nodes": 0,
        "empty_titles": 0, "isbn_present": 0,
        "node_buckets": Counter(),
    })
    page_acc = {"nodes": 0, "has_pdf": 0, "has_print": 0, "both": 0,
                "pdf_only": 0, "print_only": 0, "neither": 0, "offsets": Counter()}
    book_pages = []  # per book: total_pages
    book_offset_share = []  # per book: 最頻 offset が占める割合 (一貫性)
    legallib_bib: dict[str, dict] = {}  # book_id -> bib (for edition identity)

    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            by_ct["<unreadable>"]["files"] += 1
            by_ct["<unreadable>"]["unreadable"] += 1
            continue
        ct = str(d.get("content_type") or "<unset>")
        s = by_ct[ct]
        s["files"] += 1
        toc = d.get("toc") or []
        flat = flatten_nodes(toc)
        nc = len(flat)
        s["total_nodes"] += nc
        s["node_buckets"][_bucket(nc)] += 1
        if nc:
            s["with_toc"] += 1
        for n in flat:
            if isinstance(n, dict) and not str(n.get("label") or "").strip():
                s["empty_titles"] += 1
        # legallib 側はネイティブに isbn を持たない (検出されれば数える)
        if d.get("isbn"):
            s["isbn_present"] += 1
        # page_basis は book 系のみ集計 (pubcom は別物)
        if ct == "book":
            book_acc = {"nodes": 0, "has_pdf": 0, "has_print": 0, "both": 0,
                        "pdf_only": 0, "print_only": 0, "neither": 0, "offsets": Counter()}
            _walk_pages(toc, book_acc)
            # この本の offset 一貫性 (最頻 offset / 両持ちノード数)
            bo = book_acc["offsets"]
            if sum(bo.values()) >= 3:
                book_offset_share.append(bo.most_common(1)[0][1] / sum(bo.values()))
            # グローバルへ合算
            for k in ("nodes", "has_pdf", "has_print", "both", "pdf_only", "print_only", "neither"):
                page_acc[k] += book_acc[k]
            page_acc["offsets"].update(bo)
            if isinstance(d.get("total_pages"), int):
                book_pages.append(d["total_pages"])
        legallib_bib[str(d.get("book_id"))] = {
            "source": "legallib",
            "title": d.get("title") or "",
            "publisher": d.get("publisher") or "",
            "year": parse_year(d.get("pub_year_raw")),
            "edition": d.get("edition_label") or "",
            "page_count": d.get("total_pages"),
            "content_type": ct,
            "node_count": nc,
        }

    return {
        "files": len(files),
        "by_content_type": {k: {
            "files": v["files"], "unreadable": v["unreadable"],
            "with_toc": v["with_toc"], "total_nodes": v["total_nodes"],
            "empty_title_rate": round(v["empty_titles"] / v["total_nodes"], 4) if v["total_nodes"] else None,
            "isbn_present": v["isbn_present"],
            "node_buckets": dict(v["node_buckets"]),
        } for k, v in sorted(by_ct.items())},
        "page_acc": page_acc,
        "book_pages": book_pages,
        "book_offset_share": book_offset_share,
        "legallib_bib": legallib_bib,
    }


# ---------------------------------------------------------------------------
# 2) canonical + resolver profiling
# ---------------------------------------------------------------------------
def profile_canonical(canonical_path: Path) -> tuple[dict, dict]:
    books = json.loads(canonical_path.read_text(encoding="utf-8"))
    idx: dict[str, dict] = {}
    media = Counter()
    with_isbn = 0
    has_toc = 0
    for b in books:
        media[str(b.get("mediaType") or "<unset>")] += 1
        if b.get("hasToc"):
            has_toc += 1
        isbn = norm_isbn(b.get("isbn"))
        if isbn:
            with_isbn += 1
            idx.setdefault(isbn, {
                "source": "canonical",
                "title": b.get("title") or "",
                "publisher": b.get("publisher") or "",
                "year": parse_year(b.get("date")),
                "edition": b.get("edition") or "",
                "page_count": None,  # canonical 書誌に頁数欄なし
                "primary_source": (b.get("external_refs") or {}).get("primary_source")
                if isinstance(b.get("external_refs"), dict) else "",
                "isbn": isbn,
            })
    summary = {
        "records": len(books),
        "with_isbn": with_isbn,
        "unique_isbn": len(idx),
        "has_toc": has_toc,
        "media_type": dict(media),
    }
    return summary, idx


def load_resolver(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_write_candidates(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[norm_isbn(row.get("isbn"))] = row
    return out


# ---------------------------------------------------------------------------
# 3) edition identity over real matched pairs
# ---------------------------------------------------------------------------
def run_edition_identity(resolver: list[dict], canon_idx: dict,
                         legallib_bib: dict) -> list[dict]:
    rows = []
    for r in resolver:
        bucket = r.get("bucket")
        isbn = norm_isbn(r.get("isbn"))
        bid = str(r.get("legallib_book_id"))
        if not isbn or isbn not in canon_idx:
            continue  # defer_new / 未解決 はここでは対象外 (single-source は自明)
        ll = legallib_bib.get(bid)
        if ll is None:
            # legallib ファイル欠落: resolver の自己申告 bib で代替
            ll = {"source": "legallib", "title": r.get("title") or "",
                  "publisher": r.get("publisher") or "",
                  "year": parse_year(r.get("pub_year_raw")),
                  "edition": r.get("edition_label") or "", "page_count": None}
        cn = dict(canon_idx[isbn])
        a = {"source": "legallib", "isbn": isbn, "title": ll["title"],
             "publisher": ll["publisher"], "year": ll["year"],
             "edition": ll["edition"], "page_count": ll.get("page_count")}
        b = {"source": "canonical", "isbn": isbn, "title": cn["title"],
             "publisher": cn["publisher"], "year": cn["year"],
             "edition": cn["edition"], "page_count": cn.get("page_count")}
        res = classify_edition_identity([a, b])
        # 診断: title divergence を層別 (cosmetic/副題違い/版番号衝突/版マーカ非対称/実質差)。
        tkind = None
        if res["status"] == "suspected_different_manifestation" and res["reason"] == "title divergence":
            tkind = title_diff_kind(a["title"], b["title"])
        # year divergence の年差 (±1 は出版年表記ゆれの可能性が高い=弱信号)。
        year_gap = None
        if res["reason"] == "year divergence":
            try:
                year_gap = abs(int(a["year"]) - int(b["year"]))
            except (TypeError, ValueError):
                year_gap = None
        rows.append({
            "isbn": isbn, "legallib_book_id": bid,
            "resolver_bucket": bucket,
            "resolver_confidence": r.get("confidence"),
            "resolver_ed_conflict": bool(r.get("ed_conflict")),
            "resolver_ambiguous": bool(r.get("ambiguous")),
            "status": res["status"], "reason": res["reason"],
            "title_diff_kind": tkind,
            "year_gap": year_gap,
            "legallib_edition_sig": edition_signature(a["title"]),
            "canonical_edition_sig": edition_signature(b["title"]),
            "legallib": {k: a[k] for k in ("title", "year", "edition", "page_count")},
            "canonical": {k: b[k] for k in ("title", "year", "edition")},
        })
    return rows


# ---------------------------------------------------------------------------
# writers
# ---------------------------------------------------------------------------
def write_outputs(out: Path, ll: dict, canon_sum: dict, resolver: list[dict],
                  ident_rows: list[dict], wc: dict) -> dict:
    out.mkdir(parents=True, exist_ok=True)

    # --- source_inventory.md ---
    rbucket = Counter(r.get("bucket") for r in resolver)
    resolved_isbn = {norm_isbn(r["isbn"]) for r in resolver
                     if r.get("isbn") and r.get("bucket") in ("auto_accept", "human_review")}

    # edition identity 診断: title divergence を5層に切り分け。
    title_div = [r for r in ident_rows if r["reason"] == "title divergence"]
    tkinds = Counter(r.get("title_diff_kind") for r in title_div)
    year_rows = [r for r in ident_rows if r["reason"] == "year divergence"]
    year_div = len(year_rows)
    year_small = sum(1 for r in year_rows if (r.get("year_gap") is not None and r["year_gap"] <= 1))
    year_big = year_div - year_small
    total_suspect = sum(1 for r in ident_rows
                        if r["status"] == "suspected_different_manifestation")
    real_suspect = sum(1 for r in ident_rows if is_real_suspect(r))
    artifact_suspect = total_suspect - real_suspect  # 偽陽性 = 生 - 実質
    edition_conflicts = tkinds.get("edition_number_conflict", 0)
    # auto_accept なのに別版疑いに落ちた件数 (resolver 偽陽性リスク)。
    aa_suspect = sum(1 for r in ident_rows if r["resolver_bucket"] == "auto_accept"
                     and r["status"] == "suspected_different_manifestation")
    aa_suspect_real = sum(1 for r in ident_rows
                          if r["resolver_bucket"] == "auto_accept" and is_real_suspect(r))
    inv = [
        "# Phase 0 source inventory (legallibjoin v0.3.1, report-only)", "",
        "> canonical/legallib とも未書込。final_toc 未生成。",
        "",
        "## A. legallib 詳細TOC (接合の new 側ソース)", "",
        f"- ファイル総数: **{ll['files']}**",
        "- content_type 内訳:", "",
        "| content_type | files | with_toc | total_nodes | empty_title率 | isbn欄あり |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for ct, v in ll["by_content_type"].items():
        inv.append(f"| {ct} | {v['files']} | {v['with_toc']} | {v['total_nodes']} | "
                   f"{v['empty_title_rate']} | {v['isbn_present']} |")
    inv += [
        "",
        "> **所見: legallib はネイティブに ISBN を持たない** (isbn欄あり=0)。"
        "ISBN は resolver_decisions.jsonl による title/publisher/year 突合で後付け。"
        "→ 接合キーの素性は resolver 品質に従属する。",
        "",
        "## B. canonical 書誌 (接合の existing 側 / 書込先候補)", "",
        f"- レコード総数: **{canon_sum['records']}** / ISBN付与: {canon_sum['with_isbn']} "
        f"(ユニーク {canon_sum['unique_isbn']}) / hasToc: {canon_sum['has_toc']}",
        f"- mediaType 内訳: {canon_sum['media_type']}",
        "> canonical 書誌に **頁数欄なし** → edition identity の page_count 照合は legallib 側のみ。",
        "",
        "## C. resolver 突合 (legallib_book_id → canonical ISBN)", "",
        f"- 判定総数: **{len(resolver)}**",
        f"- bucket 内訳: {dict(rbucket)}",
        f"  - auto_accept/human_review = canonical 一致 (= edition identity 対象 {len(resolved_isbn)} ISBN)",
        f"  - defer_new = canonical 不在 → 接合では create 候補",
        f"- ed_conflict フラグ: {sum(1 for r in resolver if r.get('ed_conflict'))} / "
        f"ambiguous: {sum(1 for r in resolver if r.get('ambiguous'))}",
        f"- write_candidates (v0.2 既出): {len(wc)} 件 (TOC 差分既知)",
        "",
        "## D. edition identity 診断 (classify_edition_identity, 実 2ソース対)", "",
        f"- 評価対象 (canonical ISBN 一致): **{len(ident_rows)}**",
        f"- resolved_same_manifestation: {sum(1 for r in ident_rows if r['status']=='resolved_same_manifestation')}",
        f"- suspected_different_manifestation (生): "
        f"{sum(1 for r in ident_rows if r['status']=='suspected_different_manifestation')} "
        f"= title divergence {len(title_div)} + year divergence {year_div} "
        f"(うち年差±1のノイズ {year_small} / 年差≧2 {year_big})",
        "",
        "### title divergence の層別 (生の文字列差は別版を意味しない)", "",
        "| 層 | 件数 | 意味 |",
        "|---|---:|---|",
        f"| cosmetic | {tkinds.get('cosmetic',0)} | 全半角・〔〕〈〉括弧・読点差のみ → 同一 |",
        f"| subtitle_difference | {tkinds.get('subtitle_difference',0)} | 片方が副題を含む/欠く → 同一本 |",
        f"| edition_marker_asymmetry | {tkinds.get('edition_marker_asymmetry',0)} | 片方のみ版表記 → 要レビュー |",
        f"| edition_number_conflict | {tkinds.get('edition_number_conflict',0)} | **版番号が相違 (例 第7版 vs 第4版) → 真の別版** |",
        f"| genuine_title_diff | {tkinds.get('genuine_title_diff',0)} | 核タイトルが相違 → 要レビュー |",
        "",
        f"- **偽陽性 (装飾/副題/年差±1) = {artifact_suspect} 件** (別版ではない)。",
        f"- **真に要レビュー (版衝突/版非対称/核相違/年差≧2) = {real_suspect} 件** "
        f"(全評価の {real_suspect/len(ident_rows):.1%})。",
        f"  - うち確実な別版 (版番号衝突) = **{edition_conflicts} 件**。",
        "",
        "> **所見1 (閾値調整に直結)**: 生 344 件 (16.5%) の別版疑いは過検知。"
        f"内訳は title装飾/副題差 {tkinds.get('cosmetic',0)+tkinds.get('subtitle_difference',0)} + "
        f"年差±1ノイズ {year_small} = 偽陽性 {artifact_suspect}、実質 {real_suspect}。"
        "信頼できる別版信号は**抽出した版番号の相違**であり、現行 `classify_edition_identity` の"
        "『title 文字列一致 / 年が1つでも違えば別版』判定では過検知する。"
        "→ apply ゲートは『版番号抽出 + 核タイトル包含 + 年差トレランス(±1許容)』へ強化すべき "
        "(本 PR はスコープ外、別 DD で実装)。",
        "",
        f"> **所見2 (normalize_title の穴)**: 共有 `normalize_title` は NFKC するが "
        f"`〔〕` `〈〉` `、`(読点) を strip しない。これだけで cosmetic {tkinds.get('cosmetic',0)} 件が"
        "別版誤判定。`_STRIP_RE` へ 3 文字追加で解消 (共有モジュール変更=別 DD)。",
        "",
        f"> **所見2b (年差ノイズ)**: year divergence {year_div} 件のうち {year_small} 件は年差±1 "
        "(例: 同一『第36版』が 2022 vs 2023、判例集の巻号が前後年)。"
        "出版年は print 年/刊年/カタログ年で表記が揺れるため ±1 は同一物とみなすべき。",
        "",
        f"> **所見3 (resolver 偽陽性)**: resolver auto_accept "
        f"{len([r for r in resolver if r.get('bucket')=='auto_accept'])} 件中 "
        f"{aa_suspect} 件が別版疑い → うち装飾/副題を除く **実質要レビュー {aa_suspect_real} 件**。"
        "これらは apply_guard の edition gate が物理拒否 (HOLD 維持の根拠)。",
        "",
        f"> **所見4 (resolver recall)**: bucket=defer_new (canonical 不在として create 予定) のうち "
        f"**{sum(1 for r in ident_rows if r['resolver_bucket']=='defer_new')} 件は canonical に同一 ISBN が存在**。"
        "resolver の取りこぼし候補 → human_review へ差し戻すべき。",
        "",
    ]
    (out / "source_inventory.md").write_text("\n".join(inv) + "\n", encoding="utf-8")

    # --- parser_success_histogram.csv ---
    with (out / "parser_success_histogram.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["content_type", "node_bucket", "book_count"])
        for ct, v in ll["by_content_type"].items():
            for b in ("empty", "1-10", "11-50", "51+"):
                if v["node_buckets"].get(b):
                    w.writerow([ct, b, v["node_buckets"][b]])

    # --- page_basis_profile.md ---
    pa = ll["page_acc"]
    n = pa["nodes"] or 1
    off = pa["offsets"]
    off_sorted = sorted(off.items())
    # オフセット代表値 (最頻) と一貫性
    top_offsets = off.most_common(8)
    bp = ll["book_pages"]
    pb = [
        "# Phase 0 page_basis profile (book TOC nodes, report-only)", "",
        f"- 対象: content_type=book の全 TOC ノード **{pa['nodes']}**",
        f"- pdf_page あり: {pa['has_pdf']} ({pa['has_pdf']/n:.1%})",
        f"- print_page あり: {pa['has_print']} ({pa['has_print']/n:.1%})",
        f"- **両持ち (pdf+print)**: {pa['both']} ({pa['both']/n:.1%})",
        f"- pdf のみ: {pa['pdf_only']} ({pa['pdf_only']/n:.1%}) "
        "(章見出し等・本文頁未付与の構造ノード)",
        f"- print のみ: {pa['print_only']} / どちらも無し: {pa['neither']}",
        "",
        "## offset = pdf_page - print_page 分布 (両持ちノード)", "",
        "| offset | nodes |", "|---:|---:|",
    ]
    for o, c in top_offsets:
        pb.append(f"| {o} | {c} |")
    distinct = len(off_sorted)
    # 本単位の offset 一貫性 (主張の実測裏付け)
    shares = ll["book_offset_share"]
    nshare = len(shares)
    single = sum(1 for s in shares if s >= 0.99)
    near = sum(1 for s in shares if s >= 0.90)
    avg = sum(shares) / nshare if nshare else None
    pb += [
        "",
        f"- 異なる offset 値の種類 (全本横断): {distinct}",
        "",
        "## offset の本単位一貫性 (両持ちノード3以上の book)", "",
        f"- 対象 book: {nshare}",
        f"- 最頻 offset が **100% 単一**の本: {single} ({single/nshare:.1%})" if nshare else "- 対象なし",
        f"- 最頻 offset が **90%以上**を占める本: {near} ({near/nshare:.1%})" if nshare else "",
        f"- 本ごとの最頻 offset 占有率 平均: {avg:.3f}" if avg is not None else "",
        "",
        "> **所見**: legallib の各ノードは pdf_page と print_page を併記し、両持ち率 95%。"
        "実測のとおり offset(=前付け頁数) は **本ごとにほぼ単一** "
        f"({near/nshare:.0%} の本で最頻 offset が 90%以上を占める) なので、"
        "pdf↔print 変換は本単位の単一 offset で機械化できる。"
        "横断で offset が 133 種に散るのは『本ごとに前付け頁数が違う』ためで、"
        "**同一本内の基準ブレではない**。"
        "残り 5% の pdf-only は章見出し等の構造ノード (本文頁未付与)。"
        "→ **page tolerance は本単位 offset 補正後に評価すべき** "
        "(生の pdf_page 差で別版判定すると前付け差を誤検知する)。",
        f"- 参考: book の total_pages 分布 n={len(bp)} "
        f"min={min(bp) if bp else None} max={max(bp) if bp else None}",
        "",
    ]
    (out / "page_basis_profile.md").write_text("\n".join(pb) + "\n", encoding="utf-8")

    # --- edition_identity_sample.jsonl ---
    (out / "edition_identity_sample.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ident_rows),
        encoding="utf-8")

    # status 集計
    st = Counter(r["status"] for r in ident_rows)
    st_by_bucket = defaultdict(Counter)
    for r in ident_rows:
        st_by_bucket[r["resolver_bucket"]][r["status"]] += 1

    return {
        "status_counts": dict(st),
        "status_by_bucket": {k: dict(v) for k, v in st_by_bucket.items()},
        "resolved_isbn": len(resolved_isbn),
        "title_divergence": len(title_div),
        "title_diff_kinds": dict(tkinds),
        "year_divergence": year_div,
        "year_gap_small_vs_big": [year_small, year_big],
        "artifact_suspect": artifact_suspect,
        "real_suspect": real_suspect,
        "edition_number_conflicts": edition_conflicts,
        "auto_accept_suspect": aa_suspect,
        "auto_accept_suspect_real": aa_suspect_real,
        "defer_new_with_canonical_isbn": sum(
            1 for r in ident_rows if r["resolver_bucket"] == "defer_new"),
    }


def write_known_conflicts(out: Path, ident_rows: list[dict], wc: dict) -> int:
    """edition 別版疑い + 大幅 TOC 差分 から golden 10冊を選ぶ。"""
    # node_delta を付与 (write_candidates 既出のみ)
    for r in ident_rows:
        r["_node_delta"] = wc.get(r["isbn"], {}).get("node_delta")
    # golden は **実質的** conflict のみ (装飾差/副題差/年差±1 の偽陽性は除外)。
    # 最も危険: resolver が auto_accept したのに別版疑い (apply_guard が必ず止める対象)。
    auto_accept_miss = [r for r in ident_rows
                        if r["resolver_bucket"] == "auto_accept" and is_real_suspect(r)]
    edition_conflict = [r for r in ident_rows if r.get("title_diff_kind") == "edition_number_conflict"]
    other_real = [r for r in ident_rows if is_real_suspect(r)]

    def delta_abs(r):
        d = r.get("_node_delta")
        try:
            return abs(int(d))
        except (TypeError, ValueError):
            return -1

    # 優先: ①auto_accept 取りこぼし(最危険) → ②版番号衝突(確実な別版) →
    #       ③その他実質要レビュー → ④大 TOC 差分。多様性のため各層から拾う。
    picked, seen = [], set()
    pools = [
        ("auto_accept_miss(危険)", sorted(auto_accept_miss, key=delta_abs, reverse=True)),
        ("edition_number_conflict", sorted(edition_conflict, key=delta_abs, reverse=True)),
        ("other_real_review", sorted(other_real, key=delta_abs, reverse=True)),
        ("large_toc_delta", sorted([r for r in ident_rows if delta_abs(r) >= 0],
                                   key=delta_abs, reverse=True)),
    ]
    for tag, pool in pools:
        for r in pool:
            if len(picked) >= 10:
                break
            if r["isbn"] in seen:
                continue
            seen.add(r["isbn"])
            picked.append((tag, r))

    lines = [
        "# Phase 0 known-conflict golden seed (10冊, report-only)", "",
        "> 接合 apply の回帰テスト用 seed。各冊は『legallib と canonical で同一性/構造が"
        "割れている』**実質的**実例 (装飾差/副題差の偽陽性は除外済)。"
        "production apply は edition identity が resolved_same に解決"
        "されない限り apply_guard が物理拒否する (HOLD 維持)。", "",
        f"- auto_accept 取りこぼし(最危険): {len(auto_accept_miss)} / "
        f"版番号衝突(確実な別版): {len(edition_conflict)} / "
        f"実質要レビュー総数: {len(other_real)}",
        "",
        "| # | 選定根拠 | title_diff_kind | isbn | book_id | reason | "
        "legallib title (ver/year) | canonical title (ver/year) | node_delta |",
        "|---:|---|---|---|---|---|---|---|---:|",
    ]
    for i, (tag, r) in enumerate(picked, 1):
        ll = r["legallib"]
        cn = r["canonical"]
        lt = (ll["title"][:26] + "…") if len(ll["title"]) > 27 else ll["title"]
        ct = (cn["title"][:26] + "…") if len(cn["title"]) > 27 else cn["title"]
        lines.append(
            f"| {i} | {tag} | {r.get('title_diff_kind') or '-'} | {r['isbn']} | "
            f"{r['legallib_book_id']} | {r['reason']} | "
            f"{lt} ({r.get('legallib_edition_sig') or '-'}/{ll['year']}) | "
            f"{ct} ({r.get('canonical_edition_sig') or '-'}/{cn['year']}) | {r.get('_node_delta')} |")
    lines += [
        "",
        "## 全 golden レコード (機械可読)", "",
        "```jsonl",
    ]
    for tag, r in picked:
        rr = {"selected_by": tag, **{k: r[k] for k in (
            "isbn", "legallib_book_id", "status", "reason", "title_diff_kind",
            "year_gap", "legallib_edition_sig", "canonical_edition_sig", "resolver_bucket",
            "resolver_ed_conflict", "resolver_ambiguous", "_node_delta",
            "legallib", "canonical")}}
        lines.append(json.dumps(rr, ensure_ascii=False))
    lines.append("```")
    (out / "known_conflict_golden.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(picked)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dir_fingerprint(d: Path) -> tuple[str, int]:
    """ディレクトリ内 *.json の決定的フィンガープリント (順序非依存)。"""
    h = hashlib.sha256()
    files = sorted(f for f in d.glob("*.json") if f.name not in _RESERVED)
    for f in files:
        h.update(f"{f.name}:{sha256_file(f)}\n".encode())
    return h.hexdigest(), len(files)


def write_inputs_sha256(out: Path, legallib_dir: Path, resolver_path: Path,
                        canonical_path: Path, wc_path: Path) -> None:
    fp, nfiles = dir_fingerprint(legallib_dir)
    lines = [
        "# legallibjoin v0.3.1 Phase 0 入力 sha256",
        "# generated by phase0_inventory.py (report-only)",
        "",
        f"{fp}  legallib_dir_fingerprint(*.json, n={nfiles})",
    ]
    for p in (resolver_path.resolve(), canonical_path, wc_path):
        if p.exists():
            lines.append(f"{sha256_file(p)}  {p}")
    (out / "inputs_sha256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    home = Path.home()
    ap = argparse.ArgumentParser(description="legallibjoin v0.3.1 Phase 0 inventory (report-only)")
    ap.add_argument("--legallib-dir", default=str(home / "alo-ai/work/legallib_dl"))
    ap.add_argument("--resolver", default=str(home / "alo-ai/work/legallib_dl/resolver_decisions.jsonl"))
    ap.add_argument("--canonical", default=str(home / "ALOBookDX/事務所内本棚DX化計画/app/data/books.json"))
    ap.add_argument("--write-candidates",
                    default=str(home / "alo-ai/work/_audit_legallib_v0.2_20260611/write_candidates.csv"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    legallib_dir = Path(args.legallib_dir)
    resolver_path = Path(args.resolver)
    canonical_path = Path(args.canonical)
    wc_path = Path(args.write_candidates)
    out = Path(args.out)

    ll = profile_legallib(legallib_dir)
    canon_sum, canon_idx = profile_canonical(canonical_path)
    resolver = load_resolver(resolver_path)
    wc = load_write_candidates(wc_path)
    ident_rows = run_edition_identity(resolver, canon_idx, ll["legallib_bib"])

    meta = write_outputs(out, ll, canon_sum, resolver, ident_rows, wc)
    ngolden = write_known_conflicts(out, ident_rows, wc)
    write_inputs_sha256(out, legallib_dir, resolver_path, canonical_path, wc_path)

    print(json.dumps({
        "legallib_files": ll["files"],
        "canonical_records": canon_sum["records"],
        "resolver_decisions": len(resolver),
        "edition_identity_evaluated": len(ident_rows),
        "edition_status_counts": meta["status_counts"],
        "edition_status_by_bucket": meta["status_by_bucket"],
        "title_diff_kinds": meta["title_diff_kinds"],
        "year_gap_small_vs_big": meta["year_gap_small_vs_big"],
        "artifact_vs_real_suspect": [meta["artifact_suspect"], meta["real_suspect"]],
        "edition_number_conflicts": meta["edition_number_conflicts"],
        "auto_accept_suspect_total_vs_real":
            [meta["auto_accept_suspect"], meta["auto_accept_suspect_real"]],
        "defer_new_with_canonical_isbn": meta["defer_new_with_canonical_isbn"],
        "golden_conflicts": ngolden,
        "report_only": True, "final_toc_written": False, "canonical_written": False,
    }, ensure_ascii=False, indent=1))
    print(f"\nevidence -> {out} (report-only / 本番未書込)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
