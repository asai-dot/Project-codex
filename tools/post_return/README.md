# post-return-verdict — 属性観測層 501 dry-run 帰り後の GO/CONDITIONAL/NO-GO 判定

対象 run **"501" = 「属性観測層 501 report-only dry-run」**（DD-LITID-001-ATTR）。
3サイト共通501冊で属性観測層 v0.2 を**メモリ上だけ**で回す PoC。Mac CC ワーカーが Box
`_claude_dispatch/from_worker/attr_layer_501_dryrun_20260615/` へ `summary.md` /
`metrics.json` / `attr_observations_sim.jsonl` / `attr_canonical_sim.jsonl` /
`disputed_after_triage.csv` を返したら、本ツールが**上から走らせる**「戻り後の処理計画」。

> メトリクス契約は当て推量ではなく実 WO 由来:
> **`WO_attrlayer501_dryrun_20260615_1740.md` §4-§5 + L1 self-verify**（Box gpt_ometsuke 経由で確認）。

> **このツールは owner-gated 操作を一切実行しない。** GO でも biblio/authority 投影・DDL・
> backfill はしない（WO「やらない」厳守）。GO 時に出すのは *投影/DDL/backfill 計画の草案*
> だけで、適用は Owner ratify / T2 ゲートを経る。

## 走らせ方

```bash
ALO=tools/post_return/post_return_verdict.py
# 501 が返ったら Box から metrics.json / summary.md を落として:
python3 $ALO --metrics path/to/metrics.json --summary path/to/summary.md
python3 $ALO --metrics path/to/metrics.json --json            # JSON
python3 $ALO --metrics path/to/metrics.json --emit-plan       # GO なら投影/DDL/backfill 草案
```

exit code: **GO=0 / CONDITIONAL=1 / NO-GO=2**。

## 7 ゲート → 12 項目（上から走らせるチェックリスト）

| # | ゲート | チェック | 種別 | metrics.json キー |
|---|---|---|---|---|
| 1 | G1 接地100% | ungrounded_value_count == 0 | **hard** | `ungrounded_value_count` |
| 2 | G1 接地100% | 501処理・欠損/重複なし | **hard** | `cohort.{processed,missing_ids,duplicate_ids}` |
| 3 | G2 false-merge≈0 | classification が scheme併存・multi で潰れていない | **hard** | `classification_multi_preserved` |
| 4 | G2 false-merge≈0 | disputed率 が triage で生不一致率以下・true_conflict限定 | soft | `disputed_rate_after_triage` / `raw_disagreement_rate` |
| 5 | G3 provenance二重計上防止 | provenance_family 畳みが効く（弁コム×legallib 独立計上せず） | **hard** | `provenance_family_collapse_effective` |
| 6 | G3 provenance二重計上防止 | 畳み発生の証跡（collapse_count > 0） | soft | `provenance_collapse_count` |
| 7 | G4 決定性 | 同一入力2回で出力 hash 一致 | **hard** | `determinism.run_a_hash / run_b_hash` |
| 8 | G4 決定性 | inputs_sha256 証跡あり | **hard** | `determinism.inputs_sha256_present` |
| 9 | G5 rights | rights_profile カバレッジ 100% | **hard** | `rights_profile_coverage` |
| 10 | G5 rights | rights_blocked_rate 閾値内（既定 ≤ 0.20） | soft | `rights_blocked_rate` |
| 11 | G6 work遅延 | 成果物5点 揃い・dry-run 完走・coverage ≥ 0.95 | soft | `deliverables` / `adopted_value_coverage` |
| 12 | G7 HOLD | report-only 厳守: 書込ゼロ + access非混入 + hold_flags 空 | **hard** | `write_evidence` / `access_not_in_biblio_consensus` / `hold_flags` |

## verdict 規則（決定的）

- **NO-GO** — ハードゲート（G1 G2 G3 G4 G5 G7）のいずれか FAIL。→ dry-run やり直して 501 を返し直す。投影/DDL/backfill は**起票しない**。
- **CONDITIONAL** — ハード全通過だが、ソフト（#4 triage / #6 畳み証跡 / #10 rights_blocked / #11 完走・coverage）が WARN。→ 解消 or Owner 条件付き許可待ち。
- **GO** — 12項目すべて PASS。→ `--emit-plan` で **属性層 投影/DDL/backfill 計画草案**（適用は owner-gated）。

