# vocab_hub — 語彙オブジェクト P0（辞書ゴールド→Hub構築 dry-run）

語彙オブジェクト（辞書から Term＝語義・Hub を作る）の現ボトルネック＝
**綺麗な辞書ゴールドが語彙ハブDBに積めていない**を解く P0（read-only dry-run）ツール。

> 背景/計画: `design/vocab_object/00_…BACKGROUND` / `01_…RESOLUTION_PLAN`
> ⚠ `tools/silver_resolve/`（PR #28＝リーガルリサーチ silver）とは別スレッド。

## これは何か

DD-DICT-008 §2.4 の Hub 構築（bedrock seed→exact_match→close_match→specialty attach）を、
**DBに書かず JSONL で**回し、重なり率・同綴異義衝突・bedrock coverage を計測する。

| ツール | 役割 | 出力 |
|---|---|---|
| `build_hub_dryrun.py` | 辞書ゴールド → provisional Hub 候補 | hub_candidate / hub_membership_candidate / report |

## 監査整合の不変条件

- **read-only / DBに書かない / 全 hub_status=provisional**（canonical 昇格しない）。
- exact_match は `normalized_pref + reading 一致 かつ 定義重なり率≥閾値` のみ（**表層一致だけで統合しない**）。
- **同綴異義**（reading 違い / 同key低重なり）は統合せず **別hub＋homograph フラグ**、重なり率を保存。
- **specialty（rank≥103）は attach のみ**（bedrock hub へ close_match）。canonical 化しない。
- anchor は中立規則（e-Gov優先→scheme_id→term_id）。優劣ではない。

## 使い方

```bash
python3 tools/vocab_hub/build_hub_dryrun.py --terms <gold_terms.jsonl> \
  [--field-map field_map.json] [--overlap-threshold 0.6] --out out/hub_$(date +%Y%m%d)

python3 -m unittest discover -s tools/vocab_hub/tests -v   # 8 tests
python3 tools/vocab_hub/demo_run.py                        # artifacts/DEMO_vocab_hub_build_report.md
```

実データ（Box: 有斐閣 staging v3 / 学陽 v0.2）への向け方は `RUNBOOK.md`。
