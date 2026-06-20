# DD-LITID 書籍同定 フォワード・ロードマップ v0.2

- 作成日: 2026-06-20（v0.1=06-19 を改訂）
- 改訂理由: **Box に NDL フルダンプが既在することが判明**（`NDL_書誌情報_raw`：`ndl_all_records_001〜161.csv`
  ≈16.7GB ＋ `ndl_law_isbn.txt` 116MB ＋ NDCクラス別）。v0.1 の最大ブロッカー（NDLアクセス runner）が崩れる。
- 上位設計: DD-LITID-PLAN v0.1 / DD-LITID-001 v0.2 / DD-LITID-FP / INGEST_SPEC v0.2。
- ゲート原則（不変）: 可逆=安価先行、不可逆=高価（promote/canonical/DDL/serving）は shadow 実証後。
  **本書は計画。実装/DDL/backfill/promote は HOLD。**

## 0. 確定した現実（v0.1＋今回追加）

| 事実 | 根拠 |
|---|---|
| bib_records 実在は self/own(6,524)・bencom(3,802) のみ。LION BOLT/legallib 未投入 | snapshot 20260619 |
| self/own は ISBN↔NDL 厳密1:1・衝突0 だが `edition`7.6%/`volume`0% で版正誤は内部判定不能 | Phase 0 QA |
| 弁コム既存shadow 1,737（high962/medium775）。ISBN provenance 不一致6件 | snapshot / Phase 0 |
| **★Box に NDL フルダンプ既在**：`ndl_all_records_*.csv`(161分割,≈16.7GB)＋`ndl_law_isbn.txt`(116MB)＋NDC別 | Box 観測 20260620 |
| DB の `ndl_bib_id` 76.7% は、ほぼこのダンプ由来と推定 | 状況証拠 |

監査拘束（不変）: candidate≠confirmed / coverage≠correctness / cohort外挿禁止 / medium775=existing_unconfirmed / 全promote HOLD。

## 1. クリティカルパスの更新（v0.1→v0.2）

- v0.1: 「版品質は外部NDL照合律速 → runner（NDL API アクセス）確定が最優先」。
- v0.2: **NDLダンプが手元にある → ライブAPI不要。** 律速は
  **(1) ダンプのスキーマ/被覆検証 → (2) オフライン ISBN→NDL インデックス構築**。
  ネット不要。残る制約は「~16.7GB を処理できる計算環境（Mac か データ処理env）」のみで、API/レート/権利越境の問題が消える。

## 2. ワークストリーム

### WS-F（新設・最優先イネーブラ）NDL オフライン参照基盤
- F1 **ダンプのスキーマ/被覆検証**: `ndl_all_records_*.csv` と `ndl_law_isbn.txt` の列
  （ISBN / NDL bibid / title / publisher / pub_year / **版表示 edition** / NDC 等）と件数・収載年範囲を確認。
- F2 **オフライン ISBN→(bibid, edition) インデックス構築**（read-only 派生物。canonical ではない）。
- F3 被覆測定: cohort-A の ISBN（5,397）がダンプで何%引けるか。`ndl_law_isbn.txt` の寄与。
- 注意: 当ダンプは「外部共有」配下 → **権利/取扱い範囲の確認**（§7）。スナップショット日付＝鮮度の明示。

### WS-A 自所(cohort-A) 版同定
- A0 ✅ Phase 0 in-DB QA + サンプル91
- A1 サンプル91を **ダンプ照合（F2索引）＋奥付**で `ndl_bib_id_verified` 充填 → 版粒度精度算出（**runner不要に変更**）
- A2 穴埋め: ISBN有NDL無 421 をダンプ照合 / ISBN無NDL無 1,101 の内訳分類・難所queue化
- A3 edition 正規化（版 vs 刷, 改訂/n訂, 日付, 年刊/シリーズ）→ DD-LITID-FP 反映
- A4 provenance 6件の原本確認

