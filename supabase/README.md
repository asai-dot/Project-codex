# supabase/ — マイグレーション適用ガイド

2プロジェクト構成。マイグレーションは適用先別にディレクトリを分けています。

| ディレクトリ | 適用先プロジェクト | 内容 |
| ------------ | ------------------ | ---- |
| `staging/migrations/` | `codex-staging` | codex共通 / landing / staging / 検査・昇格関数 |
| `prod/migrations/`    | `codex-prod`    | codex共通 / prod スキーマ / ロックダウン / 公開データ |

`0001_codex_common.sql` は両プロジェクトに同一内容で適用します（別DBのため各々に必要）。

## 適用方法

### A. Supabase MCP（このリポジトリの既定）
各 `.sql` を**ファイル名の連番順に** `apply_migration` で対象プロジェクトに適用します。
staging 用は `codex-staging`、prod 用は `codex-prod` の project_id を指定。

### B. Supabase CLI（ローカル開発）
```bash
# 例: staging へ
supabase link --project-ref <codex-staging-ref>
# migrations を順に適用（CLI 管理下に置く場合は supabase/migrations へ配置）
```

## 投入フロー（門番）

```
landing へ生データ投入
   → select * from landing.validate_municipality();      -- 門番①: 検査
   → select landing.promote_municipality_to_staging();   -- clean のみ staging へ
   → staging の内容を prod/migrations のシードとして書き出す
   → GitHub で昇格 PR（チェックリスト完了）              -- 門番②: レビュー
   → マージ後 prod/migrations を codex-prod に適用
```

## 新しい参照テーブルの足し方

`staging/migrations/0004_example_municipality.sql` の構造を踏襲してください。

1. `landing.<table>`（自然キー UNIQUE は貼らない）＋ `codex.add_provenance`
2. `staging.<table>`（PK・自然キー UNIQUE・値域 CHECK・`quality_status='clean'` CHECK）
3. `landing.validate_<table>()`（検査）と `landing.promote_<table>_to_staging()`（昇格）
4. `prod/migrations` に `prod.<table>`（同じ制約＋RLSロックダウン）

## 重要な不変条件

- prod に入るのは `quality_status='clean'` のみ（CHECK 制約で保証）。
- prod への直接 INSERT/UPDATE/DELETE は anon/authenticated から剥奪済み。
- DB は常にこのディレクトリから再構築可能に保つ（手修正は必ずマイグレーション化）。
