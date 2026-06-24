# 設計三部作 横断整合性・安定性監査（実データ投入前ゲート）

> **date**: 2026-06-24 JST / **author**: 番頭(リモートClaude) / **status**: research record（実データ投入前の統一性・安定性確認）
> **対象**: DD-LAYOUT-001 v0.5（accepted 6/19）/ DD-XMODAL-001 v0.4（accepted 6/19）/ DD-XDOC-001 v0.9（accepted 6/24）
> **問題意識（owner）**: DD は時系列バラバラに作られた（XMODAL v0.4 は 6/19・XDOC は v0.1→v0.9 を 6/19→6/24）。**時的ずれによる語彙・モデルの矛盾／ドリフト**が潜む。実データを流す前に統一性・安定性を確認する。
> **依拠**: 3 DD 全文の突合 ＋ 本番 `nixfjmwxmgugiiuqfuym` スキーマ実査 ＋ 適合性ハーネス（105テスト緑）。

---

## 0. 総合判定
**深い論理的矛盾は無い。** 三部作の原理（反こたつ記事・所有分離・ゲート・HOLD・巨人の肩）は一貫している。
ただし **XMODAL v0.4 が XDOC の後発精緻化（v0.5→v0.9）を取り込んでいない**ことに起因する**語彙・モデルのドリフトが6点**。いずれも矛盾ではなく**時的ずれ**で、実データが XMODAL→XDOC を流れる際に独立性・スナップショット・facet の意味が食い違うため、**投入前に整合パッチで揃えるべき**。

凡例：🟢 整合済 / 🟡 明確化（命名・文書化）/ 🔴 投入前に要・整合（モデル/写像）

---

## 1. ★独立性モデルのドリフト（最重要・🔴）
反こたつ記事の核＝「独立2源でなければ confirmed/eligible にしない」を、**2 DD が別構造で持っている**。

| 観点 | XMODAL v0.4 | XDOC v0.9 |
|---|---|---|
| 構造 | **単一** `external_source_family_registry` | **2軸** content_independence × observation_independence |
| family/軸 | `family_kind ∈ {statute_text, legal_dictionary, classification_scheme, commentary_publisher, **ocr_engine**, editorial_source, court_db}` | content軸＝`content_origin_assertion`(origin_object_type) / observation軸＝`member_pipeline_provenance`(ocr_engine/parser/normalization) |
| confirmed/eligible 条件 | D2 ＋ DISTINCT family ≥ 2 | content independent ＋ observation independent（軸別） |

**ずれの本質**：XMODAL の単一 registry は **content 系（statute_text/commentary_publisher/editorial_source/court_db/legal_dictionary）と pipeline 系（ocr_engine）を同じ family_kind 列に混在**させている。XDOC はこれを 2 軸に**分離**した（XDOC v0.2 で「external_source_family を2軸に拡張」と明記、しかし XMODAL は後追い更新されていない）。
→ **同じ unit が XMODAL で confirmed、XDOC で eligible 判定される時、独立性の数え方が構造的に食い違う**。XMODAL は「ocr_engine も1 family」と数え、XDOC は「observation軸」として別勘定する。

**推奨整合**：
- **共有 independence/family registry を1つ定義**し、`family_kind` に **axis タグ（content_origin | observation_pipeline）** を付与。両 DD がこれを consume。
- 写像：XMODAL `statute_text/legal_dictionary/commentary_publisher/editorial_source/court_db/classification_scheme` → XDOC content軸／XMODAL `ocr_engine` → XDOC observation軸。
- 実装は **XMODAL v0.5 小パッチ**（2軸化）または **共通語彙 DD（DD-INDEP-REGISTRY）** を新設し監査ループへ。

## 2. スナップショット/リリース命名（🔴/🟡）
| 概念 | DD 表記 | 本番 control |
|---|---|---|
| コーパス版 | XDOC `corpus_snapshot_id` | `source_snapshots.source_snapshot_id`（snapshot_kind=raw_source/normalized_export・例 bencom-library） |
| 法令版 | XMODAL `law_snapshot_id` / `source_version` / `valid_at` | **未登載**（別軸の authority 版） |
| リリース | XDOC/共通 `release_id` | `releases.release_id` ✅ **一致** |

- 🔴 **corpus_snapshot_id ↔ source_snapshot_id は同一概念で別名**。実データでは `control.source_snapshots` を正本にし、DD 側を alias/rename で束ねる（XDOC の corpus_snapshot_id = source_snapshots の特定 row）。
- 🔴 **law_snapshot は corpus_snapshot と別軸**（法令原文の版）。`source_snapshots` に `snapshot_kind=law_authority` で載せるか別管理かを確定。XMODAL の D2 はこれに依存するので投入前に住所を決める。
- 🟢 release_id は一致。

## 3. "coverage" の意味衝突（🟡）
- LAYOUT `projection_result.coverage{blocks_total, blocks_typed, blocks_untyped, scope_coverage}` ＝**射影の型付け被覆**（未型付けを「存在しない」と断定しない）。
- XDOC `coverage_assessment` / `coverage_complete_for_scope` ＝**member のテキスト範囲被覆**（required_ranges を covered が包含するか）。
- 同名・別意。矛盾ではないが、データ/コードで混同しやすい。**LAYOUT=`projection_typing_coverage` / XDOC=`range_coverage` と用語注記**（または rename）。

## 4. asset/revision 命名の不統一（🟡）
| 概念 | LAYOUT | XMODAL | XDOC |
|---|---|---|---|
| asset 同定 | `asset_ref` / `asset_variant` | （view 経由） | `asset_id` |
| テキスト版 | `source_text_revision_id` | `source_version` | member_tuple は **`text_revision`**・coverage/provenance は `source_text_revision_id` |

