# WO-VOCAB-SCHEMA-LOAD-001（草案）: 語彙ハブ schema デプロイ＋辞書ゴールド load（P2）

> doc_kind: WORK ORDER 草案 / **設計のみ・実行承認ではない** / status: DRAFT（owner GO＋監査 未）
> author: Claude / date: 2026-06-21 / owner: 浅井
> 親: design/vocab_object/01_VOCAB_BOTTLENECK_RESOLUTION_PLAN（P2）/ DD-DICT-008 v0.2 / 34_vocabulary_layer
> 前提: P0 Hub dry-run の report 良好 ＋ P1 で DD-DICT-008 accepted ＋ 34_vocabulary_layer FREEZE 確定
> gate: **DDL apply / DB load は owner GO＋GPT監査＋canary→batch が必須**。本草案は段取りの設計のみ。

## 0. 一行

綺麗な辞書ゴールド（有斐閣13,344＋学陽2,662）を、物理ゲート付きの語彙ハブ schema へ **canary→batch で load** する。
これがボトルネックの「最後のひと積み」。実行は HOLD、本書は手順と検証の設計。

## 1. 着手前提（これが揃うまで apply しない）
- [ ] P0 Hub dry-run report が妥当（exact統合・同綴異義split・重なり率0.6 の感触 OK）
- [ ] `DD-DICT-008` accepted v1.0（P1）
- [ ] `34_vocabulary_layer` FREEZE 確定（owner）
- [ ] §2.3.1 gate 条件改訂を反映した DDL（P1 §2）
- [ ] owner GO ＋ GPT 独立監査（本 WO を投函）

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

## 3. STEP B — scheme 登録
`alo_concept_schemes` に rank 体系（100/100a–100d/101/102/103/104/105/106/107/200）を登録。
今回 load 対象は **rank101 有斐閣 / rank102 学陽**（bedrock 2辞書）。KOS(105=D1TAXO)は別スレ・別ゲート、本WOでは load しない。

## 4. STEP C — ゴールド load（canary→batch）
1. **canary**: 高頻度クエリ語 数百件 sub-set を load → `fn_run_all_gates()` 実行 → violation_count=0 を確認 → 目視（同綴異義が別Termで入っているか）。
2. 問題なければ **batch**: 有斐閣 13,344 terms / 25,934 labels / 4,536 relations、学陽 2,662 entries（terms/labels/relations 生成は generate_staging_v4 流用）。
3. hub は **provisional のまま**（canonical 昇格は P3 人手レビュー）。

## 5. 検証（apply 後）
- 件数照合（staging 件数 == load 件数）。
- 両ゲート violation_count = 0。
- 同綴異義サンプル（占有・社員・遺言）が別 term_id で存在し、誤統合 0。
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
