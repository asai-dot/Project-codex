<!--
SUBMITTED to Box gpt_ometsuke/to_gpt (folder 387372772162) at 2026-06-27 JST
  Box file id: 2312401828172
  Box link: https://asai-lo.app.box.com/file/2312401828172
  Box file name: 20260627_phase2_silver_projection_v1_1_DDDESIGN_REQUEST.md
  Expected RESULT in from_gpt (387373353464): 20260627_phase2_silver_projection_v1_1_DDDESIGN_RESULT.md
  Supersedes: 20260626_phase2_silver_projection_v1_DDDESIGN_REQUEST.md (file id 2312144917218)
  Prior RESULT: 20260626_..._DDDESIGN_RESULT.md (file id 2312213059089) => DDDESIGN_MODIFY_REQUIRED
-->

---
request_id: 20260627_phase2_silver_projection_v1_1_DDDESIGN
topic: phase2_bronze_to_silver_projection
gate: DDDESIGN
status: queued
result_expected_filename: 20260627_phase2_silver_projection_v1_1_DDDESIGN_RESULT.md
audit_kind: design_review_v1_1_response_to_modify_required
priority: high
supersedes_request: 20260626_phase2_silver_projection_v1_DDDESIGN (file 2312144917218)
prior_result: 20260626_phase2_silver_projection_v1_DDDESIGN_RESULT.md (file 2312213059089) => DDDESIGN_MODIFY_REQUIRED
patches_addressed: [M1, M2, M3, M4, M5, M6, M7, M8, M9]
related_artifacts_in_repo:
  - artifacts/phase2_silver_design_20260626/PLAN_PHASE2_BRONZE_TO_SILVER_v1_1.md
  - artifacts/phase2_silver_design_20260626/PROFILING_REPORT_20260627.md
  - artifacts/phase2_silver_design_20260626/PHASE2_5_BENCOM_REPROJECTION_NOTES.md
  - artifacts/phase3_embedding_20260626/EMBEDDING_VENDOR_COMPARISON.md
gate_rules: READ_ONLY_STRICT を維持。本REQUEST/v1.1プランは DB変更ゼロ。
            関数作成（CREATE FUNCTION）も含めて apply はすべて別 ratify。
---

# REQUEST 20260627_phase2_silver_projection_v1_1_DDDESIGN
# Phase 2 設計監査 v1.1 — DDDESIGN_MODIFY_REQUIRED への応答

## 0. 概要

v1.0 監査 (`DDDESIGN_MODIFY_REQUIRED`) の **M1–M9 すべてに応答**し、加えて read-only
profiling を実施して設計判断の実データ根拠を得た上で v1.1 を策定した。

成果物:
1. `PROFILING_REPORT_20260627.md` — `bib_toc` 789,218行 の異常分布 read-only 実測
2. `PLAN_PHASE2_BRONZE_TO_SILVER_v1_1.md` — M1–M9 反映済み v1.1 プラン
3. 本 REQUEST（再投函）

DB 状態: mutation 0 / DDL 0 / 関数作成 0 を維持。

## 1. M1–M9 への応答（一覧）

| Patch | v1.0 課題 | v1.1 での閉じ方 | profiling 根拠 |
|---|---|---|---|
| M1 ordinal 制約 | preflight 未定義 | §3.1 preflight クエリを実装、ordinal_null/duplicate/non_comparable で fail | NULL 0 / dup 0（両ソース）|
| **M2 level/depth 分離** | `depth = normalized_level+1` | **`source_level_raw` / `source_level_normalized` / `tree_depth = parent.tree_depth+1` の3列分離** | **lionbolt level 0→9、71冊で gap、max gap=7** |
| M3 親決定異常系 | 一意決定のみ | §3.3 anomaly決定表（multi_root=normal accept / root_not_min_level=accept w/log / level_gap=accept tree_depth は parent+1）| multi_root: 弁コム100% / lionbolt 90% / root_not_min_level lionbolt 365冊 |
| M4 正規化 | 暗黙 trim | `title_raw` 完全保持 + `title_norm` + `normalization_profile_id/version` + `source_row_hash`。`>`→`＞` は **表示encoding** と明示 | — |
| M5 embedding stale | 触らないだけ | `embedding_input_hash` / `embedding_status (missing|active|stale)` / `embedding_stale_reason` / `embedding_model_id` / `embedding_generated_at` を toc_nodes に追加 | — |
| M6 DDL gate 分離 | 関数作成を S1 に含めた | §6: SQL草案/lint=GO、CREATE FUNCTION=別ratify。`SECURITY INVOKER`、`SET search_path`、`session_user` 記録 | — |
| M7 可逆性 | source 単位 DELETE | §5: `projection_run_id` + `biblio.toc_projection_run` manifest + tombstone/supersede policy | — |
| M8 bencom非接触 | フラグ除外 | §8: `p_source='lionbolt'` 必須 + 実行前後 checksum 比較 + 自動 ROLLBACK | — |
| **M9 受入メトリクス** | N=20 サンプル | §7: input/projected/unique/dup/parent_missing/path_null/root_count分布/level_gap/orphan/inserted/updated/unchanged/bencom_touched/elapsed + 8クラス層化サンプル | profiling で測定可能性を実証 |

