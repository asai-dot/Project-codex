# P0.5 前処理計画: 短定義 anchor triage（語彙オブジェクト）20260624

> doc_kind: 計画（design-only / 実行は別ゲート） / author: Claude / date: 2026-06-24 / owner: 浅井
> 親: design/vocab_object/01_VOCAB_BOTTLENECK_RESOLUTION_PLAN / 06_DATA_QUALITY_AUDIT_FINDINGS
> 経緯: 「データほんまにきれいか」→ 監査で3穴 → hub構築実測で2穴は見かけ倒し → 残課題は短定義のみ

## 0. このフェーズの位置づけ

P0(hub dry-run)とP1(DICT-008 accept)の間に挟む**軽量前処理**。
当初「大規模前処理が要る」と見たが、§06実測で**唯一の実残課題は短定義 anchor 489 hub**に縮小した。
P0.5 はこの489件を triage するだけ。**clean subset は P0.5 を待たず P1 へ進められる**（option 2）。

## 1. スコープ（確定した数字 / reading補完込み 最終 run_2dict --quality-filter）

| 項目 | hubレベル実数 | 対応 |
|---|---|---|
| 空定義 anchor | **6 hub** | 人手で原典確認（少数）→ see_also or 再OCR |
| 短定義(<8字) anchor | **489 hub** | 本フェーズの主対象。3分類して処理 |
| 読み欠落 | reading補完で解消（defmatch残3） | 対応不要（任意で pykakasi reading スポット検証） |
| 非tier1 参照行 | 712（穴ではない） | 対応不要（seed除外が正） |
| 辞書またぎ統合 | 2037（exact key） | — 参考: cross-dict 統合が高品質キーで成立 |

## 2. 短定義489の triage 手順（read-only生成→人手判定）

1. **export**: `python3 tools/vocab_hub/probe_quality.py --export ~/dict_quality`
   → `yuhikaku_short_def.jsonl` / `hourei_short_def.jsonl`。
2. **3分類**（自動 heuristic + 人手スポット）:
   - **①末尾切れ/OCR脱落**: 定義が体言止め以外で途切れ・助詞で終わる等 → 再OCR(DD-DICT-006)候補。
   - **②正規の短定義**: 「〜の略。」「〜に同じ。」等、本当に短い正しい定義 → そのまま load 可。
   - **③parse/結合ミス**: 学陽 calibration の sense_sub 過剰分割等 → パーサ再点検。
3. ①③のみ `needs_reocr` / `needs_reparse` タグ。②は clean 扱い。
4. 短定義の多くが②なら、真の前処理対象はさらに小さくなる見込み。

## 3. clean subset 先行（並行レーン）

- `build_hub_dryrun.py --quality-filter` が短def/空def anchor に `needs_preprocessing` を付与済み。
- **needs_preprocessing 無しの hub = clean subset** を P1/P2 の load 対象にできる。
- triage 完了分を順次 clean subset に昇格（段階投入）。完璧を待って全停止しない。

## 4. 受け入れ基準（P0.5 完了条件）

- 短定義489 が ①②③ に分類され、各件数が確定。
- ①③の needs_reocr/needs_reparse 件数が DD-DICT-006 へ申し送られている。
- clean subset の hub 数が確定し、P1 accept の load 対象が明示されている。

## 5. ゲート

design-only。再OCR実行・パーサ改修・DB load は各々別ゲート（DD-DICT-006 / canonical / owner GO）。
本フェーズの成果物は triage 分類表と needs_* タグ付き candidate JSONL（read-only）のみ。
