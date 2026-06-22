# DD-LITID WS-Q — 評価プラン & ゲート表 v0.2（Q3/Q4/Q5）

- 作成日: 2026-06-22（v0.1 から改訂）
- 改訂理由: cohort-A DB 実測値（2026-06-22 snapshot）で Q4 minimum_n / CI を計算。
  Q5 gate matrix に cohort-A / bencom 行の実測値を充填。
- 監査根拠: v0.3 RESULT residual_gaps #1(Q4数値化)/#2(Q5実体化)、must_fix #7/#9。
- read-only 設計のみ。**A1 較正実行・閾値 freeze・promote は HOLD**。

---

## Q3. confusion buckets（不変）

| bucket | 定義 | 重大度 |
|---|---|---|
| `false_merge_work` | 別 work を同一 work に統合 | 致命（hard veto） |
| `false_merge_edition` | 別 edition/manifestation を同一に統合 | 致命（hard veto） |
| `false_split` | 同一を別物に分割 | 高 |
| `same_work_diff_edition` | work は同じだが edition を取り違え | 高 |
| `printing_only_diff` | 版同じ・刷だけ違うのを別版扱い | 中（A3 刷混入が主因）|
| `metadata_noise` | 表記揺れ由来の誤判定 | 中 |
| `abstain_correct` | 正しく保留した | 望ましい |

---

## Q4. 数値 sample plan（v0.2 — cohort-A 実測値で充填）

### 4-1. 母集団（cohort-A snapshot 2026-06-22）

| stratum | N（実測） | 備考 |
|---|---|---|
| TOTAL cohort-A | 6,524 | source=asai-bookshelf |
| isbn_yes + ndl_hit | 4,976 | **主 sampling frame** |
| isbn_yes + ndl_no | 421 | A2 対象 |
| isbn_no + ndl_hit | 26 | identity hazard、全件審査 |
| isbn_no + ndl_no | 1,101 | manual bib_id、title-match lane |
| edition_present | 424 | （うち ndl_hit=376） |
| printing_polluted | 51 | edition_present と完全一致（51/424=12%） |
| revision_yes | 493 | 改訂語あり |
| fresh_2024plus | 1,061 | pub_year≥2024（全体; 421 no-hit 内は53件確認済み）|
| manual_bib_id | 1,771 | alo:book:manual:* prefix |

### 4-2. sampling_frame の確定

```
sampling_frame_snapshot_id : bib_records_20260622
primary_frame              : isbn_yes + ndl_hit (N=4,976)
                             = A1 candidate 評価の主対象
secondary_frame_A2         : isbn_yes + ndl_no (N=421)
                             = freshness_miss vs. true_no_hit 分類
secondary_frame_B          : isbn_no + ndl_no (N=1,101) ← B1 title-match lane
audit_frame                : isbn_no + ndl_hit (N=26) ← 全件 identity 審査
```

### 4-3. strata 別 minimum_n とサンプリング規則

**閾値設計前提**:
- hard veto（false_merge_* 上側限界）: 95% 上側 < **2%**
  → rule-of-three（0件観測時）: n ≥ ceil(3/0.02) = **150**
  → 安全マージンで **n=300**（3/300=1.0%上限）
- soft target（precision ≥ 95% 上側 < 5%）: n ≥ ceil(3/0.05) = **60**
- 全件審査: N≤30 の stratum は全件（26件 isbn_no+ndl_hit）

| stratum | N | 推奨 n | 根拠 | 優先度 |
|---|---|---|---|---|
| isbn_yes+ndl_hit（主 random） | 4,976 | **300** | false_merge hard veto（3/300=1.0%） | ★★★ |
| printing_polluted（全件） | 51 | **51** | 全件必須（12%混入の実害源） | ★★★ |
| isbn_no+ndl_hit（全件 audit） | 26 | **26** | identity hazard 全件 | ★★★ |
| revision_yes（edition_present 内） | ≈120 | **50** | same_work_diff_edition 検出 | ★★ |
| isbn_yes+ndl_no（A2） | 421 | **全421** | freshness_miss 分類は全件必要 | ★★ |
| isbn_no+ndl_no（B1 lane） | 1,101 | **30** | title-match calibration 初期値 | ★ |

**Round 1 合計 minimum_n: 300 + 51 + 26 + 50 + 30 = 457**
（421件 A2 は分類審査であり adjudication ではない。freshness_miss 53件は別計）

### 4-4. 層化サンプリング実施条件

```text
allocation_rule          : random（主 frame）+ critical strata 上乗せ（printing_polluted 全件）
reviewer_count           : >=2（不一致は adjudication protocol Q1）
metric_denominator       : stratum 別に明示（全体 precision に埋めない）
one_sided_confidence_bound : 95% 上側
hard_veto_threshold      : false_merge_* upper_bound < 2%（n=300, 0件観測で 1.0%）
soft_target              : precision > 95% 上側（n=60, 0件で 5.0%）
abstention_treatment     : abstain は誤りに数えず manual_review backlog
stopping_rule            : 連続合格 or n 到達で停止
controls                 : positive（既知 true-positive）/ negative（既知 different editions）
                           各 stratum に >=3件ずつ埋め込み
isbn_source_trust        : isbn_yes+ndl_hit が sampling frame のため
                           all records are trusted-isbn（checkdigit 検証済み）
ndl_hit_class            : 全件 single（1:1 衝突 0 は Phase 0 で確認済み）
freshness_lane           : pub_year>=2024 の no-hit 53件は freshness_miss として
                           no_hit_after_valid_isbn カウントから除外
```

