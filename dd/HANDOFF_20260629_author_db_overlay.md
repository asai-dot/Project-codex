# 引き継ぎ書 — 著者DB 4ソース重畳 / 2026-06-29

次スレ向け。再導出せず即着手できるよう要点・ID・パス・次手を凝縮。

## 0. いま何をしている話か
ゴール＝**綺麗な著者DB（重複なし・誤紐付けなし・劣化なし）**。KAKEN・researchmap・CiNii・D1-Law の4ソースを同一研究者で重ね、立体的な著者エンティティを作る。
正＝設計資料 **`ALO_文献著者スキーマ仕様書_v1.0`**（Box `00＿設計資料/`, file_id `2158634254867`）。§2.2「source別並列・束ねない・劣化させない」が核。

## 1. ブランチ / 環境
- Git branch: **`claude/book-identification-progress-7yjxpc`**（全部 push 済）。merge済みなら default から切り直す規則。
- Supabase project_id: **`nixfjmwxmgugiiuqfuym`**（read-only execute_sql で観測）。MCP: 76fc35e2…(supabase) / 75ca4ee9…(box)。
- ワークフロースクリプト置き場: `/root/.claude/projects/.../workflows/scripts/`（このセッションで多数作成）。

## 2. オーナー確定事項（plan v0.2, `dd/DD-AUTHOR_4source_overlay_plan_v0.1_20260629.md`）
- **D1**: authority.* を仕様に寄せて拡張（text person_id 維持＋source別属性テーブル追加）。alo_persons 完全新規はしない。
- **D3**: スコープ=**全部**（人物＋alo_articles＋alo_books＋alo_serials＋work_authors）。フェーズ分割。
- **D5**: D1-Law著者ソース=**「文献編一覧」RTFエクスポート**（Box, 各誌フォルダ）。RTF→構造化パーサ要。
- **D6**: name_reading も補完（NDL/researchmap/CiNii かな）。さぼらない。
- **D4（唯一未確定）**: 実行境界。既定＝設計＋staging＋dry-run候補まで（本番DB書込/canonical昇格はゲート保留）。「scratch schemaへ実ロード」許可が出たら進める。

## 3. 確定した重要事実（再調査不要）
- **設計 alo_persons 系テーブルはDB・リポジトリ共に未構築**。`authority.person*`（text PK・128,081件）が暫定実装。
- **重複の主因**: scholar 行は CiNii *識別子トレース*（`cinii_identifier_traces`）だけロード→ `person_affiliation` 全件プレースホルダ。CiNii断片化で1研究者が最大208 person_id。
- **重複規模**: 同名>1 のクラスタ 2,832 / 24,287行（最大208）。うち scholar 22,637行。
- **名寄せキー階層**: researchmap/orcid(人物固有) ＞ nrid ＞ name_reading＋所属/分野 ＞ 手動。
  - `scholar_nrid` はトレース毎にユニーク＝**dedup に使えない（重複の原因）**。
  - **researchmap が決定打**: 重複scholar 17,516行→1,402人に収束（誤紐付けなし。1 researchmap→複数正規化名は6件のみ）。
- **join鍵（検証済）**: 記事 `creator[].personIdentifier(NRID)` == `authority.person_history.scholar_nrid` == `person_id` 末尾（`alo:person:scholar:kaken:<NRID>`）。
- **ソース別 person 構成**: scholar:kaken 73,155 / lawyer:nichibenren 48,690(実所属あり) / judge:yamanaka 6,236(裁判所＋年あり)。lawyer/judgeは重複僅少(875/24)。
- **リッチ本体は取得済・未カラム化**: CiNii=`cinii_batch`(~3GB), KAKEN Phase B spine 26,392/課題47,525, researchmap complete 13,966。所属機関・研究分野はDB未投入。
- **pacsigny person_data staging は Box未同期**（収穫機ローカルのみ）。Box `data/pacsigny/iteration/`(folder 390261083646) は D1-Law taxonomy ロード＋cinii/opac パケットのみ。突合は DD-KAKEN-RM 進捗記録(`stg_person_overlay`/25表/append-only/0エラー)を仕様として参照。

