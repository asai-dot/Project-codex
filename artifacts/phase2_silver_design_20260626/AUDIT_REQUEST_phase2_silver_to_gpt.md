<!--
SUBMITTED to Box gpt_ometsuke/to_gpt (folder 387372772162) at 2026-06-26 JST
  Box file id: 2312144917218
  Box file name: 20260626_phase2_silver_projection_v1_DDDESIGN_REQUEST.md
  Box link: https://asai-lo.app.box.com/file/2312144917218
  Expected RESULT in from_gpt (387373353464): 20260626_phase2_silver_projection_v1_DDDESIGN_RESULT.md
-->

---
request_id: 20260626_phase2_silver_projection_v1_DDDESIGN
topic: phase2_bronze_to_silver_projection
gate: DDDESIGN
status: queued
result_expected_filename: 20260626_phase2_silver_projection_v1_DDDESIGN_RESULT.md
audit_kind: design_review
priority: high
related_box_files:
  - REPO PR: https://github.com/asai-dot/Project-codex/pull/25
  - design_doc_local_path: artifacts/phase2_silver_design_20260626/PLAN_PHASE2_BRONZE_TO_SILVER.md
  - prior_audit_request: 2294791670061 (gpt_ometsuke/to_gpt, 20260618 bibrec FP dry-run)
related_artifacts_in_repo:
  - artifacts/phase2_silver_design_20260626/PLAN_PHASE2_BRONZE_TO_SILVER.md
  - artifacts/corpus_roadmap_20260626/NEXT_STEPS_20260626.md
  - artifacts/toc_accuracy_20260625/TOC_ACCURACY_DIAGNOSIS_20260625.md
  - artifacts/fp_dryrun_20260618/LIT_SOURCE_GAP_20260618.md
  - tools/toc_search_index/migration_toc_path_text_trgm.sql
gate_rules: READ_ONLY_STRICT を維持（本REQUESTはDB未変更）。本プラン適用は owner ratify 後。
---

# REQUEST 20260626_phase2_silver_projection_v1_DDDESIGN
# Phase 2 設計監査依頼 — bib_toc(ブロンズ) → toc_nodes(シルバー) 射影パイプライン

## 0. 監査の目的

文献TOCコーパスの**精度（検索 recall・意味検索・将来の embedding 同期）に直結する基盤**を
作る Phase 2 の設計が、

- **正しい階層解釈**（決定的な親決定ルール）
- **冪等性と破壊回避**（既存弁コム 552,544 行と将来の embedding を壊さない）
- **ソース非依存**（lionbolt 即時 / legallib 投入後 即時）

の3点で妥当かを、お目付け役の目で監査いただきたい。**設計上のレビュー**であり、
本REQUESTは DB変更を伴わない（READ_ONLY_STRICT 維持）。

## 1. 背景（DB実測, 2026-06-26）

| 層 | 内容 | 実測 |
|---|---|---|
| `bib_records` | asai 6,524 + 弁コム 3,802 + lionbolt 22,844 | 33,170冊 |
| `bib_toc`（ブロンズ・フラット） | bib_id/ordinal/level/page/text のみ | 弁コム 552,544 + lionbolt 236,674 = **789,218** |
| `toc_nodes`（シルバー・リッチ層: path_text/parent/depth/embedding(1536)） | 弁コムのみ | 552,544（embedding 100% NULL） |
| `_stg_legallib_raw` | legallib 投入用 staging | **0行（未投入）** |

精度レバー（path_text trgm 索引 + 将来の embedding）は **toc_nodes 上にしか効かない**。
よって lionbolt 236k・legallib 投入分が**シルバー層に乗らないと意味検索の対象外**になる。
ここを汎用パイプラインで吸うのが Phase 2。

## 2. 本プランの設計の要点（監査対象）

### 2.1 決定的な親決定ルール（ソース横断・本案の核）
```
ある行 r の親 =
  同じ bib_id 内で、ordinal < r.ordinal かつ level < r.level を満たす行のうち、
  ordinal が最大の行（= "直近で浅い行"）。
  最浅（または level=0）は parent = NULL（root）。
```
- level 起点ずれ（bencom / lionbolt で開始値が違う件）は、各 bib_id 内 `min(level)` で
  0 起点に正規化。
- 既存弁コム depth 分布 {1:43,368 / 2:144,094 / 3:216,736 / 4:148,346} と整合させるため
  正規化後 depth は `max(1, normalized_level + 1)` でクリップ。
- path_text は ルート→自身 の `text` を `' > '` で連結。区切り衝突回避のため text 内 `>` は `＞`。