### 4-5. 投入禁止

- ndl_isbn_index.csv（L1 derived）を gold に使わない（Q2 family collapse）
- candidate 生成に使った同一 NDL レコードを正解ラベルに使わない（非循環 Q1）
- 91件探索サンプル（qa_sample_cohortA_20260619.jsonl）は閾値 freeze・cohort 外挿に使わない

---

## Q5. decision gate table（v0.2 — 実測値で充填）

**default = DENY**（明示合格のみ promote 候補。全実 promote・DB write は HOLD）。

| route_cohort | decision_type | N（実測） | evidence_profile（必要条件） | hard_veto threshold | soft_target | 既定 |
|---|---|---|---|---|---|---|
| cohort-A isbn+ndl（4,976） | work | 4,976 | ISBN一致 + 異 origin_family≥1（NDL candidate + 奥付/現物 いずれか） | false_merge_work 上側<2%（n≥150） | precision>95% 上側<5%（n≥60） | deny |
| cohort-A isbn+ndl（4,976） | edition_manifestation | 376（edition_present + ndl_hit） | **異 origin_family≥2**（NDL候補 + 奥付/現物/出版社一次） | false_merge_edition 上側<**2%**（n≥150、推奨n=300） | precision>95%（n≥60） | deny |
| cohort-A printing_polluted（51） | printing | 51 | 版へ昇格しない / 同版扱いで処理 / `printing_no` 列に隔離 | false_merge_edition 禁止 | n/a（刷は版同定で無視） | n/a |
| cohort-A isbn+ndl_no（421） | freshness_miss分離 | 53（2024+） | pub_year≥2024 AND no_hit → `freshness_miss` レーン | false_merge 禁止（分類誤り） | freshness分類精度>95% | freshness_miss（別管理） |
| cohort-A isbn+ndl_no（368残） | true_no_hit | 368 | ライブNDL API or 新 snapshot で確認 | — | — | no_hit（保留） |
| cohort-A isbn_no+ndl_hit（26） | identity_audit | 26 | 全件審査: bib_id↔isbn 不整合6件を含む | false_merge_edition 禁止 | — | quarantine until audit |
| cohort-A isbn_no+ndl_no（1,101） | holding_to_title | 1,101 | B1 title-match lane: match_titles_to_ndl.py 経由 | false_merge_work 上側<2% | precision>95% | deny |
| bencom high（962） | edition_manifestation | 962 | 層化抜き取り sample 後、独立2証拠 | false_merge 上側<2%（n≥150） | — | deny |
| bencom medium（775） | edition_manifestation | 775 | existing_unconfirmed / family collapse 後の独立2証拠 | sample合格でも全件 confirm 禁止 | — | deny/quarantine |
| cohort-A'（LION）/ cohort-B（legallib） | all | 未投入 | field-profile 完了まで provisional | cohort-A 閾値を継承しない | — | deny(provisional) |

各セル共通の必須列（gate contract、値は A1 実測後に充填）:
```text
denominator           : stratum N（上表）
minimum_n             : 上表 推奨 n
point_estimate        : A1実測後
one_sided_upper_bound : A1実測後（現時点 HOLD）
hard_veto             : 上表（false_merge 系は 上側<2%）
soft_target           : precision>95% 上側<5%
abstention_rate       : A1実測後
manual_review_queue_rate_and_capacity : A1実測後
default_action        : deny（全行）
owner                 : TODO(A1開始前に owner 確定）
rollback_condition    : verified の supersede/revoke イベント（D0 §1-1）
decision_version      : rule_version を D0 event に記録
```

### rollback / supersede（不変）
- confirmed は versioned evidence を持ち、再評価は supersede/revoke イベント（D0）で。silent mutation 禁止。
- snapshot/ルール変更時は影響 link を `re_evaluated` で洗い替え。

---

## 監視 metric（freeze 対象外・常時観測）

| metric | cohort-A 現在値 | 目標 |
|---|---|---|
| isbn_source_untrusted率 | 0%（全件 checkdigit valid） | 0% 維持 |
| printing_only_diff 件数 | 51件（12% of edition_present） | 分離後 0 |
| isbn_no+ndl_hit 件数 | 26件 | 全件審査後 quarantine or resolved |
| freshness no-hit率（2024+/421） | 53/421=12.6% | freshness_miss 分離後 再集計 |
| abstention backlog | 0（A1未実施） | A1後に観測 |
| false_merge 観測件数 | 0（A1未実施） | hard veto 基準内 |

---

## HOLD（不変）

本表に基づく実 promote・DB write・閾値 freeze・A1 合否確定は別 gate。
現段は実測値に基づく「型と初期値」の定義のみ。
