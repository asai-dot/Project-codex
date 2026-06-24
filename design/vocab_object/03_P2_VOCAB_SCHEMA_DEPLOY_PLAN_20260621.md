# WO-VOCAB-SCHEMA-LOAD-001（草案）: 語彙ハブ schema デプロイ＋辞書ゴールド load（P2）

> doc_kind: WORK ORDER 草案 / **設計のみ・実行承認ではない** / status: DRAFT（owner GO＋監査 未）
> author: Claude / date: 2026-06-21 / owner: 浅井
> 親: design/vocab_object/01_VOCAB_BOTTLENECK_RESOLUTION_PLAN（P2）/ DD-DICT-008 v0.2 / 34_vocabulary_layer
> 前提: P0 Hub dry-run の report 良好 ＋ P1 で DD-DICT-008 accepted ＋ 34_vocabulary_layer FREEZE 確定
> gate: **DDL apply / DB load は owner GO＋GPT監査＋canary→batch が必須**。本草案は段取りの設計のみ。

## 0. 一行

綺麗な辞書ゴールド（有斐閣13,344＋学陽2,641、**defrag後 計15,942 / provisional hub 13,188**）を、
物理ゲート付きの語彙ハブ schema へ **canary→batch で load** する。
これがボトルネックの「最後のひと積み」。実行は HOLD、本書は手順と検証の設計。

> **精緻化(2026-06-25)**: P0実測＋品質監査の結果を反映。load 対象は **defrag済 term セット**
> （断片再結合済・homograph 44→3）。cross_reference 363 は **alias エッジとして** load（短定義 anchor ではない）。
> owner決定2件（参議=split / 重懲役=B採用）と needs_preprocessing フラグを load 前に適用。

## 1. 着手前提（これが揃うまで apply しない）
- [x] P0 Hub dry-run report が妥当（exact統合2037・同綴異義split3・重なり率0.6 感触OK・homograph defrag解決）
- [ ] `DD-DICT-008` accepted v1.0（P1 / 残ブロッカーは owner レビュー A1/A2/A3 のみ、Wave B解消済）
- [ ] `34_vocabulary_layer` FREEZE 確定（owner）
- [ ] §2.3.1 gate 条件改訂を反映した DDL（P1 §2）
- [ ] owner GO ＋ GPT 独立監査（本 WO を投函）
- [ ] **load 前処理の適用**: defrag（断片再結合）＋ owner決定2件＋ needs_preprocessing/reading_source タグ付与

## 2. STEP A — schema デプロイ（DDL apply・owner GO 後）
語彙ハブ最小 schema（34_vocabulary_layer）：
```
alo_concept_schemes   (scheme_id, name, authority_rank, role, ingest_policy)
alo_terms             (term_id, scheme_id, normalized_pref, reading, definition, term_tier, source_item_key, valid_from/to)
alo_term_labels       (term_id, label, label_type)
alo_hubs              (hub_id, anchor_term_id, hub_status)         -- 既定 provisional
alo_hub_memberships   (hub_id, term_id, map_type)                  -- exact/close/seed
alo_term_relations    (src_term_id, dst_term_id, relation_type)
alo_entity_links      (mention_id, target_term_id, ...)            -- WSDはP3。ここでは空でよい
```
**物理ゲート（VIEW＋fn_run_all_gates、CI化）**:
- `gate_canonical_promotion`（P1 §2 改訂版: 昇格可 rank 集合のみ canonical hub anchor 可）
- `gate_specialty_exact_match`（specialty 同士の exact_match を bedrock anchor なしに作らせない）
- 合格条件 = 両 violation_count = 0。

### 2.5 品質監査由来の追加フィールド（P0/06–11 の実測反映）
P0 ツール群が生成する品質メタを schema に持たせ、入口ゲートと P3 を支える:
- `alo_hubs.needs_preprocessing` (text[]): 空定義/短定義 anchor のフラグ（build_hub_dryrun --quality-filter）。
  **canonical 昇格の入口ゲート**＝needs_preprocessing 非空の hub は canonical 不可。
- `alo_hubs.homograph_genuine` (bool): defrag が保持した genuine_split（参議等）。誤統合防止の証跡。
- `alo_terms.reading_source` (text): 読み補完経路（original/kana_infer/yuhikaku_pref_match/pykakasi）。
  pykakasi 由来は P3 でスポット検証対象。
- `alo_terms.def_quality` (text): ok/short/empty/cross_reference/truncation（probe_quality・short_def_triage）。
- `alo_term_relations` に **alias エッジ**を収容: cross_reference 363 を
  `relation_type ∈ {alias_of, see_also}` で load（xref_extract.py の alias_edges_candidate）。
  = 別名解決の資産。**短定義 anchor としては load しない**（resolved 分は target hub の別表記）。

## 3. STEP B — scheme 登録
`alo_concept_schemes` に rank 体系（100/100a–100d/101/102/103/104/105/106/107/200）を登録。
今回 load 対象は **rank101 有斐閣 / rank102 学陽**（bedrock 2辞書）。KOS(105=D1TAXO)は別スレ・別ゲート、本WOでは load しない。

## 4. STEP C — ゴールド load（canary→batch）
**load 対象 = defrag済 term セット**（断片再結合・homograph 3・terms 15,942）。
1. **canary**: 高頻度クエリ語 数百件 sub-set ＋ **検証用に必ず含める**: homograph genuine 3件（参議/重懲役/将来）、
   xref alias 解決済サンプル数件（共有持分→持分 等）、needs_preprocessing 付き hub 数件。
   → `fn_run_all_gates()` → violation_count=0 → 目視（genuine split が別Term・alias が target hub に解決）。
2. 問題なければ **batch**: defrag済 terms 15,942（有斐閣由来 + 学陽2,641）/ labels / relations
   （生成は generate_staging_v4 + defrag_terms + xref_extract 流用）。alias エッジは `alo_term_relations` へ。
3. hub は **provisional のまま**（canonical 昇格は P3 人手レビュー、needs_preprocessing 非空は昇格不可）。

## 5. 検証（apply 後）
- 件数照合（defrag済 staging 件数 == load 件数）。
- 両ゲート violation_count = 0。
- 同綴異義サンプル（占有・社員・遺言＋genuine 3: 参議/重懲役/将来）が別 term_id で存在し、誤統合 0。
- **alias エッジ**: cross_reference 解決分が `alo_term_relations(alias_of/see_also)` に入り、未解決分は load されていない。
- **needs_preprocessing**: truncation 17・空定義 anchor 3 がフラグ付きで、canonical 昇格ゲートで弾かれる。
- rank103+ が canonical hub anchor に入っていない（gate で担保）。

## 6. ROLLBACK（DD-REV-001 / DICT-008 §7）
- canary 段で violation → apply 中止、staging 修正、再 canary。
- batch 後の不整合 → `gate_canonical_promotion` を一時 WARN 降格 ＋ 影響 hub の re-anchor、最悪 migration revert（schema は append-only 設計、term は valid_to で論理失効）。

## 7. FORBIDDEN（本 WO の射程外）
- owner GO／監査前の DDL apply・DB load。
- hub の canonical 昇格（P3・人手レビュー後）。
- KOS(D1TAXO)・専門辞典(rank103+)の canonical load。
- legal WSD / entity_links の本番投入（P3・DD-EL-001）。
- 外部取得（Wave の追加辞書 DL は別 WO）。

## 8. 次（P3 へ）
load 後に hub canonical 昇格（高頻度語から段階）＋ `DD-EL-001` legal WSD の Wave0 eval corpus 選定。
