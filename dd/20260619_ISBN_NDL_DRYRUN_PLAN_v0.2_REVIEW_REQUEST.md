---
request_id: 20260619_ISBN_NDL_DRYRUN_PLAN_v0.2
decision_id: ISBN→NDL read-only ドライラン計画 v0.2（v0.1 監査 must_fix 反映確認）
request_type: 設計監査 再確認 (DESIGN gate / must_fix reflection check)
topic: ISBN-bearing route dry-run plan, v0.1 must_fix 5件の反映確認
作成日: 2026-06-19
監査対象: dd/ISBN_NDL_DRYRUN_PLAN_v0.2_20260619.md（本依頼に要点同梱・§3）
source_hash: sha256:f65916cd80e486a223cbf9fb9d9fd7ba51e8f7dba3753cba396baff98d62aba6
source_commit: 3305a56 (branch claude/book-identification-progress-7yjxpc)
親監査: 20260618_ISBN_NDL_DRYRUN_PLAN_v0.1_GPTPRO_AUDIT_RESULT（DESIGN_PASS_WITH_NOTES / read-only GO after must_fix wording）
関連: DB実測スナップショット監査 20260619_DB-OBSERVED-SNAPSHOT_litid（投函済・RESULT待ち）
result_expected_filename: 20260619_ISBN_NDL_DRYRUN_PLAN_v0.2_RESULT.md
status: queued
gate: DESIGN。**read-only dry-run の文言確定のみ。実装/DB書込/backfill/promote/serving は HOLD 据置。**
---

# GPT Pro お目付け役 監査依頼: ISBN→NDL ドライラン計画 v0.2（must_fix 反映確認）

## 0. 趣旨

v0.1 監査で **DESIGN_PASS_WITH_NOTES（read-only は must_fix 反映後 GO）** をいただいた。
本 v0.2 は must_fix 5件を畳み込んだもの。**反映が十分か、過不足がないか**の再確認を依頼する。
迎合不要。文言が骨抜きになっていないか、定義が抜け穴を残していないかを厳しく見てほしい。

## 1. v0.1 RESULT must_fix と v0.2 反映の対応

| # | must_fix | v0.2 反映 | 箇所 |
|---|---|---|---|
| 1 | `resolved_single` は版確定でない | **`candidate_single_bibid` に改名**・confirmed と分離明記 | §3, §6, §9 |
| 2 | 「2独立証拠」の定義 | **異なるソース系**（colophon OCR/NDL/出版社/legallib/LION）。**同一NDLレコード内の複数フィールドは1証拠** | §3-bis |
| 3 | `no_hit` の切り分け | `no_hit_after_valid_isbn` / `_low_confidence_isbn` / `isbn_source_untrusted` の3バケット | §4 |
| 4 | route cohort / 外挿禁止 | cohort-A(self_scan) / A'(LION 未投入) / B(legallib 未着)。**cohort-A率を legallibへ外挿禁止** | §1-bis |
| 5 | no-write 保証 | canonical/count/promote/backfill/source改変/DDL なし、artifacts append-only | §10 |

## 2. should_fix の取り込み（参考）

- 例外レーン増設: `metadata_conflict` / `looseleaf_or_supplement_series` / `isbn_reused_or_suspicious`（§4）。
- 実装ゲート移行の閾値（§7-bis）。QAサンプル設計（§8）。NDL resolver版の記録（§3）。各行に raw row id / route-local id（§2）。

## 3. v0.2 要点（全文は source_hash の現物）

- waterfall: ISBN完全一致 → `candidate_single_bibid` / `multi_bibid` / `no_hit`(3バケット)。
  候補が出ても §3-bis の2独立証拠を満たすまで confirm しない。
- 実測反映（§9）: cohort-A(self_scan) は ISBN保有の92%が既に ndl_bib_id 解決済だが **candidate 扱い**。
  focus = 既存 ndl_bib_id の**版粒度QA** ＋ 穴 421(ISBN有NDL無)/1,101(両方無) の仕分け。
- 出力は cohort別、artifacts/ への append-only のみ。

## 4. 特に確認してほしい点

1. **must_fix #1 の徹底**: `candidate_single_bibid` 改名だけで「版確定でない」が運用上守られるか。
   既存 ndl_bib_id（92%）を candidate として再評価する設計で、誤って confirmed 扱いに滑らない歯止めは十分か。
2. **must_fix #2 の抜け穴**: 「異なるソース系」定義で、legallib/LION メタが NDL/出版社由来のとき
   独立性を origin で判定する方針（§11 open question）で足りるか。content_hash 一致等の併用要否。
3. **cohort 運用**: LION BOLT も実測で**未投入**だったため、当面 cohort-A は self_scan 単独。
   この現実（3ルートのうち実在1）で先行ドライランして、後合流時のバイアス管理は §1-bis/§12 で足りるか。
4. **実装ゲート閾値（§7-bis）**: 値は cohort-A 実測で較正＝決め打ちしない方針だが、閾値の「種類」に漏れはないか。

## 5. 期待する判定

`DESIGN_PASS`（v0.2 で must_fix 充足・read-only 実行可） / `DESIGN_PASS_WITH_NOTES` / `MODIFY_REQUIRED` / `HOLD`

## 6. 返答フォーマット

```text
status:
verdict_summary:
must_fix_reflection_check:
- #1 candidate_single_bibid:
- #2 independent evidence定義:
- #3 no_hit分割:
- #4 cohort/外挿禁止:
- #5 no-write保証:
remaining_gaps:
- candidate再評価の歯止め:
- 独立性判定(origin)の十分性:
- cohort-A単独先行のバイアス管理:
- 実装ゲート閾値の漏れ:
must_fix:
should_fix:
read_only_execution: (GO / HOLD)
implementation_gate:
final_gate:
```

## 7. 監査上の注意

本件は read-only dry-run の文言確定のみ。実装/DDL/DB書込/backfill/本番突合/promote/serving/embedding/外部公開は許可しない。

## 8. banto 自己申告

- v0.2 は branch claude/book-identification-progress-7yjxpc にコミット済（3305a56）、PR #24 反映。
- 関連の DB実測スナップショット監査（20260619_DB-OBSERVED-SNAPSHOT_litid）は投函済・RESULT 未着。
  本 v0.2 の §9（実測反映）はその観測に依拠しており、スナップショット監査の所見次第で §9 を追補する可能性。
- 未実施: 既存 ndl_bib_id の版粒度QA 実行、穴(421/1,101)の内訳推定。いずれも v0.2 確定後の read-only 実行段。
