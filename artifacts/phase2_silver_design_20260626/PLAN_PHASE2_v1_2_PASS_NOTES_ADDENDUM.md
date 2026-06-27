# Phase 2 v1.2 addendum — PASS_WITH_NOTES の 7 blocking notes 反映

```yaml
plan_id: PHASE2-BRONZE-TO-SILVER-v1.2-ADDENDUM-20260627
status: addendum to v1.1（SQL草案ゲートの前提条件）
audit_basis: 20260627_phase2_silver_projection_v1_1_DDDESIGN_RESULT.md → DDDESIGN_PASS_WITH_NOTES
supersedes_notes_in: v1.1 §4 / §7 / §8（再定義の差分のみ記録、本体は v1.1 を継続参照）
gate: design + SQL草案。DDL/INSERT は依然 HOLD。
```

## 1. 7 notes 反映表

| # | Note | v1.2 での閉じ方 |
|---|---|---|
| 1 | `toc_nodes.depth` の意味を `tree_depth` として明文化 | `migration_silver_projection.sql` で **`COMMENT ON COLUMN biblio.toc_nodes.depth IS 'tree_depth (1=root, child=parent.tree_depth+1). NOT source level.'`** を必須化。README / 既存利用側ドキュメントへ反映 |
| 2 | root_count 高値本を acceptance sample に必ず含める | acceptance sample 仕様（本ファイル §3）に `high_root_book`（per-book root_count 上位5冊）を必須クラスとして追加 |
| 3 | checksum contract を別紙で固定 | 別ファイル `CHECKSUM_CONTRACT_v1.md` で列順・NULL sentinel・hash 方式・row hash と aggregate hash の二層を固定 |
| 4 | bencom negative fixture は複合判定 | manifest に `bencom_check` JSONB として 4要素を保存: `{rows: int, key_set_sha256: text, aggregate_sha256: text, touched_count: int}`。before/after 完全一致を assert、`touched_count != 0` で自動 ROLLBACK |
| 5 | `embedding_status` enum と `stale_reason` 語彙を固定 | DDL に CHECK 制約: `embedding_status IN ('missing','active','stale')`、`embedding_stale_reason IN ('input_hash_changed','model_id_changed','manual_invalidation', NULL)` |
| 6 | manifest に `bencom_touched_count=0` を gate condition として保存 | `toc_projection_run` の `metrics.bencom_touched_count INT NOT NULL` 必須化、関数末尾で `IF NEW != 0 THEN RAISE EXCEPTION` |
| 7 | manifest INSERT を含む dry-run は run gate | dry-run でも manifest 1行 INSERT する設計に変更**しない**。代替: dry-run は manifest を**書かず**戻り値 JSON のみ返す。manifest INSERT は p_dry_run=false の本番 run のみ |

## 2. 用語追加・更新

| 用語 | v1.1 | v1.2 |
|---|---|---|
| `toc_nodes.depth` | 「tree_depth に固定」とだけ書いた | DDL `COMMENT` で物理的に明記 + README 更新 |
| `embedding_status` | `'missing'/'active'/'stale'` | 同。**CHECK 制約**で物理強制 |
| `embedding_stale_reason` | 自由文字列だった | **enum**: `input_hash_changed / model_id_changed / manual_invalidation` |
| dry-run 実行 | manifest 1行 INSERT する | **manifest INSERT しない**（read-only に保つ）。戻り値 JSON のみ |

## 3. acceptance sample 仕様（M9 拡張、note 2 対応）

`toc_projection_run.metrics.sample` に下記クラスから各5行を保存（計 ~30行）:

| クラス | 抽出基準 |
|---|---|
| `root` | tree_depth=1 |
| `depth_2` | tree_depth=2 |
| `depth_3_plus` | tree_depth>=3 |
| `level_gap` | parent.source_level_raw との差>=2 |
| `multi_root_book_root` | per-book root_count>=10 の本の root行 |
| **`high_root_book_root`** | **per-book root_count 上位5冊の root行（note 2）** |
| `root_not_min_level` | 該当 |
| `long_title` | length(title_raw)>120 |
| `page_null` | page IS NULL |
| `dup_risk` | 同bib_id内 (parent_toc_node_id, title_norm) 兄弟重複 |
| **bencom_negative** | bencom-library 行を「触れていないこと」のサンプル（before/after の同一行を併記）|

## 4. ゲート進行（更新版）

| Step | 内容 | gate | DB |
|---|---|---|---|
| S0 | v1.2 addendum 反映 + SQL草案 + checksum contract 別紙 | DDDESIGN→migration_review | 0 |
| S1 | migration_review 監査投函（次のお目付け役 RESULT 待ち）| migration_review | 0 |
| S2 | apply ratify（CREATE FUNCTION + ALTER TABLE + manifest テーブル）| apply gate | DDL のみ |
| S3 | dry-run（manifest INSERT 無し・戻り値 JSON のみ）| run gate | 0 |
| S4 | bencom checksum contract に従う前計測 + 本番 run + 後計測 | run gate | INSERT のみ |
| S5 | acceptance sample 検証 | review | 0 |
| S6 | legallib 投入後、同関数で射影 | run gate | INSERT のみ |

## 5. スコープ外（明示・継続）

- embedding 生成（Phase 3）
- biblio_item mint / 横断 dedup（DD-LITID）
- 事務所PDF TOC 抽出（Phase 4）
- legallib 投入（Phase 1）
- 弁コム既存の再射影（Phase 2.5、暫定 skip）
