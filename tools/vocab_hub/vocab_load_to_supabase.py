#!/usr/bin/env python3
"""STEP C: vocab_load 生成物を Supabase(asai-dot Project) に load する (canary->batch).

build_load_artifacts.py が出した ~/vocab_load/*.jsonl を FK 順に投入する.
  alo_concept_schemes -> alo_terms -> alo_hubs -> alo_hub_memberships -> alo_term_relations

安全策:
  - 既定は **canary**(FK閉じた小subset). batch は --batch を明示したときのみ.
  - 冪等: 全テーブル ON CONFLICT DO NOTHING (再実行で重複しない).
  - load 後に fn_run_all_gates() を実行し violation=0 を確認(非0なら異常終了).
  - --dry-run: 接続せず subset 件数だけ表示.

接続: 環境変数 SUPABASE_DB_URL (Supabase の direct connection string)
  例: export SUPABASE_DB_URL='postgresql://postgres:<PW>@db.nixfjmwxmgugiiuqfuym.supabase.co:5432/postgres'
依存: psycopg2  ( pip install psycopg2-binary )

    python3 tools/vocab_hub/vocab_load_to_supabase.py --dir ~/vocab_load            # canary
    python3 tools/vocab_hub/vocab_load_to_supabase.py --dir ~/vocab_load --dry-run  # 件数のみ
    python3 tools/vocab_hub/vocab_load_to_supabase.py --dir ~/vocab_load --batch    # 全件(GO後)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

TABLES_FK_ORDER = [
    "alo_concept_schemes", "alo_terms", "alo_hubs", "alo_hub_memberships", "alo_term_relations",
]
# PK / 競合キー (ON CONFLICT 対象). relations は自然キーが無いので事前ユニーク index を貼る.
CONFLICT_TARGET = {
    "alo_concept_schemes": "(scheme_id)",
    "alo_terms": "(term_id)",
    "alo_hubs": "(hub_id)",
    "alo_hub_memberships": "(hub_id, term_id)",
    "alo_term_relations": "(src_term_id, dst_label, relation_type)",
}
COLUMNS = {
    "alo_concept_schemes": ["scheme_id", "name", "authority_rank", "role", "ingest_policy"],
    "alo_terms": ["term_id", "scheme_id", "normalized_pref", "reading", "definition",
                  "term_tier", "source_item_key", "reading_source", "def_quality"],
    "alo_hubs": ["hub_id", "anchor_term_id", "hub_label", "reading", "hub_status",
                 "identity_scope", "needs_preprocessing", "homograph_genuine"],
    "alo_hub_memberships": ["hub_id", "term_id", "map_type", "is_anchor", "definition_overlap"],
    "alo_term_relations": ["src_term_id", "dst_term_id", "dst_label", "relation_type", "source"],
}


def read_tables(d: Path):
    tables = {}
    for name in TABLES_FK_ORDER:
        fp = d / f"{name}.jsonl"
        rows = [json.loads(x) for x in fp.read_text(encoding="utf-8").splitlines() if x.strip()] \
            if fp.exists() else []
        tables[name] = rows
    return tables


def canary_subset(tables, n_hubs=300):
    """FK が閉じた canary subset を作る. must-include: genuine / needs_preprocessing / xref関与."""
    hubs = tables["alo_hubs"]
    must = [h for h in hubs if h.get("homograph_genuine") or h.get("needs_preprocessing")]
    must_ids = {h["hub_id"] for h in must}
    fill = [h for h in hubs if h["hub_id"] not in must_ids][:max(0, n_hubs - len(must))]
    chosen = must + fill
    chosen_ids = {h["hub_id"] for h in chosen}

    # canary terms = chosen hub の anchor + member
    mem = [m for m in tables["alo_hub_memberships"] if m["hub_id"] in chosen_ids]
    term_ids = {h["anchor_term_id"] for h in chosen} | {m["term_id"] for m in mem}

    # canary relations = src が canary term のもの. dst_term_id があれば term を追加(FK)
    rels = [r for r in tables["alo_term_relations"] if r["src_term_id"] in term_ids]
    for r in rels:
        if r.get("dst_term_id"):
            term_ids.add(r["dst_term_id"])

    terms = [t for t in tables["alo_terms"] if t["term_id"] in term_ids]
    scheme_ids = {t["scheme_id"] for t in terms}
    schemes = [s for s in tables["alo_concept_schemes"] if s["scheme_id"] in scheme_ids]
    return {
        "alo_concept_schemes": schemes, "alo_terms": terms, "alo_hubs": chosen,
        "alo_hub_memberships": mem, "alo_term_relations": rels,
    }


def _connect(url):
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 が必要です。 pip install psycopg2-binary", file=sys.stderr)
        sys.exit(3)
    return psycopg2.connect(url)


def _insert(cur, table, rows):
    if not rows:
        return 0
    cols = COLUMNS[table]
    ph = ",".join(["%s"] * len(cols))
    sql = (f"insert into {table} ({','.join(cols)}) values ({ph}) "
           f"on conflict {CONFLICT_TARGET[table]} do nothing")
    import psycopg2.extras as _ex
    vals = [[r.get(c) for c in cols] for r in rows]
    _ex.execute_batch(cur, sql, vals, page_size=500)
    return len(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="STEP C: vocab_load -> Supabase (canary->batch)")
    ap.add_argument("--dir", default=str(Path.home() / "vocab_load"))
    ap.add_argument("--batch", action="store_true", help="全件 load (既定は canary)")
    ap.add_argument("--canary-hubs", type=int, default=300)
    ap.add_argument("--host", default="db.nixfjmwxmgugiiuqfuym.supabase.co",
                    help="Supabase direct host (既定=asai-dot Project). SUPABASE_DB_URL 未設定時に使用")
    ap.add_argument("--pooler", action="store_true",
                    help="Session pooler(IPv4)経由. direct が Connection refused のとき使う")
    ap.add_argument("--pooler-host", default="aws-0-ap-northeast-1.pooler.supabase.com",
                    help="pooler host (ダッシュボードの値と違えば指定)")
    ap.add_argument("--port", type=int, default=5432, help="接続ポート(pooler session=5432)")
    ap.add_argument("--pw-file", default=None,
                    help="DBパスワードをこのファイルから読む(getpass貼付が不安定な端末向け)")
    ap.add_argument("--dry-run", action="store_true", help="接続せず件数のみ")
    a = ap.parse_args(argv)

    tables = read_tables(Path(a.dir))
    mode = "batch" if a.batch else "canary"
    load_set = tables if a.batch else canary_subset(tables, a.canary_hubs)

    print(f"[load] mode={mode}  dir={a.dir}")
    for name in TABLES_FK_ORDER:
        print(f"  {name}: {len(load_set[name])}" + (f" / 全{len(tables[name])}" if not a.batch else ""))
    if a.dry_run:
        print("[load] --dry-run: 接続なし。上記件数を投入予定。")
        return 0

    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        # プレースホルダ事故防止: パスワードを安全に対話入力し URL を組み立てる
        import getpass
        from urllib.parse import quote
        if a.pooler:
            host, user = a.pooler_host, "postgres.nixfjmwxmgugiiuqfuym"
        else:
            host, user = a.host, "postgres"
        print(f"[load] SUPABASE_DB_URL 未設定。user={user} host={host}:{a.port} へ接続します。")
        if a.pw_file:
            pw = Path(a.pw_file).expanduser().read_text(encoding="utf-8").strip()
            print(f"[load] パスワードを {a.pw_file} から読み込み(長さ{len(pw)})。")
        else:
            pw = getpass.getpass("DB password (入力は非表示): ").strip()
        if not pw:
            print("ERROR: パスワードが空です。", file=sys.stderr)
            return 2
        url = f"postgresql://{user}:{quote(pw, safe='')}@{host}:{a.port}/postgres"

    conn = _connect(url)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            # relations 冪等用ユニーク index (idempotent)
            cur.execute("create unique index if not exists uq_alo_term_relations "
                        "on alo_term_relations (src_term_id, dst_label, relation_type)")
            total = 0
            for name in TABLES_FK_ORDER:
                n = _insert(cur, name, load_set[name])
                total += n
                print(f"  [load] {name}: {n} 投入(ON CONFLICT DO NOTHING)")
            cur.execute("select gate_name, violation_count from fn_run_all_gates()")
            gates = cur.fetchall()
        bad = [g for g in gates if g[1] != 0]
        if bad:
            conn.rollback()
            print(f"[load] ⚠ ゲート違反のため ROLLBACK: {bad}", file=sys.stderr)
            return 4
        conn.commit()
        print(f"[load] ✅ commit. gates 全て violation=0: {gates}")
        print(f"[load] {mode} 完了。{'次は --batch で全件。' if not a.batch else 'batch 完了。'}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
