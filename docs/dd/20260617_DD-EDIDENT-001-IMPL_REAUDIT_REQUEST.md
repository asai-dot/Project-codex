---
request_id: DD-EDIDENT-001-IMPL-REAUDIT
topic: edition identity v2 corrective patch 再監査 (MODIFY_REQUIRED H1-H8 の証拠付き是正)
gate: implementation_review
supersedes: なし
parallel_related: [DD-EDIDENT-001, DD-EDIDENT-001-IMPL, DD-TOCADOPT-001-IMPL, DDLEGALLIBCONCORD]
current_governing_result: DD-EDIDENT-001-IMPL = MODIFY_REQUIRED (2026-06-20, GPT-5.5)
result_expected_filename: DD-EDIDENT-001-IMPL-REAUDIT_result.md
status: queued
queued_date: 2026-06-17
守秘: 設計・状態語彙・件数レベルのみ。実依頼者データ本文は含めない。certified Phase0 サンプル + 合成 adversarial gold のみ。
---

# DD-EDIDENT-001 v2 corrective patch 再監査依頼

## 0. 趣旨

前回 MODIFY_REQUIRED (blocker H1-H4 / P1 H5-H8) を **全件証拠付きで是正**した。本書は §7
re-audit acceptance gates を1対1で充足したことの証拠インデックス。owner 裁定: classifier は
**isbn/edition/volume を読む契約** (H1 の選択肢A)。selector 既定は再監査完了まで v1 のまま。
production apply / canonical promotion / policy rewrite は HOLD 継続・report-only・書込ゼロ。

## 1. blocker/P1 → 是正 → 証拠 (前回 §3 を1対1で充足)

| # | 指摘 | 是正 | 証拠 (test/code) |
|---|---|---|---|
| **H1** | ISBN/明示edition/volume ゲート消失 | evidence-model 再設計。`_isbn_ev`/`_edition_field_ev`/`_volume_ev` で不一致を **読んで** hard conflict 検出 | `edition_identity_v2._classify_pair` / `test_edition_adversarial::test_v1_hard_check_parity` |
| **H2** | title一致・substring 単独で apply 到達 | **positive-evidence floor**: RESOLVED は isbn一致 or 核一致+≥2独立信号のみ。substring は review | gold `title_containment_no_isbn`→review / unit `subtitle 包含・ISBN不明→insufficient` |
| **H3** | 同signature で年乖離免除 | edition signature/isbn 一致でも year/page/publisher 乖離は review (Required note 2)。年 anomaly を免除しない | gold `same_sig_large_year_gap`→suspected / 2082 で同isbn+年大差→insufficient |
| **H4** | edition parser の rev 潰し/marker 残留 | `edition_grammar.py` 新設。番号/訂/ラベル/複合版をトークン化、core から完全除去、未知marker→review | gold `tei_vs_hotei`/`marker_move_same`/`unknown_marker` |
| **H5** | 回帰 oracle が classifier と循環 | classifier 独立の **人手 adversarial gold** (16ケース/10class 双方向)。件数でなく意味を固定 | `make_edition_adversarial_gold.py` / `test_edition_adversarial.py` |
| **H6** | resend が stale v1 truth 依存・book_id 後勝ち | v2 で raw から再計算・book_id 一意性 fail-closed・classifier_version/行数conservation | `resolver_resend_candidates.py` / `test_resolver_resend` |
| **H7** | 判定証跡が弱い | pair-level evidence trace + classifier/normalizer/grammar version を出力 | `classify_edition_identity_v2` 戻り値 `evidence`/`pair_traces`/`*_version` |
| **H8** | 欠損=矛盾なしになりやすい | match/mismatch/unknown/parse_error を区別。和暦→parse_error→review。unknown は positive に数えない | gold `wareki_parse_error`/`missing_fields` |

## 2. §7 re-audit acceptance gates の充足 (機械検証)

`test_edition_adversarial.py::test_reaudit_acceptance_gates` が固定:

- 10 adversarial class が独立 gold で全件 pass ✓ (`test_gold_all_match` 16/16)
- ISBN / edition / volume mismatch の false merge = 0 ✓
- substring-only の apply = 0 ✓
- same signature + large divergence の apply = 0 ✓
- parser unknown / error が silent same に入らない ✓
- resolver resend の row conservation と duplicate gate が pass ✓ (`test_resolver_resend`)
- v1 から維持すべき hard checks の **parity matrix** を提示 ✓ (`test_v1_hard_check_parity`: isbn/edition/volume/版番号衝突/核相違 を全て suspected で検出)
- selector 既定値は v1 のまま ✓ (`edition_select` default version="v1")

## 3. 前回自己申告 W1-W9 の最終状態

監査で全て「成立」とされた W1-W9 を是正: W1 独立gold化 / W2 substring floor / W3 publisher は
normalize 後 mismatch を review (alias 正規化は将来課題として明記) / W4 grammar 化 / W5 和暦
parse_error / W6 二重定義解消 (resend も v2 へ単一化) / W7 worst-case + evidence trace /
W8 unicode/marker gold / W9 candidate-only 維持 + stale v1 除去。

## 4. 挙動 (是正後・CI 凍結)

- 独立 adversarial gold: 16/16 期待一致。
- 2082 二次ロック (isbn 注入): resolved 1917 / suspected 60 / insufficient 105。
  版番号衝突 **26/26 を suspected 保持** (取りこぼし 0)。版signature mismatch を resolved に倒さない。
- resolver resend: auto_accept 偽陽性 41 (Required note 2 で v1 の 12 から増)・defer_new 58。
- known_conflict_10: 真の anomaly 8件 block / marker-move 偽陽性 2件のみ正しく resolved。
- 全テスト 1023 green。

## 5. 残る自己申告 (正直開示)

- **R1 (M)** publisher は normalize 後 exact mismatch を review にするのみ。社名 alias 辞書
  (「有斐閣」↔「(株)有斐閣」) は未実装で、別表記を過剰に review にしうる (recall 低下方向・安全側)。
- **R2 (L)** 2082 二次ロックは isbn を注入して評価する (resolver が isbn 一致で対にした provenance に
  忠実)。実 pipeline で isbn 無し bib を比較する経路があれば floor が厳しく出る (review 増)。
- **R3 (L)** edition grammar は和書の版表記中心。洋書 "2nd ed."・刷数表記は未カバー (未知→review に倒れる)。

## 6. 判定してほしいこと

1. H1-H8 は閉じたか。§7 acceptance gates を満たすか。
2. R1-R3 は再 MODIFY 級か NOTE 級か。
3. v2 ratify / selector 既定切替を GO してよいか (production apply は引き続き HOLD)。

HOLD 不変・report-only・合成/certified データのみ。赤入れ歓迎。