### 2.2 安定 ID（mint）
```
toc_node_id = 'tn:' || source || ':' || bib_id || ':' || ordinal
```
- opaque で外向き露出してOK
- 再射影で同入力→同IDを保証（embedding 同期の鍵）

### 2.3 冪等関数（DDLのみ作成、apply は別ゲート）
```
biblio.fn_project_toc_silver(
  p_source     text DEFAULT NULL,
  p_dry_run    boolean DEFAULT true,
  p_limit_books int   DEFAULT NULL
) RETURNS (projected_books, projected_nodes, inserted, updated, unchanged, orphans)
```
- WITH RECURSIVE で親決定 → path 生成 → diff upsert
- 既存 toc_node_id が一致するなら UPDATE（**embedding は触らない** — 将来生成時の温存保証）
- `p_dry_run=true` で実書き込みなし。`p_source` で増分

### 2.4 破壊回避の段階適用
| Step | 内容 | DB | 可逆 |
|---|---|---|---|
| S1 | 関数DDL作成 | DDL | DROP FUNCTION |
| S2 | dry-run（lionbolt） | 0 | — |
| S3 | apply（lionbolt のみ・bencom-library は除外） | INSERT | source単位 DELETE |
| S4 | 検証（親欠落=0 / path_text 100% / サンプル N=20） | 0 | — |
| S5 | legallib 投入後、同関数で射影 | INSERT | 同上 |
- **弁コム既存 552,544 行は S3 で touch しない**（既存命名と新 mint 規則のズレ吸収は Phase 2.5 で別PR）

### 2.5 スコープ外（別フェーズ）
- embedding 生成（Phase 3 / 外部API・ratify待ち）
- biblio_item mint / 横断 dedup（DD-LITID 本丸 / HOLD）
- 事務所PDF TOC 抽出（Phase 4）
- legallib 投入自体（Phase 1 / staging 0 行のまま）

## 3. 監査いただきたい論点（順に重要）

1. **親決定ルールの一意性**：同 level 連続・空 ordinal・level 飛び（0→3 等）で破綻しないか。
   反例があれば具体ケース（bib_id/ordinal/level の例）で示してほしい。
2. **level 正規化の妥当性**：min(level) 引き算 + `max(1, +1)` クリップは弁コム既存 depth 分布
   と整合するが、lionbolt 特有のケース（章なし・節直接など）で過剰平坦化が起きないか。
3. **冪等性のリスク**：text の微差（空白・全角）で同一物が別 toc_node_id 扱いになり履歴汚染、
   embedding 重複生成、を避けるための正規化（trim / NFKC）は十分か。過剰正規化で逆に
   情報損失しないか。
4. **embedding 温存の保証**：UPDATE 経路で「title/path_text/depth が変わったら更新」は、
   将来 embedding が乗った後、見出しの軽微変更で再 embed を強要しないか。embedding 維持
   /無効化のフラグ運用提案があれば歓迎。
5. **段階適用の独立性**：S3（lionbolt only）→ S5（legallib）→ Phase 2.5（弁コム再射影）
   の順序で本当に弁コム既存と embedding を壊さないか。
6. **可逆性**：source 単位 DELETE で完全撤去できるが、FK（toc_nodes ← embeddings 等）が
   将来加わった場合の前提崩れに警鐘を。
7. **ガバナンス**：本パイプラインを動かす per-source の権限境界、DML を打つ session_user
   の記録要件、ratify ゲートの言語化に不足はないか。

## 4. 期待する RESULT 形式

`from_gpt/20260626_phase2_silver_projection_v1_DDDESIGN_RESULT.md` に下記いずれかを格納：

- `DDDESIGN_PASS`：論点 1–7 すべて合格 → ratify ステップへ
- `DDDESIGN_PASS_WITH_NOTES`：おおむね合格、blocking ノートあり（apply 前の修正必須）
- `DDDESIGN_MODIFY_REQUIRED`：required_patches を列挙
- `DDDESIGN_NEED_MORE`：追加情報要求（具体テーブル/サンプル/SQL）

審査時、READ_ONLY_STRICT 維持（DB変更不可）でお願いします。本プランは適用前段階です。

## 5. 参考リンク（リポジトリ）

- 本プラン本体: `artifacts/phase2_silver_design_20260626/PLAN_PHASE2_BRONZE_TO_SILVER.md`
- 次工程ロードマップ: `artifacts/corpus_roadmap_20260626/NEXT_STEPS_20260626.md`
- 既存精度診断（embedding 100% NULL / path_text 100% 充足の根拠）:
  `artifacts/toc_accuracy_20260625/TOC_ACCURACY_DIAGNOSIS_20260625.md`
- 既存路線の前例監査: WO-BIBREC-FPDRYRUN-RECFIX-20260618 の REQUEST/RESULT 系列
