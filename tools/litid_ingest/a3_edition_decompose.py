#!/usr/bin/env python3
"""
A3後段: edition_statement / printing_no / date_role への raw-preserving 分解
- 入力: DB から取得した edition TSV (bib_id\tedition)、または stdin
- 出力: bib_id\tedition_raw\tedition_statement\tprinting_no\tdate_role\tdecomp_type を stdout
- 設計原則: raw を破壊しない。正規化だけで同一版と決めない。
- 投入禁止: DB への書き込みなし（read-only）。

Usage:
  python a3_edition_decompose.py < cohortA_edition.tsv > a3_decomposed.tsv
  python a3_edition_decompose.py --from-db  # 環境変数 DATABASE_URL が必要

decomp_type 語彙:
  edition_only       : 版/改訂語のみ（刷なし）
  printing_only      : 刷のみ（版なし）→ edition_statement=None
  edition_and_print  : 版＋刷の複合
  date_only          : 年月のみ → date_role に格納
  na_placeholder     : [N/A] → 全フィールド None
  unknown            : 未分類（要手動確認）
"""

import re
import sys
import csv
import argparse

# ── パターン定義（raw-preserving; 正規化はしない）──────────────────────────

# 刷のみ（版を含まない）
_PRINTING_ONLY = re.compile(
    r'^(?:第?(?:[0-9０-９]+|[一二三四五六七八九十百]+)[刷])$'
    r'|^初刷$|^重刷$|^刷重$',
    re.UNICODE
)

# 日付のみ（年月日形式・ISO形式・括弧付き表記も含む）
_DATE_ONLY = re.compile(
    r'^\d{4}年\d{1,2}月(?:\d{1,2}日)?'  # YYYY年MM月 / YYYY年MM月DD日
    r'(?:[（\(].*[）\)])?$'              # 任意の括弧付き補足 e.g. (または02月)
    r'|^\d{4}/\d{1,2}/\d{1,2}$',        # ISO: YYYY/MM/DD
    re.UNICODE
)

# 版を表す語 (後から使う)
_EDITION_WORDS = re.compile(
    r'版|訂|改|新版|補|増補|全訂|最新|初版|改版|改訂|刷新|令和|平成|昭和|年度',
    re.UNICODE
)

# 刷番号を抽出するパターン
_PRINT_NO_RE = re.compile(
    r'(?:第(?:[0-9０-９]+|[一二三四五六七八九十百]+)刷|初刷)',
    re.UNICODE
)

# 版部分を抽出するパターン（複合値から刷を除いた残り）
_EDITION_PART_RE = re.compile(
    r'第?(?:[0-9０-９]+|[一二三四五六七八九十百]+)刷|初刷',
    re.UNICODE
)


def decompose_edition(raw: str) -> dict:
    """
    Returns dict with keys: edition_statement, printing_no, date_role, decomp_type
    All values are str or None. Never modifies raw.
    """
    if not raw or raw.strip() == '':
        return dict(edition_statement=None, printing_no=None, date_role=None, decomp_type='na_placeholder')

    v = raw.strip()

    # [N/A] プレースホルダ
    if v == '[N/A]':
        return dict(edition_statement=None, printing_no=None, date_role=None, decomp_type='na_placeholder')

    # 日付のみ
    if _DATE_ONLY.match(v):
        return dict(edition_statement=None, printing_no=None, date_role=v, decomp_type='date_only')

    # 刷のみ（版を含まない）
    if _PRINTING_ONLY.match(v):
        return dict(edition_statement=None, printing_no=v, date_role=None, decomp_type='printing_only')

    # 版＋刷の複合: 「第3版第1刷」「初版第1刷」「第1版第2刷」「第15版第1刷」
    print_matches = _PRINT_NO_RE.findall(v)
    if print_matches and _EDITION_WORDS.search(v):
        # 刷部分を除いた残りが edition_statement
        edition_part = _EDITION_PART_RE.sub('', v).strip()
        printing_part = ''.join(print_matches)
        if edition_part:
            return dict(
                edition_statement=edition_part,
                printing_no=printing_part,
                date_role=None,
                decomp_type='edition_and_print'
            )
        else:
            # 刷除去後に版が残らない → printing_only 扱い
            return dict(edition_statement=None, printing_no=printing_part, date_role=None, decomp_type='printing_only')

    # 版語を含む → edition_only
    if _EDITION_WORDS.search(v):
        return dict(edition_statement=v, printing_no=None, date_role=None, decomp_type='edition_only')

    # 未分類
    return dict(edition_statement=v, printing_no=None, date_role=None, decomp_type='unknown')


def process_tsv(reader, writer):
    for row in reader:
        if len(row) < 2:
            continue
        bib_id, edition_raw = row[0], row[1]
        result = decompose_edition(edition_raw)
        writer.writerow([
            bib_id,
            edition_raw,
            result['edition_statement'] or '',
            result['printing_no'] or '',
            result['date_role'] or '',
            result['decomp_type'],
        ])


def main():
    parser = argparse.ArgumentParser(description='A3 edition decompose')
    parser.add_argument('--from-db', action='store_true', help='Read from DATABASE_URL instead of stdin')
    args = parser.parse_args()

    out = csv.writer(sys.stdout, delimiter='\t', lineterminator='\n')
    out.writerow(['bib_id', 'edition_raw', 'edition_statement', 'printing_no', 'date_role', 'decomp_type'])

    if args.from_db:
        import os, psycopg2
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            sys.exit('ERROR: DATABASE_URL not set')
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT bib_id, edition
            FROM biblio.bib_records
            WHERE source = 'asai-bookshelf'
              AND edition IS NOT NULL AND edition != ''
            ORDER BY bib_id
        """)
        for bib_id, edition_raw in cur:
            result = decompose_edition(edition_raw or '')
            out.writerow([
                bib_id, edition_raw or '',
                result['edition_statement'] or '',
                result['printing_no'] or '',
                result['date_role'] or '',
                result['decomp_type'],
            ])
        conn.close()
    else:
        reader = csv.reader(sys.stdin, delimiter='\t')
        next(reader, None)  # skip header if present
        process_tsv(reader, out)


if __name__ == '__main__':
    main()
