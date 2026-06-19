# silver-1 掲載位置→source-record 候補レポート (dry-run / read-only)

> SILVER-RESOLUTION-KICKOFF v0.1.1 整合. 出力は未レビュー候補. reviewed/canonical 化なし.
> authority_dataset_version: periodical_20260611_demo

- 入力エッジ総数: **7**
- machine_suggested (tier A+B, 未レビュー): **2** (28.6%)  ※基準 概算24%
  - A 単一exact: **1** / B alias要高密度QA: **1**
- needs_human_review (C): **2**
- ambiguous_or_unresolved (D): **3**
- blocked_by_policy_or_provenance (X): **0**

## evidence_tier 別
| tier | 件数 |
|---|---|
| A | 1 |
| B | 1 |
| C | 2 |
| D | 3 |

## blocker_code
| code | 件数 |
|---|---|
| insufficient_signal | 1 |
| index_absent | 1 |

## 監査整合の確認
- 解決先は source-record URI (d1hanrei:) = canonical case ではない (identity_scope).
- tier A/B も未レビュー候補. reviewed=true / claim_support / alo_edges に昇格しない.
- 非選択 sibling は target に保存し non_selection_reason 付与 (畳まない).
- authority_snapshot 無しは全行 blocked (gate8).

_dry-run. candidate staging 出力のみ. 本番 write なし. 商用本文は出力しない._