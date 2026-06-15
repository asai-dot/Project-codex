---
request_id: DDSELFHEAL
topic: 自己浄化型 文献データ基盤 (3層チェーン + self-healing loop)
gate: design_direction
supersedes: なし (legallibjoin v0.3.1 を恒常ループへ一般化する上位設計)
parallel_related: [DDLEGALLIBCONCORD, LEGALLIBJOIN_STRATEGY_V03_1]
withdrawal_effect: 本設計が却下されても legallibjoin v0.3.1 (report-only 接合) は単独で成立する
current_governing_result: DDLEGALLIBCONCORD_PASS_WITH_NOTES (phase0=GO / production_apply=HOLD)
result_expected_filename: DDSELFHEAL_result.md
status: draft
---

# 自己浄化型 文献データ基盤 — 設計方針 (DDSELFHEAL)

## 0. これは何か / なぜ書くか

owner が定義したゴール:

> 文献について、総合メタ（NDL書誌メタ）→ 個別メタ（詳細TOC）→ 本文（PDF or 物理本）まで
> が一貫して連なり AI 可読になれば満足。汚いデータはいらない。汚いデータは人が手で直さ
> なくても、なんらかの方法で検知され、修復され、データがどんどん綺麗になっていく — この
> 状態が理想。

legallibjoin v0.3.1 は「L1↔L2 の接合を安全に **1回** やる」装置だった。本設計はそれを
**corpus 全体を恒常的にスキャンし、汚れを検知→修復→再スキャンして単調に綺麗にしていく
ループ**へ一般化する。production apply は引き続き HOLD。本ドキュメントは方針合意を取るための
DD であり、repair 層の実装は本 DD の承認後に着手する。

---

## 1. チェーン (背骨) の定義

| 層 | 中身 | 役割 | 主ソース |
|---|------|------|---------|
| **L1 総合メタ** | NDL 書誌 (ISBN/書名/著者/出版者/年/NDC) | 同一性の錨 (edition identity) | NDL |
| **L2 個別メタ** | 詳細 TOC (node tree) | 構造・章節 | legallib / bencom |
| **L3 本文** | PDF / 物理本 (page_basis, sha256) | 実体・ページ | PDF / 蔵書 |

**「一貫して連なる」= AI 可読の検収条件 (5点):**

1. 全 L2 node・L3 page が L1 の単一 identity から到達可能 (book_id↔ISBN が一意)
2. edition identity が `resolved_same` or `manual_resolved` (`edition_identity.py`)
3. page_basis が判明し整合 (`page_basis.page_basis_consistent`)
4. `all_nodes_accounted_for == True` (orphan は silent discard せず明示 quarantine, `concordance.py`)
5. 全 node に provenance と安定 ID (toc_node_id / toc_path_id / legallib_book_id / converter_version)

達成度は `data_health.py` が **0–100 の health_score** で可視化する (L1=30 / L2=40 / L3=30 重み、
chain 破綻時は係数 0.85 で満点を抑止)。

---

## 2. 自己浄化ループ (本設計の核)

```
[corpus 全体]
   │
   ▼  ① SCAN (恒常検知)              … data_health.corpus_health + conflict_detector
各 book に health_score + defect list
   │
   ▼  ② 分類 (defect → ルート)        … data_health._repair_hints
   ├── auto       決定的・可逆        → ③a REPAIR (gated)
   ├── refetch    別ソース要          → ③b RE-FETCH / concordance
   └── human      曖昧/版差           → ③c QUARANTINE + review_queue
   │
   ▼  ③ 適用は全て apply_guard 7gate 経由 (物理拒否) + decision_log (append-only/chain)
   │
   ▼  ④ RE-SCAN → health_score 更新 (ratchet: 下がらない / 回帰は必ず log に理由)
   │
   ▼  ⑤ dashboard で corpus mean_health が上がっていくのを可視化
```

### 2.1 defect → ルート対応 (初期表, `data_health._REPAIR_ROUTE`)

| defect | route | 修復手段 (将来) |
|--------|-------|----------------|
| L1: title/publisher/year 欠落 | refetch_ndl | NDL API 再取得 |
| L1: isbn 欠落/不正 | human | 人手 (錨が無いと連結不能) |
| L2: toc_absent / flat_only / too_sparse | refetch_legallib | legallib 詳細 TOC で enrich (=接合) |
| L3: page_basis_unknown | auto_reprofile | PDF から page_basis 再推定 |
| L3: page_basis_inconsistent | auto_convert | offset 確定して print/pdf 変換 (`page_basis.to_print_page`) |
| L3: body_sha_absent | auto_hash | 実体 sha256 付与 |
| L3: edition_unresolved | human | 別版疑いは人が判断 |
| chain: nodes_unaccounted | quarantine | clean set を汚さず隔離 |

