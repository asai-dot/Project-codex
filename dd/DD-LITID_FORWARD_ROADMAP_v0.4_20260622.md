# DD-LITID 書籍同定 フォワード・ロードマップ v0.4

- 作成日: 2026-06-22（v0.3 を改訂）
- 改訂理由: Box 実地調査（RECONCILIATION.md, c7d81c9）で既存パイプライン実体が確定。
  **DD-LITID の本質を「索引・突合の再実装」から「既存 match 出力の上に edition-identity ガバナンス層を載せること」に再定義する。**
- 上位設計: DD-LITID-PLAN v0.1 / DD-LITID-001 v0.2 / INGEST_SPEC v0.2 / ROADMAP v0.3。
- ゲート原則（不変）: 可逆=安価先行、不可逆=高価は shadow 実証＋独立再監査後。
  **本書は計画＋reversible artifact 準備のみ。production 実装/DDL/DB書込/backfill/promote/serving/embedding/外部公開は HOLD。**

---

## 0. v0.3→v0.4 の主要変更（差分のみ）

| 項目 | v0.3 の記述 | v0.4 の確定事実 |
|---|---|---|
| WS-R R2 索引 | 16.7GB ダンプから rebuild | **`ndl_isbn_index.csv`（851万件/1.9GB）が既存・月次更新 → rebuild 不要** |
| WS-A1/A2 突合 | R2 rebuild 後に実施 | **`ndl_shelf_matched.csv`（5,257件）が既存 → 読むだけ** |
| WS-B1 no-ISBN | 別途 generator 設計 | **`match_titles_to_ndl.py`（版/刷除去込み）が既存 → 再利用** |
| 正本（provenance root） | 未定義 | **`bookshelf_dx/app/data/books.json`（6,384→6,525冊・成長中）** |
| bib_records（Supabase） | 正本扱い混在 | **2026-06-03 release snapshot（raw/source_url/source_hash 全て空）= 下流スナップショット** |
| DD-LITID の付加価値 | 索引・突合の整備 | **版/刷 confirmed 区別 + 2独立証拠 + adjudication 記録（D0/Q1-Q5）** |

**核心再定義**: DD-LITID は「索引/突合の再実装」ではなく、**既存 match 出力の上に edition-identity ガバナンス層を載せるプロジェクト**。

---

## 1. 確定した現実（v0.4 追加分）

**確定（RECONCILIATION.md / 実地調査で確定）**

| 事実 | 根拠 |
|---|---|
| bib_records 実在は self/own(6,524)・bencom(3,802) のみ | snapshot 20260619 |
| self/own は ISBN↔NDL 厳密1:1・衝突0 | Phase 0 |
| 421=ISBN有NDL無（53件が2024+）/ 1,101=ISBN無NDL無（全件 manual） | A2 |
| edition 424値: 版73% / 刷12%（混入）/ 日付14% | A3 |
| Box に `ndl_isbn_index.csv`（851万件/1.9GB）**既在・月次更新** | RECONCILIATION §2,§4 |
| Box に `ndl_shelf_matched.csv`（5,257件）**既在** | RECONCILIATION §4 |
| Box に `match_titles_to_ndl.py`（版/刷除去込み）**既在** | RECONCILIATION §4 |
| `bookshelf_dx/app/data/books.json` = **正本（living source of truth）** | RECONCILIATION §6 |
| `bib_records`（Supabase）= 2026-06-03 release snapshot（下流・raw列空） | RECONCILIATION §6 |
| NDL パイプライン本線 = **OAI-PMH 月次差分**（16.7GBダンプは参照用アーカイブ） | RECONCILIATION §2 |
| 6件の bib_id↔isbn 列不整合（identity hazard） | Phase 0 / RECONCILIATION §6 |

**未検証仮説（UNVERIFIED・正解ラベル化禁止）**
- 既存 `ndl_bib_id` 76.7% がダンプ由来か → import log/hash 照合まで前提化しない（WS-R R4）。
- ダンプ CSV の列スキーマ（ISBN/edition 列）→ R1 で確認。

---

## 2. provenance root の確定

```
正本（living source of truth）:
  bookshelf_dx/app/data/books.json
    ├─ 物理蔵書 / 自炊スキャン / 手入力
    ├─ NDL pipeline enrich（ndl_integrate: NDL bibid / alo:book:isbn URI 付与）
    └─ 成長中（6,384 → 6,525）

  ↓  release candidate export
  bookshelf release（books.jsonl + toc_index 776,999 + covers 1,172）

  ↓  2026-06-03 18:59 一括ロード
  Supabase: biblio.bib_records（source=asai-bookshelf）
            raw/source_url/source_hash = 全て空（provenance 列未投入）
            = 下流スナップショット（6,524）
```