### WS-B 弁コム no-ISBN shadow（既存1,737遡及）
- B1 medium 775（existing_unconfirmed）を title_norm+publisher_norm＋第2独立証拠で遡及検証
- B2 high 962 の sample precision

### WS-C 未投入ルート取り込み
- C1 LION BOLT raw intake → ゲート → cohort-A'
- C2 legallib フル → cohort-B（外挿禁止）

### WS-D NDLハブ + マッチング基盤
- F2索引を**ハブ実体**として waterfall/blocking/独立性(origin)を A1/B1 実測で較正

### WS-E identity/edition promote — **HOLD**（閾値充足後ゲート）

## 3. 依存と順序（更新）

```
WS-F1(スキーマ検証) ─▶ F2(索引) ─▶ F3(被覆) ─┬─▶ WS-A1(版粒度精度) ─┐
                                              ├─▶ WS-A2(421/1,101)   ├─▶ WS-D較正 ─▶ 閾値 ─▶ WS-E(promote,要監査)
                                              └─▶ WS-B1(775遡及)─────┘
WS-A3(edition正規化)・WS-A4(6件)・WS-Bサンプル設計 = F非依存で先行可
WS-C1/C2 = raw着地待ち、着地後 cohort別計測
```
- **今すぐ（環境非依存・read-only）**: A2前段の 421/1,101 属性集計、A3 edition 棚卸し、B 設計、F1 のうち Box 上で確認できる範囲。
- **計算環境が要る**: F2 索引構築（~16.7GB 処理）、A1/A2 実照合。

## 4. 直近スプリント（read-only・HOLD据置）

1. **WS-F1**: ダンプ列スキーマ・件数・収載範囲・ISBN/edition 有無を確認（Mac か data env で先頭ストリーム）。
2. **WS-F3 先取り**: `ndl_law_isbn.txt` で cohort-A の ISBN 被覆を見積り。
3. A2前段: 421 リスト＋1,101 属性分布（read-only 集計、DB側で実施可）。
4. A3前段: cohort-A `edition` 全値棚卸し→正規化ルール草案。
5. B 設計: 775 遡及検証の第2独立証拠の取得元定義。

## 5. 実装ゲート閾値（種類固定・値は実測較正）

version-granularity 精度 / candidate_single 妥当率 / multi-bibid 曖昧率 / no_hit(valid ISBN)率 /
low-confidence ISBN率 / metadata_conflict率 / false-confirmation 率 / medium775 precision / manual-review yield /
**＋ダンプ被覆率（ISBNがダンプで引ける割合）**。

## 6. runner 決定（v0.1 §6 を更新＝ほぼ解消）

- 採用: **(c+) Box NDLダンプに対するオフライン照合**（ライブAPI不要・全件カバー・レート/越境なし）。
- 残課題は計算環境のみ: (i) Mac ローカルで CSV をストリーム処理、(ii) 一時 data env にロードしてインデックス化。
- ライブNDL API は「ダンプに無い/鮮度不足のレコードの補完」に限定（必要時のみ・別途）。

## 7. スコープ境界・権利

- 記事/論文層（authority.publication, D1-Law 文献）は DD-PERIODICAL 別ゲート（参照リンクのみ）。
- **NDLダンプの取扱い**: 「外部共有」フォルダ配下のため、派生索引の生成・保管範囲と再配布可否を owner 確認。
  本線では **read-only 参照と内部索引**に留め、外部公開はしない。
- 不可逆処理（promote/canonical/DDL/serving/embedding/外部公開）は全 WS で HOLD。

## 8. 未確定・リスク

- ダンプの**スキーマ未確認**（ISBN/edition 列の有無）＝F1 で最優先確認。
- ダンプの**鮮度/被覆**（スナップショット日・新刊の抜け）。新刊はライブAPI補完が要るかも。
- ~16.7GB の処理環境。
- LION BOLT/legallib 実メタ未確認。独立性判定が origin 単独で足りるか。
