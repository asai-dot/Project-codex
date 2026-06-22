# DD-IMPL-ROADMAP-001 v0.1 — 設計三部作（LAYOUT/XMODAL/XDOC）実装ロードマップ candidate

> **id**: DD-IMPL-ROADMAP-001 / **version**: candidate v0.1 / **supersedes**: なし（新規）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-22 JST
> **status**: 計画 candidate（設計のみ・実装未着手）。本文書自体も GPT 監査ループ（gate=DDIMPL）に乗せる候補。
> **scope**: DD-LAYOUT-001 v0.5（accepted）/ DD-XMODAL-001 v0.4（accepted）/ DD-XDOC-001 v0.7（監査中）を、本番データ基盤に実装するための段階計画。
> **依拠（実測・2026-06-22）**: Supabase `nixfjmwxmgugiiuqfuym`（asai-dot's Project）本番スキーマ実査に基づく。再発見しない。

---

## 0. なぜこの計画が要るか（一文）
三部作は「**物理PDF→幾何→背骨TOC→本文テキスト→クロスモーダル検証→クロス文献比較→要件事実**」を数珠繋ぎにする**中間層**だが、本番にはまだ**背骨（toc_nodes）と素材（611スキャンPDF）と器（control.releases）しか無い**。中間層は丸ごと net-new。精度（反こたつ記事＝独立性ゲート）を壊さずに、**最小スライスで縦に貫通**させてから横に広げる。

## 1. 現状の地形（本番実測サマリ）
| 層 | 状態 | 実測 |
|---|---|---|
| 背骨 `biblio.toc_nodes` | **本番投入済** | 552,596行・`print_page` 552,544投入・`embedding`(pgvector) カラム有るが **0行投入** |
| 書誌 `biblio.books` / `bib_records` | 投入済 | 3,802 / 10,326 |
| 物理台帳 `bookdx.holdings` / `pdf_inventory` | 投入済 | scanned+has_pdf=**611**・isbn→Box folder_id 対応有 |
| 人物典拠 `authority.*` | 投入済 | person 128,081・publication 7,348・`ocr_extract`(bbox_json付) は**著者同定用の狭いOCR**（本文層ではない） |
| 要件事実 `formobj.*` | **設計済・空** | form_object/form_variant/requisite（`grounded_in_law`/`favors_role`）＝**XDOC table facet の出力先（キラーアプリ）** |
| 実案件 `dynamic.*` | 稼働 | cases/comms/documents/parties（body_text 有）＝アプリ側の生データ |
| リリース器 `control.*` | **機構有・未稼働** | releases 1件・active_release_pointer 未設定・source_snapshots（content_hash/artifact_path）＝**DD が前提する release_scoped/snapshot の実体** |
| 拡張 | 導入済 | pgvector 0.8.0 / pg_trgm 1.6 / pgcrypto |
| **幾何 page_block** | **無** | net-new |
| **本文OCR / chunk / source_text_revision** | **無**（書籍コーパスに対して） | net-new |
| **xmodal / xdoc 系** | **無** | net-new |

**含意**：(a) 背骨と素材は揃っている→OCR/幾何を載せれば数珠が繋がる。(b) `control.releases`/`source_snapshots` がそのまま `corpus_snapshot_id`/`release_id` になる→**再発明不要**。(c) `formobj` が XDOC の受け皿として既に待っている。

## 2. 不可侵の原則（全フェーズ通底）
1. **ゲート規律**：各 DD の HOLD（DDL/DB write/mint/Box mutation/OCR/embedding/training/production生成/clustering/promotion/claim support）は**フェーズ毎の明示 owner ratify + deploy ゲート**でしか開かない。accepted≠deployed。
2. **巨人の肩**：OCR/レイアウトは Docling+DocLayNet、整列は STAM(NW/SW)、アンカリングは W3C selectors、構造は METS/IIIF Range の内面化。自作しない（research dossier の通り）。
3. **精度ファースト**：独立性（content×observation の2軸）・confirmed には D2＋独立2 family・shared origin は裏付けにならない、を**実行コードのゲートとして**保持。promotion は常に人手。
4. **既存器に差し込む**：新テーブルは `control.releases`/`source_snapshots` に release_scoped で接続。append-only・current-by-pointer・single-writer（監査レーンと同じ規律）。
5. **inventory-probe 規律**：1カーネルで precision／撤回率／shared_source率／D2率／coverage を実測してから拡張（全 DD が要求）。
6. **設計が先に実行可能になる**：DD の受入試験（LAYOUT 9 / XMODAL ストレス5 / XDOC 12）を**コード化**し、合成 fixture で固める。DDL より前に「設計が通る」ことを機械証明する。

