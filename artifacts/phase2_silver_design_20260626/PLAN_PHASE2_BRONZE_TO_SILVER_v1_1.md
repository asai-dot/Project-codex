# Phase 2 設計 v1.1 — bib_toc(ブロンズ) → toc_nodes(シルバー) 射影パイプライン

```yaml
plan_id: PHASE2-BRONZE-TO-SILVER-v1.1-20260627
status: v1.1 PLAN（再投函候補）
supersedes: PHASE2-BRONZE-TO-SILVER-20260626 (v1.0)
audit_response_to: 20260626_phase2_silver_projection_v1_DDDESIGN_RESULT.md (DDDESIGN_MODIFY_REQUIRED)
profiling_basis: PROFILING_REPORT_20260627.md
author: Claude
gate: 本ファイルは設計提示。DB変更ゼロ。関数作成・apply は別ゲート（M6）。
target: Supabase nixfjmwxmgugiiuqfuym / biblio.bib_toc → biblio.toc_nodes
```

## 0. v1.0 からの差分（M1–M9 反映）

| Patch | v1.0 | v1.1 |
|---|---|---|
| M1 ordinal preflight | 暗黙 | **§3.2 preflight クエリ明示**（NULL/dup/non-comparable で fail）|
| **M2 source_level vs tree_depth** | `depth = normalized_level + 1` | **3列分離: `source_level_raw` / `source_level_normalized` / `tree_depth`**。後者は親tree_depth+1 で構築 |
| M3 親決定異常系 | 「親 = ordinal最大の浅行」のみ | **§3.4 anomaly決定表**（multi_root=normal 等）|
| M4 正規化 | 暗黙 trim | **`title_raw` 完全保持 + `title_norm` + `normalization_profile_id/version`**、`>`→`＞` は表示encoding明示 |
| M5 embedding stale | 「embedding は触らない」のみ | **`embedding_input_hash` / `embedding_status (missing|active|stale)` / `embedding_stale_reason` / `embedding_model_id` / `embedding_generated_at`** 列導入 |
| M6 DDL gate 分離 | 関数作成を S1 に含めた | **§6 ゲート分離**: SQL草案/lint=GO、CREATE FUNCTION=別ratify |
| M7 可逆性 | source 単位 DELETE | **`projection_run_id` + manifest テーブル + tombstone/supersede policy** |
| M8 bencom非接触 | フラグ除外 | **`p_source='lionbolt'` 必須化 + 前後 checksum 比較 + negative fixture** |
| M9 受入メトリクス | N=20 サンプル | **§7 メトリクス一式 + 層化サンプル**（root/depth2/3+/gap/multi_root/long_title/page_null/dup-risk）|

---

## 1. 動機（v1.1 では profiling 結果で根拠付け）

実測（PROFILING_REPORT_20260627）から確定:
- ordinal: NULL 0 / dup 0（クリーン）
- **lionbolt は level 0→9 / gap最大7・71冊で発生 → source_level は構造ではなく見出しスタイル**
- **multi_root は normal**（弁コム100% / lionbolt90%）
- root_not_min_level lionbolt 365冊（並び順異常を accept w/log で吸う）

→ v1.0 の `depth = normalized_level + 1` は **破綻**。M2 採用必須。

## 2. 用語の固定

| 用語 | 定義 |
|---|---|
| `source_level_raw` | bib_toc.level をそのまま保持（int） |
| `source_level_normalized` | per-book で `level - min(level)`（0起点） |
| `tree_depth` | 親決定後の木構造での深さ。**root の tree_depth = 1**、子は parent.tree_depth + 1 |
| 親決定 | 「同じ bib_id 内で ordinal < r.ordinal かつ source_level < r.source_level の **ordinal最大**」 |
| root | per-book で `source_level == min(source_level)` の全行（multi_root許容）|
| `path_text` | ルート→自身の `text` を `' > '` 連結（区切り `>` → `＞` は表示encoding明示）|

## 3. preflight（M1/M3）

