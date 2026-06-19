# DD-XDOC-001 v0.1 — faceted cross-document comparison & alignment（文献間ファセット比較）candidate

> **id**: DD-XDOC-001 / **version**: candidate v0.1 / **supersedes**: なし（新規）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-19 JST
> **gate**: 設計のみ candidate。DDL/DB/Box mutation/mint/学習/embedding/OCR は HOLD。
> **depends_on**: DD-LAYOUT-001 v0.5 accepted（型付きブロック・projection・block_ref 供給）, DD-XMODAL-001 v0.4 accepted（独立性・external_source_family registry・自己循環禁止）, DD-LITID-001（asset/work 同定）, 三軸 v0.3。
> **位置づけ**: XMODAL＝**文書内・モダリティ横断**（V/T/D）。本 XDOC＝**文書間・ファセット内**（構造だけ/テキストだけ/表だけを横並び比較）。reading projection（1文書内で抜く）の**双対**＝同じファセットを複数文献から抜いて整列。

---

## 0. 中核命題
型付き・アドレス可能なブロック（DD-LAYOUT）があれば、**文献間で1ファセットだけを独立に比較**できる：構造だけ／テキストだけ／表・図だけ。これで版差分・引用/転載・同論点・反復テンプレ・潜在構造が、コーパス規模で取れる。**派生・非canonical・claim_support_eligible=false・人手ゲート。**

## 1. ファセット別比較（巨人の肩）
| facet | できること | 乗る先行研究（→ 研究ドシエ参照） |
|---|---|---|
| **structure** | 章節ツリー整列 → 版差分・体系比較・**FRBR work クラスタ** | tree edit distance / FRBRization / DD-TOCDRIFT |
| **text** | 同一文・引用/転載・同論点・重複排除 | **MinHash/SimHash・CDC** / text-reuse / 埋め込み類似 |
| **table / figure** | 要件事実表・比較表・チャート横並び・**反復テンプレ抽出** | table structure matching / **RoadRunner** → FORMOBJ `form_variant` |

## 2. 派生レイヤ語彙
```text
xdoc_alignment                    # 派生・release scoped・claim_support_eligible=false
  facet∈{structure,text,table,figure}
  unit_a @ asset_a  ↔  unit_b @ asset_b   # toc_node↔toc_node / text_span↔text_span / block↔block
  similarity / method / method_version
  status∈{candidate,reviewed,accepted,rejected}
  provenance
xdoc_cluster                      # 多文献クラスタ（work-set / テンプレ群 / 同論点群）
  cluster_id / facet / member_units[...] / cluster_kind∈{work_set,template,doctrine_overlap}
```
- `unit_a/unit_b` は DD-LAYOUT の安定アンカー（toc_node_id / page_block / text_pos）を参照。
- asset 同定（どの版/どの本か）は **DD-LITID/FRBR**（DD-LAYOUT の cross_doc dst_asset と同じ依存）。

## 3. ★独立性の罠は corpus 規模でも同じ（XMODAL 継承・必須）
「2冊でテキスト一致」＝**同じ外部源を両方が引用しているだけ**かもしれない（両方が同一条文/判例を引く）＝**1源であって独立2源でない**。
- **G_XDOC_SHARED_SOURCE_NOT_INDEPENDENT**：cross-doc 一致は **DD-XMODAL の external_source_family registry** を継承し、共有源（同一条文/判例/編集源）の一致を「独立裏付け」と数えない。
- **G_XDOC_NO_SELF_LOOP**：比較で作った整列を観測に書き戻して再比較しない（自己確証禁止）。
- これを外すと **コーパス規模のこたつ記事**になる。

## 4. 出力（候補・人手ゲート）
- **版差分**（structure/text alignment）→ FRBR expression 差分候補（DD-LITID へ）。
- **引用/転載・同論点**（text）→ DD-LITLINK candidate（accepted は人手）。**evidence へ直接入れない**（文献chunk は supporting_analysis 止まり＝LIT DD 共通ゲート）。
- **反復テンプレ**（table/figure）→ FORMOBJ `form_variant` / `witness_cluster` candidate。
- 全て `status=candidate`、**自動正準化しない**（新hub/新構造 auto=0）。

## 5. ゲート
- G_XDOC_DERIVED（派生・非canonical）／G_XDOC_NO_CLAIM_SUPPORT（比較結果は claim_support_eligible=false）／G_XDOC_HUMAN_PROMOTION_ONLY（accepted は人手）。
- G_XDOC_SHARED_SOURCE_NOT_INDEPENDENT（§3）／G_XDOC_NO_SELF_LOOP（§3）。
- G_XDOC_FACET_ANCHORED（比較単位は DD-LAYOUT の安定アンカーに接地。生テキスト同士の素朴比較を避け、unit/selector で縛る）。

## 6. inventory-probe 規律（三軸 v0.3 / XMODAL 継承）
カーネル1本（例：賃貸借終了の要件事実表を数冊で構造比較）で precision・撤回率・**shared_source率**を実測してから拡張。`knowledge_yield` に facet 別 yield と shared_source 率を含む。

## 7. open items
O1 facet 別 similarity 手法・閾値（structure=tree edit / text=MinHash+embedding / table=構造マッチ）の選定／O2 asset 同定の DD-LITID 接続／O3 shared_source 検出（共有引用の同定）／O4 xdoc_cluster の clustering（consensus / HDBSCAN）／O5 evidence 昇格禁止の機械化。

## 8. HOLD / loop_state
HOLD：DDL/DB/mint/Box mutation/学習/embedding/OCR/production。loop_state = **candidate（新規）→ GPT 監査候補**。観測は1件も書き換えない。
