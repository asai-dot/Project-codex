# 501 帰り便 summary (sample)

- run_id: 501
- generated_at_jst: 2026-06-21
- lane: gpt_ometsuke / from_gpt (RESULT 受領後)
- 目的: ビルド/監査 run 501 の成果を post-return-verdict にかけ、正本化前の GO 判定を得る

> これは post-return-verdict のサンプル入力。実 run では 501 のビルドが summary.md と
> metrics.json を対で出力する。verdict は metrics.json から決定的に計算され、summary.md
> は人間が読む添え状 (記録用) として保存される。

## 12 項目の所在 (どのメトリクスがどのチェックに対応するか)
| ゲート | metrics.json キー | チェック item |
|---|---|---|
| G1 接地100% | grounding.{total,grounded,ungrounded_ids} | 1, 2 |
| G2 false-merge≈0 | false_merge.{rate,false_merges,sampled} | 3, 4 |
| G3 provenance二重計上防止 | provenance.{double_counted_ids,sources,distinct_sources} | 5, 6 |
| G4 決定性 | determinism.{run_a_hash,run_b_hash} | 7, 8 |
| G5 rights | rights.{blocked_ids,items,cleared} | 9, 10 |
| G6 work遅延 | work_delay.{budget_min,actual_min,sla_breaches} | 11 |
| G7 HOLD | hold.flags | 12 |
