# DD-CASEEVAL-001 — 判例同一性の精度評価（gold set ＋ false-merge 中心の計測）**draft v0.1**

- 起票: 2026-06-22 JST ／ 番頭: Claude Code (remote)
- lifecycle: **draft / candidate**（GPT Pro 独立監査 未了 → DDCASE ゲート）
- domain: CASE（判例オブジェクトの精度計測基盤）。reality_check §6.4 で予告された `DD-CASEEVAL` の本体化
- parent: `DD-CASE-001`(accepted v1.0) / `DD-CASEID-001`(accepted v1.0)
- related: `DD-CASEID-002`(符号) / `DD-CASEID-003`(forum) / `DD-CASE reality_check`(D1-LIC/OPAC metrics)
- 実装: `scripts/case_eval.py`(スコアラ) / `scripts/test_case_eval.py`(自己検証) / `app/data/case_identity/case_eval_gold_template.jsonl`

> **目的**: 「測れないものは上げられない」。accepted DD 群（CASE-001/CASEID-001/002/003）はいずれも *corpus 回帰* を Mac CC に委ねるが、**精度の定義が無い**。本DDは判例同一性（名寄せ）の精度を **false-merge 中心**で定義・計測する read-only 基盤を確定する。**設計のみ・DBなし**（AC-6/AN-5 HOLD 継承）。

---

## 0. スコープと前提
判例オブジェクトの精度は4層（L1 同一性 / L2 解釈 / L3 連結 / L4 出力）。本DD v0.1 は **L1 同一性（名寄せ精度）**に集中する。理由: L1 が誤ると L2-L4 すべてが汚染され、かつ監査が AN-4 で「false merge が最大の危険・初回は split 寄り」と確定済だが**未計測**。

## 1. 決定

### 1.1 計測モデル（clustering eval・ペア単位）
observation を真の case（gold cluster）と採番結果（pred cluster）で比較。

| 量 | 定義 |
|---|---|
| TP | same_pred ∧ same_gold |
| **false_merge (FP)** | same_pred ∧ ¬same_gold ＝ **別判断を1本化した誤り（最重要）** |
| false_split (FN) | ¬same_pred ∧ same_gold |
| precision | TP/(TP+FP) |
| recall | TP/(TP+FN) |
| **false_merge_rate** | FP/(TP+FP) = 1−precision（**主指標**） |
| per_tier_precision | same_pred ペアを高リスク側 Tier(A/B/C)で層別した precision |

→ 実装 `scripts/case_eval.py`。自己検証 `test_case_eval.py` は合成 gold で **false_merge=3 / Tier A precision=1.0・Tier C precision=0.0 を検出**（exit 0）。

### 1.2 gold set（`case_eval_gold_template.jsonl`）
各 observation に `true_case_key` を付した正解集合。スキーマ: `observation_id, true_case_key, forum_code, decision_date, case_number_norm, external_id, hard_negative_type, source`。
- **正例の核**: NII∩D1 norm 一致 12,661（CASEID-001 §4 実測）を「同一 case」シードとする。
- **ハード負例（意図的に混入）**＝精度を厳しく測る肝:
  | type | 例 | 落とし穴 |
  |---|---|---|
  | `same_number_diff_forum` | 東京地裁 R3-ワ-123 と 大阪地裁 R3-ワ-123 | 事件番号一致だけで merge する誤り |
  | `merged_sibling_docket` | 併合の第2 docket | 同一視 or 取りこぼし（CASEID-002 1:N） |
  | `provisional_no_natural_key` | 匿名/受任(jufu) | 自然キー不能を強引に merge |
  | `era_decision_date_mismatch` | 平成31事件番号×令和元年判決 | 西暦逆引きの誤同定（CASEID-002 MF-1） |

### 1.3 指標セット（reality_check §6.4 を統合・拡張）
binding precision/recall・**false_merge_rate**・false_split_rate・**Tier A/B/C 別 precision**・era unresolved 率・multi-docket 回収率。D1-LIC（resolved 5,475 等）・OPAC（accepted edge 0）は外部証拠強度として併記。

### 1.4 運用方針（AN-4 を数値化）
- **precision 優先**。Tier A 自動 bind は **per_tier_precision[A] が目標閾値以上の高信頼サブセット**に限定。
- 初回は **split 寄り**（false_merge を false_split より厳しく罰する）。閾値は gold で調整。
- リグレッションゲート: 新ロジックが **false_merge_rate を悪化させたら fail**。

## 2. why / alternatives_rejected
- **why ペア単位 false_merge 中心**: 法務では「別事件を同一視」が最も有害（誤引用・守秘混線）。recall より precision、特に false_merge を主 KPI に。
- **rejected**: 全体 accuracy 単一値（merge/split の非対称な害を隠す＝却下）。parse 率だけで精度評価（bind 精度を測らない＝却下、現状の穴）。閾値を recall 最大化で決める（false_merge 増＝却下）。

## 3. downstream_effect
- read-only。新規 DB write なし。`case_eval.py` は CSV/JSONL 入力でスコア出力。
- ②false-merge ガード（blocking key＋多シグナル合意）/④引用検証ゲート の効果判定土台。
- corpus-level 実行は **Mac CC**（実 observation データ依存）。本DDは指標定義＋合成検証まで。

## 4. verification（現状）
- deterministic_self_verification = **fixture-level done**: `test_case_eval.py` green（exit 0）。false_merge/false_split/per-tier precision/ValueError を検出。
- corpus-level = **Mac CC**（NII∩D1 12,661＋ハード負例を実 gold 化して実行）。
- independent_meaning_audit = **未了**（本draftを DDCASE ゲートへ）。owner_approval = 未了。

## 5. follow-up
- gold set を実データで構築（NII∩D1 正例＋ハード負例の体系的マイニング）。
- Tier A precision 目標閾値の確定（owner 判断）。
- L2（canonical source 選択精度）・L3（edge precision）・L4（引用検証）の eval を v0.2 以降で追加。
- ②〜⑤（false-merge ガード/多源コロボ/引用ゲート/サンプル監査）を本指標で評価。
