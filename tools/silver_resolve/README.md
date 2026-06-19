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

## 設計原則 (計画 P0 / 既決 INVARIANT 継承)

- **read-only**: 入力 JSONL/索引の集計・突合のみ。DB write・外部取得・canonical mint なし。
- **strong-only (D2)**: strong = `issue_page_exact` 単一のみ。fallback / court_date / 多候補は review queue (自動確定しない)。
- **harvest (人手 seed なし)**: 論点見出しは文献TOC heading の収穫。D1#15 分野分類で代替しない。
- **honest_empty**: 解析不能 = `locator_unresolvable` / 索引欠 = `db_unbuilt` / 評釈痕跡なし = `trace_absent` を区別。
- **ずれを畳まない**: 同頁複数判例・同section 複数判例は候補を保持し review へ (P4 信号保存)。

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