## 3. カーネル戦略（縦スライス）
横展開（611冊）の前に、**1カーネル**で全層を貫通させる。
- **カーネル候補（推奨）**：`賃貸借終了の要件事実`（XMODAL/XDOC の inventory-probe 例に既出・要件事実表が複数文献に存在＝table facet 比較が成立・formobj への出力が自然）。
- 必要素材：同一論点を扱う **2〜3冊**（論点体系／事実認定体系／民事裁判実務のいずれか重複巻）。`toc_nodes` から該当章を特定し、`pdf_inventory` で軽量PDFを引く。
- このカーネルで「目次タップ→軽量PDF該当領域→文字起こし表示」「表だけ／構造だけ／テキストだけ比較」を**実物で**出す。

## 4. 段階ロードマップ

### Phase 0 — 実行可能な契約 & 適合性ハーネス（**GO・ゲート不要・即着手可**）
DD を「accepted」から「executable & tested」へ。**production に一切触れない純関数とスキーマ。**
- **スキーマ実体化**：page_block / xdoc_alignment / xdoc_independence_assessment / xdoc_use_assessment / coverage_* / xdoc_support_edge / cluster_* を JSON Schema + 型（pydantic 等）で起こす。DD 本文と1対1。
- **純関数バリデータ（read-only）**：
  - `alignment_observation_id` canonicalization（symmetric side 正規化・cardinality 決定・companion set を ID 材料に）
  - independence `effective_value`/`effective_status` 算定（stale=fail-closed・invalid gate）
  - eligibility policy engine（XDOC §7 priority 表・purpose×target・none negative・is_positive 集合）
  - `coverage_complete_for_scope` / `_for_use_assessment`（range_class 別 adapter：interval_1d/grid_2d/rect_2d・空scope不成立・包含判定）
  - `support_edge_effective`（実在 evidence refs で active/current 判定）
  - method capability 検査（required companion ⊆ applied）
- **合成 fixture（負例中心）**：symmetric side-swap→同一id／CDC単独 vs +content_hash／reviewed=none→ineligible／coverage空scope→false／A~B,B~C で A-C missing→unknown／任意軸 invalid→ineligible。
- **適合性スイート**：各 DD の受入試験をテストとして実装。CI で回す（`tools/` 配下、監査CLIと同じ依存ゼロ規律）。
- **成果物**：`schemas/` + `validators/` + `tests/conformance/` + 適合レポート。
- **Exit 基準**：LAYOUT 9 / XMODAL 5 / XDOC 12 受入試験が**全て緑**。これが「設計の実装可能性」の機械証明であり、以降の DDL を de-risk する。
- **依存**：LAYOUT/XMODAL は即着手可。XDOC は v0.7 が PASS 圏に入り次第（設計ループと並走）。

### Phase 1 — 幾何パイプライン（1カーネル・**artifact 出力のみ**）
> ゲート：OCR/layout-detection は HOLD。**1冊・固定 snapshot 上で artifact（ファイル）生成、production DB へは書かない**狭いゲートを owner ratify で開く。
- カーネル本のうち1冊の**軽量PDF**に Docling+DocLayNet を適用 → page_block（bbox正規化・block_type 11ラベル・reading_order_key・hash bundle）を**JSON artifact**として生成。
- `toc_nodes.print_page` を介して page_block を該当 toc_node にアンカー。block_ref（脚注/図表 stitching）も artifact で。
- LAYOUT 受入ゲート（coverage可視・欠落断定しない・多重セレクタ・STAM自己修復の素振り）を実データで検証。
- **成果物**：1冊分の再現可能な幾何 artifact + coverage/quality レポート（`projection_result.coverage`）。
- **Exit 基準**：「目次→軽量PDF該当領域へジャンプ」が1冊で成立（locator が正しい領域を指す）。OCR/レイアウト品質を実測（DD-BOOKQ の digital.pdf_quality 系と接続）。

### Phase 2 — 数珠繋ぎの縦貫通（1カーネル・artifact）
- 連結：`biblio.books` → `toc_nodes`(print_page) → page_block(Phase1) → 本文 OCR chunk（source_text_revision 付）→ 軽量PDF locator → （重量PDFは保管/再OCR源）。
- カーネル章の**本文 embedding** を生成（T軸検索）— ただし staging/artifact。`toc_nodes.embedding` の本番 backfill は Phase 5。
- **成果物**：「書誌→TOC→PDF（重量/軽量）→文字起こし」が1カーネルで端から端まで辿れる参照可能チェーン。
- **Exit 基準**：意味的リンクだけで全層を追跡可能（浅井さんの「意味的に繋いでおけば追いかけられる」の実証）。

