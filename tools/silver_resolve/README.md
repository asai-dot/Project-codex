# silver_resolve — 語彙オブジェクト ボトルネック解消 P0 ツール

語彙オブジェクト (Meaning Backbone) の現ボトルネック = **意味付き citation の在庫が実測ゼロ
(関係層が raw のまま silver 未到達)** を解くための、P0 (read-only dry-run) ツール一式。

> 背景: `design/vocab_bottleneck/00_SILVER_RESOLUTION_BACKGROUND_20260618.md`
> 計画: `design/vocab_bottleneck/01_BOTTLENECK_RESOLUTION_PLAN_20260618.md`
> WO:   `design/vocab_bottleneck/WO-SILVER-CITEID-001_draft_20260618.md` ほか

## これは何か

claim_support 在庫を立ち上げるクリティカルパスは、**既取得データだけで回る silver 解決**である。
本ツールはその dry-run を、依存ゼロ (Python 3.9+)・read-only で実行する。

| ツール | WO | 役割 | 出力 |
|---|---|---|---|
| `silver_cite_id.py` | WO-SILVER-CITEID-001 | 掲載位置文字列 → 判例ID 解決 (誌名正規化＋号/頁照合＋court+date) | candidates.jsonl / report.md |
| `silver_toc_section.py` | WO-SILVER-TOCSECTION-001 | TOC 階層 → 論点section 構造化 (書籍 weight-1 全結合を section 内共起へ置換) | section/cooccurrence candidates / report.md |
| `schema_probe.py` | — | 実データ JSONL のフィールド点検・field-map 雛形生成 (実データ投入の摩擦解消) | stdout |
| `silver_stage_write.py` | WO-SILVER-WRITE-001 | **P1**: candidate→silver staging 確定書込み (既定 dry-run・`--apply` ゲート・append-only・冪等) | staging JSONL + ledger |
| `run_p0.py` | — | **ターンキー**: silver-1→silver-2→stage-write(dry-run) を1コマンドで (read-only) | 上記一式 |

実データのフィールド名が期待スキーマと違っても `--field-map`（写像 JSON）/ `--infer-kind`（kind 推定）で
吸収する。変換スクリプトは不要。詳細は `RUNBOOK.md`。

## 設計原則 (SILVER-RESOLUTION-KICKOFF v0.1.1 整合 / 既決 INVARIANT 継承)

> 整合の全体は `design/vocab_bottleneck/ALIGNMENT_NOTE_silver_kickoff_v0.1.1_20260619.md`。

- **read-only**: 入力 JSONL/索引の集計・突合のみ。DB write・外部取得・canonical mint なし。
- **未レビュー候補のみ**: 出力は `machine_suggested_*_unreviewed` 等。`reviewed=true`/canonical/claim_support 化しない（tier A/B も候補）。
- **source-record 境界**: 解決先は `target_source_record_uri`(`d1hanrei:…`)＝canonical case ではない（`identity_scope`）。
- **authority snapshot 必須**: `--authority-snapshot` 無しは全行 `blocked_by_policy_or_provenance`（gate8）。
- **blocker_code**: db_unbuilt / index_absent / policy_blocked / insufficient_signal / authority_snapshot_missing / source_registry_unratified。
- **ずれを畳まない**: 同頁複数・同section 複数は全 sibling を保存し `non_selection_reason` 付与（ambiguity_queue）。
- **no-raw-text**: 商用本文を出さない。ID/hash/正規化キー/短ラベルのみ。
- **harvest (人手 seed なし)**: 論点見出しは文献TOC heading の収穫。D1#15 分野分類で代替しない。

## 使い方

実データ (Box 同期側) で回す手順は **`RUNBOOK.md`**。スキーマと最小例は各 .py の docstring と `demo_run.py`。

```bash
# テスト (14 件) とデモ
python3 -m unittest discover -s tools/silver_resolve/tests -v
python3 tools/silver_resolve/demo_run.py   # -> artifacts/DEMO_silver_*.md
```

## 次の手 (計画フェーズ)

- **P0 (本ツール)**: 実データで dry-run → report の歩留まり/weight を計測。**owner GO 不要・ゲート無**。
- **P1 (owner ゲート)**: report を見て閾値確定 → strong/reviewed を staging へ write。
- **P2 (GPT監査ゲート)**: DD-LRINDEX v0.4 確認後、論点 harvest を N claim_type へ一般化。
- 外部取得 (#16 / D1再取得) はクリティカルパス外の別トラック (owner GO)。
