# DD-LITID WS-Q — 評価プラン & ゲート表 v0.1（Q3/Q4/Q5）

- 作成日: 2026-06-20
- 位置づけ: FORWARD_ROADMAP v0.3 WS-Q の Q3(confusion buckets)/Q4(数値 sample plan)/Q5(decision table)。
- 監査根拠: v0.3 RESULT residual_gaps #1(Q4数値化)/#2(Q5実体化)、must_fix #7/#9。
- read-only 設計のみ。**A1 較正実行・閾値 freeze・promote は HOLD**（本表は「型と初期値の置き場」。値は cohort-A 実測で較正）。

## Q3. confusion buckets（誤りの型）

| bucket | 定義 | 重大度 |
|---|---|---|
| `false_merge_work` | 別 work を同一 work に統合 | 致命（hard veto） |
| `false_merge_edition` | 別 edition/manifestation を同一に統合 | 致命（hard veto） |
| `false_split` | 同一を別物に分割 | 高 |
| `same_work_diff_edition` | work は同じだが edition を取り違え | 高 |
| `printing_only_diff` | 版同じ・刷だけ違うのを別版扱い | 中（A3 刷混入が主因） |
| `metadata_noise` | 表記揺れ由来の誤判定 | 中 |
| `abstain_correct` | 正しく保留した | 望ましい |

## Q4. 数値 sample plan（A1 開始前に固定する別 artifact の雛形）

> 監査: 「この artifact なしに A1 合否判定・閾値 freeze・cohort 外挿をしてはならない」。
> 91件は探索用（誤り0でも rule-of-three で 95%上限 ≈ 3/91 ≈ 3.3%）。不可逆 promote の証明には不足。

```text
sampling_frame_snapshot_id : <DB+dump snapshot 固定>
strata:
  - edition_present / edition_absent
  - revision_words (改訂/新版/n訂)
  - printing_pollution (刷が edition 欄に混入)
  - same_isbn_multi_bibid
  - publisher_variant (表記揺れ)
  - old_or_reprint (旧版/復刻/合冊/分冊)
  - serial_or_supplement (年刊/追録/シリーズ)
  - isbn_source_trust (trusted / low_conf / untrusted)
  - ndl_hit_class (single / multi / no_hit / metadata_conflict)
  - freshness (pub_year >= dump_snapshot_year)
allocation_rule        : random + critical strata 上乗せ
minimum_n_total        : TODO(較正前に固定)
minimum_n_per_critical_stratum : TODO（false_merge 系 stratum は厚く）
controls               : positive / negative / conflict コントロールを各 stratum に
reviewer_count         : >=2、不一致は adjudication protocol(Q1)で解決
metric_denominator     : 各 metric 明示
one_sided_confidence_bound : 95% 上側（誤確認率の上限で判定）
hard_veto_threshold    : false_merge_* は上側上限 < X%（X=TODO・厳しめ）
abstention_treatment   : abstain は誤りに数えず manual_review backlog で監視
stopping_rule          : 連続合格 or n 到達で停止
```

## Q5. decision gate table（cohort × decision_type × evidence_profile）

**default = DENY**（明示合格のみ promote 候補。本段は全て HOLD で「表の型」を置く）。

| route_cohort | decision_type | evidence_profile（必要条件） | gate 規則（型・値はTODO） | 既定 |
|---|---|---|---|---|
| cohort-A (self_scan) | work | ISBN一致 + 1独立証拠 | 上側上限<θ_work で pass | deny |
| cohort-A | edition_manifestation | **異 origin_family 独立証拠≥2**（NDL候補＋奥付/現物） | false_merge_edition hard veto | deny |
| cohort-A | printing | 刷は版同定で無視（同版扱い）/ 別管理 | 版へ昇格しない | n/a |
| cohort-A | holding_to_edition | edition 確定後に holding を着地 | edition gate 通過が前提 | deny |
| bencom (remediation) | edition_manifestation | medium775=existing_unconfirmed。family collapse 後の独立2証拠 | sample合格でも全件confirm禁止 | deny/quarantine |
| cohort-A' (LION) / cohort-B (legallib) | all | field-profile 完了まで provisional | cohort-A 閾値を継承しない | deny(provisional) |

各セル共通の必須列（gate contract）:
```text
denominator / minimum_n / point_estimate / one_sided_upper_bound /
hard_veto|soft_target / abstention_rate / manual_review_queue_rate_and_capacity /
default_action(deny) / owner / rollback_condition / decision_version
```

### rollback / supersede（監査 #9）
- confirmed は versioned evidence を持ち、**再評価は supersede/revoke イベント（D0）**で。silent mutation 禁止。
- snapshot/ルール変更時は影響 link を `re_evaluated` で洗い替え。

## 監視 metric（freeze 対象外・常時観測）
source-untrusted率 / family collapse 後の独立証拠数分布 / false_merge・false_split・printing_only 別件数 /
abstention backlog / snapshot 変更後の再評価率 / **freshness no-hit率（2024+ 新刊）**。

## HOLD
本表に基づく実 promote・DB write・閾値 freeze・A1 合否確定は別 gate。現段は型と既定値の定義のみ。