**結論**:
- identity 作業は DB（`bib_records`）を**作業面**として使ってよい（読み取り・candidate 生成）。
- **confirm/promote の provenance ルートは books.json/release**。DB に書き戻す場合は release cycle を経る。
- `bib_records` の raw/source_url/source_hash 空欄は **既知の既定状態**（不具合でなく未投入）。

---

## 3. ワークストリーム（v0.4 確定版）

### WS-R Offline NDL Reference Build → **既存再利用に変更**

| R# | タスク | 方針 |
|---|---|---|
| R1 | manifest/schema/rights 検証 | 実施（R1 manifest doc 既存） |
| R2 | ISBN 索引ビルド | **不要**。`ndl_isbn_index.csv`（851万件）を read-only 参照 |
| R3 | coverage レポート | **不要**。`ndl_shelf_matched.csv`（5,257件）を読む |
| R4 | lineage 検証 | `ndl_bib_id` 76.7% の import log/hash 照合（CONDITIONAL） |

**WS-R の実作業**: `ndl_shelf_matched.csv` / `ndl_isbn_index.csv` / `ndl_law_books_ndc320.csv` をローカルで read-only 参照し、cohort-A との差分を計算するだけ。rebuild スクリプトは投入しない。

### WS-Q Evaluation & Evidence Governance（不変・最重要）

- Q1 非循環 gold / adjudication protocol
- Q2 証拠 family lineage & collapse（origin_family / same_origin_collapse_key）
- Q3 confusion buckets（false_merge_work / false_merge_edition / false_split / same_work_diff_edition / printing_only_diff / metadata_noise）
- Q4 数値 sample plan（minimum_n / CI / hard veto / abstention）
- Q5 gate matrix（cohort × decision_type × evidence_profile、default=DENY）

→ 別文書（DD-LITID_Q_eval_plan_and_gate_table v0.1）参照。

### WS-A 自所(cohort-A) 版同定

- A0/A2/A3 ✅ 完了。
- **A1**: `ndl_shelf_matched.csv`（5,257件）を読み、Q1/Q2 証拠契約に基づき candidate/verified に分類。
  - candidate retrieval quality: 既存 match の回収率評価。
  - resolution quality: NDL と独立な奥付/現物/出版社で work/edition/printing 裁定。
- **A2 後段**: 421件を `ndl_isbn_index.csv` で照合（read-only）。2024+ 53件は `freshness_miss` レーン分離。
- **A3 後段**: raw-preserving 正規化。`edition_statement / printing_no / date_role` に分解、正規化だけで同一版と決めない。版 vs 刷分離が must（刷12%混入）。
- **A4**: 6件 bib_id↔isbn 不整合の原本確認 → Q1 gold seed 最優先。

### WS-B 弁コム no-ISBN remediation（quarantine lane）

- medium 775 = `existing_unconfirmed`（promote/training/serving 不適格）。
- **B1**: `match_titles_to_ndl.py`（版/刷除去込み・既存）を再利用。rebuild 不要。
- B2: high 962 も層化抜き取りで systematic FP 確認。
- 「TOC/fingerprint=第2独立証拠」は Q2 family collapse 後に独立証拠が立つ場合のみ confirm 候補。

### WS-C 未投入取り込み（並走・provisional）

- C1 LION BOLT=cohort-A' / C2 legallib=cohort-B。field-profile 完了まで provisional。
- P3（LION/legallib 着地待ち）を理由に P1/P2 を止めない。

### WS-D NDLマッチング基盤（二段分割）

- D0 evidence/lineage/status/abstention 契約（設計完了・別文書）。
- D1 blocking/weight/threshold 較正（A1/B1 実測後）。

### WS-E promote — HOLD

cohort×decision_type×evidence_profile 別 gate。silent mutation 禁止。

---

## 4. DD-LITID の「真の付加価値」（既存と重複しない）

既存パイプライン（ndl_harvest / ndl_normalize / ndl_integrate）は **ISBN→NDL を manifestation 級で match** するが、以下は**やっていない**:

