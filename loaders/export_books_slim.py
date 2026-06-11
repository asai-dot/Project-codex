#!/usr/bin/env python3
"""
export_books_slim.py — books.json(約33MB) から「所蔵突合に必要な列だけ」を抜いた軽量CSVを出す。
リモート番頭環境は MCP 転送上限(約8MB)で books.json 全量を取り込めないため、本スクリプトで
<2MB の books_slim.csv を作って Box material_queue に置けば、番頭が突合を完了できる。

read-only・books.json 非改変。Mac(books.json ローカル実体)で1回実行するだけ。
出力列: isbn,title,publisher,physical_present,shelf,pdf_present,pdf_quality,pdf_files,ocr_status
"""
import json, csv, re, argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--books', required=True, help='~/alo-ai/.../app/data/books.json')
    ap.add_argument('--out', default='books_slim.csv')
    a = ap.parse_args()
    data = json.load(open(a.books, encoding='utf-8'))
    recs = data.values() if isinstance(data, dict) else data
    n = 0
    with open(a.out, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['isbn','title','publisher','physical_present','shelf',
                    'pdf_present','pdf_quality','pdf_files','ocr_status'])
        for rec in recs:
            ident = rec.get('identity', {}) or {}
            bib   = rec.get('bib_core', {}) or {}
            dig   = rec.get('digital', {}) or {}
            phys  = rec.get('physical', {}) or {}
            isbn  = ident.get('isbn') or ''
            if not isbn:
                m = re.search(r'isbn_(\d{13})', ident.get('internal_id','') or '')
                isbn = m.group(1) if m else ''
            w.writerow([isbn, bib.get('title',''), bib.get('publisher',''),
                        int(bool(phys.get('present'))), phys.get('shelf_label') or '',
                        int(bool(dig.get('pdf_present'))), dig.get('pdf_quality') or '',
                        len(dig.get('pdf_files',[]) or []), dig.get('ocr_status') or ''])
            n += 1
    print(f'wrote {a.out} ({n} books)')

if __name__ == '__main__':
    main()
