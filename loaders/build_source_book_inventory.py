#!/usr/bin/env python3
"""
build_source_book_inventory.py — リーガルライブラリー(弁コムライブラリー)書式の「根拠本(175冊)」を
出典本単位に集計し、うちの蔵書 canonical (books.json) と突き合わせる前段の索引を作る。

なぜ（業務上の意味）:
  tmplstruct は 3,806書式の構造を OCR から逆算しているが、生材料はリーガルライブラリーOCR依存。
  各書式は弁コムカタログ上で必ず「出典書籍(content_id)＋ページ＋直DL URL」を持つ。
  出典本175冊を集約し ISBN を解決しておけば、(a) 各書式の native Word/PDF/Excel 原本の直DL、
  (b) うちが現物所蔵/自前PDF/OCR済みの本かどうか(books.json)、(c) 出版社サイト/付録DVDの有無、
  を判定でき、OCR より遥かにきれいな構造化材料に切り替えられる。

入力(いずれもリーガルライブラリー側カタログ。Box: 弁コム法律書カタログ_YYYYMMDD/ に保存):
  --templates  templates.csv  (1行1書式・175冊×6,976書式・tmpl_link_url 等)
  --catalog    catalog.csv    (1行1冊・全4,490冊・thumbnail_url/url に ISBN あり)
出力:
  --out        source_books_175.csv (1行1出典本)
このスクリプトは read-only・決定論。LLM 不使用、Python の csv/正規表現のみ。
"""
from __future__ import annotations
import argparse, csv, re, collections, sys
csv.field_size_limit(10**7)

ISBN13 = re.compile(r'97[89]\d{10}')
DL_RE  = re.compile(r'ダウンロード|ＤＬ|特典|サンプル書式|ひな形データ|書式データ|word\s*版|ワード版', re.I)
DVD_RE = re.compile(r'CD-?ROM|ＣＤ|DVD|ＤＶＤ|付録|ディスク|CD付|DVD付')

def isbn_from(*vals):
    for v in vals:
        if not v: continue
        m = ISBN13.search(v.replace('-', ''))
        if m: return m.group(0)
    return ''

def load_catalog(path):
    cat = {}
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            cat[r['content_id']] = {
                'isbn': isbn_from(r.get('thumbnail_url',''), r.get('url','')),
                'pub_site': r.get('url','') or '',
                'authors': r.get('authors','') or '',
                'release_date': r.get('release_date','') or '',
                'title_sub': r.get('title_sub','') or '',
                'abstract': r.get('abstract','') or '',
            }
    return cat

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--templates', default='/tmp/templates.csv')
    ap.add_argument('--catalog',   default='/tmp/catalog.csv')
    ap.add_argument('--out', default='docs/tmplstruct/sourcebook_match/source_books_175.csv')
    args = ap.parse_args()

    cat = load_catalog(args.catalog)
    books = collections.OrderedDict()
    fmt_total = collections.Counter()
    with open(args.templates, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            cid = r['tmpl_contents_id'] or r['content_id']
            b = books.setdefault(cid, {'title': r['title'], 'publisher': r['publisher'],
                                       'reader_url': r['reader_url'], 'n': 0,
                                       'fmt': collections.Counter()})
            b['n'] += 1
            fmt = (r['tmpl_format'] or '').lower(); b['fmt'][fmt] += 1; fmt_total[fmt] += 1

    rows = []
    for cid, b in books.items():
        c = cat.get(cid, {})
        blob = ' '.join([b['title'], c.get('title_sub',''), c.get('abstract','')])
        rows.append({
            'content_id': cid, 'title': b['title'], 'publisher': b['publisher'],
            'isbn': c.get('isbn',''), 'pub_site': c.get('pub_site',''),
            'authors': c.get('authors',''), 'release_date': c.get('release_date',''),
            'n_templates': b['n'], 'word': b['fmt'].get('word',0),
            'pdf': b['fmt'].get('pdf',0), 'excel': b['fmt'].get('excel',0),
            'dl_signal': int(bool(DL_RE.search(blob))),
            'dvd_signal': int(bool(DVD_RE.search(blob))),
            'reader_url': b['reader_url'],
        })
    rows.sort(key=lambda x: -x['n_templates'])

    with open(args.out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader()
        for r in rows: w.writerow(r)

    isbn_ct = sum(1 for r in rows if r['isbn'])
    print(f"source books: {len(rows)} / templates: {sum(r['n_templates'] for r in rows)}")
    print(f"format totals: {dict(fmt_total)}")
    print(f"ISBN resolved: {isbn_ct}/{len(rows)}  (→ books.json ISBN突合可)")
    print(f"no-ISBN (要 書名+出版社 突合): {len(rows)-isbn_ct}")
    print(f"wrote {args.out}")

if __name__ == '__main__':
    main()
