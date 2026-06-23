# DD-CASECITE-001 — 引用検証ゲート（CaseBundle のハルシネーション cite を 0 に）**draft v0.1**

- 起票: 2026-06-22 JST ／ 番頭: Claude Code (remote)
- lifecycle: **draft / candidate**（GPT Pro 独立監査 未了 → DDCASE ゲート）
- domain: CASE（判例精度・④出力 L4）
- parent: `DD-CASE-001`(accepted v1.0, CaseBundle/出口AC-3) / `31_case_layer.md`(§6.3 guards, §2.3 alo_pointers)
- related: `DD-CASEEVAL-001`(計測) / `DD-CASEBIND-001`(②) / `DD-CASECORROB-001`(③・canonical 源)
- 実装: `scripts/case_cite_gate.py` / `scripts/test_case_cite_gate.py`

> **目的**: 回答(CaseBundle)を serve する前に検証し、**根拠が解決しない引用（ハルシネーション cite）・無根拠 claim を fail-closed で 0 にする**。これはユーザー体感の精度（L4 出力）に直結。31_case_layer §6.3 の CaseBundle guards を**実行時ゲート**に落とす。**設計のみ・read-only**。

---

## 0. スコープ
L1〜L3（同一性・解釈・関係）がどれだけ正しくても、**出力段で根拠なき引用を1つ出せば信頼は壊れる**。本DDは CaseBundle/回答 payload の serve 前検証を確定する。検証は読み取りのみ、合否を返すだけ（DB 変更なし）。

## 1. 決定 — ゲート規則 V1〜V7（fail-closed）

| 規則 | 検証（31層 guard 由来） | 弾く誤り |
|---|---|---|
| **V1** must_cite_uris | 各 claim は ≥1 の `canonical_uri` を引用 | 無引用の主張 |
| **V2** cite_resolves | 引用 uri が既知 case に解決 | **ハルシネーション cite（存在しない判例の引用）** |
| **V3** all_claims_have_evidence | 各 claim は ≥1 evidence | 根拠なき主張 |
| **V4** pointer_case_match | evidence.case_uri が claim の cite に含まれ既知（`gate_pointer_case_mismatch`） | 別事件の本文を根拠に偽装 |
| **V5** pointer_range_inbounds | range が `[0, full_text_len]`・start≤end（`gate_pointer_range_oob`） | 原文範囲外ポインタ |
| **V6** annotation_source_canonical | `annotation_used.source` が `is_canonical` | 非正準源の要旨を権威化 |
| **V7** egress_confidentiality | **global serve は `open∧public`（=can_global_index）のみ引用**（AC-3） | 機密/商用ライセンス判例の global 漏出 |

- **fail-closed**: V1〜V7 のいずれか違反で **bundle 不合格 → serve しない**（部分配信もしない）。
- **scope 依存**: `serve_scope=global` は V7 を課す。`matter` は当該 matter 内なので egress 違反は課さない（解決・根拠は必須）。
- **L4 の精度目標**: ハルシネーション cite 率 = **0**（V2/V4 で構造的に担保）。

## 2. DD-CASEEVAL / ③CORROB との結線
- `is_canonical` 源の選択は ③CORROB の L2 annotation corroboration と接続（複数 canonical 源が一致した要旨を優先）。
- 計測: `DD-CASEEVAL` の L4 指標として **cite_resolution_rate=100% / unsupported_claim=0 / egress_violation=0** を回帰ゲート化。
- ②BIND の出力（confirmed case 集合）が known_cases を定義。provisional/`pending_source_fixation` は authoritative cite に**使わない**（②G2・CASEID-002 AC-2 と一致）。

## 3. why / alternatives_rejected
- **why serve 前 fail-closed**: 法務回答で誤引用は致命的（存在しない判例・別事件の根拠）。確率的に減らすのでなく、**解決しない引用は出さない**構造ゲートにする。
- **rejected**: cite を後検証（出してから直す＝却下、出た時点で害）。confidence 閾値で足切り（ハルシネーションを許容＝却下）。global で機密判例を要約配信（守秘違反＝却下、V7）。pointer 検証を省略（別事件本文の偽装根拠＝却下、V4/V5）。

## 4. verification（現状）
- deterministic_self_verification = **fixture-level done**: `test_case_cite_gate.py` green（exit 0）。正常通過＋V1-V7 各違反（ハルシネーション cite・無根拠・OOB・非canonical源・global×機密）を fail-closed で遮断。
- runtime/corpus = **Mac CC**（実 CaseBundle ランタイム・実 cases に対し V1-V7 を常時ゲート）。
- independent_meaning_audit = **未了**（DDCASE ゲートへ）。owner_approval = 未了。

## 5. follow-up
- known_cases を ②BIND の confirmed 集合に結線（provisional/pending を除外）。
- V6 の canonical 選択を ③CORROB の多源一致で強化。
- annotation_maturity（preliminary は要旨 null）を V3 と整合（preliminary 判例は要旨 claim を出さない）。
- runtime 統合は production gate（DDL/serving HOLD）。
