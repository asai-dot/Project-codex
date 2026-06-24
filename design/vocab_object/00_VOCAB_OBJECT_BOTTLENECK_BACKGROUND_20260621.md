# 起点メモ: 語彙オブジェクト（辞書→語彙）の最新DDと本当のボトルネック（背景収集）

> doc_kind: 背景集約メモ（report-only・apply なし・全 HOLD 据置） / author: Claude / date: 2026-06-21 / owner: 浅井
> 注: 本メモは **語彙オブジェクト（辞書から Term＝語義・Hub を作る）** のスレッド。
>     PR #28（branch `claude/vocab-object-bottleneck-knzorh`）の「リーガルリサーチ silver / 論点グラフ」とは**別物**。
> 一次ソース（Box 正本）:
>   - DD-VOCAB-000 語彙総論（Meaning Backbone）v0.1-draft 2026-06-10
>   - DD-DICT-008 Canonical Bedrock 戦略 v0.2 **candidate** 2026-06-01
>   - 34_vocabulary_layer（語彙ハブ仕様, FREEZE CANDIDATE）
>   - STATUS_dict_gold_20260612_macCC（辞書ゴールド層 状況）
>   - DD-EL-001 entity linking / legal WSD candidate v0.1

---

## 0. 一行

**辞書ゴールド（有斐閣＋学陽）はクリーン化まで出来ているのに、それを「語彙ハブ（DB）」に積む工程で止まっている。**
ボトルネックは語彙データの“汚さ”ではなく、**綺麗になったゴールドの DB 着地＋Hub 構築＋bedrock DD(DICT-008)の accept**。

## 1. 語彙オブジェクトとは（取り違え防止）

辞書・法令定義・KOS を材料に、**意味で接続する基盤（Meaning Backbone）**を作る。中核パイプライン：

```
辞書/定義 → Term(語義 sense 単位) → Hub(概念結節点) → Entity Link(文中の語→正しい語義; legal WSD)
```

- 総論 = `DD-VOCAB-000`（Term＝語義／Hub は文字列でなく概念／mention→Term は write時 legal WSD）。
- 中核各論 = `DD-DICT-008`（どの辞書を bedrock にするか・どう積むか）。
- 語彙ハブ仕様 = `34_vocabulary_layer`（alo_terms / alo_hubs / alo_term_labels / alo_hub_memberships / alo_entity_links …）。

## 2. 実は「辞書ゴールド」はかなり出来ている（背景・measured）

`STATUS_dict_gold_20260612` より：

| 辞書 | 状態 |
|---|---|
| 有斐閣『法律用語辞典』(rank101) | staging v3 = **13,344 terms / 25,934 labels / 4,536 relations**、SKOS整合・OCR 98.6% → **ゴールド確定可**（ただし DB 未着地） |
| 学陽『法令用語辞典』(rank102) | Phase1.5 較正済 = **2,662 entries**（空定義0.4%・重複1.2%・末尾切れ5.1%） |
| 2辞書 突合 | **2,100一致(78.9%)** ＋ **学陽only 562**（「以下「…」という」等の立法技術語彙の地層）＋ 有斐閣only 10,515 |

`DD-DICT-008 v0.2`（candidate）が **bedrock 戦略**を確定：
- rank 100-102（e-Gov定義／基本辞典／法令用語辞典）は**対等な骨格**、rank103+専門辞典は **attach のみ**。
- 「業界独自定義が法的標準に昇格する事故」を **物理ゲート**（`gate_canonical_promotion` / `gate_specialty_exact_match`）で防ぐ。

## 3. 「語彙データが汚い」話のその後（解消済み）

“汚さ”は主に**辞書OCR／パースのノイズ**で、ほぼ片付いている：

- 学陽パースが小見出し・凡例を見出し語に昇格（raw 3,102・「805各省各庁」等のゴミ）→ **較正パーサ v0.2 で 2,662 にクリーン化**（重複 9.4%→1.2%）。
- 5/14 の突合は旧ノイズで無意味だった → **両側クリーンで再突合**し、562の「学陽only」は*ゴミでなく立法技術語*と判明。
- 同綴異義語 64件（遺言 ゆいごん/いごん 等）→ **Term＝語義で分離**（表層一致 merge は物理ゲートで禁止）。
- 業界定義の混入リスク → bedrock-first ＋ rank103 attach-only ＋ 物理ゲートで**汚れを canonical に昇格させない**設計。
- 残ノイズ＝OCR末尾切れ約5.1% → `needs_reocr`（DD-DICT-006）で再OCR課題として残置（致命的でない）。

→ **結論: 「汚い」は取り込みノイズの話で、較正＋再突合＋bedrock戦略で対処済み。** 今の詰まりは汚さではない。

## 4. 本当のボトルネック

> **綺麗になった辞書ゴールドを「語彙ハブ（DB）」に積む“最後のひと積み”が止まっている。**

1. **語彙ハブの DB が未デプロイ**（`34_vocabulary_layer` は FREEZE CANDIDATE。「DB着地は別DD＋owner GO」と明記）。
   → Term/Label/Relation の JSONL はあるが **alo_terms / alo_hubs に入っていない**。
2. **Hub構築（DICT-008 §2.4 の Stage1-6: bedrock seed→exact→close→canonical昇格→specialty attach）が未実行**。
3. **`DD-DICT-008` が candidate 据え置き** — 残ブロッカー＝①owner review、②Wave計画の一部URL実在性確認（W1b/W1c/W3a/W3b）。
4. **legal WSD（`DD-EL-001`）は候補設計のまま**（文中の「占有」等を正しい語義へ貼る・eval 未）。
5. 後続：学陽の staging 生成（terms/labels/relations）、**定義レベルの突合**（両方定義を持つ2,100件の食い違い検出）。

## 5. 最新状況の再確認（2026-06-12 以降）

- 06-15 に `alo_terms` ロード一式（DDL・scheme_register・gate_migration・apply_preflight）が用意されたが、
  これは **D1-Law体系目次＝KOS(Tier2)側の terms**。
- 06-16 に `DD-D1TAXO-001 alo_terms_load v3.1` 監査が **`MODIFY_REQUIRED`／DDL・DB・apply は HOLD** → `_held_…` へ退避。
- 辞書 bedrock 側（DICT-008）の accept・schema デプロイの形跡は **なし**。

→ **ボトルネックは変わらず「DB に積めていない」。直近のロード試行（KOS側）も監査で止められた。**

## 6. 次工程に向けた論点（owner 判断・別途計画）

- 語彙ハブ schema の **DB デプロイDD**（FREEZE CANDIDATE の確定＋owner GO）。bedrock 物理ゲートを CI 化。
- `DD-DICT-008` の **accepted 化**（owner review ＋ Wave URL 実在性確認の片付け）。
- **Hub 構築の dry-run**（bedrock seed→exact→close を read-only で回し、重なり率0.6 を Wave0 実測で再校正）。
- `DD-EL-001` legal WSD の **Wave0 eval corpus** 選定（O5）。
- bedrock の **DB着地は HOLD 継続**（DDL/DB write/canonical mint は owner GO ＋ 監査ゲート）。

## 7. ゲート（本メモの射程）

- 本メモは read-only 集約のみ。candidate 生成・DB write・外部取得なし。
- 継続 HOLD: 語彙ハブ schema デプロイ / DDL / alo_terms・alo_hubs への load / canonical hub 昇格 / WSD 本番。