### 2.2 修復 (repair) の不変条件 — 「自動で汚れを触る」ための安全装置

汚いデータを人手なしで触る以上、repair は次を**全て**満たす時のみ実行する:

1. **決定的** — 同じ入力に同じ出力 (LLM 等の非決定は v0.4 semantic 層に隔離)
2. **可逆** — rollback bundle 必須 (apply_guard `rollback_bundle_present`)
3. **gated** — apply_guard 7gate (whitelist / no_unresolved_conflict / edition_resolved /
   pdf_qualified / rollback / decision_log_append_only / all_nodes_accounted_for) 通過必須
4. **記録** — decision_log に before/after と basis を append (chain hash で改竄検出)
5. **冪等** — 再実行で収束 (二度がけしても壊れない / 既に綺麗なら no-op)
6. **隔離優先** — 直せないものは clean に混ぜず quarantine。**clean set は単調にしか増えない**

→ auto route であっても whitelist 無しでは物理的に書けない (P0-5 を踏襲)。

### 2.3 ratchet (単調改善の保証)

- health_score は再スキャンのたび更新。**下降した場合は decision_log に regression 理由が
  必ず残る** (証拠なき悪化を許さない)。
- 冪等性により、同じ corpus を何度通しても収束する (発散しない)。
- owner は「mean_health が時間とともに上がる」ことだけ見ていればよい。下がったら log を見る。

---

## 3. 既存資産の再利用 (新規実装を最小化)

| 機能 | 既存モジュール | 本設計での役割 |
|------|---------------|----------------|
| 正規化 | `_toc_text.normalize_title` | L2 突合・auto 正規化修復 |
| 多ソース対応付け | `concordance.build_concordance` | all_nodes_accounted_for / orphan 検出 |
| 矛盾検知 | `conflict_detector.detect_conflicts` | SCAN の defect 源 |
| 版同一性 | `edition_identity.classify_edition_identity` | L1 錨 / human route 判定 |
| ページ基準 | `page_basis.*` | L3 連結 / auto_convert |
| 権威解決 | `authority_resolver.resolve_authority` | どのソースを正にするか |
| owner サマリ | `review_report.book_summary` | risk / 推奨アクション |
| 物理拒否 | `apply_guard.evaluate_apply_gate` | 全書き込みの 7gate |
| 監査 | `decision_log` | append-only / chain hash |
| **健全度** | `data_health` (新規・本足場) | health_score / defect / repair_hints |
| **閾値集約** | `thresholds` (新規・本足場) | 実データ調整をコード変更なしに |
| **回帰** | `tests/golden/` (新規・本足場) | 既知 conflict 10冊の回帰固定 |

新規に作るのは **repair 層のみ** (本 DD 承認後)。SCAN/分類/可視化の足場は本コミットで report-only 実装済み。

---

## 4. フェーズ計画

- **Phase 0 (Mac, 実行中)**: 実データ inventory / profiling → 閾値の実分布把握
- **Phase A (web)**: `thresholds.json` を実分布で調整 → evidence 5点実データ版 → owner whitelist
  → gate 通過 ISBN のみ apply (HOLD 解除は owner ratify 後)
- **Phase B**: 接合を「恒常 SCAN」に格上げ (`data_health.corpus_health` を corpus 全体へ)
- **Phase C**: repair 層 (決定的 repairer から順に / 全て gated / ratchet 可視化)  ← **本 DD の対象**
- **Phase D (v0.4)**: semantic matching / NDC 補完 / L3 PDF 深い連結 (非決定は隔離)

---

## 5. GPT への問い (DD で確認したい点)

1. **repair の決定性境界**: どこまでを「決定的 auto」と認め、どこからを human/semantic に隔離すべきか。
   特に L3 page offset 確定と orphan 再 parent は auto に入れてよいか。
2. **ratchet の定義**: health_score 下降を「decision_log に理由必須」で許容する設計で、単調改善の
   保証として十分か。スコア式 (L1=30/L2=40/L3=30, chain 係数0.85) の重み付けは妥当か。
3. **quarantine の扱い**: 直せない汚れを clean から隔離するだけで「綺麗になっていく」と言えるか、
   それとも quarantine 自体の縮小目標 (KPI) を設けるべきか。
4. **apply_guard の repair への適用**: auto repair も whitelist 必須とする (P0-5 踏襲) で過剰防衛で
   ないか。auto かつ可逆なら whitelist を緩めてよい余地があるか (owner 運用コストとの trade-off)。

> production apply / RDB write は引き続き **HOLD**。本設計は report-only の SCAN/分類/可視化までを
> 実装済みとし、repair の書き込みは本 DD 承認 + owner ratify 後に限る。
