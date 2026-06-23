# 判例精度 ①〜⑤ v0.2 notes closure — **owner 確認済（accepted reflection）**

- 確認(ratify)日時: **2026-06-23 JST（浅井さん「両方アクセプト」）**
- 監査: **`DDCASE_PASS_WITH_NOTES`**（2026-06-23, GPT Pro, result 2303560820828）。「notes closure として合格。**再ratify は owner 確認のみで足り、全面再監査は不要**」。
- closure packet: `DD-CASE_precision_v0.2_notes_closure_20260623.md`(Box 2303445523158)
- 対象 accepted 正本: DD-CASEEVAL-001 / DD-CASEBIND-001 / DD-CASECITE-001 / DD-CASEREVIEW-001（各 accepted v1.0_with_notes）

> 本書は v0.2 notes closure の **owner 確認記録**。各 accepted 正本を supersede せず、accept-notes の該当 AC に対する実装反映を確定する。production は HOLD 継続。

## 1. 確定した closure（accepted 正本の accept-notes に反映）
- **① CASEEVAL AC-3**: cluster-level **B-cubed** を `score()` に同梱（pairwise 併用）。
- **② CASEBIND AC-4**: **G6** cross-source conflict（同一 source:id が複数 case に跨る→review・非merge）。
- **④ CASECITE AC-5**: **V8** matter scope 認可（`requester_matters` 未指定/別matter は fail-closed）。
- **⑤ CASEREVIEW AC-4**: `required_sample_size` / Wilson CI / `unsure_rate` / per-tier `recommended_n`。
- 検証: `test_case_precision_v02.py` 12/12 green、既存5テスト回帰なし。

## 2. v0.2 監査 should_fix（本確認で本文則化・v0.x 消化）
- **SF-1**: `unsure_rate` は precision 分母外でも **別ゲートの運用警告値**に出す（高 unsure × 高 precision を過信しない）。
- **SF-2**: 初期値（A0.99/B0.95/C0.90・margin±0.02・95%）は妥当。ただし初回実 corpus はサンプル数過大を避け **hard negative 優先の二段サンプリング**を許容。
- **SF-3**: **V8 は viewer だけでなく出力先 scope も見る**。authorized viewer でも **global bundle へ混入させない**（V7×V8 併用で担保、恒久則）。

## 3. HOLD
production DDL / DB write / canonical mint / serving / claim-support / 実 corpus の自動bind閾値確定は HOLD。read-only shadow evaluation・fixture regression は GO。

## 4. 残務
- Mac CC: SF-1〜SF-3 の v0.x 反映、実 corpus shadow evaluation、台帳登録（各 accepted DD に v0.2 反映追記）。
