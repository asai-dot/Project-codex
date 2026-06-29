# DD-AUTHOR — 4-source overlay load + dedup 実装計画 v0.1

**Status:** DRAFT / plan for review  **Date:** 2026-06-29
**Spec of record:** `ALO_文献著者スキーマ仕様書_v1.0`（Box `00＿設計資料/`）
**Governance:** INGEST_SPEC v0.2（§7-A manifest gate / §7-D candidate≠confirmed / §7-E GO・HOLD）、DD-LITID append-only 原則

---

## 1. Context（なぜ）

ゴールは「綺麗な著者DB」＝**重複なし・誤紐付けなし・劣化なし**で、KAKEN・researchmap・CiNii・D1-Law の4ソースを同一研究者で重ね、立体的な著者エンティティを作る。これは新規発想ではなく、仕様 §2.2「リッチなデータはリッチなまま持つ…source列でソースを区別し、束ねない。元データは劣化させない」の実装に他ならない。

**根本原因（確定済）:** scholar 行は CiNii *識別子トレース* レーン（`cinii_identifier_traces`）だけがロードされ、`authority.person_affiliation` は全件プレースホルダ（"CiNii scholar identifier anchor"）。同一研究者が CiNii 断片化で最大208 person_id に膨張。リッチ本体（実所属・NDC分野・論文）は Box に既収穫だが**カラム化されていない**。

**現状の事実:**
- 設計 `alo_persons` 系テーブルは**DB・リポジトリともに未構築**（live DB 確認済み）。`authority.person*`（text PK・128,081件）が暫定実装。
- 4ソースの素材は既に存在: CiNii(`cinii_batch` ~3GB) / KAKEN(Phase B spine 26,392・課題47,525) / researchmap(13,966 complete) / D1-Law(文献449,677・※未ロード)。
- 6月のKAKEN intake が append-only staging 計画 `stg_person_overlay`（25テーブル）を作成済だが **本リポジトリ外**（Box `app/data/pacsigny/iteration/`）。本計画と重複させないため要参照。

---

## 2. 決定事項（推奨デフォルト。▲＝要確認）

| # | 論点 | 推奨 | 理由 / トレードオフ |
|---|------|------|------|
| D1 ▲ | スキーマ方針 | **authority.* を仕様に寄せて拡張**（text person_id 維持＋source別属性テーブル追加） | 128K人と publication_author_claim 等のFKを再キーイングせずに、仕様の「source別並列・劣化なし」を実現。完全な alo_persons(bigserial) 新規は理想だが大規模移行になる |
| D2 ▲ | 既存 stg_person_overlay | **新規設計するが互換に保ち、実行前に必ず突合** | pacsigny 一式が本リポジトリに無く未読。二重構築回避のため、実装着手前に当該ファイルをリポ取込 or 参照 |
| D3 | スコープ | **人物/著者のみ** | alo_persons + source別属性 + external_ids + resolution_log + work_authors(スタブ)。alo_articles/books/serials（D1-Law 449k 等）は別タスク |
| D4 | 実行境界 | **設計＋staging＋dry-run 成果物まで**（candidate） | 本番DB書込/canonical昇格は §7-E HOLD のまま。現行ガバナンス整合 |

---

## 3. 現 authority.* → 仕様 カラムマッピング

### 3.1 人物本体
| 仕様 `alo_persons` | 現 `authority.person` | 措置 |
|---|---|---|
| person_id (bigserial) / person_uri | person_id (text, 例 `alo:person:scholar:kaken:<NRID>`) | **維持**（text を canonical uri 兼用）。dedup 後の代表IDを `canonical_person_id` 列で別管理 |
| name_raw / name_norm / name_reading | canonical_name / canonical_name_normalized / （読みは person_history?） | name_reading は NDL読み未取得→補完課題 |
| person_type | person_type (4値CHECK) | 仕様も単一。多役割は別表（既提案 person_role / specialties）へ |

### 3.2 source別並列属性（**ここが本計画の核**）
| 仕様テーブル | source 値 | 現状 | 措置 |
|---|---|---|---|
| `person_external_ids` (cinii_nrid/kaken_id/researchmap_id/orcid/ndl_auth) | — | person_history に nrid/researchmap/orcid が散在 | **新設**し history から正規化移送 |
| `person_affiliations` (institution/department/position, **source**, as_of, is_current) | kaken/researchmap/cinii | person_affiliation は単一source_system・placeholder | **source列付きで再設計**。CiNii分は parser 出力で実値投入 |
| `person_specialties` (specialty_label, **source**, source_detail) | kaken/researchmap/cinii | 無し | **新設**。KAKEN研究キーワード / NDC / researchmap 分野 |
| `person_degrees` / `person_awards` (**source**) | kaken/researchmap | 無し | **新設**（researchmap/KAKEN由来） |
| `resolution_log` (decision/decision_basis: nrid_match/name_reading_match/kaken_coauthor) | — | dedup は TSV のみ | **新設**。既存 dedup 成果を decision イベント化 |
| `work_authors` (entity×person, role, ordinal) | publication_author_claim | 近い | claim を work_authors 形に写像（スタブ）|

---

## 4. 作業分解（既存資産を再利用・重複回避）

