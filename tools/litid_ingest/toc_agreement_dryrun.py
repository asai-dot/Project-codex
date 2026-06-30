#!/usr/bin/env python3
"""
TOC agreement dry-run for θ calibration (cross-source gold seed).

Goal: compute toc_agreement(self_toc, bencom_toc) for each sampled candidate pair,
so that θ_high / θ_low thresholds can be calibrated by human reviewers (≥2).

Design constraints (audit binding notes):
- read-only: no DB write, no Box upload, no canonical projection
- non-circular: uses TOC content agreement only; ISBN/NDL not re-used as adjudicator
- parent-qualified where possible (bencom has depth 1-3; self is all depth=1)
- norm_title version must be recorded in output

Self TOC format (observed 2026-06-27, toc_source=books_or_jp, all files):
  [{"l":1, "p":null, "t":"<title>", "toc_node_id":"...", "depth":1,
    "parent_toc_node_id":"", "toc_path_id":"cNN", "page_start":null,
    "toc_source":"books_or_jp", "toc_status":"simple"}, ...]
  Noise: real chapters appear first; noise starts at "著者略歴" / "もっと見る" / JS code.

Bencom TOC format (biblio.toc_nodes):
  toc_node_id, title, depth (1-4), parent_toc_node_id, print_page, book_id

Output: toc_agreement_dryrun_<date>.tsv
  self_bib_id, bencom_bib_id, edition_risk_flag, self_real_node_count,
  bencom_d1_count, intersection_count, union_count, jaccard_d1,
  toc_agreement, norm_title_version, parser_hash, notes

Usage (local only, requires DATABASE_URL + Box API credentials):
  python toc_agreement_dryrun.py --sample sample_manifest.tsv [--limit 10]
  python toc_agreement_dryrun.py --pair 9784000248914 NOBN_20200414_民法改正と不法行為_01

norm_title_version: "v1.0" (NFKC + strip whitespace/punct, normalize numeric chars)
"""

import csv
import json
import re
import sys
import unicodedata
import hashlib
import argparse
from pathlib import Path

# ── norm_title v1.0 ────────────────────────────────────────────────────────
NORM_TITLE_VERSION = "v1.0"
_STRIP_CHARS = re.compile(r'[\s　・「」『』（）()【】\[\]〔〕〈〉《》\-―‐—〜~、。，．・…]')
_NUMERIC_WIDE = str.maketrans(
    '０１２３４５６７８９',
    '0123456789'
)
_CHAPTER_PREFIX = re.compile(r'^第?(\d+)[章節項部編]')


def norm_title(t: str) -> str:
    if not t:
        return ''
    t = unicodedata.normalize('NFKC', t)
    t = t.translate(_NUMERIC_WIDE)
    t = _STRIP_CHARS.sub('', t)
    return t.lower()


# ── self TOC noise filter ───────────────────────────────────────────────────
_NOISE_TRIGGERS = {'著者略歴', 'もっと見る', '著者紹介', 'さらに表示'}
_CODE_PATTERN = re.compile(
    r'let |var |function |^\s*//|if \(|\$\(|\$\.|\.append\('
    r'|inputList|hasVisibleButton|listData|for \(var'
)


def filter_self_toc(nodes: list) -> list:
    """
    Keep only 'real' TOC nodes from self (books_or_jp) JSON.
    Truncates at first noise marker (author bio, JS code, etc.).
    """
    real = []
    for n in nodes:
        t = n.get('t', '') or ''
        t_stripped = t.strip()
        if t_stripped in _NOISE_TRIGGERS:
            break
        if _CODE_PATTERN.search(t):
            break
        if len(t_stripped) > 200:
            break
        real.append(n)
    return real


