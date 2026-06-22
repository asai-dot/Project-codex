# DD-CASEID-002 — 事件符号の正規化と display romaji **accepted v1.0_with_notes**

- accept(ratify)日時: **2026-06-22 JST（浅井さん「両方アクセプト」）**
- lifecycle: v0.3(再々監査 patch) → **`accepted_v1.0_with_notes`**（design accept。production は HOLD）
- 監査: 3監査経由 — v0.1 `MODIFY_REQUIRED`(2299867559432) → v0.2 `MODIFY_REQUIRED`(2301890416366) → **v0.3 `DDCASEID_PASS_WITH_NOTES`(2302129156078, 2026-06-23)**
- 設計本体: `DD-CASEID-002_..._v0.3_20260622.md`(Box 2302088591886) ／ closure packet: `..._v0.3_closure_packet_20260622.md`(Box 2302112183981)
- parent: `DD-CASEID-001`(accepted v1.0) / `31c_case_number_norm_spec.md` / `DD-CASE-001`(accepted v1.0)

> **本書は accepted 正本**。設計本体は v0.3（Box 2302088591886）。本書は ratify を記録し accept-notes（監査の HOLD/should_fix を本文則へ格上げ）と残務を付す。これは **design-level accept** であり production acceptance ではない（監査 §3 明示）。

---

## 0. 確定（accept 済の中核）
- `case_number_norm` は事件符号を**かな/漢字保持**・ローマ字化しない。romaji は **display 専用・identity/dedup/FK 非使用**。
- 解析不能は `norm=null`＋provisional（推測・最近傍丸めしない）。
- 併合事件は **1:N docket**。各 segment はまず full parser、**継承は省略要素のみ・明示値を上書きしない**。

## 1. 決定（v0.3 §1〜§3 を accept）
- **N1〜N5**: 元号観測時のみ正規化（西暦逆引き禁止）／漢数字→算用は元号年のみ／符号は NFKC（互換字畳み込み）＋NFC／delimiter registry／枝番別field。
- **1:N docket**: `component_basis`(observed|inherited|unresolved|absent)・`parse_status`・`review_status`・`raw span`・`is_display_primary`。
- **2表**: `case_symbol_romanization`(display専用) / `case_symbol_semantics`(forum・時期・手続を複合スコープ)。

## 1.5 Accept-notes（ratify時に確定・本文則へ格上げ＝拘束）

監査 v0.3 PASS_WITH_NOTES の HOLD/must_fix(production)/should_fix を accept 条件とする：

- **AC-1（不可逆ガード）**: 継承で resolved した docket は **必ず `partial`＋`review_required`** を保持。fixtures green を理由に緩めない。**継承要素を observed と扱わない**。
- **AC-2（pending 行の非供給）**: `pending_source_fixation` 行は **case 分類・forum 推定・seed serving・canonical mint・下流の法的効果に供給しない**（`confirmed` 昇格まで）。
- **AC-3（fail-closed 維持）**: 未知 delimiter / 未知連結は **fail-closed**（unresolved/review_required）を恒久維持。
- **AC-4（romaji 非 identity）**: romaji は **display 専用、identity を持たない**（恒久則）。
- **AC-5（HOLD）**: 本 accept は **design のみ**。31c production / DDL / DB write / canonical mint / seed serving / `pending_source_fixation` 行の分類利用 / 継承要素の observed 扱い / romaji identity 利用 / multi-docket alias の本番確定は **HOLD**。

### production 前 must_fix（監査 §4・Mac CC/web）
1. 公式 doc の version/hash を Mac CC/web で取得し MF-2 を固定。
2. `pending_source_fixation` → `confirmed` 昇格は source hash＋captured_at 証拠が付くまで不可。
3. corpus-level 回帰（実 case-number 文字列・多docket 含む）を実行。
4. 継承 docket 要素は component provenance＋review_required を保持。
5. 未知 delimiter/連結は fail-closed を維持。

### should_fix（v0.x で消化）
- DD に observed/inherited/unresolved の例表追加（SF1）／機械可読 parser result schema（SF2・Docket dataclass を JSON schema 化）／delimiter registry を版管理（SF3）／OCR ノイズ delimiter fixtures（SF4）／romaji display-only 明文ルール（SF5・本書 AC-4 で本文則化）。

## 2. verification（充足）
- deterministic_self_verification = **done**: `test_case_number_norm.py` 全 green（exit 0、MF-1/MF-4-1..4/P0-1/P0-2/P1-1/同字異義/raw span）。`check_case_symbol_tables.py` C1-C9 PASS。commit `989dc4c`・SHA256 は closure packet。
- independent_meaning_audit = **PASS_WITH_NOTES（2026-06-23）**。MF-4 closure ACCEPT、MF-2 no-web 委譲 ACCEPT_WITH_HOLD。
- owner_approval = **ratified（2026-06-22, 浅井さん）**。

## 3. 残務
- Mac CC/web: 公式 doc hash 固定（MF-2 完全閉鎖）→ `pending_source_fixation`→`confirmed`。corpus 回帰。
- Mac CC 単一書き手: DESIGN登録簿 / `DD_REGISTRY.json` 登録（`accepted_v1.0_with_notes`）、`_AUDIT_LEDGER.jsonl` 追記、approval_queue clear。
- v0.3（Box 2302088591886）は設計本体として併存（非削除）。
