# 属性観測層 501 dry-run summary (sample)

- run_id: attr_layer_501_dryrun_20260615
- WO: WO_attrlayer501_dryrun_20260615_1740.md（report-only / DB write・DDL・backfill 一切なし）
- 戻り先: Box `_claude_dispatch/from_worker/attr_layer_501_dryrun_20260615/`
- 目的: 3サイト共通501冊で属性観測層 v0.2 をメモリ上だけで回し、設計破綻なしと metrics を実測

> これは post-return-verdict のサンプル入力。実 run では Mac CC ワーカーが summary.md と
> metrics.json を対で返す。verdict は metrics.json から決定的に計算する。

## 12 項目の所在（どのメトリクスがどのチェックに対応するか）
| ゲート | metrics.json キー | チェック item |
|---|---|---|
| G1 接地100% | ungrounded_value_count / cohort.{processed,missing_ids,duplicate_ids} | 1, 2 |
| G2 false-merge≈0 | classification_multi_preserved / disputed_rate_after_triage(+raw) | 3, 4 |
| G3 provenance二重計上防止 | provenance_family_collapse_effective / provenance_collapse_count | 5, 6 |
| G4 決定性 | determinism.{run_a_hash,run_b_hash,inputs_sha256_present} | 7, 8 |
| G5 rights | rights_profile_coverage / rights_blocked_rate | 9, 10 |
| G6 work遅延 | deliverables / adopted_value_coverage | 11 |
| G7 HOLD | write_evidence / access_not_in_biblio_consensus / hold_flags | 12 |

## 再現性
- 同一入力を 2 回流して出力 hash 一致（determinism.run_a_hash == run_b_hash）。
- inputs_sha256.txt を同梱（入力固定の証跡）。
