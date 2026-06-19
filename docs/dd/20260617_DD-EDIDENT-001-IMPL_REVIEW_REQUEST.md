---
request_id: DD-EDIDENT-001-IMPL
topic: edition/manifestation 同定ゲート v2 + resolver 差し戻しの批判的監査 (ratify 前・自己申告 weak points 付き)
gate: implementation_review
supersedes: なし
parallel_related: [DD-EDIDENT-001, DD-TOCADOPT-001-IMPL, DDLEGALLIBCONCORD]
current_governing_result: DD-EDIDENT-001 = SUBSUMED (design-of-record / v2 並行実装済)
result_expected_filename: DD-EDIDENT-001-IMPL_result.md
status: queued
queued_date: 2026-06-17
守秘: 設計・状態語彙・件数レベルのみ。実依頼者データ本文は含めない。certified Phase0 サンプル(sha256固定)のみで検証。
---

# DD-EDIDENT-001 実装 (edition identity v2 + resolver 差し戻し) の批判的監査依頼

## 0. 依頼の趣旨

EDIDENT は全パイプラインのキーストーン (TOCADOPT Step1 / 接合 apply gate / repair gate の同定基盤)。
owner は **GPT 監査 → owner ratify** の経路を選択。tocadopt 同様 **甘い PASS は不要・赤入れを期待**する。
実装者(CC)が自信を持てない箇所を §4 に洗いざらい開示する。

production apply / canonical / policy 本番切替は **HOLD 継続**。本実装は report-only・書込ゼロ。
原則: 「title が違う/年が違うは別版の証拠ではない。一次信号は《タイトルから抽出した版番号の相違》」。

## 1. 監査対象 (branch claude/legallib-integration-design-Jgrtf, 2e6629a)

- `scripts/edition_identity_v2.py` — 強化版 classify (版番号抽出/核包含/年±1/Required note 2)。
- `scripts/resolver_resend_candidates.py` — §4 resolver 差し戻し候補抽出 (report-only)。
- `scripts/phase0_inventory.py` — `edition_signature` / `_core_title` / `title_diff_kind` / `is_real_suspect` (昇格元)。
- `tests/test_edition_identity_v2.py` (18 checks) — 単体 + **実 2,082 対の §6 回帰凍結**。
- `tests/test_resolver_resend.py` (10 checks) — §4 の 12+58=70 を凍結。
- 一次証拠: `handoff/legallibjoin_v0.3.1_phase0_20260615/edition_identity_sample.jsonl` (2,082 対, sha256 固定)。
- 全テスト 975 green。

## 2. owner 決定 (2026-06-17 ratify・本監査の前提)

| OQ | 決定 | 実装状態 |
|---|---|---|
| OQ-1 版マーカ非対称 | **要レビュー** | `INSUFFICIENT` で実装 (apply 不可)。 |
| OQ-2 共有 `_STRIP_RE` 拡張 | **実データ dry-run 後に延期** | 未適用。v2 は自前 `_CORE_STRIP` で自経完結 (identity 非依存)。concordance クラスタリングは未修正のまま残置。 |
| OQ-3 resolver 差し戻し | **本 DD に含める** | `resolver_resend_candidates.py` + test で 70 件を CI 凍結。 |
| OQ-4 年差トレランス | **±1** | `year_tolerance=1`。 |
| OQ-5 改訂/新版系 | rev 同士は核一致なら同一・v1↔rev は非対称 | `edition_signature` / `title_diff_kind` で実装。 |

## 3. 検収 §6/§4 の達成 (CI 凍結済の実測)

実 2,082 対に v2 を適用 (test_edition_identity_v2 が固定):

| 層 (title_diff_kind) | 件数 | v2 status | §6 |
|---|---:|---|---|
| edition_number_conflict | 26 | **suspected 26/26** | 真の別版を取りこぼさない ✓ |
| cosmetic | 123 | **resolved_same 123** | 過検知回収 ✓ |
| subtitle_difference | 87 | resolved_same 80 / suspected 7(年差≧2) | 同一本回収 ✓ |
| edition_marker_asymmetry | 53 | insufficient 53 | 要レビュー (OQ-1) |
| genuine_title_diff | 30 | suspected 30 | 核相違は混ぜない |
| (差分なし) | 1763 | resolved_same 1754 / suspected 9(年差≧2) | |

