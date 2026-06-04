# 蔵書 owner重要度 重み付け 仕様（継続タスク・2026-06-05起票）

> **status: OPEN（継続タスク）。点数付けは浅井さんが「実本棚の棚卸」時に実施。本スクリプト/Claudeは値を埋めない。**
> 基準＝**実本棚（`biblio.bib_records` source=asai-bookshelf, 6,524）**。外部の推薦リスト(9系統)は補助の事前値。
> 「どの本が当事務所で重要か」は owner にしか分からない＝**owner重要度が正本（canonical firm weight）**、external endorsement は prior（参考）。

## なぜ実本棚ベースか（owner判断 2026-06-05）
- 重要度は事務所固有。外部の教科書系リストでは拾えない必携書がある（例: 年刊・ISBN無の **赤い本**＝機械突合の盲点）。
- 棚卸時にしか分からない実務的ニュアンス:
  - **実棚にあって裁断（スキャン）するか迷う本** → scan判断
  - **実棚にあって2冊目を買うほど重要な本**（例: 会社法実務スケジュール）→ 強い重要シグナル
  - **「この本しかない」級の代替不能な必携**（例: 破産管財実践マニュアル）→ 最高重み

## 明示カラム定義（owner が棚卸時に付与）
各 bib_record（asai-bookshelf、bib_id をキー。ISBN欠落本も title 経由で1行）に対し:
| カラム | 型 | 内容 |
|---|---|---|
| `asai_importance_score` | int 0–5 | **5=代替不能(この本しかない) / 4=必携 / 3=重要 / 2=有用 / 1=参考 / 0=処分検討**。当事務所での実務重要度。 |
| `asai_essential` | bool | 代替不能級（score=5相当）の明示フラグ |
| `scan_decision` | enum | scan / keep_physical / undecided（裁断するか迷う本の判断） |
| `copies_intent` | enum | single / want_second（2冊目を持つ/買う級＝重要度の強シグナル） |
| `owner_note` | text | 自由記述（用途・代替可否など） |

機械の事前値（read-only ヒント・既算出）: `endorsement_count` / `sources` / 至誠堂`standard_tier` / `field`
（出所: `build/search_bench/multisource_shelf_endorsements.csv`）。

## 関係（重要）
- **owner_importance_score が最終の重み**。external endorsement は出発点の参考にすぎない。
- 乖離が情報になる:
  - 外部高×owner低 → 当事務所では不要（やらない分野等）
  - **外部低/ゼロ×owner高** → 機械が取りこぼす事務所固有の必携（**赤い本・破産管財実践マニュアル・新版会社法実務スケジュール(ISBN無)** 型）。ここを owner知見で救うのが本タスクの主眼。

## ワークフロー
1. （将来・号令で）私が **採点シート**を生成: 実棚6,524行に bib_id/title/事前値＋上記の**空のownerカラム**を並べる（owner_*は空。Claudeは埋めない）。
2. 浅井さんが**棚卸時**に各本へ点数付け。
3. 確定後、`biblio` 側への格納（列/側テーブル）を A0契約枠で codex/花岡 とスキーマ合意（DB書込はその後）。

## owner名指しの必携（種・点数は未付与＝owner待ち）
- 会社法実務スケジュール（ISBN 9784788291249）＋新版(ISBN無) … copies_intent=want_second級
- 破産管財実践マニュアル（ISBN 9784417015987）… essential級「この本しかない」
- 赤い本 民事交通事故訴訟 損害賠償額算定基準（ISBN無・年刊・スキャン済）… essential級
- 要件事実マニュアル（岡口・第5版全5巻ほか）… essential級
- 家庭裁判所における遺産分割・遺留分の実務（片岡武）… 相続の定評書

## 継続タスク
- [ ] 棚卸時に owner重要度を点数付け（owner）。
- [ ] 採点シート生成（号令で。実棚6,524＋事前値＋空ownerカラム）。
- [ ] 確定後のDB格納スキーマ合意（codex/花岡）。
