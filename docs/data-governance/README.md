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
| `gate_run_id` | text | どの検査実行で通したかの識別子（監査証跡。prod では NOT NULL） |
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

## 補足原則（設計の境界を明確にする）

レビューで出た論点への立場を明記します。設計の重さは**実際の更新頻度と規模に合わせて**
調整してください。

### 正本（source of truth）はどこか

- **`supabase/prod/migrations/` が prod の正本。** prod のデータは必ずここを経由する。
- **`staging` は検査用の使い捨て。** いつ作り直しても良く、勝手に正本扱いしない。
  これにより「staging と prod-seed のどちらが真か」という二重管理のドリフトを断つ。

### 検査ロジックはどこに置くか

- **DB制約（UNIQUE / CHECK / FK / enum）が"最後の砦"。** 何があっても汚いデータが prod に
  物理的に入らない最終防壁であり、ここは必ず効かせる。
- **`validate_*()` / `promote_*()` 関数は補助。** landing での検査・昇格を楽にするための
  道具であって、門番の最終権限ではない。
- **門番の最終権限は CI ＋ PR レビュー。** これが「DBではなく Git が門番」という方針の実体。
  検査関数を将来コード側（CI）へ寄せても、DB制約という最後の砦は残す。

### 規模に応じた段階移行（過剰設計を避ける）

| 状況 | 推奨 |
| ---- | ---- |
| 更新が稀・少量の純粋な静的マスタ | landing を省き、CIでseedを検査 → 制約付き prod へ直接ロードでも可 |
| ある程度継続的に投入・要クレンジング | 本設計（landing→staging→prod）の3層が活きる |
| 小規模・少人数でコスト重視 | まず1プロジェクト＋スキーマ分離で開始し、規模が出たら2プロジェクトへ移行 |

層やプロジェクト数は固定ではない。**思想（clean-only・門番・再構築可能）を保ったまま**、
重さだけを実態に合わせて増減させる。

### 状態列は「成熟度」一軸に保つ（語彙の混在を禁止）

`quality_status` は **データの成熟度（どこまで検査・昇格が進んだか）だけ**を表す一軸の
語彙であり、他の意味を混ぜてはならない。

- **許される値はこれだけ**：`unverified` / `clean` / `dirty` / `quarantined`。
- **検証の事実**（誰がいつ確認したか）は `validated_at` / `validated_by` に置く。状態語彙に
  `live_confirmed` のような検証種別を足さない。
- **役割・出所**（生成プロセス、投入経路）は `source` / `ingested_by` に置く。
- **権限・実装の限定**（例: 「設計としては確定だが本番DDL未適用」「書込不可」）が必要なら、
  状態語彙を増やさず **`notes` または専用の qualifier 列**で表す。
- **行の処理状態**（赤入れ・補正・破棄など、レビュー作業上の区分）も状態語彙とは別列にする。

理由：状態語彙に検証・権限・役割・処理区分を混ぜると、「綺麗さの段階」を表すはずの列が
多義になり、後から見た人（や別のAI）が別の軸の値を成熟度と誤読する。**状態の混同を防ぐ
ための列が、自ら状態を混在させる**という自己矛盾が起きる。成熟度・検証・役割・権限・処理
区分は、それぞれ独立した列（軸）として持つ。
