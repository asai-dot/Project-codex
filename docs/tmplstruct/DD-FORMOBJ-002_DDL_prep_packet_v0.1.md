# DD-FORMOBJ-002 DDL前設計パケット（owner ratify card ＋ filled_instance物理境界 ＋ witness evidence locator）

> date: 2026-06-16 / author: 番頭(リモートClaude) / gate: 設計のみ（DDL/DB write/apply は本カードの ratify 後・別REQUEST）
> 監査 `DDFORMOBJ2_PASS_WITH_NOTES`（schema freeze prep go）の `required_before_DDL_apply` を埋める叩き台。
> **owner判断を仰ぐ文書**。ここに○が付くまで DDL に進まない。

---

## A. owner ratify card（DDLに進む前の確認カード）

```text
RATIFY-FORMOBJ-002-DDL
対象: form_object.v0.2 スキーマ（4層・判定軸・記載事項細分・defect_kind・16ゲート）
状態: schema freeze prep = GO（GPT監査3回 PASS_WITH_NOTES 済）

owner が ○ を付ける項目:
 [ ] 1. v0.2 スキーマで DDL設計に進むことを承認（本番DB書込みは含まない）
 [ ] 2. filled_instance 物理境界を §B の方針で確定（知識層と案件層を物理分離）
 [ ] 3. witness evidence locator schema を §C で確定
 [ ] 4. DDL は dry-run apply のみ先行、本番 DB write は別 RATIFY を要する
 [ ] 5. corpus 全書式展開は別ゲート（PoC代表性が薄い＝N-02、追加サンプル後）
 [ ] 6. form_uid 採番 = alo:form:{uuidv7}（PROVISIONAL slug は移行用 alias）

不可逆・失敗モードの確認:
 - スキーマ固定後の変更コスト（→ dry-run のみで実体は可逆）
 - filled_instance 混入（→ §B 物理分離＋16ゲートで防止）
 - 版違い誤接続（→ G_WITNESS_EDITION_VERIFIED で防止・本日事故を実証済）

owner 署名: ____________  日付: ________
```

## B. filled_instance 物理境界（監査 N-03＝DDL前最大リスク）
**原則: 知識層と案件層を物理的に別DB/別ストアに置く。FKで跨がない（参照は不透明IDの一方向のみ）。**

| レイヤ | 中身 | 置き場所（案） | 機微 | AIアクセス |
|---|---|---|---|---|
| **知識層** form_object/variant/witness/requisite/design_knowledge | 抽象書式・型・観測・記載事項・押し引き | 静的DB（biblio隣接・公開可能メタ） | 低（公的書式・文献由来） | 可 |
| **案件層** filled_instance | 実案件で値が埋まった文書 | **別DB/案件ストア（SF/案件Box）** | 高（依頼者・相手方・個人情報） | redacted/approved のみ |
| 橋渡し | filled_instance → form_object の参照 | 案件層側に `based_on_form_uid`（一方向・知識層からは案件を参照しない） | — | — |

ルール:
- 知識層スキーマに filled 値の列を作らない（`gate_filled_instance_separated` が静的に保証）。
- 実務生成物を witness にする場合は **redacted/abstracted/approved** を通し、`source_type=internal_generated` ＋ approval 記録必須。
- 知識層 → 案件層への FK 禁止。案件層 → 知識層は `based_on_form_uid` の一方向参照のみ。

## C. witness evidence locator schema（監査 required #4）
`form_witness` が「どこの何版のどこ」を再現可能に指す最小スキーマ:
```jsonc
witness_evidence_locator {
  witness_id,                  // 不透明
  form_uid,                    // どの form_object の観測か
  source_type,                 // biblio_item | web | court | registry | internal_generated | uploaded_sample
  source_uri,                  // biblio_item_uri / URL / box_file_id / citation
  edition_or_version,          // ★版（タイトル一致のみ禁止）
  edition_year,                // ★temporal 判定用
  locator: { toc_node, section_path, page_span, pdf_page_span, page_offset },
  content_hash,                // 観測内容の指紋
  extraction_method,           // jisui_vision_ocr | text_layer | manual | api
  extracted_at, extractor_version,
  source_confidence,
  provenance_family,           // ★同一供給元の再配信を独立票にしない
  verified_status,             // edition_verified | toc_only | toc_only_coarse | statute_citation | EDITION_MISMATCH_FLAGGED | pending
  adopted,                     // この witness を form_object に採用したか
  counts_as_independent        // 独立観測として数えるか（provenance_family で抑制）
}
```
- 既存 `form_snapshot.v1` の anchor（toc_node_id/page_span/page_offset）は本 locator の `locator` 区画にマップ＝001資産の再利用。
- `verified_status` の既定: 版未確定は `toc_only/coarse`。これらは **claim_support・mandatory根拠に使わない**（監査明文化要求）。

## D. 追加 property test（監査 required #2・実装済み）
`tools/validate_form_object.py`（**16ゲート**）に実装・全緑:
- multi-witness 無断canonical / provenance_family 多数決 / temporal 矛盾 / severity 単調性 / forum-null 正常系。
- 実行: PoC2件 0 violations、negative 10/10 発火、positive 1/1。

## E. 次（owner ○ 後）
1. DDL **dry-run** 設計（知識層テーブル：form_object/form_variant/form_witness/requisite/edge）。本番 write は別 RATIFY。
2. PoC 追加サンプル（裁判所/行政提出書式・通知書・解除通知・議事録・同意書）で代表性を上げる（N-02）。
3. 手続きオブジェクト接続（serves/submitted_under の薄い規則）。

## HOLD（継続）
DB write / 本番 schema apply / corpus 全展開 / filled_instance 投入。
