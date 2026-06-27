# CHECKSUM_CONTRACT_v1 — toc_nodes 完全性検証の固定契約

```yaml
contract_id: TOC-NODES-CHECKSUM-CONTRACT-v1-20260627
purpose: Phase 2 projection の bencom非接触検証 / 一般の不変性assertの基準
status: 設計確定（実装は migration_silver_projection.sql に組み込み）
audit_basis: 20260627 PASS_WITH_NOTES note #3, #4
```

## 1. 何のための契約か

- bencom 552k 行が projection で **1行も触られていないこと**を確実に証明する
- 将来の状態 vs 過去の状態を再現性ある形で比較する
- false positive（同一なのに差異と誤判定）/ false negative（差異なのに同一と誤判定）を排除

md5 単一・空文字とNULL混同・列順未定義などの**素朴な checksum は採用しない**（PASS notes #4）。

## 2. 比較対象（per-row）

`biblio.toc_nodes` の以下列、**この順序で固定**:

```
toc_node_id, book_id, source_level_raw, source_level_normalized,
tree_depth, parent_toc_node_id, path_text, title_raw, title,
print_page, normalization_profile_id, normalization_profile_version,
source_row_hash, embedding_input_hash, embedding_status,
embedding_stale_reason, embedding_model_id,
to_char(embedding_generated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS.US')
```

**embedding 列は除外**（vector(1536)、text化コストと表現ゆれが大きい。embedding は別契約で扱う）。除外を明示し、本契約は **構造・本文・stale管理列**の完全性のみを保証する。

## 3. NULL sentinel・正規化規則

| 値 | 文字列表現 |
|---|---|
| NULL | `'\N'`（リテラル2文字）|
| 空文字 `''` | `''`（NULLとは区別）|
| timestamptz | UTC固定、`YYYY-MM-DD HH24:MI:SS.US`（マイクロ秒6桁）|
| int | 10進文字列、先頭0なし |
| text | そのまま（trim しない。trim/NFKC は projection側で済んでいる前提） |

列値の連結区切り: **`U+001F` (UNIT SEPARATOR)**。本文に出現しない制御文字。

## 4. row hash

```
row_hash := sha256(
  toc_node_id || U+001F || coalesce_to_N(book_id) || U+001F || ... || U+001F ||
  coalesce_to_N(timestamp_utc_str)
)
```

`coalesce_to_N(x) := COALESCE(x::text, '\N')`。Postgres での実装例:

```sql
encode(digest(
  concat_ws(chr(31),
    n.toc_node_id, n.book_id,
    coalesce(n.source_level_raw::text,'\N'),
    coalesce(n.source_level_normalized::text,'\N'),
    coalesce(n.tree_depth::text,'\N'),
    coalesce(n.parent_toc_node_id,'\N'),
    coalesce(n.path_text,'\N'),
    coalesce(n.title_raw,'\N'),
    coalesce(n.title,'\N'),
    coalesce(n.print_page::text,'\N'),
    coalesce(n.normalization_profile_id,'\N'),
    coalesce(n.normalization_profile_version,'\N'),
    coalesce(n.source_row_hash,'\N'),
    coalesce(n.embedding_input_hash,'\N'),
    coalesce(n.embedding_status,'\N'),
    coalesce(n.embedding_stale_reason,'\N'),
    coalesce(n.embedding_model_id,'\N'),
    coalesce(to_char(n.embedding_generated_at AT TIME ZONE 'UTC',
                     'YYYY-MM-DD HH24:MI:SS.US'),'\N')
  ), 'sha256'), 'hex')
```

依存: `pgcrypto`（`digest`）。未導入なら `CREATE EXTENSION IF NOT EXISTS pgcrypto`（DDL ratify 範囲）。

## 5. aggregate hash（per source）

行集合の hash は、row_hash を **toc_node_id 昇順で並べて連結 → sha256**:

```sql
encode(digest(
  string_agg(row_hash, ',' ORDER BY toc_node_id),
  'sha256'), 'hex')
```

per-source で取得し、本契約の完全性証明はこの値の一致で行う。

## 6. bencom 非接触の判定（PASS note #4 複合判定）

projection 前後に以下4要素を取得し、**4要素すべて一致**を必須:

```json
{
  "rows": 552544,
  "key_set_sha256": "sha256( sort(toc_node_id) で連結 )",
  "aggregate_sha256": "sha256( row_hash を toc_node_id 順で連結 )",
  "touched_count": 0
}
```

- `touched_count` は projection 内で `WHERE source='bencom-library' AND (INSERT|UPDATE|DELETE) > 0` のカウント
- いずれか1つでも差異が出たら **RAISE EXCEPTION → トランザクション ROLLBACK**

## 7. manifest への保存

`biblio.toc_projection_run.metrics.bencom_check` JSONB に before/after を併記:

```json
{
  "bencom_check": {
    "before": {"rows": 552544, "key_set_sha256": "abc...", "aggregate_sha256": "def...", "touched_count": 0},
    "after":  {"rows": 552544, "key_set_sha256": "abc...", "aggregate_sha256": "def...", "touched_count": 0},
    "equal": true
  }
}
```

`equal=false` を許容しない（必ず true で commit、false なら commit 自体に到達しない）。

## 8. 契約の version 管理

- 本契約 = v1
- 変更時は契約 ID をインクリメント（`v2`）し、関数内に契約 ID を hard-code
- 過去 run の manifest には当時の契約 ID が記録される
- 異なる契約間で aggregate_sha256 を直接比較してはならない（contract_id を見ること）
