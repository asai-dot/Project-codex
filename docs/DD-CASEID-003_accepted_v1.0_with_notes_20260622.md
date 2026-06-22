# DD-CASEID-003 — forum registry（発令機関コード体系） **accepted v1.0_with_notes**

- accept(ratify)日時: **2026-06-22 JST（浅井さん「両方アクセプト」）**
- lifecycle: draft v0.1 → **`accepted_v1.0_with_notes`**（design accept。production は HOLD）
- 監査: **`DDCASEID_PASS_WITH_NOTES`**（2026-06-22, GPT Pro, result 2301895897751）
- 設計本体: `DD-CASEID-003_forum_registry_draft_v0.1_20260621.md`(Box 2301069549462) ／ 基礎: `31d_forum_code_registry_spec.md`
- parent: `DD-CASEID-001`(accepted v1.0) ／ related: `DD-CASE-001`(accepted v1.0) / `DD-CASEID-002`(accepted v1.0)
- 生成器: `scripts/build_forum_registry_seed.py` ／ 検証: `scripts/check_forum_registry_seed.py`(K1-K8)

> **本書は accepted 正本**。設計本体は v0.1（Box 2301069549462）。本書は ratify を記録し accept-notes（監査 notes/HOLD/ゲートを本文則化）と残務を付す。**design accept** であり production acceptance ではない。

---

## 0. 確定（accept 済の中核）
`court_code`→`forum_code` 一般化で裁判所・準司法・ADR・行政庁を自然キー第1要素に載せる。`forum_type`（機関の種別）と `case_type`（判断・手続類型）を**分離・1:1 束縛しない**。

## 1. 決定（v0.1 §1〜§2 を accept）
- **forum_code 命名**: 裁判所 `{place}-{court_type}`／最高裁 `saikosai`（法廷は `cases.bench`）／知財高裁 `chizai-kosai`／大審院 `daishin-in`／支部 `{place}-{type}-{branch}`＋`parent_forum_code`／準司法スラッグ。採番後不変。
- **`alo_forum_registry` スキーマ**: `forum_code` PK / `forum_type`(7値 CHECK) / `forum_name` / `parent_forum_code` / `jurisdiction_scope` / `source_basis` / `valid_from` / `valid_to`。
- **seed 123**（裁判所＋準司法23、生成済・Mac CC）。支部162 は `__REVIEW__` 保留。

## 1.5 Accept-notes（ratify時に確定・本文則へ格上げ＝拘束）

- **AC-1（軸分離）**: `forum_type` は「どこが出したか」、`case_type`/disposition は「何を出したか」。**1:1 対応させない**（簡裁=court が調停も出す等）。case_type 定義は DD-CASE-001 が唯一（N-2）。
- **AC-2（mint 禁止）**: `__REVIEW__` を含む tentative_code は **canonical mint しない**（K3）。支部162 は romaji 確定まで保留。
- **AC-3（jufu 隔離）**: `jufu` は registry 上 court 型だが、**出口可否・機密は source registry / access policy 側で fail-closed**（registry に `can_global_index`/confidentiality を持たせない）。K6 を production gate で必ず維持。
- **AC-4（valid 意味）**: `valid_to` は**排他上限**（同日以降は別機関）として実装。欠損は空でなく `unknown`（K7）。
- **AC-5（HOLD）**: 本 accept は **design のみ**。DDL / canonical mint / `cases.forum_code` 移行 / `__REVIEW__` 採番 / 支部162 未検証投入 / jufu global 配信 / source registry 迂回の出口利用は **HOLD**。

### should_fix（v0.2 で消化・監査 §3）
- `source_basis` 多重化に備え `forum_source_evidence` 別表化を検討（同一 forum_code に NII/D1/court官/provisional が重なる）。
- `jurisdiction_scope` の controlled vocabulary（`jurisdiction_scope_kind`）。
- `forum_type=other` の件数・理由・source_basis を gate で可視化。
- 最高裁小法廷名の正規化辞書（bench、cases 側）。

### 昇格ゲート（K1-K8・v0.2 実 seed 前）
K1 forum_code unique / K2 forum_type domain(7) / K3 no `__REVIEW__` mint / K4 quasi23 が source registry 一致 / K5 parent exists / K6 jufu isolation / **K7 valid 意味文書化** / **K8 source_basis 欠損0 or provisional 明示**。

## 2. verification（充足）
- deterministic_self_verification = **K1-K6 selftest PASS**（checker）。実 seed123 の生成・K1-K8 再実行は **Mac CC**（builder ローカル TTL+CSV 依存）。RUNBOOK 完備。
- independent_meaning_audit = **PASS_WITH_NOTES（2026-06-22）**。
- owner_approval = **ratified（2026-06-22, 浅井さん）**。

## 3. 残務
- Mac CC: `forum_registry_seed.csv`(123) 実生成（RUNBOOK）＋ K1-K8 を実 seed に再実行＋再現ログ/SHA。支部162 romaji 確定（権威表・独立検証）。
- Mac CC 単一書き手: DESIGN登録簿 / `DD_REGISTRY.json` 登録、`_AUDIT_LEDGER.jsonl` 追記、approval_queue clear。
- v0.1（Box 2301069549462）・31d は併存（設計本体/基礎）。
