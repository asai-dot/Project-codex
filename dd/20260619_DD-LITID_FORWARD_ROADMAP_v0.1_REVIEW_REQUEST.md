---
request_id: 20260619_DD-LITID_FORWARD_ROADMAP_v0.1
decision_id: DD-LITID 4ルート書籍同定の今後方針（フォワード・ロードマップ）
request_type: 方針監査 (ROADMAP / direction gate)
topic: 実測+Phase0+2監査を踏まえた go-forward 計画、WS分割・順序・ブロッカー
作成日: 2026-06-19
監査対象: dd/DD-LITID_FORWARD_ROADMAP_v0.1_20260619.md（本依頼に要点同梱・§3）
source_hash: sha256:29612d078f1e25a4ea1a9664659927410b9d82a5daf162c6de746700182e9402
source_commit: 7b40480 (branch claude/book-identification-progress-7yjxpc)
親監査: DD-LITID-PLAN v0.1（DESIGN_PASS_WITH_NOTES）/ ISBN_NDL_DRYRUN_PLAN v0.2 RESULT / DB-OBSERVED-SNAPSHOT RESULT
result_expected_filename: 20260619_DD-LITID_FORWARD_ROADMAP_v0.1_RESULT.md
status: queued
gate: ROADMAP。**方針・WS分割・順序・ゲートの妥当性のみ。実装/DDL/backfill/promote は HOLD 据置。**
---

# GPT Pro お目付け役 監査依頼: DD-LITID フォワード・ロードマップ v0.1

## 0. 独立監査の要請（迎合不要）

実測（DB snapshot）・Phase 0 QA・2監査 RESULT を踏まえ、4ルート書籍同定の今後方針をまとめた。
**結論ありきの追認は不要。** WS分割・順序・ブロッカー認定・ゲート閾値の置き方を厳しく疑ってほしい。
特に「クリティカルパス＝NDLアクセス runner」という因果認定が正しいか、優先順位が実価値と合っているかを見てほしい。

## 1. 確定した現実（根拠つき）

- bib_records 実在は self/own(6,524) と bencom(3,802) のみ。**LION BOLT/legallib 未投入**（snapshot）。
- self/own は ISBN↔NDL が**厳密1:1・衝突0**だが `edition`7.6%/`volume`0% で **版正誤は内部判定不能**（Phase 0）。
- 弁コム突合は既存1,737（high962/medium775）。ISBN provenance 不一致6件（Phase 0）。
- **NDL外部照合は現実行環境から不可**（要 runner）。

## 2. 方針の骨子（全文は source_hash の現物）

- WS-A 自所版同定（A0✅→A1外部照合→A2穴埋め421/1,101→A3 edition正規化→A4 provenance6件）
- WS-B 弁コム既存shadow遡及（medium775=existing_unconfirmed の第2独立証拠検証 / high962 抜き取り）
- WS-C 未投入ルート取り込み（LION BOLT=cohort-A' / legallib=cohort-B、外挿禁止）
- WS-D NDLハブ+マッチング基盤（設計先行、A1/B1実測で較正）
- WS-E identity/edition promote（**HOLD**、閾値充足後ゲート）
- クリティカルパス: **NDLアクセス runner の確定**（§6 owner決定）。ここが律速。

## 3. 特に厳しく監査してほしい点

1. **クリティカルパス認定**: 「版品質は外部照合律速 → 最初に解くべきは runner 確定」は妥当か。
   それとも runner非依存で価値が出る WS（A3 edition正規化 / B1 設計 / A2属性集計）を先に厚くすべきか。
2. **WS分割の過不足**: A〜E の粒度は適切か。統合/分割すべき箇所、欠落 WS（例: 著者名寄せ・DD-PERIODICAL接続）はないか。
3. **順序の load-bearing 依存**: §3 依存グラフで、shadow実証前 promote 禁止は守れているか。
   cohort-C 着地待ちを理由に A/B が停滞しない設計になっているか。
4. **medium775 の位置づけ**: 「既存だが existing_unconfirmed」を本線 WS-B に入れた判断は正しいか、
   それとも別レーン据置が筋か。遡及検証で confirmed 化する場合のリスク。
5. **閾値の置き方(§5)**: 種類先決め・値は実測較正、で実装ゲート判断に足りるか。危険な抜けは。
6. **runner 選択肢(§6)**: (a)Mac local / (b)ネット許可env / (c)既存キャッシュ先行 のどれを推すか。
   (c)で先行する場合のバイアス（キャッシュ収載済みに偏る）の扱い。
7. **スコープ境界**: 記事/文献層を DD-PERIODICAL に切る判断、bengo4新規生成を本線外にしつつ既存遡及だけ本線に入れる判断の整合。

## 4. 期待する判定

`ROADMAP_PASS` / `ROADMAP_PASS_WITH_NOTES` / `MODIFY_REQUIRED` / `HOLD`

## 5. 返答フォーマット

```text
status:
verdict_summary:
critical_path_check: (runner律速の認定は妥当か)
workstream_review:
- WS-A 自所:
- WS-B 弁コム既存:
- WS-C 未投入取り込み:
- WS-D NDLハブ基盤:
- WS-E promote(HOLD):
sequencing_and_dependencies:
medium775_treatment:
threshold_design:
runner_recommendation: (a/b/c)
scope_boundary:
missing_workstreams:
must_fix:
should_fix:
recommended_next_sprint:
final_gate:
```

## 6. 監査上の注意

本件は方針・順序・ゲートの設計可否のみ。実装/DDL/DB書込/backfill/本番突合/promote/serving/embedding/外部公開は許可しない。

## 7. banto 自己申告

- ロードマップは branch claude/book-identification-progress-7yjxpc にコミット済（7b40480）、PR #24 反映。
- Phase 0 成果物（PHASE0_existing_ndl_quality_QA_cohortA / qa_sample_cohortA 91行）が根拠。read-only・DB無変更。
- 未実施: 外部照合(A1)、421/1,101の属性集計、edition棚卸し、B遡及検証。runner決定待ち・read-onlyで順次。
- 既知の不確実: LION BOLT/legallib 実メタ形状未確認、独立性判定の十分性（origin単独か content_hash併用か）。