## 4. 既存資産（再構築禁止・流用する）
- `tools/scholar_enrich/parse_cinii_detail.py` … CiNii detail→所属/NDC分野（**検証済**）。バルク化が次手。
- `artifacts/author_dedup_kaken_researchmap_20260629.tsv` … researchmap名寄せ（主キー, 17,507行→1,402人）。
- `artifacts/author_dedup_claimlinked_20260629.tsv` … 著作ベース名寄せ（要確認, needs_review多）。
- `artifacts/person_multirole_profiles_20260629.{tsv,json}` … 多役割98人（source別 roles 配列）。
- `artifacts/ptype_correction_verified_20260629.tsv` … person_type訂正（ブラインド検証, 27件中21追認/6食違い）。
- `artifacts/author_uncertain_resolved_20260629.tsv` … uncertain 31→yes（catalog実証）。
- `artifacts/person_roles_DDL_proposal_20260629.sql` … 多役割DDL提案（HOLD, Phase A で統合）。
- `artifacts/author_db_dedup_rootcause_20260629.md` … 根本原因＆名寄せ方針。
- governance: `tools/litid_ingest/manifest_gate.py`, `tools/gpt_audit/alo_gpt_audit.py`, `dd/INGEST_SPEC_raw_intake_v0.2_20260618.md`, DD-LITID 各 md。

## 5. Box 参照ID（次手で使う）
- 設計資料フォルダ `00＿設計資料`: **370000902528** / 著者スキーマ仕様 file: **2158634254867**。
- CiNii detail フォルダ: **370904926857**（記事別JSON, ~50万件規模）。親 cinii_batch: 370902411861。
- scholar_author_context_20260422: **378151194740**（windows jsonl群, ただし所属はplaceholder）。
- D1-Law 文献編RTF 例フォルダ: ジュリスト **370941047499** / 判例タイムズ **370921111021** / 金融・商事判例 **365340847081** / 判例時報 **386846413287**。ファイル名パターン `文献編一覧_YYYYMMDD_HHMM.rtf`。
- ⚠ 大きいjsonl/rtf は MCP `get_file_content` がテキスト不可/巨大で落ちる。**バルクは Box ローカル同期の収穫機で走らせる**のが現実解。単一小ファイル(6KB JSON)は取得可。

## 6. 次手（優先順）
1. **Phase A**: source別属性テーブルの DDL 提案（`person_affiliations`(source列付き)/`person_specialties`/`person_degrees`/`person_external_ids`/`resolution_log`）を `person_roles_DDL_proposal` と統合 → `artifacts/author_overlay_DDL_proposal_v0.1.sql`。**apply しない**。
2. **Phase F サンプル**: D1-Law 文献編RTF を1誌（ジュリスト）でパーサ検証 → alo_articles + work_authors の candidate TSV。著者⇄記事の結線が人物重畳の核。
3. **Phase B バルク**: `parse_cinii_detail.py` を CiNii detail 全体へ（収穫機実行）→ 所属/分野 enrichment。
4. **Phase C**: `person_external_ids` spine 構築 → 既存 dedup 成果を `resolution_log` candidate 行へ。誤紐付け回避（キー不一致は needs_review）。
5. **Phase B+**: name_reading 補完。
- 全て candidate / artifacts 出力、DB書込・DDL apply・canonical昇格は §7-E HOLD。

## 7. ガバナンス（厳守）
- candidate ≠ confirmed（≥2独立origin_family＋adjudicationで確定）。
- DDL/backfill/promote/serving/embedding/外部公開は別監査ゲート。現状すべて HOLD。
- external_egress=prohibited は NDLダンプ/派生索引。CiNii/KAKEN/researchmap は別だが、バルク取得は Box内データの再処理で完結させる方針（盲目クロール不可）。
- 出力は local isolated artifact のみ。処理は trusted 環境。

## 8. このセッションの成果コミット（参考）
journal_reclassify / author_claim_adjudication / author_uncertain_resolved / ptype_correction_verified / person_multirole_profiles(98) / person_roles_DDL_proposal / author_db_dedup_rootcause / author_dedup_kaken_researchmap / author_dedup_claimlinked / scholar_enrich parser / DD-AUTHOR plan v0.2。全て branch に push 済。
