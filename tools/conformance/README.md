# conformance — 設計三部作 適合性ハーネス（Phase 0）

DD-LAYOUT-001 / DD-XMODAL-001 / DD-XDOC-001 の**受入試験を実行可能コードにする**依存ゼロ
ハーネス。「accepted」を「executable & tested」へ。**production に一切触れない純関数のみ。**

> 原則（DD-IMPL-ROADMAP-001 §2-6）：DDL より前に「設計が機械的に通る」ことを証明し、
> 以降の本番実装を de-risk する。GPT 監査が最も誤実装を警戒した箇所を最初に固める。

## 現状（v0.7 反映分）

| module | DD 箇所 | 内容 |
|---|---|---|
| `xdoc_canonical.py` | XDOC v0.7 §5 | `alignment_observation_id` 正規化（symmetric side 正規化・単一 cardinality・companion を ID 材料・self-loop gate） |
| `xdoc_eligibility.py` | XDOC v0.7 §7 | eligibility policy engine（purpose×target 互換・positive relation 集合・priority 解決・none/invalid 防御） |

## 受入試験カバレッジ（XDOC v0.7 §12）

| # | 試験 | テスト |
|---|---|---|
| 2 | purpose×target 別 key | `test_02_distinct_keys_per_purpose_target` |
| 3 | shared origin → ineligible / unknown → hold / invalid → 110 | `TestProofCorroboration` |
| 6 | absence + coverage 不完全 → ineligible | `test_06_absence_with_incomplete_coverage_ineligible` |
| 9 | symmetric side-swap → 同一 id / multi-member 先頭でも一意 / directional は別 | `TestSymmetricId` |
| 10 | companion set・field 変化で id 変化 | `TestCompanionAndDrift` |
| 12 | reviewed=none → positive target で ineligible | `TestReviewedNone` |
| (gate) | self-loop / 空 side / 非互換組合せ | `TestSelfLoopGuards`, `test_compatibility_false_rejected` |

## 実行

```bash
python3 -m unittest discover -s tools/conformance/tests -p 'test_*.py' -v
```

依存なし（Python 3.9+）。production DB / Box / OCR に触れない。

## 未実装（次の Phase 0 増分）

- LAYOUT: page_block hash bundle・coverage projection・reading_order_key(LexoRank)・block_ref。
- XMODAL: agreement_signal・external_source_family DISTINCT 計数・D0/D1/D2・confirmed=D2+独立2family。
- XDOC 残: coverage `range_class` adapter（interval_1d/grid_2d/rect_2d）・`support_edge_effective`・
  method capability（required companion ⊆ applied）・use_assessment revision 履歴・cluster pairwise。
- 合成 fixture を JSON 化し、スキーマ（JSON Schema）と相互検証。
