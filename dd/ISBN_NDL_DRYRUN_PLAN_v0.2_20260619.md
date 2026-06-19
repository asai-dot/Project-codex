# ISBN→NDL read-only ドライラン計画 v0.2

- 作成日: 2026-06-19（v0.1 = 2026-06-18 を改訂）
- 改訂理由: GPT Pro 監査 RESULT `20260618_ISBN_NDL_DRYRUN_PLAN_v0.1_GPTPRO_AUDIT_RESULT`（判定
  **DESIGN_PASS_WITH_NOTES / read-only は must_fix 反映後 GO**）の must_fix 5点を畳み込み。
- 対象: DD-LITID-PLAN 4ルート版同定のうち **ISBN持ちルート**（self_scan / LION BOLT / legallib）
- ゲート: read-only dry-run のみ GO。**実装/DB書込/backfill/promote/serving/embedding は HOLD。**
- 前提契約: INGEST_SPEC v0.2（§7-A field-profile ゲート / §7-D リンク状態）, DD-LITID-001 v0.2（fingerprints/2独立証拠）
- 既存資産参照: colophon_ndl_results.json（奥付→NDL実績）, legallibjoin v0.3.1 resolver, DD-LITID-FP（4信号）
- 実測前提: DB実測スナップショット `artifacts/DB_OBSERVED_SNAPSHOT_litid_20260619.md`
  （現状 bib_records 投入済は **self/own(asai-bookshelf) のみ**。LION BOLT/legallib 未投入）

## 0. v0.1 からの変更点（監査 must_fix の反映）

| # | must_fix | v0.2 での反映箇所 |
|---|---|---|
| 1 | `resolved_single` は版確定でない | **`candidate_single_bibid` に改名**（§3, §6）。confirmed と明確に分離 |
| 2 | 「2独立証拠」の定義 | §3-bis に定義追加：**同一NDLレコード内の複数フィールドは独立2証拠に数えない。別ソース系で2つ** |
| 3 | `no_hit` の切り分け | §4 で抽出信頼度別 3バケットに分割 |
| 4 | route cohort ラベル / 外挿禁止 | §1-bis cohort 定義。**cohort-A の率を legallib(cohort-B) へ外挿しない** |
| 5 | no-write 保証 | §10 runbook no-write 保証を明記 |

## 1. スコープと非スコープ

- IN: ISBN正規化 → NDL bibid 解決 → **候補**状態の分類 → 例外レーン仕分け → QAサンプル抽出。**全て read-only**。
- OUT（HOLD据置）: edition/work/canonical への書き込み, promote, DDL, backfill, serving, embedding, 外部公開。
- OUT（別レーン）: bengo4 no-ISBN は本ドライランに含めない（`bengo4_noisbn_shadow`, 監査 must_fix #3 / 本件 OUT OF SCOPE）。

### 1-bis. route cohort（外挿禁止・監査 must_fix #4）

| cohort | ルート | 現況（実測） | 扱い |
|---|---|---|---|
| **cohort-A** | self_scan（自所 asai-bookshelf） | bib_records 投入済 6,524 | 先行ドライラン可 |
| cohort-A' | LION BOLT | **未投入**（bib_records 行ゼロ） | 投入後に cohort-A へ合流 |
| **cohort-B** | legallib | **未着** | 到着後に別 cohort として計測、合算は再集計 |

- 各アーティファクト行に `route_cohort` を必須付与。
- **cohort-A の解決率/例外率を legallib へ外挿しない。** 合算サマリは legallib 到着後に再計算する。

## 2. 入力

- field-profile ゲート（v0.2 §7-A）通過済みの raw。manifest_gate PASS が前提。
- ISBN は `normalize_isbn`（field_profile と同ロジック）で `-`/空白除去 → ISBN13/10 判定 → 13へ正規化。
- ISBN欠落レコード（self_scan の奥付欠落等）は本ドライラン対象外 → §6 で no-ISBN として別計上。
- **各行に raw input row id と route-local id を保持**（should_fix・再現性）。

## 3. NDL 解決手順（waterfall, read-only）

各 ISBN について:
1. **ISBN完全一致**で NDL bibid を引く（NDL Search API / 既存 resolver 経由, 読むだけ）。
2. ヒット件数で分岐:
   - `candidate_single_bibid`: bibid 1件 → **候補 edition evidence のみ**（§7-D。**版確定ではない**。confirmed にしない）。
   - `multi_bibid`: 同一ISBNに複数 bibid（版違い・刷違いが別 bibid 等）→ 例外レーンへ。
   - `no_hit`: NDLヒット0 → §4 のバケットへ仕分け。
3. 候補が出ても **2独立証拠（§3-bis）を満たすまで confirm しない**。ドライランは候補生成と計測まで。

NDL へのアクセスは既存 resolver/キャッシュ（colophon_ndl_results.json 等）を**読むだけ**で再利用。
**NDL resolver/cache のバージョンとアクセス方式をアーティファクトに記録**（should_fix・再現性）。

### 3-bis. 「2独立証拠」の定義（監査 must_fix #2）

