# Phase 2 設計プラン — ブロンズ(bib_toc) → シルバー(toc_nodes) 射影パイプライン

```yaml
plan_id: PHASE2-BRONZE-TO-SILVER-20260626
status: PLAN（プランモードで承認待ち）
author: Claude
target: Supabase nixfjmwxmgugiiuqfuym / biblio.bib_toc → biblio.toc_nodes
gate: 本プラン承認後に、まず read-only dry-run（DB mutation 0）の SQL/レポートをPR提出。
      apply は ratify 後。マイグレーションは可逆。
related: NEXT_STEPS_20260626.md / TOC_ACCURACY_DIAGNOSIS_20260625.md / DD_LIONBOLT_INGEST_v0.1.md
```

---

## 1. なぜやるか（前提の再確認）

実測（2026-06-26）:
- **bib_toc**（ブロンズ・フラット層、3列：`bib_id/ordinal/level/page/text`）
  - 弁コム 552,544 + lionbolt 236,674 = **789,218ノード**
- **toc_nodes**（シルバー・リッチ層、`path_text/parent/depth/embedding(1536)` 等）
  - 弁コムのみ 552,544。lionbolt は **未射影**
- 精度レバー（path_text trgm索引・embedding）は **toc_nodes 上にしか効かない**
- legallib は本日時点で DB 未投入（staging 空）。**Phase 2 はソース非依存**で組み、入った瞬間に同じパイプラインで吸う

価値:
- いま即: lionbolt 236k 分の検索/embedding 対象化（recall 大幅増）
- legallib 投入後: 同じパイプラインで自動取り込み（追加工事ゼロ）
- 弁コム既存552kとは **冪等な再射影**ができることを保証（破壊しない）

---

## 2. 設計のスコープと非スコープ

### スコープ
- A) **path_text 生成**: bib_toc の `(bib_id, ordinal, level, text, page)` からスレッド階層をたどり、`祖先1 > 祖先2 > … > 自身` の見出しパスを作る
- B) **toc_node_id mint**: 安定ID `'tn:'||source||':'||bib_id||':'||ordinal`（外向き露出してOKなopaque、後段の embedding 同期に必要）
- C) **toc_nodes upsert**: source 横断で射影。冪等（同入力→同結果）。削除は DELETE+INSERT ではなく diff ベース（既存FK・既存embedding を温存）
- D) **品質ガード**: depth0 ルート以外で parent 空ゼロを保証、孤児（bib_records無し）排除、空title排除
- E) **冪等ジョブ実行**: 1つのSQL関数 `biblio.fn_project_toc_silver(p_source text default NULL, p_limit_books int default NULL)` を提供。source指定で増分・全量どちらも回せる
- F) **検証クエリ**: 射影前後の counts、サンプル、recall測定

### 非スコープ（別フェーズ）
- embedding 生成（Phase 3 / 外部API・ratify待ち）
- biblio_item mint / 横断dedup収斂（DD-LITID 本丸）
- 事務所PDF TOC 抽出（Phase 4）
- legallib 投入自体（Phase 1。本プランは投入済を前提にしない）

---

## 3. ソースごとの階層解釈（決定的なのはここ）

bib_toc は `level` 整数（深さ）と `ordinal`（出現順）だけ。**親はテーブルに無く、隣接ordinalで深さが浅い直近の行が親**という構造的ルールで決める。これがソース横断の核。

```text
親決定ルール（決定的・全ソース共通）:
  ある行 r の親 = 同じ bib_id 内で
                 ordinal < r.ordinal かつ level < r.level であって
                 ordinal が最大の行（= "直近で浅い"）。
  level==0（または最浅）は parent = NULL（root）。
```

ソース別の癖を吸収する正規化:
- **bencom**: level 開始値が source 依存。各 bib_id 内で min(level) を差し引いて 0 起点に正規化
- **lionbolt**: 同様。先頭が level=0 or 1 の混在を許容
- 既存 toc_nodes（弁コム）の depth 分布 {1:43368, 2:144094, 3:216736, 4:148346} と整合する形に合わせる（既存に**破壊的変更を入れない**ため、正規化後の depth は max(1, normalized_level+1) でクリップ）

path_text 生成:
- ルートから自身まで`text`を `' > '` で連結（既存サンプル `第8章 先取特権 > 第3節 先取特権の順位 > §§329-332(西原道雄)` と一致）
- text の `>` は `＞` にエスケープ（区切り衝突回避）
- 各セグメント trim、空セグメントスキップ（path_text の空欠落を防ぐ）

---

## 4. 実装（DDL + 関数）

### 4.1 マイグレーション `tools/toc_silver_projection/migration_silver_projection.sql`
- `CREATE EXTENSION IF NOT EXISTS pg_trgm`（既存）
- 補助 unique index 確認: `toc_nodes (book_id, toc_node_id)` が一意である前提で、衝突しない安定IDを使う
- 関数本体は WITH RECURSIVE で親決定 → path 生成 → upsert。一発SQLで完結

