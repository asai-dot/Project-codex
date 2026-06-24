# データ品質監査 findings: 辞書ゴールドは「ほんまにきれい」か（実測）20260624

> doc_kind: 実測記録（read-only） / author: Claude / date: 2026-06-24 / owner: 浅井
> 親: design/vocab_object/01_VOCAB_BOTTLENECK_RESOLUTION_PLAN / tools/vocab_hub/probe_quality.py
> 経緯: owner「データほんまにきれいなんか？」→ STATUS_dict_gold の要約を鵜呑みにせず実データを直接測った.

## 0. 結論（一行）

**初版**: 「きれい」とは言えない。生カウントで hub 統合を阻む穴が3つ見える(空定義712/読み欠落2583/短定義585)。

**更新(§2 で hub構築に通した実測後)**: 3つのうち**2つは見かけの穴**だった。
空定義712は非tier1の参照行(seed除外が正)で**真の穴は8 hubのみ**、読み欠落はdefmatchで1973救済済み。
**残る実課題は短定義 anchor 約580 hub のみ** = 局所的な再OCR/末尾切れtriage。大規模前処理は不要。
STATUS の「ゴールド確定可」は*見出し突合率*の話だったが、hub レベルの穴も実測したら局所的だった。

## 1. 実測（probe_quality.py / 2026-06-24）

| 指標 | 有斐閣(rank101, 13344) | 学陽(rank102, 2662) | 評価 |
|---|---|---|---|
| OCRゴミ(置換/制御) | 0% | 0% | ✅ |
| 見出し空 | 0% | 0% | ✅ |
| 定義長 中央値 | 119 | 455 | ✅ 健全 |
| **読み欠落** | 0.3% (42) | **97.0% (2583)** | ❌ 学陽は読みキー突合がほぼ不能 |
| **空定義** | **5.3% (712)** | 0.4% (11) | ❌ 定義でも読みでも繋げない穴 |
| **短定義(<8字)** | 3.5% (463) | 4.6% (122) | ⚠ 末尾切れ/OCR脱落 疑い |
| 見出し長すぎ(>25) | 1.0% (128) | 0.04% (1) | ⚠ parse/結合ミス疑い |
| 定義に英字連続 | 1.2% (166) | 1.1% (30) | ⚠ OCR誤認 疑い |
| 重複(見出し+読み) | 13 | 32 | △ 一部は homograph(正) |
| 定義長 max | 606 | **3751** | ⚠ 学陽の一部が複数entryを飲み込み疑い |

## 2. hub構築で実測した「穴の正体」(2026-06-24 追記 / probe_empty_def + run_2dict --quality-filter)

§1 の生カウント(空定義712 等)を **hub 構築に通すと、大半は構造的に吸収される**ことが判明した。
監査のフィールド健全性カウントと、hub レベルで実際に残る穴は別物だった。

### 2.1 「空定義712」の正体 = ほぼ全部が非tier1の参照行(穴ではない)

`probe_empty_def.py` 実測: 空定義 term 723件の内訳
- **bedrock+非tier1 (seed除外) = 712** ← 有斐閣の語義サブエントリ/参照行(tier2+)。
  元から独立定義を持たない正常な行で、bedrock hub を seed しないのが**正しい挙動**。
- bedrock+tier1 = 11 (うち 単独hub anchor=8 が**真の空定義の穴**, redundant吸収=3)
- specialty = 0

→ **空定義の真の穴は 8 hub のみ**。「712件の大穴」は生カウントの誤読だった(STATUSと同じ轍)。
   build_hubs は非tier1を黙って落とすため `dropped_nontier1` を stats に計上した(no silent drop)。

### 2.2 「読み欠落2583」= defmatch で救済済み

`run_2dict.py` 実測(16006 terms): 辞書またぎ統合 **1950** / 読み救済(defmatch) **1973** / homograph 46。
学陽97%読み欠落は定義重なりで橋渡しされ cross-dict 統合が機能した(前回 辞書またぎ=0 → 解消)。
本質的には読み補完(MeCab)が望ましいが、hub 統合自体は既に機能している。

### 2.3 唯一の実残課題 = 短定義 anchor 約580 hub

短定義(<8字)が anchor の hub: run_2dict(0.5-0.7) で **507** / probe(0.6) で **581**。
末尾切れ/OCR脱落の疑い。**これが P0.5 前処理の唯一の実対象**。
(507 vs 581 の差は triage 時に1本化。構造的結論は不変。)

## 3. これが計画に意味すること(更新)

- **大規模な前処理フェーズは不要**だった。空定義712は非tier1で穴ではなく、読み欠落はdefmatch救済済み。
- P0.5 は **短定義 anchor 約580 hub の triage** に1本化できる(再OCR/末尾切れ救済)。
- load 戦略: `--quality-filter` で短def/空def anchor に `needs_preprocessing` を付け、
  clean subset を先行 load、フラグ付き約580+8は別レーンで triage(option 2 = 前進しつつ並行triage)。
- DD-DICT-008 の bedrock 物理ゲートに加え、**入口品質ゲート(短定義を canonical anchor にしない)** を quality_filter が担保。

## 4. 推奨次手（前処理 P0.5: 短定義に集中）

1. **短定義 anchor hub を export して triage**（`probe_quality.py --export ~/dict_quality` の `*_short_def.jsonl`）。
   約580件を「①末尾切れ(再OCR) / ②本当に短い正規定義(そのまま可) / ③parse結合ミス」に3分類。
2. 空定義 anchor 8 hub: 原典確認 → see_also or 再OCR(少数なので人手で足りる)。
3. (任意) 学陽読み欠落: MeCab で yomi 補完すると defmatch 依存を減らせる。優先度は低(統合は既に機能)。
4. clean subset(needs_preprocessing 無し)で P1 → P2 を先行。短def triage は並行レーン。

## 5. ゲート

read-only 監査のみ。本 findings は「きれい」断定の撤回と前処理の必要性の記録。DB/canonical/再OCR は別ゲート。