### 3.1 ordinal preflight（fail で射影中断）
```sql
-- 異常 0 件であること
SELECT count(*) FILTER (WHERE ordinal IS NULL) AS ordinal_null,
       count(*) FILTER (WHERE NOT (ordinal::text ~ '^-?\d+$')) AS ordinal_non_comparable
FROM biblio.bib_toc WHERE bib_id IN (...対象...);
-- 重複: (bib_id, ordinal) で count>1 が 0
```

### 3.2 level preflight（fail で射影中断）
- `level IS NULL` 行数 = 0 を確認

### 3.3 anomaly 決定表（fail にせず分類して記録）

| anomaly | 検出 | 措置 | 理由（profiling） |
|---|---|---|---|
| `multi_root` | 同 bib_id 内で min_level の行が複数 | **accept**（normal扱い） | 100%/90%発生 |
| `root_not_min_level` | 先頭行の level ≠ per-book min level | **accept w/log** | lionbolt 365冊 |
| `level_gap_down` | 隣接で level差 ≥ 2 (降下方向) | **accept**, tree_depth は親+1で算出 | lionbolt 71冊・max7 |
| `level_gap_up` | 上行方向の飛び | accept | normal（章末→次章先頭）|
| `orphan_due_to_bad_order` | 親候補が見つからない非rootノード | **log + accept** (root扱い) | edge case |
| `ordinal_duplicate` | (bib_id, ordinal) 重複 | **fail（射影中断）** | preflight で 0 確認済 |
| `ordinal_null` / `level_null` | NULL | **fail** | preflight で 0 確認済 |

### 3.4 親決定の決定論

```text
親候補集合 = { r' ∈ bib_toc | r'.bib_id = r.bib_id
                            ∧ r'.ordinal < r.ordinal
                            ∧ r'.source_level < r.source_level }
parent(r) = argmax_{r' ∈ 親候補集合} (r'.ordinal)
           ※ 候補空集合のとき NULL（root or orphan）
```

## 4. シルバー層スキーマ（toc_nodes 拡張案）

既存列を温存しつつ、v1.1 で追加するもの:

| 列 | 型 | 役割 |
|---|---|---|
| `toc_node_id` | text unique | `'tn:'||source||':'||bib_id||':'||ordinal`（既存 unique 制約活用）|
| `book_id` | text | 既存 |
| `source_level_raw` | int | 新規（M2）|
| `source_level_normalized` | int | 新規（M2）|
| `tree_depth` | int | 新規。**既存 `depth` 列をこの意味に固定 or リネーム**（migration で決定）|
| `parent_toc_node_id` | text | 既存 |
| `path_text` | text | 既存（' > ' 区切り、`>` は `＞` 置換）|
| `title_raw` | text | 新規（M4）|
| `title` | text | 既存（=`title_norm` の出力）|
| `normalization_profile_id` | text | 新規（M4。例 `nfkc_trim_v1`）|
| `normalization_profile_version` | text | 新規（M4）|
| `source_row_hash` | text | 新規（M4。bib_toc 行の sha256）|
| `embedding` | vector(1536) | 既存（触らない）|
| `embedding_input_hash` | text | 新規（M5。path_text+title_normの sha256）|
| `embedding_status` | text | 新規（M5。`missing`/`active`/`stale`）|
| `embedding_stale_reason` | text | 新規（M5）|
| `embedding_model_id` | text | 新規（M5）|
| `embedding_generated_at` | timestamptz | 新規（M5）|
| `projection_run_id` | text | 新規（M7）|

> 列追加マイグレーションは **別ratify**。本v1.1 PR では SQL 草案のみ提示、apply はしない（M6）。

## 5. projection_run manifest（M7）

```sql
CREATE TABLE biblio.toc_projection_run (
  projection_run_id text PRIMARY KEY,            -- 例 'proj:lionbolt:20260627T15:00Z:1'
  p_source text NOT NULL,
  p_dry_run boolean NOT NULL,
  p_limit_books int,
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  session_user text NOT NULL,
  metrics jsonb,                                  -- §7 受入メトリクス全部
  source_snapshot_checksum text,                  -- 実行前の bib_toc 該当source 全件 checksum
  rollback_policy text NOT NULL,                  -- 'source_unit_delete' 等
  tombstone_policy text                           -- 削除時の supersede 仕様
);
```