全体: resolved_same 1957 / suspected 72 / insufficient 53。**別版疑い v1 344 → v2 72**。
4ラベル・`APPLY_OK_STATUS={resolved_same,manual}` 不変。resolver §4: auto_accept 偽陽性 12 + defer_new 58 = 70 を human_review へ (report-only)。

## 4. 実装者が自信を持てない箇所 (= 赤入れ対象・全件開示)

重大度: **H**=同定の正しさに直結 / **M**=精度 / **L**=様式。

- **W1 (H) 回帰の自己参照性**: §6 回帰は `title_diff_kind` (= phase0_inventory の診断ロジック) が貼ったラベルに
  対して v2 を検証している。同じ核ロジック族なので「v2 が phase0 診断と一致」を固定しているだけで、
  **独立した ground truth ではない**。独立アンカーは `known_conflict_golden.md` の確実な別版 26 のみ。
  cosmetic/subtitle のラベル自体が誤っていれば検出できない。
- **W2 (H) subtitle 包含の誤マージ risk**: 核タイトルの**包含**を「副題差=同一本」と判定する (§3.3)。
  実際には別本だが片方の核がもう片方の部分文字列になるケース (例: 短い総論題が長い別本の一部) を
  誤って resolved_same にしうる。サンプルでは年差≧2 の7件が suspected に落ちて救われたが、
  **年信号が無い包含**は誤マージに倒れる。
- **W3 (M) publisher 完全一致の脆さ**: Required note 2 は normalize 後の publisher 不一致を INSUFFICIENT に
  落とす。「有斐閣」vs「有斐閣株式会社」「(株)有斐閣」等の**社名表記ゆれで過剰に INSUFFICIENT**になりうる
  (同一本を確定不可にする = recall 低下)。閾値は exact match のみで部分一致を見ていない。
- **W4 (M) 版番号抽出の被覆**: `_ED_NUM_RE`/`_kanji_to_int` は「第N版」系中心。「新装版」「第3刷」「補訂2版」
  「上巻/下巻 + 版」「2nd ed.」等の変種で抽出漏れ・誤抽出がありうる。サンプル外の実 corpus 形式は未検証。
- **W5 (M) 和暦・刷年**: `_year` は最初の4桁を取る。「平成20年」など**和暦は None**になり年判定が効かない。
  「2020年第2刷」は 2020 を取るが初版年と刷年の区別はしない。
- **W6 (M) is_real_suspect と v2 の二重定義**: resolver 差し戻しは `phase0_inventory.is_real_suspect` を使い、
  identity 判定は `classify_edition_identity_v2` を使う。「実質要レビューか」の判定が**2 経路**に分かれ、
  将来ドリフトしうる。単一化すべきでは。
- **W7 (M) worst-case 集約**: 3 源以上で最も疑わしいペアを採る。1 つのノイズ源が全クラスタを
  ブロックしうる。また rank 順序 suspected(3) > insufficient(2) > resolved(1) の妥当性 (insufficient より
  suspected を優先) は要検討。
- **W8 (L) OQ-2 残置の射程**: 共有 `normalize_title` 未修正のため concordance の title クラスタリングは
  依然 cosmetic 差で割れうる (DD §3.1 residual)。edition gate からは外したが DD スコープに穴が残る。
- **W9 (L) 差し戻しは候補のみ**: §4 は derived ファイルを書くだけで live resolver には未適用 (apply HOLD)。

## 5. 判定してほしいこと

1. v2 の判定順序 (§3.4) と Required note 2 は安全か。**W1 (自己参照回帰) / W2 (包含誤マージ)** は
   再 MODIFY 級か、NOTE 級か。
2. W3 (publisher) / W5 (和暦) は ratify ブロッカーか、実 corpus 投入時の改善事項か。
3. W6 (is_real_suspect と v2 の二重定義) は単一化必須か。
4. resolver 差し戻し (§4) を本 DD に含めた設計 (OQ-3) は妥当か。
5. PASS / PASS_WITH_NOTES / MODIFY_REQUIRED の判定。

HOLD 不変・report-only・certified Phase0 サンプルのみ。赤入れ歓迎。
