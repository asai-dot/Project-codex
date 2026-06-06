# データガバナンス規程

Supabase 上に「綺麗な静的リファレンスRDB」を構築・維持するためのルール集です。
**綺麗なデータベースを作る前提は「綺麗なデータしか入れない」こと。** 汚いデータを扱う
場合は、汚いと明示ラベルした隔離区画にのみ置きます。

## 4原則

| # | 原則 | 何を構造で強制するか |
| - | ---- | -------------------- |
| 1 | **Clean-only** | 本番（prod）には検査通過データしか到達できない。 |
| 2 | **環境の物理分離** | テスト用と本番用を別 Supabase プロジェクトに分離。混入が物理的に起きない。 |
| 3 | **門番（ゲートキーパー）必須** | 自動検査＋PRレビューの二段。どちらかを欠いたデータは進めない。 |
| 4 | **DBを一人歩きさせない** | 真の正本はGit。DBは定義の投影で、再構築可能。 |

## 文書一覧

| 文書 | 内容 |
| ---- | ---- |
| [01-environments.md](01-environments.md) | 環境の定義・書込可否・命名規則 |
| [02-ingestion-procedure.md](02-ingestion-procedure.md) | データ投入の手順（landing→検査→staging→昇格→prod） |
| [03-quality-gate-checklist.md](03-quality-gate-checklist.md) | **入力前検査チェックリスト（門番の実体）** |
| [04-dirty-data-policy.md](04-dirty-data-policy.md) | 汚いデータのラベリング規程 |
| [05-roles-and-change-control.md](05-roles-and-change-control.md) | 権限・昇格者・変更管理 |

## 来歴メタデータ（全テーブル共通・必須）

どのテーブルにも「どこから来た・誰がいつ検査した・綺麗か汚いか」を追える列を必須化します。

| 列 | 型 | 意味 |
| -- | -- | ---- |
| `source` | text | データの出所（例: `e-gov:municipality-code`） |
| `source_ref` | text | 出所内の識別子・URL・版番号 |
| `ingested_at` | timestamptz | landing に入った時刻 |
| `ingested_by` | text | 投入者 |
| `validated_at` | timestamptz | 検査通過時刻（未検査は NULL） |
| `validated_by` | text | 検査者・検査プロセス名 |
| `quality_status` | enum | `unverified` / `clean` / `dirty` / `quarantined` |
| `row_hash` | text | 業務列のハッシュ。二重投入・改竄の識別に使う |
| `version` | integer | 同一自然キーの版 |
| `notes` | text | 備考（dirty の理由など） |

二重投入で「どちらが綺麗か分からない」問題は、**自然キーの UNIQUE 制約**＋`row_hash`＋
`version` で識別します。`quality_status` が `clean` の行だけが昇格対象になります。

## quality_status の意味

| 値 | 意味 | 置ける場所 |
| -- | ---- | ---------- |
| `unverified` | landing に入ったが未検査 | landing のみ |
| `clean` | 検査通過。昇格可能 | landing / staging / prod |
| `dirty` | 汚いと判明・明示ラベル済み | landing のみ（prod へ昇格不可） |
| `quarantined` | 検査で弾かれ隔離中 | landing のみ |
