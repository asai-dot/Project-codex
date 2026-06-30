# DD-AUTHOR — 4-source overlay load + dedup 実装計画 v0.2

**Status:** DRAFT / decisions locked by owner 2026-06-29  **Date:** 2026-06-29

> v0.2 更新: オーナー回答で論点確定。D1=authority.*拡張 / スコープ=全部(人物+articles+books+serials) / D1-Law著者ソース=「文献編一覧RTF」 / name_reading も補完(さぼらない) / pacsigny の person_data staging は Box 未同期(収穫機ローカルのみ)＝Boxから取込不可。
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

## 2. 決定事項（オーナー確定済 ✅ / 既定 △）

| # | 論点 | 決定 | 補足 |
|---|------|------|------|
| D1 ✅ | スキーマ方針 | **authority.* を仕様に寄せて拡張**（text person_id 維持＋source別属性テーブル追加） | 128K人と claim FK を再キーイングせずに「source別並列・劣化なし」を実現 |
| D2 ✅ | 既存 stg_person_overlay | **任せる／先にリポジトリ取込可** → ただし **person_data staging は Box 未同期**（収穫機ローカルのみ）。Box `data/pacsigny/iteration/` 実体は D1-Law taxonomy ロード＋cinii/opac パケット。**person_data_append_only_staging_load_v1_* は取込不可** | 突合は DD-KAKEN-RM 進捗記録（schema `stg_person_overlay`/25表/append-only/検証0エラー）を仕様として参照。実ファイルが要るならオーナーが Box 同期 |
| D3 ✅ | スコープ | **全部**（人物＋alo_articles＋alo_books＋alo_serials＋work_authors） | 大規模プログラム。フェーズ分割で着手（§4） |
| D4 △ | 実行境界 | **設計＋staging＋dry-run 候補まで**（既定。未明示回答） | 本番DB書込/canonical昇格は §7-E HOLD。scratch schema 実ロードに進める場合は一声 |
| D5 ✅ | D1-Law著者ソース | **「文献編一覧」RTFエクスポート**（Box: ジュリスト/金融・商事判例/判例タイムズ/判例時報 各誌, 各~0.5–0.7MB） | これが D1-Law 文献編（著者⇄著作）のリッチ原本。RTF→構造化パーサが要 |
| D6 ✅ | name_reading | **補完する**（NDL読み仮名等で人物正規化の質を上げる） | specialties/affiliations 前段の人物同定品質に効く |

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

### Phase B+ — name_reading 補完（D6）
- 人物正規化品質のため `name_reading`（読み仮名）を NDL 典拠 / researchmap / CiNii kana から補完し `alo_persons.name_reading` 相当へ。dedup の `name_reading_match` 基準にも効く。source別・劣化なしで保持。

### Phase F — 文献コンテナ（D3 全部スコープ。著者と並行する大規模レーン）
- **alo_serials**: ISSN マスタ（文献編RTF / staging_periodical から）。
- **alo_books**: 既 biblio.books / bib_records / NDL から（edition_number 抽出は仕様 §8、既 A3 edition 成果を流用）。
- **alo_articles**: **D1-Law 文献編RTF（D5）→ パース**（著者・誌名・巻号・事項索引・分類）。449,677件規模。`work_authors` で著者⇄記事を結線し、人物次元（A–E）と重畳。
- 規模が桁違いのため、サンプル誌（例: ジュリスト1誌）で RTF パーサと article/work_authors 投入を検証→横展開。

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

## 7. 残・確認事項（v0.2）
- **D4 のみ未確定**: dry-run候補まで（既定で進行）か、scratch schema へ実ロードまで許可するか。返答なければ既定（dry-run候補・昇格HOLD）で進める。
- **pacsigny person_data staging**: Box 未同期で取込不可。実ファイル突合が必要ならオーナーが Box へ同期。なければ DD-KAKEN-RM 進捗記録を仕様として整合（重複回避は維持）。
- 他（D1/D2/D3/D5/D6）は確定。

## 8. 検証（dry-run）
- Phase B パーサは小サンプル（各source数十NRID）で TSV を生成し、source列・evidence_source・カラム充足を確認。
- 名寄せは researchmap キーの「1 researchmap→複数正規化名」件数を再監視（現状6件のみ＝安全）。
- DDL は `EXPLAIN`/構文チェックのみ、apply しない。
- 全出力は `artifacts/` candidate、DB書込なし（§7-E）。
