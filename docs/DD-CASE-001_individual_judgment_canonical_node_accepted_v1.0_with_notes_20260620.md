# DD-CASE-001 — 個別判断の正準ノード母型（判決・審判・裁決・答申・ADR） **accepted v1.0_with_notes**

- 再構成日: 2026-06-19 JST ／ **accept(ratify)日時: 2026-06-20 JST（浅井さん ratify＝「アクセプト」）**
- recon_status: **`reconstructed_from_residual_materials`**（原本回収不能・本 recon が後継。原本 v0.4 = `blocked_unrecoverable_reconstructed`）
- lifecycle: draft/candidate(v0.1-recon) → **`accepted_v1.0_with_notes`**（GPT-5.5 Pro 独立監査 `DDCASESOURCE_PASS_WITH_NOTES`／must_fix 6点 closure → owner ratify）
- 監査: `20260619_quasijudicial_v0.5_DDCASESOURCE_recon_RESULT.md`（Box 2295309962089）
- 設計本体（full）: `DD-CASE-001_individual_judgment_canonical_node_v0.1-recon_20260619.md`（Box 2295258030670、must_fix反映版）
- domain: CASE（判例レイヤ エンティティ母型 / 準司法取水口）
- parent: `31_case_layer.md`(SPEC-02 v1.4) / 統合仕様書 v3.0 CaseBundle v1.5
- related: `DD-CASEID-001`(accepted v1.0／本DDが case_type/node schema を供給) / `DDCASESOURCE`(準司法・機密一次所有) / `DD-DYNDB-CASES-001`(受任案件master＝別オブジェクト)

> **本書は accepted 正本**。設計本体は recon v0.1（Box 2295258030670）。本書は ratify を記録し、accept-notes（must_fix closure を本文則へ格上げ）と残務を付した版。DESIGN登録簿 / `DD_REGISTRY.json` / `_AUDIT_LEDGER.jsonl` 登録は Mac CC 単一書き手（§5）。

---

## 0. 確定した設計思想（accept済）

個別判断（判決・審判・裁決・答申・ADR・仲裁・調停）を**1つの正準ノード**として扱い、判決をその特殊形とする母型。判例レイヤの「事件同一性 / ソース別解釈」分離（31_case_layer §1.1）を準司法へ一般化し、**3軸（同一性 A1 / 解釈 A2 / 出口 A3）を分離**する。case_type 正準enum と node schema は本DDが唯一定義（N-2）、出口可否は DDCASESOURCE 一次所有（N-3）。

## 1. 決定（recon v0.1 §1〜§4.5 を accept）

1. **§D5' 3軸分離**: A1同一性（case_key anchor＋自然キー）／A2解釈（case_annotations）／A3出口（confidentiality_class）。識別・公開可否は独立、同一カラムに畳まない。
2. **case_type 正準enum**: `judicial`(既定) / `adjudication` / `administrative_review` / `advisory` / `adr` / `conciliation`。cases(A1)のNOT NULLカラム。本DDが唯一の定義元。
3. **node schema**: DD-CASEID-001 §3 と同一フィールド集合を共有（重複定義なし）。`case_type` と `export_override jsonb` を本DDが所有。
4. **出口ポリシー（RP-01〜06＋監査 must_fix）**: global egress は **`confidentiality_class==open ∧ redistribution==public`** のみ。matter_scoped_only は当該matter内 `mcp_serve` 限定。jufu は global embedding 禁止・identity evidence 限定。record-level `export_override` が source/class 既定に優先。

## 1.5 Accept-notes（ratify時に確定・本文則へ格上げ）

監査 `DDCASESOURCE_PASS_WITH_NOTES` の must_fix 6点を**accept条件＝拘束力ある本文則**とする（全て recon版・seed・negative_test に反映済）：

- **AC-1**: 全 recon 成果物は `recon_status=reconstructed_from_residual_materials` を保持。**原本同一性を主張しない**。台帳もこの status で登録。
- **AC-2**: 原本 v0.4 は `blocked_unrecoverable_reconstructed`（superseded ではない）。原本がローカルから発見されれば recon を `superseded_by` で更新し差分照合。
- **AC-3**: global content index への backfill 条件は **`open ∧ public`**。商用(D1/判タ/判秘/LIC)・有償(saikousai-db)・manual・matter_confirmed は出口禁止。
- **AC-4**: `matter_scoped_only` の same_matter 許可は **`mcp_serve` 限定**。export / claim_support は同一matterでも別gate。
- **AC-5**: record-level `export_override` が最優先（source単位ポリシーは粗い前提）。公表コーパスでも個人情報・匿名化・robots/API・再利用条件を record メモに保持。
- **AC-6（HOLD）**: 本 accept は**設計確定のみ**。production DDL / canonical case mint / DB write / alo_edges / embedding / MCP serve / export / claim_support / jufu出口利用は **G2 production-readiness gate で別審査**。

### reconcile 不変則（DD-CASEID-001 と双方向一致）
- **N-1**: `case_key`(判例) と `alo_matter_id`(受任案件) は別オブジェクト。混在・相互代入禁止。
- **N-2**: `case_type` 定義 = 本DD（唯一）。CASEID-001 は参照・整合のみ。
- **N-3**: 機密・配布可否 = DDCASESOURCE 一次所有。
- **N-4**: 本DD=エンティティ母型 / CASEID-001=ID確定上流機能。重ねない。
- **AN-2（merge禁止）**: 審級・原処分↔取消訴訟・答申↔抗告訴訟・ADR↔執行決定は別case_key＋`alo_edges` link。

## 2. verification（昇格3条件＝充足）

- **deterministic_self_verification = done**: `registry_negative_test.py` v0.2 = **15/15 green（exit 0）**。RP-01〜06＋must_fix#3〜#6 を符号化（A1〜A9 / B1〜B6）。
- **independent_meaning_audit = PASS_WITH_NOTES（2026-06-19, GPT-5.5 Pro）**: 3軸分離・RP-03線引き・jufu隔離 PASS。must_fix 6点 closure 済。
- **owner_approval = ratified（2026-06-20, 浅井さん「アクセプト」）**。

## 3. accept後の経路（監査 next_action）

owner ratify → **(a) DD台帳 backfill** → **(b) forum_registry_seed 実生成**（Mac CC, local TTL+CSV, 再現ログ＋SHA 添付・should_fix#4）→ 次DD。production系は AC-6 で HOLD。

## 4. follow-up（accept後の課題）

- **should_fix（監査）**: ①欠落10行 `missing_recon_sources`（Box 2297404163649）を別queueで埋める。②`can_global_index` は保存列でなく**導出view**化（本番）。③公表コーパスの record-level 再利用条件 note。④forum_registry_seed の Mac CC 再現ログ＋SHA。
- **sibling**: closure本体は本DD§2-§5＋CASEID-001 で吸収済（形式note別出力可）。
- **原本回収**: ローカル発見時は AC-2 に従い差分照合。

## 5. accepted 正本の残務（Mac CC 単一書き手）

- DESIGN登録簿 / `DD_REGISTRY.json` への `accepted_v1.0_with_notes` 登録（recon_status 併記）。
- `_AUDIT_LEDGER.jsonl` に reflect/closed 追記、approval_queue カード clear。
- recon v0.1（Box 2295258030670）は非削除で併存（設計本体として参照）。
- forum_registry_seed 実生成（builder はローカル TTL+CSV 依存・リモート不可）。
