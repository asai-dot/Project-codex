# post-return-verdict — 501 帰り後の GO/CONDITIONAL/NO-GO 判定ハーネス

GPT Pro 監査レーン (`alo-gpt-audit`) の**帰り便**が回り、ビルド/監査 run（本ツールでは
総称して **"501"**）が `summary.md` と `metrics.json` を返したら、**上から走らせる**
「戻り後の処理計画」チェックリストを実体化した依存ゼロ CLI。

> **このツールは owner-gated 操作を一切実行しない。** GO になっても DDL 適用・backfill・
> 本番 DB 投入はしない。GO 時に出すのは *DDL/backfill 計画の草案 (draft)* だけで、適用は
> Owner ratify / 所定 T2 ゲートを経る（`tools/gpt_audit/RUNBOOK_macCC.md` §6）。

## 走らせ方

```bash
ALO=tools/post_return/post_return_verdict.py
python3 $ALO --metrics path/to/metrics.json --summary path/to/summary.md   # 判定を出す
python3 $ALO --metrics path/to/metrics.json --json                         # JSON で出す
python3 $ALO --metrics path/to/metrics.json --emit-plan                    # GO なら DDL/backfill 草案
```

exit code: **GO=0 / CONDITIONAL=1 / NO-GO=2**（CI ゲートに使える）。

## 7 ゲート → 12 項目（上から走らせるチェックリスト）

| # | ゲート | チェック項目 | 種別 | metrics.json キー |
|---|---|---|---|---|
| 1 | G1 接地100% | grounded == total（接地率 100%） | **hard** | `grounding.total / grounded` |
| 2 | G1 接地100% | 未接地 ID 列挙が空 | **hard** | `grounding.ungrounded_ids` |
| 3 | G2 false-merge≈0 | false-merge 0 件 / rate==0 | **hard** | `false_merge.rate / false_merges` |
| 4 | G2 false-merge≈0 | サンプル数が下限以上（≈0 を主張できる） | soft | `false_merge.sampled` |
| 5 | G3 provenance二重計上防止 | 二重計上 ID 列挙が空 | **hard** | `provenance.double_counted_ids` |
| 6 | G3 provenance二重計上防止 | distinct ≤ sources（水増しなし） | soft | `provenance.sources / distinct_sources` |
| 7 | G4 決定性 | 再走ハッシュ一致 | **hard** | `determinism.run_a_hash / run_b_hash` |
| 8 | G4 決定性 | 再走が2回実行された（両ハッシュ存在） | **hard** | `determinism.run_a_hash / run_b_hash` |
| 9 | G5 rights | 権利ブロック 0 件 | **hard** | `rights.blocked_ids` |
| 10 | G5 rights | 権利評価カバレッジ完全 | **hard** | `rights.items / cleared` |
| 11 | G6 work遅延 | actual ≤ budget かつ SLA 違反なし | soft | `work_delay.budget_min / actual_min / sla_breaches` |
| 12 | G7 HOLD | HOLD フラグ無し | **hard** | `hold.flags` |

## verdict 規則（決定的）

- **NO-GO** — ハードゲート（G1 G2 G3 G4 G5 G7）のいずれかが FAIL。→ 再ビルド/再監査で 501 を返し直す。DDL/backfill は**起票しない**。
- **CONDITIONAL** — ハードゲート全通過だが、ソフト項目（G6 work遅延 / サンプル下限 / provenance 注記要）が WARN。→ ソフトを解消するか Owner が条件付き許可するまで GO にしない。
- **GO** — 12 項目すべて PASS。→ 次成果物として **DDL/backfill 計画草案**を出力できる（適用は owner-gated）。

## fail-closed（安全側の既定）

- 必須メトリクスが**欠落／壊れている**と、その項目は FAIL 扱い。判定不能を GO にしない。
- `grounding.total==0` や `rights.items==0` など「対象が空」も FAIL（≈ 何も検証していない）。
- 同じ `metrics.json` → 同じ verdict（決定性。`reasons` まで一致）。

## metrics.json 契約（501 ビルド側が満たすべき形）

```json
{
  "run_id": "501",
  "grounding":   { "total": 1240, "grounded": 1240, "ungrounded_ids": [] },
  "false_merge": { "sampled": 400, "false_merges": 0, "rate": 0.0 },
  "provenance":  { "sources": 1240, "distinct_sources": 1240, "double_counted_ids": [] },
  "determinism": { "run_a_hash": "sha256:…", "run_b_hash": "sha256:…" },
  "rights":      { "items": 1240, "cleared": 1240, "blocked_ids": [] },
  "work_delay":  { "budget_min": 90, "actual_min": 72, "sla_breaches": [] },
  "hold":        { "flags": [] }
}
```

サンプル一式は `samples/`（GO / CONDITIONAL / NO-GO の3パターン + `summary.md`）。

## テスト

```bash
python3 -m unittest discover -s tools/post_return/tests -v
```

## 成果物

`artifacts/POST_RETURN_demo_501.txt` — GO / CONDITIONAL / NO-GO / `--emit-plan` の実行例。

## alo-gpt-audit との接続

```
Owner「監査を回して」
  → alo-gpt-audit close-all --apply        # 帰り便（退避/台帳/振分け・承認不要）
  → 501 ビルドが summary.md + metrics.json を返す
  → post-return-verdict --metrics metrics.json     ← ここ（上から12項目）
      ├ NO-GO       : 再ビルド/再監査。DDL/backfill 起票せず。
      ├ CONDITIONAL : ソフト解消 or Owner 条件付き許可待ち。
      └ GO          : --emit-plan で DDL/backfill 草案 → Owner ratify / T2 ゲートへ
```
