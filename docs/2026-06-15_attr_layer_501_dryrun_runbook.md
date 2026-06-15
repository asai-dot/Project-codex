# 属性観測層 501 report-only dry-run runbook（最小attr_registry + 射影シミュレーション）v0.1

- 作成: 2026-06-15 / Claude（リモートセッション・浅井さん指示）
- 親設計: `docs/2026-06-15_dd-litid-001_addendum_attr_observation_layer.md` v0.2（GPT `DESIGN_PASS_WITH_NOTES` / result Box 2286160319588）
- PoC枠: `docs/2026-06-14_poc_thick_501_spec.md` の P3「積層dry-run」を v0.2 設計で具体化したもの。
- 実行主体: **Mac ワーカー**（`identity_candidates.jsonl` と NDL生アーカイブはローカル）。リモートからは本runbookまで。
- **ゲート: report-only。DDL・backfill・biblio書込・scalar上書き・embedding・外部送信は一切しない。** owner ratify 後に実行。

## 0. 目的（このdry-runで何を見るか）

3サイト共通501冊で、属性観測層 v0.2 の **「観測→triage→決定的射影→出所付き採用値」** を**メモリ上だけ**で回し、
(a) 積層効果（採用値カバレッジ）、(b) precision系メトリクス（single_authority率・triage後disputed率）、
(c) anti-hallucination（ungrounded=0）、(d) rights遮断率 を実測する。**スキーマもDBも触らない。**

## 1. 入力（読み取りのみ・ローカル）

| 用途 | パス | 取り出すもの |
|---|---|---|
| コホート501 | `build/newsources_books_identity/20260611/identity_candidates.jsonl` | basis=title_publisher_year かつ members の source 集合 ⊇ {bengo4, lionbolt, legallib} の501クラスタ |
| 書誌staging | `build/newsources_books_identity/20260611/books_staging.jsonl` | 各 source_item の title_norm/publisher_norm/pub_year/page_count/genre/category/field/abstract |
| NDL観測 | `ndl_20260513/ndl_raw.jsonl.gz` → `scripts/ndl_xml_parser_v1.py` | ndl_ndc10 / ndl_ndlc / ndl_subjects / ndl_pages / ndl_publisher（ISBN解決分のみ） |
| 蔵書(access) | bookdx（biblioの asai-bookshelf 由来） | held_by_office / shelf_locator / fulltext_access（自炊PDF有無） |

> ISBN解決: 501の各冊について LION BOLT 実ISBN＋NDL書名突合で ISBN を引き、NDL観測を付す（無ければ NDL観測なしで可）。

## 2. 最小 attr_registry（**501 PoC 必要属性のみ**・過剰一般化しない / 監査next-steps#2）

| attr_key | scheme(s) | cardinality | rollup_scope | fact_class | priority_profile | currency_sensitive |
|---|---|---|---|---|---|---|
| classification | NDC, NDLC, vendor_genre:lionbolt, vendor_category:bencom, vendor_field:legallib | multi | item_only(本dry-run) | bibliographic | ndl>publisher>legallib>bencom>lionbolt | no |
| pub_year | (null) | single | item | bibliographic | ndl>publisher>legallib>bencom>lionbolt | yes |
| page_count | (null) | single | item | bibliographic | ndl>publisher>… | no |
| publisher | (null) | single | item | bibliographic | ndl>publisher>… | no |
| title | (null) | single | item | bibliographic | （sanity用） | no |
| abstract | (null) | single | item | bibliographic | bencom（保有元のみ） | no |
| held_by_office | (null) | single | item | **access** | bookdx | no |
| shelf_locator | (null) | single | item | **access** | bookdx | no |
| fulltext_access | (null) | single | item | **access** | bookdx | no |

- **work rollup は本dry-runでは行わない**（`rollup_status=item_only` 固定。work昇格前ゆえ＝must-fix5/`gate_work_rollup_requires_work_promotion`）。
- access系3つは `fact_class=access`＝**書誌の合議に混ぜない**（rights/serving と分離・should-fix）。
- NDC は pivot にしない＝classification の一 scheme として併存（modify-within-pass）。

### 2.1 attr_policy 初版（dry-runの採用規律）

