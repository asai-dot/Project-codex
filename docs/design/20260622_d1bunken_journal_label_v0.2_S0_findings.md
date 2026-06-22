# S0 確定メモ — 誌名「?」の真因 と v0.2 後処理

- date_jst: 2026-06-22
- 関連: `docs/design/20260620_d1bunken_journal_label_v0.2_plan.md`（計画・集結条件）
- 実装: `tools/d1_bunken/label_journals_v0.2.py`

## 真因（診断で確定）

パーサ v0.1 の出力 `article_meta_all.jsonl`（282,761件）を Mac で実測:

- 綺麗な誌名フィールド **`掲載誌名` は 5,830件（約2%）にしか無い**。
- 誌別集計の `?` = **276,931 = 282,761 − 5,830**（ピッタリ）＝ パーサが `掲載誌名` だけで集計し、
  無い98%が `?` に落ちていた。**誌名が壊れているのではなく、集計が綺麗フィールド依存だっただけ**。
- 全レコードに **`_source_file`（取得元RTFの絶対パス, 100%）** があり、**親フォルダ名＝誌名**。
  → フォルダ名から **282,761 / 282,761 = 100%** 復元できることを確認。
- `掲載誌名` がある5,830件との一致 4,836、不一致994は**ほぼ表記ゆれ**（接尾辞/全角半角/`&`の`_`化）。

→ 判定: **後処理だけで解決（パーサ非改修）**。誌名の一次ソースはフォルダ名、`掲載誌名` は照合専用。

## 正規化で潰すパターン（実データ由来）

| 種別 | 例（folder） | 正規化後 |
|---|---|---|
| 接尾辞ノイズ | `金融法務事情 雑誌記事メタデータ` / `金融・商事判例　雑誌記事メタデータ` | `金融法務事情` / `金融・商事判例` |
| 検索語ゴミ | `銀行法務21(1～60回分）発行年月日昇順` | `銀行法務21`（最初の括弧で切る＋NFKC） |
| 不可視差で二重計上 | `ジュリスト` と `ジュリスト␣` | `ジュリスト`（NFKC＋trim＋空白畳みで統合） |
| ASCII の `&` が `_` 化 | `Law___Technology` | `Law & Technology`（明示エイリアス） |
| **統合してはいけない別誌** | `論究ジュリスト`（掲載誌名が稀に「ジュリスト」） | `論究ジュリスト` を**保持**、食い違いは要目視リストへ |

## v0.2 スクリプトの方針

- canonical = **正規化フォルダ名を正**。少数の表記ゆれのみ明示エイリアス `_ALIAS` で吸収。
- `掲載誌名` は **canonical を上書きしない**（照合のみ）。食い違いは `match_status=meishi_conflict`
  として件数集計し、`summary_labeled.json` に出す＝エイリアスを安全に育てる素材にする。
- **非破壊・冪等**: 入力 jsonl は読むだけ。`<build>/labeled_v0.2/` に新規出力。件数は不変。

付与列: `journal_raw / journal_norm / journal_canonical / journal_source / match_status`
（`priority.json` を渡すと `in_priority` も付与）。

## 実行（Mac）

```bash
JSONL="ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/article_meta_all.jsonl"
python3 tools/d1_bunken/label_journals_v0.2.py "$JSONL"
# 優先JSONがあれば in_priority も付く:
# python3 tools/d1_bunken/label_journals_v0.2.py "$JSONL" path/to/d1_bunken_journal_acquisition_priority_20260612.json
```

## 受け入れ基準（S2）

- `empty journal (?) = 0`。
- `by_journal_canonical TOP` が評釈順位と整合（判例評論≈5,888 / 法律時報 等）。
- 入力件数 == 出力件数（282,761 不変）。
- `meishi_conflict` を目視し、表記ゆれは `_ALIAS` に追記、別誌はそのまま。

## 検証済み（合成データ）

接尾辞除去・括弧切り・不可視差統合・`&`エイリアス・別誌保持の5系統を単体確認（`?`=0）。
