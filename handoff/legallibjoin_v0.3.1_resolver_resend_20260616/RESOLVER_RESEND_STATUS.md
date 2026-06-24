# legallibjoin v0.3.1 — resolver human_review 差し戻し候補 (2026-06-16, report-only)

> Phase 0 所見3/4 の実体化。**原本 `resolver_decisions.normalized.jsonl` は上書きしていない**
> (mtime Jun 8 のまま)。差し戻し適用は derived ファイルとして別出力。apply は HOLD 継続。
> corpus 待ち (owner決定=b) とは**独立**に進められる resolver 品質修正。

## 1. 候補 70 件 (= 58 + 12)

| 理由 | 件数 | from → to | 根拠 |
|---|---:|---|---|
| `defer_new_recall_isbn_in_canonical` | 58 | defer_new → human_review | bucket=defer_new (canonical 不在として create 予定) だが **その isbn が canonical に存在** = resolver の recall 取りこぼし。 |
| `auto_accept_false_positive` | 12 | auto_accept → human_review | bucket=auto_accept だが `is_real_suspect` (版番号衝突/版マーカ非対称/核相違/年差≧2) = 実質要レビュー。apply 時に edition gate が物理拒否すべき対象。 |

## 2. 再現 (L1 deterministic self-verification)

一次ソース = Phase 0 の certified 成果物 `edition_identity_sample.jsonl` (sha256 固定)。
```
python3 scripts/resolver_resend_candidates.py \
  --edition-sample handoff/legallibjoin_v0.3.1_phase0_20260615/edition_identity_sample.jsonl \
  --resolver       ~/alo-ai/work/legallib_dl/_resolve/resolver_decisions.normalized.jsonl \
  --out            handoff/legallibjoin_v0.3.1_resolver_resend_20260616
# => candidates=70  by_reason={auto_accept_false_positive:12, defer_new_recall_isbn_in_canonical:58}  consistent=true
```
- 58 は resolver+canonical からの独立再計算とも一致 (defer_new かつ isbn∈canonical = 58)。
- 整合 guard: derived の再バケット件数 (70) == 候補件数 (70)。book_id 一致時に isbn も一致を確認。

## 3. 成果物

| ファイル | 内容 |
|---|---|
| `resolver_resend_candidates.csv` / `.jsonl` | 70 件の差し戻し候補 + 根拠 (edition_status / title_diff_kind / 版sig / 両タイトル等)。owner レビュー用。 |
| `resolver_decisions.resend_applied.jsonl` | **derived**: 原本 2,760 件のうち該当 70 件のみ bucket=human_review + `original_bucket`/`resend_reason` を付与。原本は不変。 |

## 4. 採用パス (HOLD・owner/統合時に判断)

これは **候補の提示と derived 版の用意**まで。原本の置換はしていない。
join (DD-TOCADOPT-001 統合 corpus 経由 / owner決定=b) が走る際に:
- 接合の入力 resolver を `resolver_decisions.resend_applied.jsonl` に差し替える、または
- 70 件を owner が個別 ratify してから原本へ反映。

どちらにせよ **human_review 化は保守側** (auto 確定を増やさず、レビュー対象を増やすだけ) なので
誤差し戻しの blast radius は小さい。確実な別版/取りこぼしを apply 前に止める効果。

## 5. 残注意

- `auto_accept_false_positive` の 12 件は title が cosmetic に見えても reason が
  年差≧2 / 版マーカ非対称 等であり `title_diff_kind` が None のことがある (= 正しい挙動)。
  CSV の `edition_reason` 列で実際の発火理由を確認できる。
