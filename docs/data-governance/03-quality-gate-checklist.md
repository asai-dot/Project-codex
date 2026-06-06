# 03. 入力前検査チェックリスト（門番の実体）

**このチェックリストの完了は、データ投入の必須条件です。** 完了せずに landing へ投入した
データは、検査未実施として扱い staging 以降へ進めません。PR ではこのリストを貼り付け、
全項目にチェックを入れてください（`.github/PULL_REQUEST_TEMPLATE.md` に同梱）。

## A. 出所・来歴（Provenance）

- [ ] `source`（出所）を特定し記録した。
- [ ] `source_ref`（版番号・URL・取得日）を記録した。
- [ ] このデータを Supabase に置く許諾・ライセンス上の問題がないことを確認した。
- [ ] 個人情報・機微情報を含まない（含む場合は別途取扱い判断を経た）。

## B. 構造（Structure）

- [ ] 列構成が対象テーブル定義と一致している。
- [ ] 文字コードは UTF-8、改行・区切りが想定通り。
- [ ] 余分な前後空白・全角空白・制御文字を除去した。

## C. 値の正しさ（Validity）

- [ ] NOT NULL 必須列に欠損がない。
- [ ] 型・桁・書式（コード体系・日付書式等）が規定どおり。
- [ ] 値域・ドメイン（区分値の許容集合）に収まっている。
- [ ] 自然キーに重複がない。
- [ ] 外部キー参照先が存在する（参照整合性）。

## D. 一貫性・重複（Consistency）

- [ ] 同一データの二重投入でないことを確認した（`row_hash` で照合）。
- [ ] 既存 prod データと矛盾・抵触しない（更新なら `version` を上げる方針を確認）。

## E. dirty 判定（Dirty handling）

- [ ] 汚い行を `quality_status='dirty'` でラベルし、`notes` に理由を記載した。
- [ ] dirty 行は prod へ昇格しないことを理解している。

## F. 検査の実行（Gate execution）

- [ ] `landing.validate_<table>()` を実行し、結果（clean/quarantined 件数）を確認した。
- [ ] quarantined 行の原因を確認し、対応（修正 or 破棄 or dirty ラベル）を決めた。

---

### 記入例（PR 本文に貼る）

```
対象テーブル: landing.municipality
source: e-gov:全国地方公共団体コード
source_ref: 2026-04-01版 / https://www.soumu.go.jp/...
投入件数: 1,966 / clean: 1,962 / quarantined: 4 / dirty: 0
quarantined の原因: muni_code が6桁でない行（修正のうえ再検査済み）
```