| attr_key/scheme | single_authority_ok | corroboration_required | human_review_required |
|---|---|---|---|
| classification:NDC / :NDLC | yes（NDL権威） | no | no |
| classification:vendor_* | yes（各値を multi で保持） | no | no |
| pub_year | yes | no（ただし edition_suspected は別item候補） | no |
| page_count | yes | no（definition_difference_allowed） | no |
| publisher | yes | no（表記揺れは triage） | no |
| abstract | yes（bencom単独） | no | no |
| access系 | yes（bookdx単独） | no | no |

## 3. 射影シミュレーション（メモリ上・決定的・**書込なし**）

```
for each of 501 clusters:
  1. 観測生成(in-memory): 各 source_item の各 attr を attr_observation 形に展開
       {item_tmp_id, attr_key, attr_scheme, value_raw, value_norm, norm_rule,
        source_system, provenance_group, provenance_family(+grouping_confidence),
        observed_at, fetched_at, medium_origin, ocr_accuracy_rank, rights_profile, source_locator}
     ※ DBには書かない。jsonl 出力のみ。
  2. provenance_family 畳み: 弁コム/legallib/publisher由来で同一 family と判定される観測は
       高リスク属性で独立計上しない（grouping_confidence 付きで記録）。
  3. triage（§addendum 3.5）: value_norm 差を
       equivalent_after_normalization | definition_difference_allowed | edition_suspected | true_conflict | needs_owner_policy に分類。
  4. 採用(adopted_status): single は priority_profile→recency で1値。
       true_conflict→disputed / needs_policy→unresolved / それ以外→corroborated|single_authority。
       multi(classification)は値を捨てず各値を採用値化、rollup_status=item_only。
  5. 接地: 各採用値に contributor_obs(obs_id列) と rights_profile と norm_rule を必須付与。
```

- **再現性**: 同一入力を2回流して出力 hash 一致を確認（`gate_attr_projection_deterministic` のdry-run版）。

## 4. 出力（`build/attr_layer_501_dryrun/` に report-only。biblioには入れない）

- `attr_observations_sim.jsonl` … 展開した観測（生事実保全の確認用）
- `attr_canonical_sim.jsonl` … 採用値＋adopted_status＋contributor_obs＋rights_profile＋rollup_status
- `disputed_after_triage.csv` … true_conflict のみ（人手review見本。triageで吸収された差は別表）
- `metrics.json` … §5
- `summary.md` … 数行サマリ＋再現hash

## 5. メトリクス（監査should-fix）

| 指標 | 定義 |
|---|---|
| adopted_value_coverage | 501×attr_key のうち採用値が付いたセルの割合 |
| single_authority_rate | 採用値のうち adopted_status=single_authority の割合 |
| disputed_rate_after_triage | triage後に true_conflict→disputed となった割合（**triage前の生不一致率と対比**） |
| rights_blocked_rate | serving可否で rights により遮断される採用値の割合 |
| ungrounded_value_count | contributor_obs が空の採用値数（**0であるべき**＝anti-hallucination） |
| provenance_collapse_count | provenance_family 畳みで独立計上から外した観測数（二重計上回避の効き） |

## 6. L1 self-verify（全部通れば dry-run PASS）

1. 501クラスタを処理（欠損・重複を列挙）。
2. `ungrounded_value_count == 0`。
3. 同一入力2回で出力 hash 一致（決定性）。
4. classification が scheme 併存・multi で保持（NDC/NDLC/vendor が潰れていない）。
5. provenance_family 畳みが効いている（弁コム×legallib 同一family を独立計上していない）。
6. **biblio/DBに一切書いていない・DDLを発行していない**（書込ゼロの証跡）。
7. access系(held_by_office等)が書誌合議に混入していない（fact_class分離）。

## 7. やらないこと（ゲート明示）

DDL／biblio書込／scalar上書き／backfill／canonical promotion／work rollup／embedding／外部送信 ── **一切しない**。
本dry-runは「設計v0.2が501で破綻なく回り、metricsが想定内か」を**紙の上＝メモリ上**で確認するだけ。
結果を見て owner ratify → 別途 DDL/backfill 計画（監査next-steps#5）。

## 8. handoff
- 実行: Mac ワーカー（ローカル資産保有インスタンス）。
- 報告: `build/attr_layer_501_dryrun/summary.md` ＋ Box `_inventory/` か `from_worker/` に要約。
- 本runbookの正本: 本リポジトリ（doc）。構造化産物は build/Box（GitHubに置かない）。
