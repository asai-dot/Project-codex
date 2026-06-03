#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
load_biblio_terms.py — リッチ用語カードを biblio.terms へ provisional 投入（冪等・可逆）

ガバナンス（codex作法に整合）:
  control.source_snapshots → ingest_jobs → releases(approval_status=pending) は登録済み
  （snapshot:golden-term-card:0053466a340b / ingest:biblio:golden-term-card-rich:20260603 /
    release:biblio-terms-golden-rich:20260603）。本スクリプトは ingest_job の rows_inserted を更新する。

投入先 biblio.terms（実スキーマ実測）: term_id PK / term / term_yomi / scheme / broader_id(self-FK) /
  scope_note / source / raw jsonb / updated_at。値CHECK無し・空テーブル。
raw は compact provenance（錨URI・gloss源・読み源・ゲートフラグ）で統一（MCPパイロットと同形）。

冪等: ON CONFLICT (term_id) DO NOTHING。可逆: DELETE FROM biblio.terms WHERE source='golden_term_card_v1'。
昇格（provisional→canonical）は浅井が control.releases.approval_status を 'approved' にした後に別途。

実行（DB接続情報が要る＝クラウドsandboxには無い。codex/owner/ローカルで）:
  export SUPABASE_DB_URL='postgresql://...:5432/postgres'   # service role / direct connection
  python3 load_biblio_terms.py data/db_staging/biblio_terms_richcards_v1.jsonl
依存: psycopg (v3) または psycopg2。無ければ pip install psycopg[binary]。
"""
import json
import os
import sys

SCHEME = "jp_statutory_definition"
SOURCE = "golden_term_card_v1"
INGEST_JOB = "ingest:biblio:golden-term-card-rich:20260603"


def compact_raw(card_raw):
    """staging の raw（フル）→ DB用 compact provenance に圧縮（パイロットと同形）。"""
    sd = card_raw.get("statutory_definitions", []) or []
    return {
        "anchor_uris": [d.get("uri") for d in sd if d.get("uri")],
        "anchor_count": len(sd),
        "gloss_sources": list((card_raw.get("glosses") or {}).keys()),
        "reading_sources": list((card_raw.get("readings") or {}).keys()),
        "jlt_en": ((card_raw.get("jlt") or {}) or {}).get("en", []) if card_raw.get("jlt") else [],
        "source_authority_rank": 100,
        "extraction_confidence": card_raw.get("extraction_confidence", "high"),
        "canonical_status": "provisional",
        "review_status": "unreviewed",
        "card_class": card_raw.get("card_class", "rich"),
    }


def rows(path):
    for l in open(path, encoding="utf-8"):
        l = l.strip()
        if l[:1] != "{":
            continue
        r = json.loads(l)
        yield (r["term_id"], r["term"], r.get("term_yomi"), SCHEME, None,
               r.get("scope_note"), SOURCE, json.dumps(compact_raw(r.get("raw", {})), ensure_ascii=False))


def main(argv=None):
    path = (argv or sys.argv[1:])[0] if (argv or sys.argv[1:]) else "data/db_staging/biblio_terms_richcards_v1.jsonl"
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        sys.exit("SUPABASE_DB_URL を設定してください（service role / direct connection）。")
    data = list(rows(path))
    try:
        import psycopg            # psycopg v3
        conn = psycopg.connect(url)
    except ImportError:
        import psycopg2 as psycopg  # noqa
        conn = psycopg.connect(url)
    sql = ("INSERT INTO biblio.terms "
           "(term_id, term, term_yomi, scheme, broader_id, scope_note, source, raw, updated_at) "
           "VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb, now()) ON CONFLICT (term_id) DO NOTHING")
    inserted = 0
    with conn:
        with conn.cursor() as cur:
            for i in range(0, len(data), 200):
                cur.executemany(sql, data[i:i + 200])
            cur.execute("SELECT count(*) FROM biblio.terms WHERE source=%s", (SOURCE,))
            inserted = cur.fetchone()[0]
            cur.execute(
                "UPDATE control.ingest_jobs SET status=%s, rows_inserted=%s, finished_at=now() "
                "WHERE ingest_job_id=%s",
                ("succeeded" if inserted >= len(data) else "partial", inserted, INGEST_JOB))
    print(f"biblio.terms source={SOURCE}: {inserted} rows present (staged {len(data)}).")
    print("rollback: DELETE FROM biblio.terms WHERE source='golden_term_card_v1';")
    return 0


if __name__ == "__main__":
    sys.exit(main())
