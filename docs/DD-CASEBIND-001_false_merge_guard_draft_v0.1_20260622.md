# DD-CASEBIND-001 — false-merge 防止ガード（名寄せの自動bind境界）**draft v0.1**

- 起票: 2026-06-22 JST ／ 番頭: Claude Code (remote)
- lifecycle: **draft / candidate**（GPT Pro 独立監査 未了 → DDCASE ゲート）
- domain: CASE（判例同一性の精度・②false-merge ガード）
- parent: `DD-CASEID-001`(accepted v1.0, Tier A/B/C・resolution_log) / `DD-CASE-001`(accepted v1.0, merge禁止・edge)
- related: `DD-CASEEVAL-001`(精度計測・本ガードの効果判定) / `DD-CASEID-003`(forum_code) / `DD-CASEID-002`(norm)
- 実装: `scripts/case_bind_guard.py` / `scripts/test_case_bind_guard.py`（gold で false_merge=0 実証）

> **目的**: 精度4層の L1 同一性で、**別判断の1本化（false merge）を構造的に防ぐ**。監査 AN-4「false merge が最大の危険・初回は split 寄り」を実装則に落とす。`DD-CASEEVAL` の主指標 `false_merge_rate` を直接下げる打ち手。**設計のみ・read-only**（AC-6/AN-5 HOLD 継承）。

---

## 0. スコープ
CASEID-001 が決めた束ね順（決定的自然キー→強外部ID→fuzzy→人手）に対し、本DDは **「いつ自動 bind してよいか／いつ review に逃がすか」の境界＝ガード**を確定する。bind 戦略そのものでなく、**false-merge を出さない fail-closed 規則**。

## 1. 決定（ガード規則 G1〜G5）

| 規則 | 内容 | 防ぐ誤り |
|---|---|---|
| **G1 blocking** | 比較は決定的キー `(forum_code, decision_date, case_number_norm)` 内のみ。**forum_code が違えば絶対に同一視しない** | `same_number_diff_forum`（同番号別裁判所の誤統合） |
| **G2 provisional** | `case_number_norm` が null / `era_resolution_status=unresolved` は**自動bind禁止**。observation 単位 provisional、人手で confirmed 昇格 | 匿名/受任/元号未解決の強引 merge |
| **G3 multi-signal 合意** | 同一決定キー内で外部IDが**同一source内で衝突**するなら、自然キー一致でも自動bindせず review(Tier B) | 同一番号に別事件が紛れる誤統合 |
| **G4 別docket** | `case_number_norm` が異なれば**別 case_key**（併合は `alo_edges` link、merge しない） | 併合 sibling の同一視（CASE-001 AN-2） |
| **G5 Tier 境界** | 決定キー合意=**Tier A（auto-bind）**。外部ID/fuzzy のみの跨ぎ候補=**Tier B/C（review・非merge）** | 弱い証拠での自動統合 |

- **split 寄り（AN-4 数値化）**: 自動bind は Tier A（決定的多シグナル合意）のみ。Tier B/C/prov は **merge しない**＝observation 単位に倒す。recall を犠牲にしても false_merge を出さない。
- **decision_basis 記録**: 各決定を `resolution_log`（CASEID-001 should_fix②）に `tier / signals / decided_by / decided_at` で残す。
- **confidentiality 非干渉**: jufu/matter ノードは identity evidence として bind 計算に使えるが（CASE-001 AC-3）、出口可否は本ガードの判断対象外（DDCASESOURCE）。

## 2. DD-CASEEVAL との結線（効果の実証）
ガードの `auto_bound_assignment`（Tier A のみ採用・他は split）を **gold テンプレ（ハード負例4型）に適用 → `case_eval.score` で計測**：
- **結果: false_merge=0 / precision=1.0 / recall=1.0**（`test_case_bind_guard.py`、exit 0）。
- すなわち本ガードは `same_number_diff_forum`・`merged_sibling_docket`・`provisional`・`era_mismatch` のいずれも**自動統合しない**ことを機械的に実証。
- **回帰ゲート**: 将来 bind ロジック変更時、本テスト＋実 gold で `false_merge_rate` が悪化したら **fail**（CASEEVAL §1.4）。

## 3. why / alternatives_rejected
- **why fail-closed blocking**: 自然キーの第1要素（forum）を跨いだ比較を**そもそも禁止**すれば、同番号別forum の false-merge は構造的に起きない（閾値調整に頼らない）。
- **rejected**: 全 observation を fuzzy 比較し閾値で足切り（forum 跨ぎ false-merge を閾値依存にする＝却下）。自然キー一致だけで無条件 auto-bind（外部ID衝突を見逃す＝却下、G3）。null norm を近傍 bind（誤同定＝却下、G2 provisional）。併合を同一 case に畳む（CASE-001 AN-2 違反＝却下、G4 edge）。

## 4. verification（現状）
- deterministic_self_verification = **fixture-level done**: `test_case_bind_guard.py` green（exit 0）。gold テンプレ false_merge=0＋G1-G5 単体。
- corpus-level = **Mac CC**（実 observation・実 gold で `false_merge_rate` / Tier A precision を計測）。
- independent_meaning_audit = **未了**（DDCASE ゲートへ）。owner_approval = 未了。

## 5. follow-up
- 実 gold（NII∩D1 12,661＋ハード負例）で Tier A precision 閾値を確定（owner）。
- G3 を強化: 外部ID の source 横断照合（D1-LIC crosswalk を corroboration 源に＝③へ接続）。
- review queue の人手UI 最小項目（CASEID-001 should_fix①）と接続。
- bind 変更の CI 回帰（本テストを必須化）。