### 4.2 関数の骨子（疑似SQL、実装時にPR本体で確定）
```sql
CREATE OR REPLACE FUNCTION biblio.fn_project_toc_silver(
  p_source text DEFAULT NULL,        -- NULL=全ソース。'lionbolt' 等で限定
  p_dry_run boolean DEFAULT true,    -- 既定 dry-run。実適用は明示false
  p_limit_books int DEFAULT NULL
) RETURNS TABLE (
  projected_books bigint,
  projected_nodes bigint,
  inserted bigint,
  updated  bigint,
  unchanged bigint,
  orphans bigint
) LANGUAGE plpgsql AS $$
DECLARE
  ...
BEGIN
  -- 1) 対象 bib_id 集合（source フィルタ + 孤児除外）
  -- 2) WITH RECURSIVE で各行に祖先ordinal列を蓄積、path_text を構築
  -- 3) toc_node_id = 'tn:'||source||':'||bib_id||':'||ordinal
  -- 4) 既存 toc_nodes と diff:
  --      新規: INSERT
  --      title/path_text/depth が変化したもの: UPDATE（embedding は触らない）
  --      同一: skip
  -- 5) 孤児（bib_records から source 取れない）はカウントのみ
  -- 6) p_dry_run=true なら ROLLBACK 相当（実体は SAVEPOINT/RAISE NOTICE 等）
END;
$$;
```

### 4.3 既存弁コム行への影響
- 弁コム 552,544 はすでに toc_nodes にいて embedding 列を持つ（NULLだが）
- 関数は **既存 toc_node_id が一致するなら同じ行を UPDATE**（embedding 温存）
- ただし弁コム既存の `toc_node_id` 命名が新 mint 規則と異なる場合は、**source='bencom-library' は touch しない**フラグを設けて初期は除外 → 別途 再mint移行は Phase 2.5 として切り出し（破壊回避）
- 初回適用は **lionbolt のみ**（+ legallib 投入後に legallib も）で安全に積む。弁コムは別PRで一度比較してから

### 4.4 検証クエリ群（read-only）
- 射影前後の counts（per source）
- 親欠落チェック: depth>1 なのに parent_toc_node_id IS NULL なら **0 件**であること
- path_text サンプル N=20（lionbolt の見出しが期待形）
- recall 比較: 例 `'先取特権' '債権者代位'` で title索引 only vs path_text の差（Phase 3 効果の前倒し見積）

---

## 5. 段階適用（破壊回避 + 可逆）

| Step | 内容 | DB書込 | 可逆 |
|---|---|---|---|
| S0 | プラン承認（本ファイル） | 0 | — |
| S1 | 関数 `fn_project_toc_silver` を DDL で作成（実行なし） | DDL のみ | DROP FUNCTION で完全撤去 |
| S2 | dry-run 実行（`p_source='lionbolt', p_dry_run=true`） — 結果レポートを artifacts/ に出す | 0 | — |
| S3 | ratify 後 apply（lionbolt のみ） | INSERT のみ（弁コム既存は触らない） | 該当source分の DELETE で巻戻し可 |
| S4 | 検証クエリで親欠落=0 / path_text 100% を確認 | 0 | — |
| S5 | legallib 投入完了後、`p_source='legal-library'` で同じ関数を実行 | INSERT のみ | 同上 |
| S6 | （別PR）弁コム既存を再射影する場合の比較・移行設計 | — | — |

各 Step の独立性: **S3で問題が起きても S5/弁コムには影響しない**。

---

## 6. 成果物（PRに含めるもの）

```
tools/toc_silver_projection/
  README.md                                # 設計サマリ・適用手順
  migration_silver_projection.sql          # 関数 + 補助 view（NOT APPLIED）
  verify_silver_projection.sql             # 検証クエリ集
  rollback_silver_projection.sql           # ロールバックSQL
artifacts/phase2_silver_design_20260626/
  PLAN_PHASE2_BRONZE_TO_SILVER.md          # 本ファイル
  DRYRUN_lionbolt_<date>.json              # S2 実測（appply 前に追加）
  VERIFY_REPORT_<date>.md                  # S4 実測（apply 後に追加）
```

---

## 7. リスクと打ち手

| リスク | 対策 |
|---|---|
| 弁コム既存行を壊す | S3 では source='bencom-library' を**触らない**（フラグで除外）。Phase 2.5 で別途 |
| level 起点ずれで階層が崩れる | 各 bib_id 内 min(level) で正規化、サンプル20件で目視確認後 apply |
| 巨大bookで関数が長時間化 | `p_limit_books` で段階適用可能、500冊ずつバッチも選択肢に |
| 親決定が一意に決まらない（同 level 連続） | 「ordinal最大の浅行」で**一意確定**。テストで保証 |
| 適用後の取り消し | source 単位の DELETE（rollback_silver_projection.sql）で完全撤去 |

---

## 8. 承認後の手順（私が動かす範囲）

1. `tools/toc_silver_projection/` 一式を作成して PR #25 へ追加
2. dry-run（read-only相当の関数呼出）を本DBで1回実行し、結果を `artifacts/phase2_silver_design_20260626/DRYRUN_lionbolt_<date>.json` に保存
3. 浅井さんに dry-run 結果を提示 → 「apply OK」をもらってから S3 へ
4. S3 適用、S4 検証、レポート格納

ここまで承認お願いします。
