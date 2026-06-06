# Project Codex — 静的リファレンスRDB

「綺麗な静的データベース」を Supabase 上に構築するためのリポジトリです。
このリポジトリは **DBの正本（source of truth）** であり、Supabase 上のデータベースは
ここにある定義（スキーマSQL・参照データ・手順）の *投影* にすぎません。
DBはいつでもこのリポジトリからゼロ再構築できます。

## なぜこの構成か

データベースは一度作ると「一人歩き」します。誰が・いつ・どの経路で入れたのか分から
ないデータが積み上がり、二重投入や矛盾が起きると「どちらが綺麗でどちらが汚いのか」が
識別できなくなります。これを防ぐため、本リポジトリは次の4原則を構造で強制します。

1. **Clean-only** — 本番には検査を通過したデータしか入らない。
2. **環境の物理分離** — テスト用と本番用を Supabase プロジェクトレベルで分離する。
3. **門番（ゲートキーパー）必須** — 検査を通らないデータはDBに到達できない。
4. **DBを一人歩きさせない** — 真の正本はGit。変更はPRレビューを必ず通る。

詳細は [`docs/data-governance/`](docs/data-governance/README.md) を参照してください。

## 環境（2プロジェクト構成）

| プロジェクト   | 役割                       | 書き込み可否                         |
| -------------- | -------------------------- | ------------------------------------ |
| `codex-staging` | プレ本番・試作・テスト       | 自由（landing は何でも可、要ラベル） |
| `codex-prod`    | 本番・公開                 | レビュー済み昇格スクリプト経由のみ   |

```
codex-staging                           codex-prod
┌───────────────────────────┐  昇格 PR  ┌────────────────────────┐
│ schema landing (検疫区画)   │ ───────▶ │ schema prod            │
│  └ 生データ / dirty可 / 要ラベル│ レビュー  │  └ 検査通過品のみ / 読取主体│
│ schema staging (検証済候補)  │          │  └ 直接INSERT権限なし    │
└───────────────────────────┘          └────────────────────────┘
      ▲ 門番①: landing→staging              ▲ 門番②: staging→prod
        （自動検査＋ラベル付与）                （PRレビュー＋昇格スクリプト）
```

## ディレクトリ

```
docs/data-governance/   ガバナンス規程（ルール・手順・チェックリスト）
supabase/staging/       codex-staging に適用するマイグレーション
supabase/prod/          codex-prod に適用するマイグレーション
supabase/README.md      適用手順
.github/                PRテンプレート・CI（門番の一部）
```

## はじめての投入

[`docs/data-governance/02-ingestion-procedure.md`](docs/data-governance/02-ingestion-procedure.md)
の手順に従ってください。投入前に
[`03-quality-gate-checklist.md`](docs/data-governance/03-quality-gate-checklist.md)
の入力前検査チェックリストを必ず完了させます。
