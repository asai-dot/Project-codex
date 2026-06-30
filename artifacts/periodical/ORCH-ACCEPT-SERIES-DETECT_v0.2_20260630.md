# ORCH-ACCEPT — SERIES-DETECT 本採用 ＋ v0.2 偽系列除去（owner GO 2026-06-30）

- 種別: 本採用記録（accepted・owner GO 済）/ head 実行
- 親検収: `ORCH-AUDIT-SERIES-VALIDATE_verdict_20260630.md`（精度 99.33% PASS）
- owner GO: 1) v0.1 本採用 2) 偽候補69件 demote 3) v0.2 再発防止、を承認

---

## 1. 本採用（item 1）

SERIES-DETECT v0.1（10,243系列 / 73,373記事）を **精度 99.33%（≥90% ゲート）で本採用**。
連載系列メタを静的DBの accepted 構造として確定（DB書込・外部公開は別途 owner GO・本記録の対象外）。

## 2. 偽系列除去 → v0.2（item 2・3 を同時達成）

`tools/periodical/detect_series.py` を patch（`is_junk_series_name`: 部マーカー/汎用ラベル/2字以下を系列キーから除外）。
**実データ再生成で検証**:

| | v0.1 | v0.2(patch後) |
|---|---|---|
| 系列数 | 10,243 | **10,174**（**-69**・偽候補と完全一致）|
| 記事数 | 73,373 | 72,921 |
| junk 除外記事 | — | 511 |
| 推定精度 | 99.33% | **≈99.8%+** |

除去確認: 各論/特集/中/下/論説/資料 等の偽系列タイトルは v0.2 で残存 0。
→ item2(demote) と item3(再発防止) を **1つの生成パッチで恒久的に達成**（次回以降の生成も自動でクリーン）。

## 3. 成果物

- `tools/periodical/detect_series.py`（v0.2 patch・コミット）
- `artifacts/periodical/article_series_summary_v0.2.json`（クリーン版サマリ・コミット）
- `artifacts/periodical/article_series_v0.2.csv`（11.6MB・**git非載せ**。patch 済スクリプトで再生成可・データ正本はローカル/atlas）
- 偽候補の根拠: `series_validate_false_candidates_v0.1.csv`（69件）

## 4. caveat / HOLD

- v0.2 は head 検証ベース。さらに厳密化するなら GPT 監査も可（任意）。
- **HOLD（owner GO 必須・未実施）**: 静的DB/canonical への v0.2 反映・DB書込・外部公開。本記録は受入・生成パッチまで。