- 独立 = **異なるソース系（source family）**：colophon OCR / NDL / 出版社 / legallib / LION metadata。
- **同一 NDL レコード内の複数フィールド（出版年 ＋ 版表示 等）は独立2証拠に数えない。**
- legallib/LION のメタが NDL/出版社由来の場合、独立性は origin で判定（循環回避、open question §11）。

## 4. 例外レーン（監査 should_fix で増設）

| レーン | 条件 | 後段の扱い（本ドライランでは仕分けのみ） |
|---|---|---|
| `multi_bibid` | 1 ISBN → 複数 bibid | 版/刷の粒度差を人手サンプルで確認 |
| `no_hit_after_valid_isbn` | 妥当ISBNでヒット0 | NDL未収載の本命。書誌fingerprintへ回す候補 |
| `no_hit_after_low_confidence_isbn` | 低信頼ISBNでヒット0 | 再OCR/抽出見直し候補 |
| `isbn_source_untrusted` | ISBN出所が信頼できない | 抽出器/出所の検証対象 |
| `looseleaf_or_supplement_series` | 加除式・追録・シリーズ | bibid が版を表さない疑い |
| `isbn_invalid` | チェックサム不正 | 抽出/OCR誤りの疑い |
| `isbn_reused_or_suspicious` | ISBN再利用/重複の疑い | 別書に同ISBNの可能性 |
| `metadata_conflict` | ISBN一致だが title/publisher/year が著しく不一致 | 誤一致の疑い（should_fix） |

## 5. 出力（read-only アーティファクトのみ）

- `dryrun_isbn_ndl_<cohort>_<date>.jsonl`: 1行 `{raw_row_id, route_local_id, route_cohort, isbn13, status, bibid(s), exception_lane}`。
- `dryrun_isbn_ndl_summary_<date>.md`: **cohort別**の被覆/解決分布/例外率（§7 指標）。
- `qa_sample_<cohort>_<date>.jsonl`: §8 のサンプル設計に従う人手確認用サンプル。
- いずれも artifacts/ に出すのみ。**canonical テーブルへは書かない。**

## 6. 計測指標（本実装ゲートの判断材料）

cohort別に:
- ISBN被覆率, `candidate_single_bibid率`, `multi_bibid率`, `no_hit`各バケット率, `isbn_invalid率`。
- no-ISBN レコード比率（self_scan で重要）。
- multi_bibid の「版粒度で正しく割れているか」QAサンプル精度。
- **route別 disagreement rate**（ソース系間で版判定が割れる率）。

## 7. 受け入れ基準（ドライランの合否 ≠ 本実装許可）

- ✅ cohort別に上記分布が出る。multi_bibid/no_hit の QA サンプルが揃う。
- ✅ 監査 §4-1（NDLハブ妥当性）への定量回答：「ISBN持ちルートで candidate_single が支配的か、
  加除式/改訂で no_hit/multi が無視できない水準か」。
- ⛔ promote/DDL/backfill の許可を**含まない**。結果を持って次の監査ゲートへ。

### 7-bis. 実装ゲート移行の閾値（監査 should_fix）

本実装設計へ進む前に最低限の閾値を置く（値は cohort-A 実測で較正、決め打ちしない）:
- valid ISBN rate / `candidate_single_bibid` rate / multi_bibid 人手精度 / no_hit false-negative rate / route別 disagreement rate。

## 8. QAサンプル設計（監査 should_fix）

- ランダム ＋ 層化（route_cohort × {invalid ISBN, no_hit各バケット, multi_bibid, looseleaf, 高価値法律シリーズ}）。
- multi_bibid の実装ゲート開放に要する最小サンプルサイズは open question（§11）。

## 9. 計測の焦点（実測スナップショット反映）

cohort-A(self_scan) は実測で **ISBN保有の92%(4,976/5,397)が既に ndl_bib_id 解決済み**。ただし監査 must_fix #1 により
これは **candidate 扱い**で、版粒度の正しさは未検証。よって本ドライランの focus は:
- 既存 ndl_bib_id の **版粒度QA**（candidate_single が本当に版で正しいか抜き取り検証）。
- 穴 **421（ISBN有NDL無）** と **1,101（両方無）** の内訳推定と例外レーン仕分け。

## 10. runbook の no-write 保証（監査 must_fix #5）

ドライラン実行手順は以下を**保証**する（破る操作は手順に含めない）:
- canonical 化なし / count 表生成なし / promote なし / backfill なし / source（raw）改変なし / DDL なし。
- 出力は artifacts/ への append-only のみ。NDL へは read-only アクセスのみ。

## 11. リスクと未確定（open questions）

- legallib/LION metadata が NDL/出版社由来の場合の「独立証拠」判定（循環依存）。
- 加除式の検出がタイトル語だけで足りるか、出版社/シリーズ heuristic が要るか。
- multi_bibid QA の実装ゲート開放に要する最小サンプルサイズ。
- NDL API のレート/カバレッジ。既存キャッシュで足りない範囲は計測対象を明示限定。

## 12. 次手

1. 本 v0.2 を監査レーンへ（v0.1 RESULT の must_fix 反映確認）。
2. cohort-A(self_scan) のみ先行ドライラン（v0.2 確定後）。LION BOLT は投入後合流。
3. legallib は cohort-B として到着後に別計測 → 合算は再集計。