- 🟡 **XDOC 内部で不統一**：member_tuple `text_revision` ↔ coverage/provenance `source_text_revision_id`。
- 🟡 **DD 間で不統一**：asset_ref(LAYOUT) ↔ asset_id(XDOC)。
- **推奨**：`asset_id` と `source_text_revision_id` に統一（DD-LITID の asset 同定が正本）。投入前に正規語へ寄せる。

## 5. ★block_type → facet 写像が未定義（🔴・データ投入の前提）
- LAYOUT `block_type` ＝ DocLayNet 11（Caption/Footnote/Formula/List-item/Page-footer/Page-header/Picture/Section-header/Table/Text/Title）＋ALO subtype。
- XDOC `facet` ＝ structure | text | table | figure。
- **XDOC が LAYOUT のブロックを facet 別に比較するには、11ラベル→4facet の写像が要る**が、どの DD にも無い。
- **推奨写像（要 ratify）**：Table→table / Picture→figure / Text・List-item・Caption・Footnote→text / Section-header・Title・(toc tree)→structure / Formula→text(or 別扱い) / Page-header・Page-footer→除外。これを LAYOUT か XDOC に明文化。

## 6. canonicalization/hash 規約の一元化（🟡）
- XDOC §5 は canonical_json（NFC・key コードポイント昇順・sha256）を**精密に定義**。
- LAYOUT hash bundle（asset_content_hash 他5種）・XMODAL の id/hash は**正規化規則を明記していない**。
- 適合性ハーネスは**全モジュールで単一 canonical_json を共有**（de-facto 統一・良い安定化要因）。
- **推奨**：「全 DD のハッシュ/ID は XDOC §5 canonicalization に従う」と一文で横断宣言（cross-DD ハッシュ照合の前提）。

## 7. 依存 DD の版固定（🟡）
- XDOC/XMODAL は `DD-LITID-001` / `DD-LITLINK-001` を**版無し**で depends_on。
- DD-LITID は活発に進行中（`DD-LITID_TOC_RECONCILIATION`・`DD-LITID_FORWARD_ROADMAP v0.2/v0.3` の RESULT が Box に存在）。
- **推奨**：depends_on に版を固定（例 DD-LITID-001 v0.x）。LITID の asset 同定が三部作の入口（84/611 ギャップの解消経路）なので、版ずれは波及大。

## 8. 整合済み（🟢・確認済）
- **所有境界**：block_ref(LAYOUT・明示参照, cross_doc 含む) / lit_link(LITLINK・外部リンク) / xdoc_alignment(XDOC・推定整列)。XDOC `OWNERSHIP_NO_REDEF` で再定義しない。✅
- **unit_ref FK**：XDOC member_tuple.unit_ref{unit_kind: toc_node|page_block} は LAYOUT `block_id` / biblio `toc_node_id` を正しく参照（狭めない）。✅
- **ゲート名前空間**：G_LAYOUT_* / G_XMODAL_* / G_XDOC_* 衝突なし。✅
- **claim_support_eligible / evidence 昇格 HOLD**：3 DD すべて派生・claim_support 禁止で一貫。✅
- **reading projection の coverage 可視化**（未型付けを断定しない）と XDOC の coverage 不完全→ineligible は**思想的に同方向**（欠落を真と断定しない）。✅

## 9. 安定性（stability）所見
- **適合性ハーネス 105テスト緑**が三部作の **executable な共通契約**として機能（単一 canonical_json・受入試験全網羅）。最大の安定化資産。
- **本番ガバナンス機構**（control.releases/source_snapshots/active_release_pointer）は存在・健全。三部作テーブルはここに release_scoped で差し込む前提が成立。
- ただし上記 §1〜§7 のドリフトは**ハーネスでは未検出**（各 DD 内の整合は見るが、DD 間の語彙写像は範囲外）。→ **DD 間整合は本監査が担う**。

## 10. 実データ投入前ゲート・チェックリスト
投入（Phase 1 以降）の前に、以下を closed にする：
- [ ] 🔴 §1 独立性 registry 一元化（共有 family registry ＋ axis タグ・XMODAL 2軸化 or 共通 DD）
- [ ] 🔴 §2 snapshot 住所確定（corpus_snapshot_id=source_snapshots / law_snapshot の home）
- [ ] 🔴 §5 block_type→facet 写像の明文化＋ratify
- [ ] 🟡 §3 coverage 用語の曖昧性除去（projection_typing vs range）
- [ ] 🟡 §4 asset_id / source_text_revision_id へ命名統一
- [ ] 🟡 §6 canonicalization 横断宣言（XDOC §5 を正本）
- [ ] 🟡 §7 depends_on の版固定（DD-LITID/DD-LITLINK）

## 11. 推奨アクション（最小・巨人の肩）
1. **整合パッチを1本に束ねる**：「三部作整合付録（DD-TRILOGY-RECONCILE）」を新設し §1〜§7 の写像/命名/版固定を1文書に記述 → GPT 監査ループ（gate=DDRECONCILE 等）へ。各 DD を大改訂せず、付録で束ねるのが手戻り最小。
2. **XMODAL v0.5 小パッチ**は §1（2軸化）のみ実施（最も実害が大きいため）。他は付録で吸収可。
3. 付録 ratify 後に Phase 1 着手（block_type→facet・snapshot 住所が決まっていれば実データが筋を通る）。

## 12. loop_state
research record（投入前ゲート）。次アクション = 整合パッチ（DD-TRILOGY-RECONCILE）起票 → 監査。実装/DDL は引き続き HOLD。