## 6. ゲート分離（M6）

| Step | 動作 | gate | DB |
|---|---|---|---|
| S0 | 本プラン v1.1 を gpt_ometsuke に再投函 | DDDESIGN | 0 |
| S1 | DDDESIGN PASS 後、SQL 草案 + 列追加 migration を PR に提出 | review | 0 |
| S2 | apply ratify | apply gate（**READ_ONLY_STRICT 外**） | DDL: 列追加 + manifest テーブル + 関数 |
| S3 | dry-run 実行（`p_source='lionbolt', p_dry_run=true`） | run gate | manifest 1行 INSERT のみ |
| S4 | bencom checksum 前後比較 + negative fixture テスト | run gate | 0 |
| S5 | apply 実行（`p_source='lionbolt', p_dry_run=false`） | run gate | INSERT のみ |
| S6 | 検証 + メトリクス記録 | review | 0 |
| S7 | legallib 投入後、`p_source='legal-library'` で同関数 | run gate | INSERT のみ |
| S8 | （必要時のみ）Phase 2.5 弁コム再射影 | 別 DDDESIGN | — |

関数の `SECURITY INVOKER` を既定とし、`search_path = pg_catalog, biblio`、`SET search_path` 句明示。`session_user` を manifest に記録（呼出元の identity を残す）。

## 7. 受入メトリクス（M9）

dry-run 関数の返り値 / manifest.metrics に格納:

```
input_rows, projected_nodes,
unique_toc_node_ids, duplicate_toc_node_ids (=0 を要求),
parent_missing_rows (=non-root の orphan),
path_text_null_or_empty (=0 を要求),
root_count_per_book {avg, max, p50, p99},
level_gap_down_rows, max_gap,
orphan_due_to_bad_order_rows,
inserted, updated, unchanged,
bencom_touched_rows (=0 を厳格要求),
elapsed_ms
```

層化サンプル（各クラスから 5行ずつ、計 ~40行を artifacts に出力）:
- root行 / tree_depth=2 / tree_depth≥3 / level_gap_down 行 / multi_root 本の root行 / long_title（>120字） / page_null / dup-risk（同 title_norm 兄弟）

## 8. negative fixture（M8 / bencom 非接触）

```sql
-- before/after で bencom が物理的に動かないことの厳格証明
WITH before AS (
  SELECT md5(string_agg(toc_node_id||':'||coalesce(path_text,'')||':'||coalesce(embedding::text,''),
                        '|' ORDER BY toc_node_id)) AS chk
  FROM biblio.toc_nodes n JOIN biblio.bib_records r
    ON r.bib_id=n.book_id WHERE r.source='bencom-library'
)
SELECT chk FROM before;
-- → projection 後に同クエリを再実行し、文字列一致を assert
```

manifest に `source_snapshot_checksum_before` と `_after` を保存。差があれば自動 ROLLBACK。

## 9. ロールバック

| 状況 | 手順 |
|---|---|
| projection中の異常 | TX を ROLLBACK（dry-run でも catch 用）|
| 適用後の取り消し | `DELETE FROM biblio.toc_nodes WHERE projection_run_id = :id` |
| 列追加自体の撤去 | 別マイグレーションで `ALTER TABLE ... DROP COLUMN`（embedding 触らない） |
| 弁コム既存への波及 | negative fixture により発生時点で abort、ROLLBACK のみで完結 |

## 10. スコープ外（明示）

- embedding 生成（Phase 3 / OpenAI 3-small 推奨。Phase 3 vendor matrix 参照）
- biblio_item mint / 横断 dedup 収斂（DD-LITID）
- 事務所PDF TOC 抽出（Phase 4）
- legallib **投入そのもの**（Phase 1）
- 弁コム既存の再射影（Phase 2.5、暫定 skip）

## 11. 監査者へ

本 v1.1 は M1–M9 すべて応答済み。論点 3.4 の親決定アルゴリズムは決定論で、profiling 実データ（multi_root normal / lionbolt level gap 実在）と整合。次に閉じるべき残論点があれば指摘ください。