### Phase A — スキーマ提案（DDL, HOLD）
- 仕様 §4 の **source別属性テーブル**（person_external_ids / person_affiliations(v2,source列) / person_specialties / person_degrees / person_awards / resolution_log）の DDL 提案を起こす。
- 既存 `artifacts/person_roles_DDL_proposal_20260629.sql`（多役割）と統合し、矛盾のない1セットに。
- 成果物: `artifacts/author_overlay_DDL_proposal_v0.1.sql` + mapping doc。**apply しない**。

### Phase B — ソース別パーサ → candidate TSV
各ソースを source タグ付きで正規化（劣化させない）。
- **CiNii**: `tools/scholar_enrich/parse_cinii_detail.py`（**既存・検証済**）をバルク化。所属＋NDC分野→ affiliations(source=cinii) / specialties(source=cinii)。実行は3GBがローカル同期された収穫機。
- **KAKEN**: 新パーサ。Box KAKEN overlay（spine/課題/キーワード/所属）→ affiliations(source=kaken)/specialties(source=kaken)/degrees。※pacsigny overlay と突合（D2）。
- **researchmap**: 新パーサ。所属歴/分野/学位/受賞 → 各 source=researchmap。
- **D1-Law(著者)**: 著者⇄著作リンク → work_authors。著者属性は持たない（D1は著作次元）。
- 出力規約: `artifacts/<table>_<source>_candidate_YYYYMMDD.tsv`、claim_status=candidate、evidence_source/decision_method 付与。

### Phase C — external-id spine + 名寄せ → resolution_log(candidate)
- `person_external_ids` を nrid/researchmap/orcid で構築（同定の鍵）。
- 名寄せ確定キー優先順位（仕様 decision_basis）: **researchmap/orcid（人物固有）＞ nrid＞ name_reading＋所属/分野一致＞ 手動**。
- 既存成果を decision 化: `author_dedup_kaken_researchmap_20260629.tsv`（researchmap, high）＋ `author_dedup_claimlinked_20260629.tsv`（著作, needs_review）→ `resolution_log` candidate 行。
- **誤紐付け防止**: 同名でもキー不一致は merge せず needs_review（仕様/ユーザ要件）。
- researchmap無し5,126行は Phase B の KAKEN/CiNii 機関・分野で再評価。

### Phase D — 重畳アセンブリ + QA ゲート + manifest
- 4ソースを person_id(代表) で重ね、立体プロファイル（source別に全保持）を候補生成。
- QA（仕様 §11 LIT-style）: external_id無し率、merge根拠無し0件、同名異所属の分離率、placeholder残存0。
- INGEST_SPEC §2 manifest を各ソースに付与（source/fetched_at/rights_class/evidence_locator…）。

### Phase E — ゲート昇格（HOLD）
- append-only staging への COPY dry-run（D2の既存計画と整合）→ 監査（GPT audit loop）→ owner ratification → canonical 昇格。**本計画では設計/ dry-run まで**。

---

## 5. 再利用する既存資産（再構築しない）
- `tools/scholar_enrich/parse_cinii_detail.py`（CiNii→所属/分野、検証済）
- `artifacts/author_dedup_kaken_researchmap_20260629.tsv`（researchmap名寄せ・主キー）
- `artifacts/author_dedup_claimlinked_20260629.tsv`（著作名寄せ・要確認）
- `artifacts/person_multirole_profiles_20260629.json`（多役割・98人）
- `artifacts/ptype_correction_verified_20260629.tsv`（person_type訂正）
- `artifacts/person_roles_DDL_proposal_20260629.sql`（多役割DDL）
- governance: `tools/litid_ingest/manifest_gate.py`, `tools/gpt_audit/alo_gpt_audit.py`, `dd/INGEST_SPEC_*`

## 6. 重複リスク（要回避）
- 6月 `stg_person_overlay`（25テーブル, 180,762行）と Phase A/B が二重になる恐れ → **着手前に pacsigny 一式を確認**（D2）。

---

## 7. 未確定・ユーザ確認事項
1. **D1 スキーマ方針**: authority.*拡張（推奨）か、alo_persons 完全新規か。
2. **D2 既存staging**: 既存 stg_person_overlay を土台にするか／新規か。→ pacsigny `person_data_append_only_staging_load_v1_*` をリポジトリに取り込めるか（私が読めるように）。
3. **D3 スコープ**: 人物のみ（推奨）か、articles/books も含む全構築か。
4. **D4 実行境界**: dry-run候補まで（推奨）か、scratch schema 実ロードまでか。
5. **D1-Law 著者データの所在**: D1-Law 文献編（著者⇄著作）の取込元はどこか（Box path / 既存テーブル）。authority.publication は7,348件のみ＝D1著者は未ロードと推定。
6. **NDL読み仮名**: name_reading 充足の要否（specialties/affiliations の前に人物正規化の質に効く）。

## 8. 検証（dry-run）
- Phase B パーサは小サンプル（各source数十NRID）で TSV を生成し、source列・evidence_source・カラム充足を確認。
- 名寄せは researchmap キーの「1 researchmap→複数正規化名」件数を再監視（現状6件のみ＝安全）。
- DDL は `EXPLAIN`/構文チェックのみ、apply しない。
- 全出力は `artifacts/` candidate、DB書込なし（§7-E）。
