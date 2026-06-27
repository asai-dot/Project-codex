# GPTQ-NNN DD-CASELINK-001 v0.2 — GPT Pro 監査 submission card

> ⚠ `NNN` は audit_id 連番。**Owner/Mac CC が _AUDIT_QUEUE_INDEX 台帳の次番号を採番**してリネーム。
> state はフォルダ位置で表現(本カードは `10_READY_TO_SUBMIT`)。実体は並行canonicalを作らない。

- gate: **DDCASE** / target: DD-CASELINK-001 / version: **v0.2** / 作成: 2026-06-24 / 番頭: Claude Code (remote)
- 求めるラベル: **DDCASE_PASS** / `DDCASE_PASS_WITH_NOTES`(許容) ／ 他: MODIFY_REQUIRED / FAIL / NEED_MORE

## 対象正本(canonical)
- **repo `asai-dot/project-codex` PR #26 / branch `claude/precedent-object-progress-gwb47u`**
  - DD: `docs/DD-CASELINK-001_commentary_to_case_link_extraction_draft_v0.2_20260624.md`
  - REQUEST(詳細パケット): `docs/20260624_caselink_v0.2_DDCASELINK001_REQUEST.md`
  - 実装(read-only): `scripts/case_link_extract.py` / `case_link_map.py` / `case_link_eval.py` / `case_vocab.py`(link層ミラー) / 各 `test_*` + `test_case_pipeline_e2e.py`(⑥)
- 本キュー内の DD/REQUEST は **投函用 snapshot**(canonical は上記 PR)。docs/alo 反映は Mac CC 同期 / 正典反映は監査通過後。

## カバー文(1段落)
雑誌・文献の本文から該当判例を取り出し、評釈と判例を**型付きで繋いで意味層を厚くする**設計。難所「1記事:N判例(評釈と判例が1:1でない)」を、フラットなN本の同格エッジにせず正典 `35_link_layer` の alo_edges(evaluates/review_chain/compares + assertion_mode + stance)に載せる。v0.1 の独自語彙(自己ドリフト)を v0.2 で正典へ全面 crosswalk 済。求めるのは設計の意味妥当性監査(下記5点)。

## 求める判定(重点) — REQUEST §2 と同じ
(a) 正典語彙への crosswalk が十分か(独自 edge_type を作らない / masthead=vendor_explicit→auto・本文=vendor_implicit→review) ／ (b) 1記事:N の役割モデル(主=evaluates 原則1 / 論文=central_case ヒント / 主検出シグナル順位) ／ (c) 同旨/反対を stance 列で保存(§11 OPPOSES 整合) ／ (d) llm_inferred 禁止下の境界と fail-closed の recall 損 ／ (e) precision 目標(evaluates/review_chain=0.97, compares=0.90, stance=0.85)。

## 投函前6点ゲート
1. **対象正本明示**: ✅ repo PR #26(DD v0.2 / REQUEST / 実装一式)。
2. **既存 accepted 関係**: ✅ DD-CASE-001 / DD-CASEID-001/002/003 (accepted v1.0)、`35_link_layer`(alo_edges 正典)。
3. **不可逆・失敗モード ≥1**: ✅ 誤 `evaluates`(評釈対象の取り違え)は意味層を汚染し利用者を誤誘導(欠落より有害)。stance 列追加は schema 変更(post-audit・owner GO)。
4. **求めるラベル**: ✅ DDCASE_PASS / PASS_WITH_NOTES。
5. **守秘確認**: ✅ 設計・合成データ・公開メタのみ。実データ不使用。
6. **実案件 匿名化 / Owner 承認**: ✅ 合成 fixture のみ(実案件情報なし)。

→ 6点充足 = `10_READY_TO_SUBMIT`。**Owner が正規UIへ投函** → 本カードを `20_SUBMITTED_awaiting_GPT` へ move。