1. **版/刷の confirmed 区別**: 版（edition）を識別子で束ね、刷（printing）は無視。現状 12% の刷混入を識別・分離。
2. **2独立証拠での confirm**: candidate（NDL match alone）≠ confirmed（≥2 独立 origin_family）。
3. **adjudication 記録**: Q1 adjudication record（reviewer / basis / source_hash / decision_type / decided_at）。
4. **confusion bucket 集計**: false_merge_work / false_merge_edition 等の誤り型分類。
5. **evidence lineage**: origin_family / same_origin_collapse_key / content_hash / parser_lineage。
6. **状態機械（D0）**: candidate→{verified/rejected/abstain} / verified→{superseded/revoked/re_evaluated}。append-only、silent mutation 禁止。

→ **既存 match output（`ndl_shelf_matched.csv`等）は L1 derived artifact として前提として使い、その上に D0/Q1-Q5 ガバナンス層を構築する。**

---

## 5. クリティカルパス（v0.4 修正）

```
P1 cohort-A較正:
  ndl_shelf_matched.csv(read-only)
    → Q1/Q2 gold・証拠契約（D0 event schema）
    → A1 評価（candidate retrieval + resolution quality）
    → D1 較正
    → E 個別 gate（HOLD）

P2 bencom remediation:
  match_titles_to_ndl.py(read-only 再利用)
    → 証拠 lineage 契約（Q2）
    → B1/B2
    → D1 較正
    → E 個別 gate（HOLD）

P3 source landing:
  C1/C2 field-profile（並走・blocking なし）
```

---

## 6. 直近スプリント（GO 範囲）

**GO（即時・read-only / reversible）**
1. `ndl_shelf_matched.csv` を read-only で参照し、cohort-A 被覆を集計。
2. A1 candidate 分類: 5,257件の cohort-A ISBN 有の match を Q1/Q2 条件で分類。
3. A2 後段: 421件を ndl_isbn_index.csv で照合（local read-only）。`freshness_miss` 53件分離。
4. A3 後段: edition_statement / printing_no / date_role 分解（raw-preserving）。
5. A4: 6件 bib_id↔isbn 不整合の原本確認。Q1 gold seed 投入。
6. Q4 数値 sample plan: strata 別 minimum_n / CI の初期値を計算。
7. Q5 gate matrix: cohort-A / bencom 行に実測値を充填。

**CONDITIONAL GO（reversible artifact-only）**
- R1 manifest の owner 欄（internal_use_class / external_egress / storage_location）確定後、
  ndl_isbn_index.csv を isolated artifact 参照（Mac local trusted のみ）。

**HOLD（不変）**
- R2 rebuild / DB write / backfill / promote / serving / embedding / 外部公開 / egress 条件確認前の外部搬出。
- `ndl_bib_id` の verified 一括昇格。
- R2 索引を canonical truth 扱い。
- 閾値 freeze は A1 実測後のみ。

---

## 7. 権利・egress（不変）

- NDL ダンプ原本・派生索引の external_egress = **prohibited**（owner 確認まで）。
- 処理は Mac local trusted のみ。出力は local isolated artifact に限定。
- Box source / DB / accepted_identity_state を変更しない（read-only 参照のみ）。

---

## 8. 監査拘束（不変）

- candidate ≠ confirmed
- coverage ≠ correctness（dump hit率は候補回収指標）
- cohort 外挿禁止
- medium 775 = existing_unconfirmed
- false-confirmation は hard veto（平均 precision に埋めない）
- 全 production HOLD

---

## 9. v0.3 監査 must_fix との対応（v0.4 追加分）

| 追加事項 | v0.4 での対応 |
|---|---|
| 「索引再ビルド不要」の確定 | §3 WS-R → 既存再利用に変更 |
| provenance root 確定 | §2 provenance root（books.json） |
| bib_records = 下流 snapshot 確定 | §2, §1 確定事実 |
| DD-LITID 付加価値の再定義 | §4 |
| books.json の成長（6384→6525）への対応 | §1, §2 |

---

## 10. 未確定・リスク（v0.4 更新）

- ダンプ列スキーマ未確認（R1 最優先）
- `ndl_bib_id` 76.7% の lineage 未確認（R4）
- 鮮度（2024+ 新刊抜け: `freshness_miss` 53件実証済み）
- LION BOLT・legallib 実メタ未確認（C1/C2）
- 6件 bib_id↔isbn 不整合の原本（A4・優先）
- 独立性判定が origin_family 単独で足りるか（content_hash 併用検討）
