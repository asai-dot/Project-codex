#!/usr/bin/env python3
"""
match_sourcebooks_to_bookjson.py — 出典本175冊 (source_books_175.csv) を、うちの蔵書 canonical
(books.json / bookdx_canonical_schema_v1) と突き合わせ、「きれいな材料がうちにあるか」を判定する。

判定する材料チャネル（各出典本ごと）:
  owned_physical   : books.json physical.present                → 現物を所蔵（高品質再スキャン可）
  pdf_present      : books.json digital.pdf_present + pdf_files  → 自前スキャンPDFあり
  ocr_status       : books.json digital.ocr_status              → OCR済みか
  pub_download     : source側 dl_signal / 出版社サイト          → 出版社の書式DL特典あり
  dvd_cdrom        : source側 dvd_signal                        → 付録CD-ROM/DVDあり
  native_dl        : 弁コム doc-templates 直DL (tmpl_link_url)  → native Word/PDF/Excel 原本（全件あり）

突合鍵: ① ISBN 完全一致（books.json identity.isbn / internal_id=isbn_<13>）
        ② ②書名正規化＋出版社正規化の一致（ISBN欠落74冊向け）。曖昧は match='fuzzy' で human_review。

read-only・決定論。books.json は改変しない。出力は CSV + サマリ MD のみ。
※ books.json は約33MB・Mac ローカル (~/alo-ai/.../app/data/books.json) にあるためワーカーが実行する。
"""
from __future__ import annotations
import argparse, csv, json, re, sys, collections
csv.field_size_limit(10**7)

def norm_title(s):
    s = s or ''
    s = re.sub(r'[〔（(【\[].*?[〕）)】\]]', '', s)          # 版次・括弧注記を除去
    s = re.sub(r'[\s　・,，、。.\-—―ー~〜/／【】\[\]「」『』〈〉]', '', s)
    s = s.replace('第','').replace('版','').replace('改訂','').replace('新','')
    z2h = str.maketrans('０１２３４５６７８９', '0123456789')
    return s.translate(z2h).lower()

def norm_pub(s):
    s = s or ''
    for a,b in (('株式会社',''),('(株)',''),('（株）',''),('出版',''),('研究会',''),(' ',''),('　','')):
        s = s.replace(a,b)
    return s.lower()

def _slim_rows(path):
    """books_slim.csv（export_books_slim.py 出力）を canonical 風 dict に正規化して返す。"""
    out = []
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            out.append({
                'identity': {'isbn': r.get('isbn','')},
                'bib_core': {'title': r.get('title',''), 'publisher': r.get('publisher','')},
                'physical': {'present': r.get('physical_present') in ('1','True','true'),
                             'shelf_label': r.get('shelf') or None},
                'digital':  {'pdf_present': r.get('pdf_present') in ('1','True','true'),
                             'pdf_quality': r.get('pdf_quality') or None,
                             'pdf_files': [None]*int(r.get('pdf_files') or 0),
                             'ocr_status': r.get('ocr_status') or None},
            })
    return out

