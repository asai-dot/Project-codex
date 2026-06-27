# DD-CASEID-003 — forum registry（発令機関コード体系・自然キー第1要素）**draft v0.1**

- 起票: 2026-06-21 JST ／ 番頭: Claude Code (remote)
- lifecycle: **draft / candidate**（GPT Pro 独立監査 未了 → DDCASEID ゲート）。確定表 `31d_forum_code_registry_spec.md`(candidate v0.1・123 forum_code 生成済) を **DD へ昇格**し設計判断を明文化
- domain: CASEID（判例ID確定 / 発令機関コード）。**DD-CASEID-001 の下位DD**（accepted v1.0 §5 follow-up: 「forum registry に forum_type/jurisdiction_scope/source_basis/valid_from-to」）
- parent: `DD-CASEID-001`(accepted v1.0) / `31b_case_id_resolution_flow.md` §2 / `31d_forum_code_registry_spec.md`
- related: `DD-CASE-001`(accepted v1.0／forum_type↔case_type) / `DD-CASEID-002`(符号・**独立**) / `DDCASESOURCE`(jufu 出口)
- 生成器: `scripts/build_forum_registry_seed.py`(Box 2264377914086) ／ 検証: `scripts/check_forum_registry_seed.py`(K1-K6)

> 確定前提（DD-CASEID-001 §1.2 accept 済）: `court_code` を **`forum_code`** へ一般化し `fn_generate_case_uri_v2(forum_code, decision_date, case_number_norm)` の第1要素とする。本DDはその体系・スキーマ・seed・未確定ギャップ処理を実装粒度で確定する。

---

## 0. スコープ
判決機関（裁判所）と準司法機関（審判所・審査会・ADR・仲裁・行政庁）を**一意の ASCII forum_code** で採番する確定表＝`alo_forum_registry`。自然キー `{forum_code}-{decision_date}-{case_number_norm}` の第1要素（CASEID-002 が第3要素・符号、本DDが第1要素・機関で**直交**）。

## 1. 決定

### 1.1 forum_code 命名規則（31d §1 確定）
- **裁判所**: `{place_romaji}-{court_type}`、court_type ∈ {`kosai`/`chisai`/`kasai`/`kani`}。例 `tokyo-chisai`/`osaka-kosai`。
- **最高裁**: `saikosai`。**大法廷/小法廷は forum_code に含めず `cases.bench`(case属性)**（法廷は判決属性であって別機関でない）。
- **知財高裁**: `chizai-kosai`。**大審院**(戦前最上級審 1875-1947): `daishin-in`。
- **支部**: `{place}-{court_type}-{branch_romaji}`、`parent_forum_code`=本庁（疎結合）。
- **準司法**: 機関スラッグ（ASCII）。`jftc`/`churoi`/`kokuzei-fufuku-shinpan`/`finmac`/`jsaa` 等。
- 全て小文字・ハイフン・ASCII・**採番後不変**（case_key 同様の anchor 性）。

### 1.2 `alo_forum_registry` スキーマ（31d §5 ＋ CASEID-001 should_fix④ 拡張）
| カラム | 説明 | 由来 |
|---|---|---|
| `forum_code` PK | 採番後不変 ASCII | 31d |
| `forum_type` | court / administrative_tribunal / administrative_review / adr / arbitration / agency / other（CHECK） | 31d §2 |
| `forum_name` | 正式名称（日本語） | 31d |
| `parent_forum_code` | 支部→本庁（疎結合・自己参照） | 31d |
| `jurisdiction_scope` | 管轄（地理/事物。例 租税・労働(不当労働行為)） | **追加(should_fix④)** |
| `source_basis` | `court_official` / `quasi_judicial_台帳` / `nii_hanrei` / `d1_hanrei` / `alo_provisional` | **追加(should_fix④)** |
| `valid_from` / `valid_to` | 機関の存続期間（大審院=…/1947、旧法機関の廃止日 等） | **追加(should_fix④)** |
| `bench`（参考） | 最高裁法廷等は **cases 側属性**（registry に持たない） | 31d §5 |

