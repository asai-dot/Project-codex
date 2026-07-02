#\!/usr/bin/env python3
"""
run_article_join_dryrun.py — ORCH-ARTICLE-JOIN dry-run executor (L4, read-only)

Inputs
  --authority   artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v15.csv
  --labeled     build/labeled_v0.2.1/article_meta_labeled.jsonl
                (Mac側: /Users/yuta/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/labeled_v0.2.1/)
  --out-csv     artifacts/periodical/article_join_dryrun_v0.1.csv
  --out-json    artifacts/periodical/article_join_summary_v0.1.json

Treatment (per ORCH-ARTICLE-JOIN_order_20260624.md / PROGRESS_REVIEW D2):
  * key_value == 'BN01263667' (別冊ジュリスト系=判例百選58誌) → isbn_per_issue として扱う。
    通巻接合を行わず、issue_id = isbn:bj-{N} (Nは 別冊ジュリスト{N})。
  * 掲載誌等 に 別冊ジュリスト{N} が含まれる(他誌からの 所収) → 同上扱いに昇格。
  * key_type == 'isbn_per_issue' → issue_id = isbn:{書誌キー(『...』から抽出)}。
  * それ以外(ISSN/NCID解決済み) → 掲載誌等 から (通巻 | 巻号 | YYYY-MM) を抽出し
    issue_id = {key_type}:{key_value}#{tsuukan_or_ym}。
  * 不解決 → orphan + reason (authority_unresolved / tsuukan_unavailable / meta_missing)。

Read-only。DB/Box/ネット書込なし。canonical promotion / accepted edge化 / 外部公開なし。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_AUTHORITY = "artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v15.csv"
DEFAULT_LABELED = "/Users/yuta/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/labeled_v0.2.1/article_meta_labeled.jsonl"
DEFAULT_OUT_CSV = "artifacts/periodical/article_join_dryrun_v0.1.csv"
DEFAULT_OUT_JSON = "artifacts/periodical/article_join_summary_v0.1.json"

BESSATSU_NCID = "BN01263667"

# collision_split された canonical を、掲載誌等の先頭表記で実在誌へ振り分ける（ORCH-L4-COVERAGE-LIFT）。
# キー=元 canonical, 値=(掲載誌等prefix, 振り分け先 canonical) のリスト（先勝ち）。
# 振り分け先は authority に解決済みで存在すること。既存マージは一切変更せず orphan のみ救済する。
SPLIT_MAP = {
    "商事法務": [
        ("旬刊商事法務", "旬刊商事法務"),
        ("国際商事法務", "国際商事法務"),
        ("資料版商事法務", "資料版商事法務"),
    ],
    "タイム": [
        ("判例タイムズ", "判例タイムズ"),
    ],
}

HEADERS = [
    "article_id", "issue_id", "journal_canonical", "key_type", "key_value",
    "tsuukan_or_ym", "pub_year", "vol", "issue_no", "page_start",
    "seq_in_issue", "title", "join_status", "orphan_reason",
]


def nfkc(s):
    return unicodedata.normalize("NFKC", s) if s else ""


_BESSATSU_RE = re.compile(r"別冊ジュリスト\s*(\d+)")
_SHOZO_TITLE_RE = re.compile(r"『([^』]+)』")
_NUM_AFTER_NAME_RE = re.compile(r"(\d+(?:[-—―]\d+)?(?:[・·]\d+)*)")
_VOL_ISSUE_RE = re.compile(r"^(\d+)[-—―](\d+)$")
_COMBINED_RE = re.compile(r"^(\d+)(?:[・·](\d+))+$")
_PAGE_RE = re.compile(r"[pｐ]\s*(\d+)")
_YEAR_RE = re.compile(r"(\d{4})")
_MONTH_RE = re.compile(r"\d{4}[.\-/．](\d{1,2})")


def load_authority(path):
    by_canonical = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            jc = (row.get("journal_canonical") or "").strip()
            if not jc:
                continue
            by_canonical[jc] = {
                "key_type": (row.get("key_type") or "").strip(),
                "key_value": (row.get("key_value") or "").strip(),
                "status": (row.get("status") or "").strip(),
            }
    return by_canonical


def extract_bessatsu_no(keishi_norm):
    m = _BESSATSU_RE.search(keishi_norm)
    return m.group(1) if m else None


def extract_book_key(keishi_norm):
    m = _SHOZO_TITLE_RE.search(keishi_norm)
    if not m:
        return None
    title = m.group(1)
    title = re.sub(r"（別冊ジュリスト\s*\d+）", "", title)
    title = re.sub(r"\s+", "", title).strip()
    return title or None


def parse_journal_number_segment(keishi_norm, journal_canonical):
    """掲載誌等 から journal_canonical を剥がした後の '号' 文字列を返す。
    入力例:
      '判例タイムズ1508,p14~35' → '1508'
      '税理69-3,p2~3'          → '69-3'
      '労働法律旬報2095・2096,p4~48' → '2095・2096'
      '銀行法務2170-4（増刊号）,p1~119' → '2170-4'
    """
    if not keishi_norm:
        return None
    s = keishi_norm.split(",")[0]
    s = re.sub(r"[（(].*?[)）]", "", s).strip()
    if journal_canonical and s.startswith(journal_canonical):
        s = s[len(journal_canonical):]
    else:
        for prefix in ("旬刊", "月刊", "週刊", "季刊"):
            if s.startswith(prefix + journal_canonical):
                s = s[len(prefix) + len(journal_canonical):]
                break
    s = s.strip(" ,.")
    if not s:
        return None
    m = _NUM_AFTER_NAME_RE.match(s)
    if m:
        return m.group(1)
    m2 = re.search(r"\d+(?:[-—―]\d+)?", s)
    return m2.group(0) if m2 else None


def parse_page_start(keishi_norm):
    if not keishi_norm:
        return None
    m = _PAGE_RE.search(keishi_norm)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def parse_pub_ym(pub_date_norm):
    if not pub_date_norm:
        return "", ""
    y = _YEAR_RE.search(pub_date_norm)
    m = _MONTH_RE.search(pub_date_norm)
    year = y.group(1) if y else ""
    month = m.group(1).zfill(2) if m else ""
    return year, month


def derive_tsuukan_or_ym(num_seg, year, month):
    """returns (tsuukan_or_ym, vol, issue_no, rule)
       rule ∈ {direct, vol_issue, combined, ym_terminal, none}
    """
    if num_seg:
        m_vi = _VOL_ISSUE_RE.match(num_seg)
        if m_vi:
            vol, issue = m_vi.group(1), m_vi.group(2)
            return f"v{vol}n{issue}", vol, issue, "vol_issue"
        m_comb = _COMBINED_RE.match(num_seg)
        if m_comb:
            parts = re.split(r"[・·]", num_seg)
            return "-".join(parts), "", "-".join(parts), "combined"
        if num_seg.isdigit():
            return num_seg, "", num_seg, "direct"
    if year:
        ym = f"{year}-{month}" if month else year
        return ym, "", "", "ym_terminal"
    return "", "", "", "none"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--authority", default=DEFAULT_AUTHORITY)
    ap.add_argument("--labeled", default=DEFAULT_LABELED)
    ap.add_argument("--out-csv", default=DEFAULT_OUT_CSV)
    ap.add_argument("--out-json", default=DEFAULT_OUT_JSON)
    args = ap.parse_args()

    authority_path = Path(args.authority)
    labeled_path = Path(args.labeled)
    if not authority_path.exists():
        print(f"ERROR authority not found: {authority_path}", file=sys.stderr)
        return 2
    if not labeled_path.exists():
        print(f"ERROR labeled jsonl not found: {labeled_path}", file=sys.stderr)
        return 2

    authority = load_authority(authority_path)
    print(f"[info] authority loaded: {len(authority)} canonical entries", file=sys.stderr)

    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    joined_n = 0
    orphan_n = 0
    reason_cnt = Counter()
    orphan_by_journal = Counter()
    issue_seq_counter = defaultdict(int)
    article_id_seen = {}
    collision_count = 0

    fout = out_csv.open("w", encoding="utf-8", newline="")
    writer = csv.writer(fout)
    writer.writerow(HEADERS)

    with labeled_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            total += 1

            title = (rec.get("標題") or "").replace("\n", " ").strip()
            jc_raw = (rec.get("journal_canonical") or "").strip()
            keishi = nfkc(rec.get("掲載誌等") or "")
            pub_date = nfkc(rec.get("発行年月日") or "")
            year, month = parse_pub_ym(pub_date)
            page_start = parse_page_start(keishi)

            # collision_split canonical の掲載誌先頭表記による実在誌への振り分け（orphan救済のみ）
            if jc_raw in SPLIT_MAP:
                for prefix, target in SPLIT_MAP[jc_raw]:
                    if keishi.startswith(prefix):
                        jc_raw = target
                        break

            bj_no = extract_bessatsu_no(keishi)
            auth = authority.get(jc_raw)

            join_status = "orphan"
            orphan_reason = ""
            key_type_out = ""
            key_value_out = ""
            issue_id = ""
            article_id = ""
            tsuukan_or_ym = ""
            vol = ""
            issue_no = ""
            journal_canonical_out = jc_raw

            is_bessatsu = bool(bj_no) or (auth and auth["key_value"] == BESSATSU_NCID)

            if is_bessatsu and bj_no:
                journal_canonical_out = f"別冊ジュリスト{bj_no}"
                key_type_out = "isbn_per_issue"
                key_value_out = f"{BESSATSU_NCID}#bj-{bj_no}"
                tsuukan_or_ym = f"bj-{bj_no}"
                issue_id = f"isbn:bj-{bj_no}"
                join_status = "joined"
            elif is_bessatsu and not bj_no:
                orphan_reason = "tsuukan_unavailable"
                orphan_by_journal[jc_raw] += 1
            elif not auth:
                orphan_reason = "authority_unresolved"
                orphan_by_journal[jc_raw or "(empty)"] += 1
            elif auth["status"] in {"unresolved", "collision_split"} or not auth["key_type"]:
                orphan_reason = "authority_unresolved"
                orphan_by_journal[jc_raw] += 1
            elif auth["key_type"] == "isbn_per_issue" or auth["status"] in {"seed_isbn_per_issue", "seed_bessatsu_jurist"}:
                book_key = extract_book_key(keishi)
                if book_key:
                    key_type_out = "isbn_per_issue"
                    key_value_out = book_key
                    tsuukan_or_ym = book_key
                    issue_id = f"isbn:{book_key}"
                    join_status = "joined"
                else:
                    # 『…』書誌が無い isbn_per_issue/別冊系: 誌自身の号数を per-issue キーに用いる
                    # (例: 季刊・民事法研究21 / 商法研究24 / 現代刑事法4-1)。号が取れなければ orphan。
                    num_seg = parse_journal_number_segment(keishi, jc_raw)
                    series_no, _v, _i, _rule = derive_tsuukan_or_ym(num_seg, year, month)
                    if series_no:
                        key_type_out = "isbn_per_issue"
                        key_value_out = f"{jc_raw}#{series_no}"
                        tsuukan_or_ym = series_no
                        issue_id = f"isbn:{jc_raw}#{series_no}"
                        join_status = "joined"
                    else:
                        orphan_reason = "tsuukan_unavailable"
                        orphan_by_journal[jc_raw] += 1
            else:
                num_seg = parse_journal_number_segment(keishi, jc_raw)
                tsuukan_or_ym, vol, issue_no, rule = derive_tsuukan_or_ym(num_seg, year, month)
                if not tsuukan_or_ym:
                    orphan_reason = "tsuukan_unavailable"
                    orphan_by_journal[jc_raw] += 1
                else:
                    key_type_out = auth["key_type"]
                    key_value_out = auth["key_value"]
                    issue_id = f"{key_type_out}:{key_value_out}#{tsuukan_or_ym}"
                    join_status = "joined"

            seq_for_row = ""
            if join_status == "joined":
                issue_seq_counter[issue_id] += 1
                seq_in_issue = issue_seq_counter[issue_id]
                seq_for_row = seq_in_issue
                if page_start is not None:
                    article_id = f"{issue_id}#p{page_start}"
                else:
                    article_id = f"{issue_id}#a{seq_in_issue}"
                prev = article_id_seen.get(article_id)
                if prev is None:
                    article_id_seen[article_id] = title
                elif prev != title:
                    collision_count += 1
                    article_id = f"{article_id}.{seq_in_issue}"
                    article_id_seen[article_id] = title
                joined_n += 1
            else:
                orphan_n += 1
                if not orphan_reason:
                    orphan_reason = "meta_missing"
                reason_cnt[orphan_reason] += 1

            writer.writerow([
                article_id, issue_id, journal_canonical_out, key_type_out, key_value_out,
                tsuukan_or_ym, year, vol, issue_no, page_start if page_start is not None else "",
                seq_for_row, title, join_status, orphan_reason,
            ])

    fout.close()

    coverage = joined_n / total if total else 0.0
    summary = {
        "total": total,
        "joined": joined_n,
        "orphan": orphan_n,
        "coverage": round(coverage, 4),
        "orphan_by_reason": dict(reason_cnt),
        "orphan_by_journal_top20": [
            {"journal_canonical": jc, "orphan": n}
            for jc, n in orphan_by_journal.most_common(20)
        ],
        "collision_count": collision_count,
        "authority_path": str(authority_path),
        "labeled_path": str(labeled_path),
        "schema_version": "v0.1",
    }
    Path(args.out_json).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[done] total={total} joined={joined_n} orphan={orphan_n} coverage={coverage:.2%}", file=sys.stderr)
    print(f"[out]  {args.out_csv}", file=sys.stderr)
    print(f"[out]  {args.out_json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
