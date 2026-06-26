# P0.5 完了記録: shortdef triage 実施結果 20260626

> doc_kind: 完了記録（実測値確定） / author: Claude / date: 2026-06-26 / owner: 浅井
> 親: 07_P0_5_SHORTDEF_TRIAGE_PLAN_20260624
> 決定根拠: owner「並行して」指示 2026-06-26（P0.5 triage + clean subset P1/P2 先行を並行）

## 0. サマリ

| 分類 | 件数 | 対応 |
|---|---|---|
| ② 正規（参照/略語/見出し参照） | **535件** | clean subset = P1/P2 load 対象確定 |
| ① 末尾切れ/OCR疑い | 29件 | needs_reocr → DD-DICT-006 申し送り |
| ③ parse ミス | 21件 | needs_reparse → パーサ再点検 |
| gray 残 | 0件 | 全件分類完了 |
| **合計** | **585件** | |

clean subset 比率: 91.5%（計画の489 hub に対して実数 535件はterm-level集計のため差異）

## 1. 実施内容

入力: `~/dict_quality/yuhikaku_short_def.jsonl`（463件）+ `hourei_short_def.jsonl`（122件）

決定的 heuristic（`/tmp/claude/triage_shortdef.py`）で3分類:
- **② 判定規則**: 参照矢印（↳⇨→⇒↓⇩↴➡⇓▷等）/「」形式/略語パターン（〜の略/〜に同じ）/名詞句1語
- **① 判定規則**: 文末が助詞・動詞途中・括弧未閉/数字/...
- **③ 判定規則**: 記号・数字のみ/読み仮名が本文に混入

## 2. 出力成果物

`~/dict_quality/` に以下を生成（read-only・DB未投入）:
- `shortdef_triage_cat2_canonical.jsonl` — 535件（clean）
- `shortdef_triage_cat1_ocr.jsonl` — 29件（needs_reocr）
- `shortdef_triage_cat3_parse.jsonl` — 21件（needs_reparse）

## 3. P0.5 DoD 充足確認

| DoD 項目 | 状態 |
|---|---|
| 短定義が ①②③ に分類され件数確定 | ✅ 完了 |
| ①③の件数が DD-DICT-006 へ申し送り可 | ✅ 29件(reocr) + 21件(reparse) |
| clean subset の hub 数が確定し P1 load 対象明示 | ✅ 535件 |

## 4. 下流への申し送り

### DD-DICT-006（再OCR対象）
① 29件: 文章途中でOCR脱落の疑い。`~/dict_quality/shortdef_triage_cat1_ocr.jsonl` を参照。
例: 「一部支払: 手形・小切手の」「管理の委託: ① 各省各庁の」

### パーサ再点検対象
③ 21件: 学陽 calibration の sense_sub 過剰分割等。`shortdef_triage_cat3_parse.jsonl` を参照。
例: 「現金前渡し: （ぜんと）」（読み仮名混入）

### canonical 昇格（P2以降）
clean 535件は canonical 昇格の対象候補。現在 provisional 13,188 hub の内。
昇格 GO は別ゲート（owner ratify・PR #35 ②項目）。
