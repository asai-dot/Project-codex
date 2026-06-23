# P0 実データ実行 findings（語彙Hub構築 dry-run）20260623

> doc_kind: 実行記録（read-only dry-run の結果記録） / author: Claude / date: 2026-06-23 / owner: 浅井
> 親: design/vocab_object/01_VOCAB_BOTTLENECK_RESOLUTION_PLAN（P0）/ tools/vocab_hub/
> 実行環境: Mac CC（term_dict ゴールドの在る単一書き手レーン）

## 0. 一行

語彙Hub構築 P0 が **実データでフルスケール完走**（有斐閣 13,344 terms）。スケール・実スキーマ・定義 join とも検証済。
2辞書（有斐閣＋学陽）の cross-dict 実行ツールも実装・単体テスト済（17 tests）。**残るは 2辞書 report の実測値**。

## 1. 実行できたこと（measured）

### 単辞書（有斐閣のみ・2026-06-23 実行）
```
terms=13344  hubs=12619  homograph=0
```
- 13,344 terms → **12,619 provisional hub**（≈725 が辞書内同一(見出し+読み)で統合）。
- `homograph=0` は**想定どおり**：有斐閣ゴールドは staging 時点で同綴異義を読みで分離済
  （`homograph_variant_ix`）＝真の同綴異義は別 hub に正しく割れる（“衝突”として立たない）。
- これにより **スケール（1.3万件）・実スキーマ（stg_term_key／定義は labels 側）・定義 join** が検証された。

### 実スキーマ適合（実行で確定）
- 有斐閣: `stg_term_key`／定義は `labels(label_type=="definition")` 側 → `--labels` で join 済。
- 学陽: `hourei_all_entries_v0.2`（headword/reading/definition インライン）→ `adapt_hourei.py` で
  rank102 Term へ変換。
- 辞書間の見出し/読みは `norm_pref`(NFC+全角英数→半角)／`norm_reading`(NFKC+カナ→かな) で正規化し揃える。

## 2. まだ出ていない（2辞書 report 待ち）

単辞書では cross-scheme ペアが無いため、**意味のある信号は未測定**：
- **exact統合（辞書をまたいだ同概念の統合）数**
- **homograph_conflict（同見出し+読みで定義が食い違う）数**（社員=会社法 vs 一般 等）
- **重なり率 0.6 の妥当性**（統合/非統合の境界感触）

→ これらは `--terms 有斐閣 学陽 --labels 有斐閣labels` の 2辞書 run で初めて出る。ツールは ready。

## 3. 次の決定ゲート（数字が来たら即動く）

1. 2辞書 `hub_build_report.md` の実測（生成hub数・size分布・homograph_conflict・tier分布）。
2. しきい値感触: 0.5 / 0.6 / 0.7 を同一データで比較 → **0.6 を Wave0 実測で再校正（DICT-008 Q2）**。
3. 確定後 → **P1（DD-DICT-008 accept 片付け）** へ。

## 4. ゲート

read-only dry-run のみ。DB load / canonical 昇格 / DDL は P2 以降（owner GO＋監査）で HOLD 継続。