def load_books(path):
    """books.json か books_slim.csv を読み、isbn索引 と (title,pub)索引 を作る。"""
    if path.lower().endswith('.csv'):
        recs = _slim_rows(path)
    else:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        recs = data.values() if isinstance(data, dict) else data
    by_isbn, by_tp = {}, collections.defaultdict(list)
    for rec in recs:
        ident = rec.get('identity', rec)
        bib   = rec.get('bib_core', rec)
        dig   = rec.get('digital', {}) or {}
        phys  = rec.get('physical', {}) or {}
        isbn  = (ident.get('isbn') or '')
        if not isbn:
            iid = ident.get('internal_id','') or ''
            m = re.search(r'isbn_(\d{13})', iid);  isbn = m.group(1) if m else ''
        slim = {
            'isbn': isbn,
            'title': bib.get('title',''), 'publisher': bib.get('publisher',''),
            'physical_present': bool(phys.get('present')),
            'shelf': phys.get('shelf_label'),
            'pdf_present': bool(dig.get('pdf_present')),
            'pdf_quality': dig.get('pdf_quality'),
            'pdf_files': len(dig.get('pdf_files',[]) or []),
            'ocr_status': dig.get('ocr_status'),
        }
        if isbn: by_isbn[isbn] = slim
        by_tp[(norm_title(slim['title']), norm_pub(slim['publisher']))].append(slim)
    return by_isbn, by_tp

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default='docs/tmplstruct/sourcebook_match/source_books_175.csv')
    ap.add_argument('--books',  required=True, help='books.json (Mac local; bookdx canonical)')
    ap.add_argument('--out',    default='docs/tmplstruct/sourcebook_match/sourcebook_holdings_match.csv')
    ap.add_argument('--summary',default='docs/tmplstruct/sourcebook_match/_HOLDINGS_MATCH_SUMMARY.md')
    args = ap.parse_args()

    by_isbn, by_tp = load_books(args.books)
    out, cnt = [], collections.Counter()
    with open(args.source, encoding='utf-8') as f:
        srcs = list(csv.DictReader(f))
    for s in srcs:
        hit, match = None, 'none'
        if s['isbn'] and s['isbn'] in by_isbn:
            hit, match = by_isbn[s['isbn']], 'isbn'
        else:
            cands = by_tp.get((norm_title(s['title']), norm_pub(s['publisher'])), [])
            if len(cands) == 1: hit, match = cands[0], 'fuzzy'
            elif len(cands) > 1: hit, match = cands[0], 'fuzzy_ambiguous'
        row = {
            'content_id': s['content_id'], 'title': s['title'], 'publisher': s['publisher'],
            'isbn': s['isbn'], 'n_templates': s['n_templates'],
            'word': s['word'], 'pdf': s['pdf'], 'excel': s['excel'],
            'match': match,
            'owned_physical': hit['physical_present'] if hit else '',
            'shelf': hit['shelf'] if hit else '',
            'pdf_present': hit['pdf_present'] if hit else '',
            'pdf_quality': hit['pdf_quality'] if hit else '',
            'ocr_status': hit['ocr_status'] if hit else '',
            'pub_download': s['dl_signal'], 'dvd_cdrom': s['dvd_signal'],
            'pub_site': s['pub_site'],
        }
        out.append(row); cnt[match] += 1
        if hit and hit['physical_present']: cnt['_owned'] += 1
        if hit and hit['pdf_present']: cnt['_pdf'] += 1

    out.sort(key=lambda r: -int(r['n_templates']))
    with open(args.out,'w',encoding='utf-8',newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

    tot_t = sum(int(r['n_templates']) for r in out)
    owned_t = sum(int(r['n_templates']) for r in out if r['owned_physical'] is True)
    pdf_t   = sum(int(r['n_templates']) for r in out if r['pdf_present'] is True)
    lines = ['# 出典本175冊 × 蔵書(books.json) 突合サマリ','',
        f'- 出典本: {len(out)}冊 / 紐づく書式: {tot_t}',
        f'- ISBN一致: {cnt["isbn"]} / fuzzy: {cnt["fuzzy"]} / fuzzy曖昧: {cnt["fuzzy_ambiguous"]} / 不一致: {cnt["none"]}',
        f'- 現物所蔵(owned_physical): {cnt["_owned"]}冊（書式 {owned_t}件ぶん）',
        f'- 自前PDFあり(pdf_present): {cnt["_pdf"]}冊（書式 {pdf_t}件ぶん）',
        f'- 出版社DL特典 signal: {sum(1 for r in out if r["pub_download"]=="1")}冊 / 付録CD-DVD signal: {sum(1 for r in out if r["dvd_cdrom"]=="1")}冊',
        '', '## 所蔵 or PDF がある根拠本（書式数降順・きれいな材料の最優先）','']
    for r in out:
        if r['owned_physical'] is True or r['pdf_present'] is True:
            tag = []
            if r['owned_physical'] is True: tag.append('現物'+(f"@{r['shelf']}" if r['shelf'] else ''))
            if r['pdf_present'] is True: tag.append(f"PDF({r['pdf_quality']},OCR={r['ocr_status']})")
            lines.append(f"- {r['n_templates']}式 {r['title']}（{r['publisher']}）: {'/'.join(tag)}")
    open(args.summary,'w',encoding='utf-8').write('\n'.join(lines)+'\n')
    print('\n'.join(lines[:8]))
    print(f"\nwrote {args.out} and {args.summary}")

if __name__ == '__main__':
    main()
