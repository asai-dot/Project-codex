# gate_edition_identity_phase0_regression — classify_edition_identity_v2 回帰 (report-only)

DD-TOCADOPT-001 v0.2 / GPT required gate 2 の充足証跡。
`scripts/edition_identity_v2.py` を Phase0 の 2,082 対 (`edition_identity_sample.jsonl`) へ適用。

## v1 → v2 の status 分布

| | v1 (現行 classify_edition_identity) | v2 (強化版) |
|---|---:|---:|
| resolved_same_manifestation | 1,738 | **1,957** |
| suspected_different_manifestation | 344 | **72** |
| insufficient_evidence (要review) | 0 | **53** |

別版疑いの過検知 **344 → 72** に圧縮 (偽陽性 ≈226 を解消)。

## gate 充足

- **確実な別版 (版番号衝突) を SUSPECTED に: 26/26** ✓
- **装飾/副題差を RESOLVED_SAME で通過: 203/210** ✓
  - 残り 7 は **バグではなく v2 の精度向上**: phase0 の title 分類が cosmetic/副題と誤った
    実際の別版/別巻を、v2 が年差≧2 + 版信号で救出。例:
    - `労働関係訴訟Ⅱ`(2018) vs `労働関係訴訟II 改訂版`(2021) = 改訂版
    - `コンメンタール民事訴訟法Ⅵ`(2014) vs `…V[第2版]`(2022) = 別巻 (Ⅵ≠Ⅴ)
    - `個人情報保護法コンメンタール`(2021) vs `…第2版 第1巻`(2025) = 第2版
  - → これらは「同一本の再分割」ではなく真の別物。gate_2 の趣旨 (同一本を割らない) は保持。

## Required note 2 の実装

ISBN 一致だけで確定しない。`_classify_pair` は版番号一致でも:
- page_count 差が tolerance(10%) 超 → INSUFFICIENT (要review)
- publisher 正規化不一致 → INSUFFICIENT
- 核タイトル空 → INSUFFICIENT
（本データは canonical 側に page_count / publisher が無く未発火。SRU enriched で再検証可能。）

## 検証
- `tests/test_edition_identity_v2.py` 9件 + `tests/test_phase0_inventory.py` 18件 = 27 PASS。
- 書き込み: canonical/snapshot/DB へ 0 (report-only)。
