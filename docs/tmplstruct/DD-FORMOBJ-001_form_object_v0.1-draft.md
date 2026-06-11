# DD-FORMOBJ-001: 書式オブジェクト確立 設計 v0.1-draft

> **id**: DD-FORMOBJ-001 / **version**: v0.1-draft / **supersedes**: なし
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / date: 2026-06-11
> **gate**: 設計のみ。DDL・移行・policyファイル変更・DB書込みなし。
> **依存**: DD-LITID-001(書籍identity) / DD-TOCATTACH-001(着脱式TOC, toc_nodes) / D-5(toc_merge_policy v2)
> **狙い**: テンプレ書式(式6,976)を、identity安定な「書式オブジェクト」へ。正着＝**住所と同一性を先に確定し、中身(OCR)は後**。

---

## 1. 原則（なぜこの順か）
1. **アドレス先行**: 中身から作ると版違い・源違いの同じ書式を名寄せできず重複する。住所(book+node)があれば版跨ぎ・源跨ぎでdedup/マージ/版管理が効く。
2. **snapshot→canonical**: 先に混ぜると誤りが伝播し源を後から足せない。層分離なら源追加・修正swapが安全(同源swap 100% auto実証済)。
3. **発明禁止＋品質層**: 書式は「空欄・条項の有無」が命。盛ると実害。誤り(廷→延等)は消さず品質層で持つ。

## 2. オブジェクトモデル
`form_object` = 〈identity｜anchor｜content｜provenance｜quality｜confidence〉

```text
form_object
  form_uid            sticky不変ID(下記§3)。具体的1書式=1書籍内1ノードに係留
  anchor              §4: canonical_book_id + toc_node_id + page_span
  form_title          式名(正準。norm_title_v1で誤謬クラス吸収)
  form_kind           contract|agreement|notice|minutes|application|bylaw|clause_set|other
  language            ja|en|…
  content             §5: blocks[] + blanks_total + clause_count
  provenance          §6: 源別snapshotの集合(merge前)
  canonical_source    §6: 基底に選ばれた源(policy)
  quality             §7: overlay(誤謬クラス・verdict)
  confidence          §8: 分解係数(source_authority × merge × quality)
  form_group_uid?     §9: 版跨ぎ「同一抽象書式」の束ね(候補のみ・自動禁止)
  resolution_log_ref  確立・改訂の監査ログ
```

## 3. form_uid（sticky ID）採番規則
- **opaque不変ID**: `alo:form:{ULID}`。**初回確立時に発番、以後不変**(再抽出・版改訂・源追加で変わらない)。
- provisional key（`{book_id}:{toc_node_id}`）→ form_uid の対応は `form_resolution_log` で保持。
- 係留単位: **具体的1書式 = 1書籍 × 1 toc_node**（その式の住所）。抽象書式の束ねは form_group_uid(§9)で別途。
- gate: `gate_sticky_form_uid`（同一(book,node)へは常に同一form_uid。再実行で収束）。

## 4. アンカー（住所）— OCRで決めない
```text
anchor
  canonical_book_id     DD-LITIDで解決した正準書籍ID
  toc_node_id           その式に対応するTOCノード(toc_nodes)。親パス修飾ladder(§DD-TOCATTACH1.3)で同定
  page_span_print       [start,end] = ノードの start/endHeadlinePage(LIONBOLT)/page(他源)
  page_span_pdf[]       源スキャンごとの物理頁範囲(校正後。§ pdf=print+offset、本ごとに実測)
  span_kind             single_node | subtree(式が小節点群) | multi_node(またがり)
```
- **DBのtoc_nodesだけで住所が決まる**（画像不要）。式境界＝page_span。
- gate: `gate_form_anchor_required`（anchor無き書式オブジェクトを作らない）。

## 5. content スキーマ（パイロット正準形）
```json
{
  "blocks": [
    {"type":"heading|party|recital|clause|item|signature|date|attachment|note",
     "no":"第1条 等(任意)","title":"見出し(任意)",
     "text":"…","items":["…"],
     "blanks":["空欄ラベル"],"ref":"別紙1 等(attachment時)"}
  ],
  "blanks_total": 0,
  "clause_count": 0
}
```
- 既存パイロットJSON（`pilot_keiyakukaisho/out_*.json` の解除通知/製造委託基本契約/発起人決定書）は**この正準形へ整える**（block型・blanks・anchor付与）。
- gate: `gate_no_blank_invention`（blanks/clauses/署名欄は源に在るものだけ。プレースホルダ`[ ]`【 】`___`は保持、創作しない）。

