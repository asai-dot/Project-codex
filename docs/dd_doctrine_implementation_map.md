# ドクトリン ⇄ 実装 対応マップ（別冊）

> `docs/dd_doctrine.md`（思想の正本）から分離した実装トレーサビリティ（GPT DDDOCTRINE 監査 Finding 1）。
> ここは「どの思想が、どのコード/データで具現化されているか」だけを持つ。思想の主張は本体を見ること。

| 思想（dd_doctrine の章） | 実装 / データ |
|---|---|
| 手続フローの保持・検証・描画（§2 三層, §3 地面の種別） | `scripts/procedure_flow.py`（各 node `source` 必須＝地面の宣言の萌芽） |
| 本から抽出して手作りしない（§7 巨人の肩） | `scripts/procedure_flow_from_toc.py`、実フロー `pipeline/procedure_flow/commercial_share_delivery.json`（bencom綺麗TOC由来） |
| 層0分類（§2 L0 の入口の仕分け） | `scripts/procedure_match.py`（書式/書名×spine、leaf/broad 2段突合） |
| 手続類型の背骨（§2） | `pipeline/procedure_spine.json`（24類型・bottom-up 化は今後） |
| 書式 face（§2 L2／手続×書式を並べる） | `commercial_share_delivery.json` の node `書式`（同書TOCの書式例を頁出典で貼付） |
| 巨人の階層・源の実査（§7） | bencom-library 3,802冊(綺麗TOC, Supabase `biblio.bib_toc`) / asai-bookshelf 6,524冊(自炊OCR)、e-Gov 民訴・刑訴 条見出し＋law_id |
| 全体可視化（地図⇄現在地） | `/dd` ダッシュボード（`scripts/pipeline_dashboard.py`）の structure セクション、`docs/dd_index.md` |

## まだ実装が無い思想（next の種）
- §6 名著蘇生（条文アンカー＋改正Δ注記）→ 時点別法令（lawtime）＋ e-Gov 改正履歴 diff が前提。
- §5 記載事項の床（条文各号×書式の収束）→ 書式の意味的構造化＋号IDマップが前提。
- §8 足場検索（拠り所の最大 recall ＋ 荷重格付け）→ 留意点/解釈の横断 RAG が前提。
- §7 委任の typed hole → e-Gov 委任グラフの consume が前提（主権者待ち）。