### 1.3 seed 被覆（31d §3・生成済）
`forum_registry_seed.csv` = **123 distinct forum_code**：裁判所(NII 81 集約＋D1本庁＋`daishin-in`、NII側REVIEW=0) ＋ 準司法23（台帳 Tier S/A ＋ `jufu`）。forum_type 内訳: court 105 / administrative_tribunal 6 / administrative_review 4 / adr 5 / agency 4 / arbitration 1 / other 2。

### 1.4 未確定ギャップ＝支部162（turnkey）
D1 **支部162種**は本庁マップ済だが**支部地名 romaji 未確定** → `forum_registry_unmapped_d1.csv`（`romaji_TODO` 列）。
- **`__REVIEW__` を含む tentative_code は canonical mint しない**（K3／AC-6 HOLD）。`romaji_TODO` を出現件数順に確定 → 再生成。
- romaji は**権威表（郵便/ISO）準拠**。ローカルLLM 下訳時は独立検証必須（forum_code は同一性キーゆえ誤り厳禁）。154地名で全支部を覆える。

## 2. reconcile（accepted 上位DDと双方向一致）
- **DD-CASE-001 N-2/§2**: `case_type`（judicial/adjudication/administrative_review/advisory/adr/conciliation）は DD-CASE-001 が唯一定義。本DDの `forum_type`（7値）は **forum の種別**であり case_type と**別軸**。対応は多対多になりうる（例 簡裁=court が conciliation も出す）ため、**forum_type→case_type を1:1 固定しない**。判断種別は disposition/case_type 側で確定し、forum_type は発令機関の属性に留める。
- **DD-CASEID-001 N-1/N-4**: `forum_code` は判例側 anchor。受任案件 `alo_matter_id` と無関係。本DD=機関コード体系、CASEID-001=ID確定上流、重ねない。
- **DDCASESOURCE / AC-3**: `jufu` は forum_code 上 `court` 型だが、**出口は source registry で `can_global_index=false`・`lawyer_client_confidential`**（registry の forum_type は機関種別であって出口可否を表さない）。

## 3. why / alternatives_rejected
- **why forum_code 一般化**: court_code(裁判所限定)では準司法（審判・裁決・答申・ADR）を自然キーに載せられない（DD-CASE-001 母型の前提）。
- **rejected**: 最高裁法廷を別 forum_code 化（法廷は判決属性＝`bench`。却下）。支部を本庁に畳む（管轄・事件番号系列が別＝却下、別 forum_code＋parent）。forum_type を case_type に1:1束縛（簡裁の調停等で破綻＝却下）。未確定支部を暫定 romaji で mint（誤同定＝却下、`__REVIEW__` 保留）。

## 4. verification（昇格条件・現状）
- deterministic_self_verification = **fixture-level done / seed-gen は Mac CC**:
  - `check_forum_registry_seed.py`（K1-K6）= **--selftest PASS**（正常fixtureクリーン／壊れfixtureが K1-K6 全検出）。K1 forum_code一意・K2 forum_type値域・K3 `__REVIEW__`はmint不可・K4 準司法23が source registry 一致・K5 parent参照健全・K6 jufu出口隔離(AC-3)。
  - 実 `forum_registry_seed.csv`(123) の生成・検証は **Mac CC**（builder がローカル `hanrei.ttl`＋`判例一覧.csv` 依存）。RUNBOOK 完備（`RUNBOOK_forum_registry_seed_generation_maccc`）。
- independent_meaning_audit = **未了**（本draftを DDCASEID ゲートへ）。
- owner_approval = **未了**。

## 5. 品質ゲート（31d §6・production）
`gate_forum_code_unique`(0 dup) / `gate_case_forum_resolved`(confirmed case の forum_code 在籍, 0 orphan) / `gate_ingest_forum_mapped`(未解決→review_queue) / `gate_branch_parent_exists`(0)。**DDL 化は AC-6 HOLD**。

## 6. follow-up（31d §7）
- 支部162 romaji 確定 → v0.2 で全裁判所確定。
- 準司法 forum_type 細分（裁断/答申/あっせん/仲裁を disposition と整合）。
- 旧法機関（区裁判所・控訴院、D1 の更に古い層）と `valid_from/valid_to` 確定。
- 既存 court_code（例 `tky-chisai`）→ `tokyo-chisai` migration note（cases 未投入なら影響なし）。