## なぜこの 12 項目か（WO との対応）

WO の L1 self-verify「501処理 / ungrounded=0 / 2回流して hash 一致(決定性) / classification
scheme併存multi未潰し / provenance_family畳み有効(弁コム×legallib同一familyを独立計上しない) /
biblio・DB 書込ゼロ証跡 / access系が書誌合議に混入しない」を、あなたの 7 ゲート
（接地100% / false-merge≈0 / provenance二重計上防止 / 決定性 / rights / work遅延 / HOLD）に
1:1 で割り付けた。metrics.json の 6 指標（adopted_value_coverage / single_authority_rate /
disputed_rate_after_triage / rights_blocked_rate / ungrounded_value_count /
provenance_collapse_count）はそのまま閾値判定に使う。

## fail-closed（安全側の既定）

- 必須メトリクス/証跡が**欠落・壊れている**と、その項目は FAIL。判定不能を GO にしない。
- `cohort.processed != 501`・`rights_profile_coverage < 1.0`・書込証跡 > 0 はいずれも止める。
- 同じ `metrics.json` → 同じ verdict（`reasons` まで一致）。

## metrics.json 契約（501 ワーカーが満たすべき形）

サンプル一式は `samples/`（`metrics_GO.json` / `metrics_CONDITIONAL.json` /
`metrics_NOGO.json` + `summary.md`）。GO サンプルが満たすべき最小形:

```json
{
  "cohort": { "expected": 501, "processed": 501, "missing_ids": [], "duplicate_ids": [] },
  "adopted_value_coverage": 0.985,
  "raw_disagreement_rate": 0.18,
  "disputed_rate_after_triage": 0.03,
  "disputed_all_true_conflict": true,
  "rights_blocked_rate": 0.04,
  "rights_profile_coverage": 1.0,
  "ungrounded_value_count": 0,
  "provenance_collapse_count": 137,
  "provenance_family_collapse_effective": true,
  "classification_multi_preserved": true,
  "access_not_in_biblio_consensus": true,
  "determinism": { "run_a_hash": "…", "run_b_hash": "…", "inputs_sha256_present": true },
  "deliverables": { "attr_observations_sim.jsonl": true, "attr_canonical_sim.jsonl": true,
                    "disputed_after_triage.csv": true, "metrics.json": true, "summary.md": true },
  "write_evidence": { "db_writes": 0, "ddl": 0, "backfill": 0, "biblio_writes": 0,
                      "scalar_overwrite": 0, "work_rollup": 0, "embedding": 0, "external_sends": 0 },
  "hold_flags": []
}
```

> WO の metrics.json は中核6指標のみを要求している。本ツールは判定に必要な L1 self-verify の
> 証跡（cohort 完全性 / 決定性ハッシュ / classification multi 保持 / family 畳み有効 /
> rights_profile カバレッジ / 書込ゼロ証跡 / access 非混入 / deliverables）を **boolean/数値の
> evidence として metrics.json に同梱する**ことを契約とする。欠ければ fail-closed で FAIL。

## テスト

```bash
python3 -m unittest discover -s tools/post_return/tests -v   # 16 OK
```

## 成果物

`artifacts/POST_RETURN_demo_501.txt` — GO / CONDITIONAL / NO-GO / `--emit-plan` の実行例。

## 現況（2026-06-21 時点・Box 実観測）

- 501 ワーカー（Mac CC）の成果物は **まだ返ってきていない**。
  `_claude_dispatch/from_worker/`・`done/`・`_status/` は空、
  `attr_layer_501_dryrun_20260615/` フォルダ未生成。
- よって本物の verdict は未算定。**判定器は返り次第そのまま走る状態**で用意済み。

## パイプライン上の位置

```
owner GO (2026-06-15) → Mac CC が attr_layer_501 dry-run をメモリ上で実行
  → from_worker/attr_layer_501_dryrun_20260615/ に summary.md + metrics.json を返す
  → post-return-verdict --metrics metrics.json     ← ここ（上から12項目）
      ├ NO-GO       : dry-run やり直し。投影/DDL/backfill 起票せず。
      ├ CONDITIONAL : ソフト解消 or Owner 条件付き許可待ち。
      └ GO          : --emit-plan で投影/DDL/backfill 草案 → Owner ratify / T2 ゲートへ
```