## 6. 源別snapshot → canonical（層分離）
- **snapshot**: `(form_uid, source_system)` に1 active。源＝ native_docx / 自炊600dpi_vision / lionbolt / bencom / legallib。`provenance_group`単位で独立観測を数える(同一データ再配信は1票)。
- **canonical_source選択(policy)**: 推奨優先 **native_docx > 自炊vision > lionbolt > bencom > legallib > codex_ocr**（§12 D-F1で確定）。粒度ガード(最富源比20%)準用。
- **crosswalk**: 源間のblock対応を heading/clause番号＋頁で取る（DD-TOCATTACH ladder準用）。異源rebasingは全件review。
- gate: `gate_snapshot_per_source` / `gate_no_node_invention_in_merge`（合成で条項を生まない）。

## 7. 品質オーバーレイ（誤りは吸収せず層で持つ）
- OCR系統誤字（**廷→延** 等の確定誤謬クラス）は **norm_titleでは検索吸収するが、表示テキストは corrected snapshot で直す**（生snapshotは不変）。
- verdict: error_confirmed / undecided / legitimate → canonical投影時に confidence減点＋review表示（DD-TOCATTACH §3準拠）。
- gate: `gate_quality_overlay_not_silently_absorbed`（意味のある誤りを正規化で消さない）。

## 8. confidence 分解
```text
form_confidence_final =
  source_authority(native1.0 / 自炊vision0.95 / lionbolt0.85 / bencom0.8 …)
  × merge_confidence(crosswalk: auto1.0 / review0.8 / 頁補完のみ0.95)
  × quality_adjustment(legitimate1.0 / undecided0.9 / error_confirmed0.7)
```
各係数を列保持しfinalは導出(再計算可)。

## 9. 版跨ぎの同一抽象書式（form_group_uid・自動禁止）
- 第2版「業務委託契約書(サンプル)」と第3版の同書式は **form_group_uid** で束ねる。
- 束ねは**候補生成のみ**（form_title正規化＋構造類似＋book_group）。**タイトル一致だけでの自動マージ禁止**（DD-LITID §6.3準用）。
- v0.1ではスキーマ予約のみ。実束ねは Phase 2（owner決定 D-F3）。

## 10. ゲート一覧
`gate_form_anchor_required` / `gate_sticky_form_uid` / `gate_no_blank_invention` /
`gate_snapshot_per_source` / `gate_no_node_invention_in_merge` /
`gate_quality_overlay_not_silently_absorbed` / `gate_no_auto_group` /
`gate_page_calibration_recorded`（pdf↔print頁オフセットを本ごとに記録）/
`gate_form_uid_resolution_logged`

## 11. パイプライン対応（正着S0→S5）
| S | 内容 | 依存 | 本環境で可否 |
|---|---|---|---|
| S0 | form_object定義・form_uid採番規則(本DD) | — | ✅ 設計済 |
| S1 | アドレス確定（identity→toc_node→page_span） | toc_nodes投入後 | DB読取で可(投入後) |
| S2 | 源別snapshot（自炊vision OCR等） | 画像≤約365MB or Mac | ✅ パイロット実証済 |
| S3 | canonical合成（policy＋crosswalk＋品質） | S2複数源 | 設計可・実装後 |
| S4 | 三点測量検証 | 複数源TOC/snapshot | ✅(D-6で実証) |
| S5 | 永続化（form_uid＋来歴＋log） | apply権限 | Mac側承認フロー |

## 12. owner決定事項（決定カード）
| ID | 問い | 推奨 |
|---|---|---|
| D-F1 | canonical_source優先順位＝native_docx>自炊vision>lionbolt>bencom>legallib>codex_ocr | 採用 |
| D-F2 | form_uid係留単位＝(book,toc_node)。抽象束ねはform_group_uidで分離 | 採用 |
| D-F3 | 版跨ぎ束ね(form_group_uid)はPhase 2・候補のみ自動禁止 | 採用 |
| D-F4 | 品質誤謬クラス(廷→延)はnorm吸収＋corrected snapshotの二段 | 採用 |

## 13. 監査に確認したい点
1. form_uidを(book,toc_node)係留＝具体書式単位、抽象束ねを別IDにする二層は、DD-LITID(provisional→biblio_item)と整合か。
2. canonical_source優先(native>自炊vision>業者OCR)は、書式の「正確さ」軸で妥当か（TOCのD-5とは別軸でよいか）。
3. 「式境界＝toc_nodeのpage_span」で取りこぼす式（1ノード内に複数書式／ノード未立ての埋込書式＝契約解消型）の扱い — page_span内をvisionで再分割する運用でよいか。
