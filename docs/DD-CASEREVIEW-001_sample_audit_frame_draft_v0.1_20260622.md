# DD-CASEREVIEW-001 — サンプル監査 frame（生きた精度の監視・ドリフト検知）**draft v0.1**

- 起票: 2026-06-22 JST ／ 番頭: Claude Code (remote)
- lifecycle: **draft / candidate**（GPT Pro 独立監査 未了 → DDCASE ゲート）
- domain: CASE（判例精度・⑤運用監視）
- parent: `DD-CASEID-001`(accepted v1.0, should_fix① 人手最小項目 / CASE_HUMAN_REVIEW_SAMPLE_FRAME) / `DD-CASE-001`(accepted v1.0)
- related: `DD-CASEEVAL-001`(計測) / `DD-CASEBIND-001`(Tier) / `DD-CASECORROB-001`(corroboration)
- 実装: `scripts/case_review_sample.py` / `scripts/test_case_review_sample.py`

> **目的**: ②③④は構造ガードだが、**実運用の精度はドリフトする**（源更新・新類型）。本DDは bind/annotation を**層化抽出して人手監査**し、`DD-CASEEVAL` の指標を**生きた値**で推定・ドリフト検知する。CASEID-001 が予告した `CASE_HUMAN_REVIEW_SAMPLE_FRAME` の本体。**設計のみ・read-only**。

---

## 0. スコープ
全件監査は不能。**層化サンプル**で precision を統計推定し、目標未達（drift）を早期検知して ②ガード調整・③conflict 処理にフィードバックする運用ループを確定。

## 1. 決定

### 1.1 層化抽出（`sample_for_review`）
- **stratum = tier(A/B/C/prov) × corroboration_level**。各層から決定的（seed）に n 件抽出。
- worksheet 行は**人手最小表示項目**（CASEID-001 should_fix①）: `forum_code / decision_date / case_number_raw / case_number_norm / external_id / source_system / content_grade` ＋ `stratum / tier` ＋ 空欄 `reviewer_label`。
- 決定的（同 seed → 同抽出）で再現・監査可能。

### 1.2 precision 推定 ＋ drift 検知（`estimate_precision`）
- `reviewer_label ∈ {correct, false_merge, false_split, unsure}`。
- **precision = correct/(correct+false_merge)**（false_merge が precision killer、unsure/false_split は分母外）。per-tier / per-stratum。
- **層別目標**（split寄り）: Tier A 0.99 / B 0.95 / C 0.90 / prov 監査対象外。
- **drift_detected**: いずれかの tier が目標未達 → 旗を立てて `DD-CASEBIND` 閾値見直し・原因類型の追加負例化（①gold へ還流）。

## 2. ロードマップ結線（①〜⑤の閉ループ）
- ①CASEEVAL が**合成/実 gold** の精度を測るのに対し、⑤は**本番トラフィックの実精度**をサンプルで測る（gold に無い新類型を捕捉）。
- drift の原因 observation を ①gold の**新ハード負例**として追加 → ②ガード強化 → 再計測、の**閉ループ**。
- ③conflict_review・②Tier B review と同じ worksheet 様式（最小項目）で人手レーンを統一。

## 3. why / alternatives_rejected
- **why 層化**: Tier A（自動bind・大量）と Tier C（少量・高リスク）を均等サンプルすると稀な誤りを見逃す。層化で**各 tier の precision を独立に**監視。
- **rejected**: 単純ランダム抽出（稀な高リスク層を取りこぼす＝却下）。全件人手（不能＝却下）。精度を自動bind の confidence だけで自己申告（自己検証バイアス＝却下、独立人手が要る）。

## 4. verification（現状）
- deterministic_self_verification = **fixture-level done**: `test_case_review_sample.py` green（exit 0）。層化抽出数・全表示項目・決定性・**precision 推定（Tier A 0.8）・drift 検知（<0.99）**・全correct→drift無し を確認。
- corpus/運用 = **Mac CC**（実 bind を層化抽出 → 人手レビュー → 実 precision・drift）。
- independent_meaning_audit = **未了**（DDCASE ゲートへ）。owner_approval = 未了。

## 5. follow-up
- サンプルサイズと信頼区間の確定（owner：各 tier の許容誤差）。
- worksheet を ②Tier B review・③conflict_review の人手レーンと統合。
- drift→①gold 還流の運用手順（新類型の負例化）。
- 監査頻度（日次/源更新時）と responsible（番頭 Mac CC）。
