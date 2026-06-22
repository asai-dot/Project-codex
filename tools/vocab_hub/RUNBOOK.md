# RUNBOOK — 語彙Hub構築 dry-run を実データで回す（P0）

> read-only dry-run のみ。DB write / DDL / canonical mint なし。計画: `design/vocab_object/01_…RESOLUTION_PLAN` の P0。

## 1. 入力データ（Box 同期側・既存ゴールド）

| 役割 | 既知の所在（STATUS_dict_gold_20260612 より） |
|---|---|
| 有斐閣『法律用語辞典』terms (rank101) | `staging/yuhikaku_legal_dict_terms_stg_v3.jsonl`（13,344 terms） |
| 学陽『法令用語辞典』entries (rank102) | `sources/dict_ocr_hourei/hourei_all_entries_v0.2_20260612.jsonl`（2,662） |
| 2辞書 突合 | `staging/dict_overlay_v0.2_clean_20260612.jsonl`（参考） |

## 2. 期待スキーマと写像

`build_hub_dryrun.py` の期待 Term スキーマ:
```json
{"term_id","scheme_id","authority_rank":101,"normalized_pref":"占有","reading":"せんゆう","definition":"...","term_tier":1}
```
実フィールド名が違う場合は `head -n3` で確認し `--field-map`（`{expected: actual}`）で吸収。
- 有斐閣/学陽の rank は `authority_rank`（101/102）。e-Gov定義があれば rank100。
- 学陽は `definition` が畳み込み済（sense_sub 反映）。空定義は overlap=0（exact 統合されにくい→安全側）。

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