### Phase 3 — XMODAL 検証（1カーネル・read-only candidate）
- カーネル上で V/T/D 三角測量：V(page_block幾何+画像)・T(OCR+toc構造)・D(外部法体系 D0/D1/D2)。
- D軸の外部分類：DD-D1TAXO 系（既存・監査済 anchor）を D1 mapper の入力に。D2 は外部証拠（条文/判例DB）。
- agreement_signal candidate + possible_reason を生成。**external_source_family registry の DISTINCT family で独立性カウント**。confirmed 昇格は HOLD・writeback 無し。
- **成果物**：反こたつ記事機構の実データ実証。knowledge_yield（D2率・shared_source率・abstain率）。
- **Exit 基準**：「同一条文を両方が引くだけ」を independent と誤計上しないことを実データで確認。

### Phase 4 — XDOC ファセット比較（1カーネル・read-only・キラーデモ）
> XDOC v0.7+ が accepted に達していること。
- 同一カーネル（賃貸借終了要件事実）を2〜3冊で比較：**table facet**（要件事実表）／**structure facet**（章節）／**text facet**（同論点/引用）。
- xdoc_alignment observation + use_assessment candidate を生成（eligible 昇格は HOLD）。content×observation 独立性・coverage scope 包含・support graph を実行ゲートで強制。
- 候補 form_variant を `formobj` に **candidate として**渡す（accepted は人手）。
- **成果物**：「他文献の表だけ/構造だけ/テキストだけを比べる」実物 + 独立性ゲートが効いている証跡。要件事実層への candidate 供給。
- **Exit 基準**：版差分/引用/同論点/反復テンプレが candidate として取れ、shared origin が proof 裏付けに昇格しないことを確認。

### Phase 5 — 本番化（DD 毎に**個別 owner ratify + deploy ゲート**）
スライスが精度を実証して初めて：
- DDL：page_block / xdoc_* / xmodal_* テーブルを `control.releases` に release_scoped で作成。
- スケール：611冊へ OCR/幾何を展開（バッチ・冪等・single-writer）。
- backfill：`toc_nodes.embedding` 本番投入。release pointer 稼働化。
- 各昇格（FRBR/LITID/LITLINK/block_ref current）は引き続き人手ゲート。
- **Exit 基準**：適合性スイート（Phase0）+ スライス実測（Phase1-4）を deploy ゲートの証拠として提示。

## 5. フェーズ依存とゲート対応
```
Phase 0 (GO, gate不要) ──┬─→ Phase 1 (狭gate: 1冊OCR artifact)
  └ LAYOUT/XMODAL即着手    │      └─→ Phase 2 (数珠繋ぎ artifact)
  └ XDOC は v0.7 PASS後     │            └─→ Phase 3 (XMODAL read-only)
                          │            └─→ Phase 4 (XDOC read-only, XDOC accepted後)
                          └───────────────────────→ Phase 5 (本番 deploy gate × DD毎)
```
- Phase 0 は設計ループと**並走**（XDOC 監査と同時進行可）。
- Phase 1-4 は全て**固定 snapshot 上・production 不変・artifact 出力**＝reversible。
- Phase 5 だけが production mutation＝**個別 ratify 必須**。

## 6. 横断要素
- **ツール**：適合性ランナー & スライス生成 CLI を `tools/` に（`alo_gpt_audit.py` と同じ依存ゼロ・single-writer・append-only 規律）。
- **メトリクス**：全フェーズで knowledge_yield（precision・撤回率・shared_source率・D2率・coverage・facet別 yield）を artifact 化。
- **ガバナンス**：固定 `source_snapshot_id` 上で作業。台帳 append-only。Phase 5 まで production へ書かない。
- **監査**：本ロードマップ自体を gate=DDIMPL で GPT 監査に投函可（設計同様、別 family の目で叩く）。

## 7. 当面の具体アクション（次の着手・Phase 0）
1. 本ロードマップを commit（必要なら DDIMPL 監査へ投函）。
2. `schemas/`：LAYOUT page_block + XMODAL agreement + XDOC v0.7 の型を起こす。
3. `validators/`：observation_id canonicalization と eligibility policy engine から着手（最も誤実装を生む2箇所）。
4. `tests/conformance/`：XDOC 受入試験 9（symmetric id）と 7（CDC companion）を最初の負例 fixture に。
5. カーネル確定（§3 推奨＝賃貸借終了要件事実、対象 2〜3冊を `toc_nodes`/`pdf_inventory` で具体化）。

## 8. owner 判断が要る点（実装前に確認したい）
- **D1**：パイロット・カーネルは「賃貸借終了の要件事実」で良いか（別論点希望なら差し替え）。
- **D2**：Phase 0（適合性ハーネス）から始める方針で良いか（DDL より先に設計を実行可能化）。推奨＝Yes。
- **D3**：OCR/レイアウトは Docling+DocLayNet 路線で良いか（既存スキャン pipeline と二重にしない）。

## 9. loop_state
candidate（新規・実装未着手）→ owner レビュー / DDIMPL 監査候補。production mutation は全て HOLD。
