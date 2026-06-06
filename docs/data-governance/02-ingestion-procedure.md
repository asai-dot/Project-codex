# 02. データ投入手順

データは必ず次の経路を通ります。**近道（prod への直接投入）は存在しません。**

```
[1] 準備          [2] landing 投入     [3] 門番①検査      [4] staging        [5] 門番②昇格        [6] prod
ソース取得   →   codex-staging へ  →  自動検査関数   →  検査通過品の  →  PRレビュー＋    →  公開
クレンジング     生データ投入         で clean 判定      昇格候補集合      昇格マイグレーション
```

## ステップ詳細

### [1] 準備（投入前検査の実施義務）

- ソースを取得し、`docs/data-governance/03-quality-gate-checklist.md` の
  **入力前検査チェックリスト**を完了させる。
- 出所・版・取得日を控える（`source` / `source_ref` に入れる）。
- この段階で明らかに汚いと分かるものは、04（dirty 規程）に従ってラベルを決める。

### [2] landing 投入（codex-staging）

- `landing` スキーマの対象テーブルに投入する。`quality_status` は既定で `unverified`。
- landing は検疫区画。何を入れても良いが、**ここから先へは検査なしでは1行も進めない。**
- 汚いと分かっているデータは `quality_status='dirty'` を明示し、`notes` に理由を書く。

### [3] 門番①：自動検査（landing → clean 判定）

- `landing.validate_<table>()` 検査関数を実行する。
- 検査内容: スキーマ適合・型・NOT NULL・自然キー UNIQUE・FK整合・CHECK（値域/ドメイン）・重複検知。
- 通過した行は `quality_status='clean'`、`validated_at` / `validated_by` が記録される。
- 落ちた行は `quality_status='quarantined'` のまま landing に残る（staging へは進まない）。

### [4] staging へ反映

- `landing.promote_to_staging_<table>()` を実行し、`clean` 行のみを `staging` へ反映。
- `staging` のデータは検査関数で作り直すのが原則。**手で直さない。**

### [5] 門番②：昇格（staging → prod、PRレビュー）

- `staging` の内容を `supabase/prod/migrations/` のシード/昇格マイグレーションとして書き出す。
- **GitHub で PR を作成**し、レビューを受ける（チェックリスト完了が必須条件）。
- 2プロジェクト構成のため staging→prod は同一DB内関数では行えない。
  「staging から書き出し → レビュー済みマイグレーションを prod に適用」という
  Git を経由する経路にすることで、昇格は必ず人の目を通る。

### [6] prod 反映

- マージ後、`supabase/prod/migrations/` を `codex-prod` に適用する（`supabase/README.md` 参照）。
- prod に入るのは `quality_status='clean'` の行のみ（CHECK 制約で保証）。

## 二重投入・更新の扱い

- 同じ自然キーで再投入する場合、`row_hash` が一致すれば内容無変更（昇格不要）。
- `row_hash` が異なれば内容変更 → `version` を上げて昇格 PR を出す。
- これにより「どちらが綺麗でどちらが古い/汚いか」が常に識別できる。