def parser_hash(nodes: list) -> str:
    """SHA-256-16 of the raw JSON for provenance tracking."""
    raw = json.dumps(nodes, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── toc_agreement metric ────────────────────────────────────────────────────

def compute_agreement(self_nodes: list, bencom_nodes: list) -> dict:
    """
    Compare self real-nodes vs bencom depth=1 nodes using normalized title Jaccard.

    Returns:
      self_real_count, bencom_d1_count, intersection, union, jaccard_d1, toc_agreement
    """
    self_real = filter_self_toc(self_nodes)
    self_titles = {norm_title(n.get('t', '')) for n in self_real if n.get('t')}
    self_titles.discard('')

    bencom_d1 = [n for n in bencom_nodes if n.get('depth') == 1]
    bencom_titles = {norm_title(n.get('title', '')) for n in bencom_d1 if n.get('title')}
    bencom_titles.discard('')

    if not self_titles or not bencom_titles:
        return {
            'self_real_count': len(self_real),
            'bencom_d1_count': len(bencom_d1),
            'intersection': 0,
            'union': max(len(self_titles), len(bencom_titles)),
            'jaccard_d1': None,
            'toc_agreement': None,
            'notes': 'empty_after_filter',
        }

    intersection = len(self_titles & bencom_titles)
    union = len(self_titles | bencom_titles)
    jaccard = intersection / union if union else 0.0

    return {
        'self_real_count': len(self_real),
        'bencom_d1_count': len(bencom_d1),
        'intersection': intersection,
        'union': union,
        'jaccard_d1': jaccard,
        'toc_agreement': jaccard,   # v1.0: toc_agreement = jaccard_d1 (page/hierarchy TBD)
        'notes': '',
    }


# ── sample generation ───────────────────────────────────────────────────────

def make_sample(tsv_path: Path, collision_all: bool = True,
                clean_n: int = 150, seed: int = 42) -> list:
    """
    Stratified sample:
      - ALL rows with edition_risk_flag=1 (collision cases)
      - random clean_n rows with edition_risk_flag=0
    """
    import random
    rng = random.Random(seed)

    collision, clean = [], []
    with open(tsv_path) as f:
        for row in csv.DictReader(f, delimiter='\t'):
            if row['edition_risk_flag'] == '1':
                collision.append(row)
            else:
                clean.append(row)

    rng.shuffle(clean)
    sample = collision + clean[:clean_n]
    print(f"Sample: {len(collision)} collision + {len(clean[:clean_n])} clean = {len(sample)} total",
          file=sys.stderr)
    return sample


# ── Box + DB helpers (require credentials at runtime) ─────────────────────

def fetch_self_toc_box(isbn: str, box_folder_id: str = '370441454337') -> list:
    """
    Fetch self TOC JSON from Box via requests + Box API.
    Requires BOX_ACCESS_TOKEN env var.
    """
    import os, requests
    token = os.environ.get('BOX_ACCESS_TOKEN')
    if not token:
        raise RuntimeError('BOX_ACCESS_TOKEN not set')
    # Find file by name pattern
    search_url = 'https://api.box.com/2.0/search'
    params = {
        'query': f'isbn_{isbn}.json',
        'ancestor_folder_ids': box_folder_id,
        'type': 'file',
        'limit': 1,
    }
    r = requests.get(search_url, params=params,
                     headers={'Authorization': f'Bearer {token}'})
    r.raise_for_status()
    items = r.json().get('entries', [])
    if not items:
        return []
    file_id = items[0]['id']
    content_url = f'https://api.box.com/2.0/files/{file_id}/content'
    r2 = requests.get(content_url, headers={'Authorization': f'Bearer {token}'})
    r2.raise_for_status()
    return r2.json()


def fetch_bencom_toc_db(bencom_bib_id: str) -> list:
    """
    Fetch bencom toc_nodes from DB via psycopg2.
    Requires DATABASE_URL env var.
    """
    import os, psycopg2
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise RuntimeError('DATABASE_URL not set')
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("""
        SELECT toc_node_id, title, depth, parent_toc_node_id, print_page
        FROM biblio.toc_nodes
        WHERE book_id = %s
        ORDER BY toc_node_id
    """, (bencom_bib_id,))
    rows = cur.fetchall()
    conn.close()
    return [
        {'toc_node_id': r[0], 'title': r[1], 'depth': r[2],
         'parent_toc_node_id': r[3], 'print_page': r[4]}
        for r in rows
    ]


# ── bencom cache loader ─────────────────────────────────────────────────────

def load_bencom_cache(cache_path: Path) -> dict:
    """
    Load pre-fetched bencom depth=1 toc_nodes from JSON cache.
    Returns dict: bencom_bib_id -> list of node dicts.
    Cache format: artifacts/bencom_toc_d1_cache_pilot_20260627.json
    """
    with open(cache_path) as f:
        data = json.load(f)
    return data['bencom']


# ── main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', type=Path,
                        default=Path('artifacts/TOC_cross_source_gold_candidates_20260623.tsv'),
                        help='Candidate TSV path')
    parser.add_argument('--manifest', type=Path, default=None,
                        help='Stratified sample manifest TSV (overrides --sample + sampling logic)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Cap number of pairs to process')
    parser.add_argument('--pair', nargs=2, metavar=('ISBN', 'BENCOM_BIB_ID'),
                        help='Process a single pair for testing')
    parser.add_argument('--clean-n', type=int, default=150,
                        help='Number of clean (non-collision) pairs to sample')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path, default=None)
    parser.add_argument('--bencom-cache', type=Path, default=None,
                        metavar='PATH',
                        help='Pre-fetched bencom depth=1 JSON cache (skips DATABASE_URL)')
    args = parser.parse_args()

    bencom_cache: dict | None = None
    if args.bencom_cache:
        bencom_cache = load_bencom_cache(args.bencom_cache)
        print(f"Loaded bencom cache: {len(bencom_cache)} bencom_bib_ids", file=sys.stderr)

    def get_bencom_nodes(bencom_bib_id: str) -> list:
        if bencom_cache is not None:
            nodes = bencom_cache.get(bencom_bib_id)
            if nodes is None:
                raise KeyError(f'bencom_bib_id not in cache: {bencom_bib_id}')
            return nodes
        return fetch_bencom_toc_db(bencom_bib_id)

    out_fields = [
        'self_bib_id', 'self_isbn', 'bencom_bib_id', 'edition_risk_flag',
        'self_real_count', 'bencom_d1_count', 'intersection', 'union',
        'jaccard_d1', 'toc_agreement', 'norm_title_version', 'self_parser_hash', 'notes',
    ]

    out = csv.DictWriter(
        open(args.output, 'w', newline='') if args.output else sys.stdout,
        fieldnames=out_fields, delimiter='\t', lineterminator='\n'
    )
    out.writeheader()

    if args.pair:
        isbn, bencom_bib_id = args.pair
        self_nodes = fetch_self_toc_box(isbn)
        bencom_nodes = get_bencom_nodes(bencom_bib_id)
        result = compute_agreement(self_nodes, bencom_nodes)
        out.writerow({
            'self_bib_id': f'alo:book:isbn:{isbn}',
            'self_isbn': isbn,
            'bencom_bib_id': bencom_bib_id,
            'edition_risk_flag': 'N/A',
            'norm_title_version': NORM_TITLE_VERSION,
            'self_parser_hash': parser_hash(filter_self_toc(self_nodes)),
            **result,
        })
        return

    # Use manifest directly if provided (pre-stratified), else sample from candidate TSV
    if args.manifest:
        sample = []
        with open(args.manifest) as f:
            for row in csv.DictReader(f, delimiter='\t'):
                sample.append(row)
        print(f"Manifest: {len(sample)} pairs", file=sys.stderr)
    else:
        sample = make_sample(args.sample, clean_n=args.clean_n, seed=args.seed)
    if args.limit:
        sample = sample[:args.limit]

    for row in sample:
        isbn = row['self_isbn']
        bencom_bib_id = row['bencom_bib_id']
        try:
            self_nodes = fetch_self_toc_box(isbn)
            bencom_nodes = get_bencom_nodes(bencom_bib_id)
        except Exception as e:
            out.writerow({
                'self_bib_id': row['self_bib_id'],
                'self_isbn': isbn,
                'bencom_bib_id': bencom_bib_id,
                'edition_risk_flag': row['edition_risk_flag'],
                'self_real_count': '',
                'bencom_d1_count': '',
                'intersection': '',
                'union': '',
                'jaccard_d1': '',
                'toc_agreement': '',
                'norm_title_version': NORM_TITLE_VERSION,
                'self_parser_hash': '',
                'notes': f'ERROR:{e}',
            })
            continue
        result = compute_agreement(self_nodes, bencom_nodes)
        out.writerow({
            'self_bib_id': row['self_bib_id'],
            'self_isbn': isbn,
            'bencom_bib_id': bencom_bib_id,
            'edition_risk_flag': row['edition_risk_flag'],
            'norm_title_version': NORM_TITLE_VERSION,
            'self_parser_hash': parser_hash(filter_self_toc(self_nodes)),
            **result,
        })


if __name__ == '__main__':
    main()
