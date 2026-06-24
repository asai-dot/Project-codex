# RUNBOOK — 語彙Hub構築 dry-run を実データで回す（P0）

> read-only dry-run のみ。DB write / DDL / canonical mint なし。計画: `design/vocab_object/01_…RESOLUTION_PLAN` の P0。

## 1. 入力データ（Box 同期側・既存ゴールド）

| 役割 | 既知の所在（STATUS_dict_gold_20260612 より） |
|---|---|
| 有斐閣『法律用語辞典』terms (rank101) | `staging/yuhikaku_legal_dict_terms_stg_v3.jsonl`（13,344 terms） |
| 学陽『法令用語辞典』entries (rank102) | `sources/dict_ocr_hourei/hourei_all_entries_v0.2_20260612.jsonl`（2,662） |
| 2辞書 突合 | `staging/dict_overlay_v0.2_clean_20260612.jsonl`（参考） |

## 2. 実スキーマと写像（generate_staging_v3.py で確認済・2026-06-21）

**★重要: 有斐閣ゴールドは `term_id` でなく `stg_term_key`、定義は terms でなく labels 側**にある。

`yuhikaku_legal_dict_terms_stg_v3.jsonl`（1件）:
```json
{"stg_term_key":"tstg_...","scheme_id":"yuhikaku_legal_dict","authority_rank":101,
 "term_tier":1,"pref_label":"占有","normalized_pref":"占有","reading":"せんゆう","review_state":"accepted"}
```
`yuhikaku_legal_dict_labels_stg_v3.jsonl`（定義はここ）:
```json
{"stg_term_key":"tstg_...","label_type":"definition","label_text":"<定義文>"}
```

→ 本ツールは **`--labels` で定義を join** できる（実スキーマ対応済）。`--field-map` で `term_id←stg_term_key`:
```bash
echo '{"term_id":"stg_term_key"}' > field_map.json
python3 tools/vocab_hub/build_hub_dryrun.py \
  --terms  staging/yuhikaku_legal_dict_terms_stg_v3.jsonl \
  --labels staging/yuhikaku_legal_dict_labels_stg_v3.jsonl \
  --term-key stg_term_key --field-map field_map.json \
  --overlap-threshold 0.6 --out out/hub_20260621
```
- 学陽（rank102）も terms＋labels を同様に渡す（または 2 辞書を結合して 1 本に）。
- 有斐閣 staging は既に **homograph_variant_ix** で同綴を分離済（meta）。本ツールの homograph 検出はその上で重なり率を見る。
- e-Gov 定義があれば rank100（anchor 優先）。

## 3. 実行

```bash
# 2辞書を結合して 1 本の terms.jsonl にしてから（または順に）投入
python3 tools/vocab_hub/build_hub_dryrun.py \
  --terms gold_terms_yuhikaku_plus_hourei.jsonl \
  --overlap-threshold 0.6 \
  --out out/hub_20260621
```

## 4. 見るべき数字（report）

- 生成 hub 数 / exact統合 hub 数 → bedrock の重なり具合。
- **同綴異義 homograph_conflict 数** → Term=sense 分離が効いているか（社員・占有 等）。
- **重なり率 0.6 の妥当性**: 統合/非統合の境界付近のペアを目視し、Wave0 実測で 0.6 を再校正（Q2）。
- specialty attach 数（rank≥103 が bedrock に付くか）。

## 5. canary→反復

まず高頻度クエリ語（数百）に絞って回し、exact統合と homograph_split の中身を目視 → 妥当なら全量。
閾値を変えて（0.5/0.6/0.7）同一データで比較し、precision/recall の感触を掴む。

## 6. やってはいけない（HOLD）

- candidate を alo_terms/alo_hubs（DB）へ load（P2・owner GO＋監査）。
- hub の canonical 昇格（人手レビュー後・P3）。
- 語彙ハブ schema の DDL apply（P2）。