## 2. v1.1 の核となる設計決定（要旨）

### 2.1 source_level と tree_depth の物理分離（M2）
```
source_level_raw            = bib_toc.level（生）
source_level_normalized     = level - per_book_min(level)
tree_depth                  = (root の場合) 1
                              (子の場合) parent.tree_depth + 1
toc_nodes.depth は tree_depth に固定（v1.0 の意味を上書き）
```

### 2.2 multi_root は normal（決定的）
profiling: 弁コム 3,802/3,802（100%）・lionbolt 3,727/4,135（90%）が multi_root。
1冊あたり最大 **493 root**。よって anomaly ではなく仕様。

### 2.3 親決定（v1.0 と同じだが、決定論を明文化）
```
parent(r) = argmax_{r' : r'.bib_id=r.bib_id ∧ r'.ordinal<r.ordinal ∧ r'.source_level<r.source_level}
                  (r'.ordinal)
候補空集合 → root（NULL）
```

### 2.4 embedding 同期（M5）
- 入力テキスト `path_text||'\n'||title_norm` の sha256 を `embedding_input_hash` に保存
- projection で path_text/title_norm が変わったら **embedding は触らず**、`embedding_status='stale'`、`embedding_stale_reason='input_hash_changed'` を立てる
- Phase 3 の backfill 側で `WHERE embedding_status IN ('missing','stale')` を拾う

### 2.5 ゲートの厳格分離（M6）
本 v1.1 PASS 後でも、CREATE FUNCTION / ALTER TABLE は別ratify。dry-run も manifest 1行だけ insert する点を明示し、それ自体を run gate とした。

## 3. 監査いただきたい論点（v1.0 から進化させた部分）

1. **3列分離（source_level_raw / source_level_normalized / tree_depth）**は M2 を閉じるに足るか。命名や運用上の不足はあるか。
2. **multi_root を仕様**として受け入れる判断は妥当か（profiling 根拠）。root の per-book 最大 493 件で path_text 構造に弊害はないか。
3. **embedding stale 5列**（`_input_hash` / `_status` / `_stale_reason` / `_model_id` / `_generated_at`）で Phase 3 backfill との同期は十分か。逆に過剰設計はないか。
4. **negative fixture の checksum** は md5 ベース。embeddings 列を含む 552k 行の比較で false positive/negative リスクはないか（NULL embedding の表現等）。
5. **projection_run_id manifest** の rollback_policy/tombstone_policy の最低必要フィールドに不足は？
6. **READ_ONLY_STRICT と run gate の境界**: dry-run でも manifest 1行 INSERT する点を「run gate」に分類した妥当性。

## 4. 期待 RESULT 形式

`from_gpt/20260627_phase2_silver_projection_v1_1_DDDESIGN_RESULT.md`:
- `DDDESIGN_PASS`：論点 1–6 すべて閉鎖 → SQL草案/migration の review gate へ
- `DDDESIGN_PASS_WITH_NOTES`：blocking note あり（apply 前修正必須）
- `DDDESIGN_MODIFY_REQUIRED`：required_patches 列挙
- `DDDESIGN_NEED_MORE`：追加情報要求

## 5. 参照（リポジトリ）

- 設計本体 v1.1: `artifacts/phase2_silver_design_20260626/PLAN_PHASE2_BRONZE_TO_SILVER_v1_1.md`
- profiling 実測: `artifacts/phase2_silver_design_20260626/PROFILING_REPORT_20260627.md`
- v1.0 RESULT: Box file 2312213059089
- v1.0 REQUEST: Box file 2312144917218
