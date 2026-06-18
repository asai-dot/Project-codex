# ISBN→NDL read-only ドライラン計画 v0.1

- 作成日: 2026-06-18
- 対象: DD-LITID-PLAN 4ルート版同定パイプラインのうち **ISBN持ち3ルート**（self_scan / LION BOLT / legallib）
- ゲート: 監査 RESULT(2293126734299) で **GO** とされた「read-only dry-run 計画」。
  本書は計画のみ。**実行も HOLD 対象（DDL/実装/backfill/本番突合/promote/serving）には触れない。**
- 前提契約: INGEST_SPEC v0.2（§7-A field-profile ゲート / §7-D リンク状態）, DD-LITID-001 v0.2（fingerprints/2独立証拠）
- 既存資産参照: colophon_ndl_results.json（奥付→NDL実績）, legallibjoin v0.3.1 resolver, DD-LITID-FP（4信号）

## 0. 目的（このドライランで「測る」こと）

ISBN持ち3ルートを NDL に当て、**版同定がどれだけ機械で解けるか／どこで穴が開くか**を
本番に一切書かずに把握する。監査の懸念（NDLハブ妥当性・加除式・multi-bibid）を**実データで定量化**し、
本実装ゲートを開けるか判断する材料を作る。canonical も count も作らない。

## 1. スコープと非スコープ

- IN: ISBN正規化 → NDL bibid 解決 → 解決状態の分類 → 例外レーン仕分け → QAサンプル抽出。**全て read-only**。
- OUT（HOLD据置）: edition/work/canonical への書き込み, promote, DDL, backfill, serving, embedding, 外部公開。
- OUT（別レーン）: bengo4 no-ISBN は本ドライランに含めない（`bengo4_noisbn_shadow` で別途, 監査 must_fix #3）。

## 2. 入力

- field-profile ゲート（v0.2 §7-A）通過済みの raw 3ルート。manifest_gate PASS が前提。
- ISBN は `normalize_isbn`（field_profile と同ロジック）で `-`/空白除去 → ISBN13/10 判定 → 13へ正規化。
- ISBN欠落レコード（self_scan の奥付欠落等）は本ドライラン対象外 → §6 で no-ISBN として別計上。

## 3. NDL 解決手順（waterfall, read-only）

各 ISBN について:
1. **ISBN完全一致**で NDL bibid を引く（NDL Search API / 既存 resolver 経由, 読むだけ）。
2. ヒット件数で分岐:
   - `resolved_single`: bibid 1件 → 候補 edition link（**candidate のみ**, §7-D。confirmed にしない）。
   - `resolved_multi`: 同一ISBNに複数 bibid（版違い・刷違いが別 bibid 等）→ `multi_bibid` 例外レーンへ。
   - `no_hit`: NDL未収載 → `ndl_absent` 例外レーンへ。
3. 解決できても **2独立証拠（DD-LITID-001 v0.2）を満たすまで confirm しない**。ドライランは候補生成と計測まで。

NDL へのアクセスは既存 resolver/キャッシュ（colophon_ndl_results.json 等）を**読むだけ**で再利用。
レート制御・キャッシュ前提。新規大量クロールはしない（範囲外）。

## 4. 例外レーン（監査 should_fix の NDL 例外を先取り）

| レーン | 条件 | 後段の扱い（本ドライランでは仕分けのみ） |
|---|---|---|
| `multi_bibid` | 1 ISBN → 複数 bibid | 版/刷の粒度差を人手サンプルで確認 |
| `ndl_absent` | NDLヒット0 | 加除式/頻繁改訂/古書の可能性。書誌fingerprintへ回す候補 |
| `looseleaf_suspect` | タイトル/書誌に加除式・追録の語 | bibid が版を表さない疑い |
| `isbn_invalid` | チェックサム不正 | 抽出/OCR誤りの疑い。再OCR候補 |

## 5. 出力（read-only アーティファクトのみ）

- `dryrun_isbn_ndl_<route>_<date>.jsonl`: 1行=1レコード `{route_local_id, isbn13, status, bibid(s), exception_lane}`。
- `dryrun_isbn_ndl_summary_<date>.md`: ルート別の被覆/解決分布/例外率（§7 指標）。
- `qa_sample_<route>_<date>.jsonl`: 各 status から層化抽出した人手確認用サンプル（既定 各50件）。
- いずれも artifacts/ に出すのみ。**canonical テーブルへは書かない。**

## 6. 計測指標（本実装ゲートの判断材料）

ルート別に:
- ISBN被覆率（field_profile 由来）, `resolved_single率`, `resolved_multi率`, `no_hit率`, `isbn_invalid率`。
- no-ISBN レコード比率（self_scan で重要）。
- multi_bibid の「版粒度で正しく割れているか」QAサンプル精度。
- no_hit の内訳推定（加除式/古書/単なる未収載）。

## 7. 受け入れ基準（ドライランの合否 ≠ 本実装許可）

- ✅ 3ルートで上記分布が出る。multi_bibid/no_hit の QA サンプルが揃う。
- ✅ 監査 §4-1（NDLハブ妥当性）への定量回答が出る:「ISBN持ちルートで resolved_single が支配的か、
  加除式/改訂で no_hit/multi が無視できない水準か」。
- ⛔ 本ドライランは promote/DDL/backfill の許可を**含まない**。結果を持って次の監査ゲートへ。

## 8. リスクと未確定

- legallib フル版未着 → 当面は self_scan / LION BOLT の2ルートで先行ドライラン、legallib は到着後合流。
- NDL API のレート/カバレッジ。既存キャッシュで足りない範囲は計測対象を明示限定。
- multi_bibid の正解定義（版 vs 刷）は QA サンプルで人手確定が要る（自動では決めない）。

## 9. 監査に問いたい点（adversarial）

1. ISBN完全一致を起点にする waterfall で、**刷違い/重版を別 editionと誤って割る**リスクの抑え方。
2. `no_hit` を「NDL未収載」と「ISBN抽出ミス」に切り分ける read-only な判別法は十分か。
3. multi_bibid を版粒度に落とす際、DD-LITID-001 の 2独立証拠だけで足りるか、NDL内メタ（出版年/版表示）併用要否。
4. legallib 未着で 2ルート先行することの妥当性（後合流でバイアスが出ないか）。
5. このドライランの出力だけで本実装ゲートを開ける判断ができるか、追加で測るべき指標はないか。
