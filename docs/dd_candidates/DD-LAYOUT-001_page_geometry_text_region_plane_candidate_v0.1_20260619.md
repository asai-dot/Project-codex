# DD-LAYOUT-001 v0.1 — page 幾何・text-region 面（PDFに添える構造）candidate

> **id**: DD-LAYOUT-001 / **version**: candidate v0.1 / **supersedes**: なし（新規）
> **owner**: 浅井 / **author**: 番頭(リモートClaude) / **date**: 2026-06-19 JST
> **gate**: **設計のみ（candidate）**。DDL・DB書込み・Box mutation・mint・embedding/OCR 実行・canonical 発番は **含まない／HOLD**。
> **canonical 配置**: **未決**。CANONICAL_MAP（②の相談）確定までは本ファイル（`docs/dd_candidates/`）を candidate として扱い、`docs/tmplstruct/` への昇格は owner ratify 後。
> **位置づけ**: 7 オブジェクト宇宙（法令・判例・文献・雑誌・語彙・手続き・書式）の**横断基盤レイヤ**。文献本文(LIT)と書式(FORMOBJ)が共有する「紙面座標 ⇄ 論理テキスト ⇄ 構造」の橋渡し面を定義する。
> **再発見回避メモ**: Box 設計コーパスを `bbox/レイアウト/reading order/ブロック/座標/region` で探索し、対応する独立 DD は不在を確認（2026-06-19）。ただし H 側ローカルのみに相当 DD が存在する可能性は排除できない → §9 O1（ratify 前ゲート）。

---

## 0. 中核命題

PDF は線形テキストではない（段組・脚注・表・図・ヘッダ・ノンブル）。**未来の AI が PDF を縦横無尽に読む**には、ページ画像（pixels）・論理テキスト（OCR 本文）・構造（章節）を**一つの座標系で相互参照**できる必要がある。

既存スパイン（`source_text_revision` の char-offset／`toc_nodes.path`）に対し、**今は紙面幾何の面が空いている**。FORMOBJ `form_witness` が `page_span/toc_node` を持つのに **bbox を持たない**のと同根。本 DD はこの**幾何面 `page_block`**（＋ toc→ページの `toc_locator`）を、**派生・非 canonical・claim_support 不可**のレイヤとして定義し、最小追加で縦横無尽アクセスを開く。

---

## 1. AI が PDF に要求するアクセス様式（設計の動機）

| 様式 | 必要構造 | 既存/新規 |
|---|---|---|
| 縦（掘る）work→章→節→段落→文→語 | `toc_nodes.path` ＋ block 入れ子 | 既存＋新規(block) |
| 横（飛ぶ）他法令/判例/語彙/書式/他文献・別本の同論点 | DD-LITLINK ＋ 三軸 research_unit | 既存 |
| 指す（point）この一文＝紙面のどの矩形か／逆引き | **bbox ⇄ char_span** | **新規（本DD）** |
| 意味で寄る | chunk ＋ embedding | 既存(DD-LITCHUNK) |
| 時で見る（版・年次 drift・as_of） | TOCDRIFT / lawtime | 既存 |

---

## 2. 接地する既存オブジェクト（流用・新語彙を作らない）

- **論理テキストスパイン** = DD-LITTEXT-001 `source_text_revision`（char-offset・hash lineage・正規化 profile）。**再 OCR に耐える同一性の真**。
- **構造スパイン** = `biblio.toc_nodes`（DDTOCNODES 本番投入済 552,544 行。列: `book_id,title,page,depth,path,parent,toc_source,status`。`page`＝印刷ページ）。
- **意味** = DD-LITCHUNK-001（chunk / embedding input 境界）。
- **関係** = DD-LITLINK-001（lit_link_signal → candidate → accepted edge）。
- **資産** = books.json `digital.*`（DD-BOOK-002 §3 / DD-BOOKQ-001：`digital.pdf_quality.{tier,score,verified}`）。heavy(600dpi・OCR/保管) と light(pdf_light・表示) の variant。
- **位置決め語彙の先例** = FORMOBJ `form_witness.{source_identifier,page_span,toc_node,content_hash,extraction_method,source_confidence,provenance_family}` ＋ `gate_witness_edition_verified`。
- **観測ライフサイクル** = 01_TOC DD の `raw / observation / alignment / candidate / current view` 分離、**単一観測を canonical にしない**、版差分は上書きせずシグナル（DD-TOCDRIFT）。
- **配置思想** = 正本 H 側 / Box release store / Supabase read-mostly catalog（active_release pointer）。

---

## 3. 幾何面 `page_block`（新規・派生・非 canonical）

```text
page_block                         # 派生・release scoped・canonical にしない
  block_id
  asset_ref / asset_variant        # heavy | light（pixels の出所）
  physical_page
  bbox            [x0,y0,x1,y1]     # ページ正規化座標（0..1）。DPI 非依存 → heavy/light 共用可
  block_type      heading|body|footnote|table|figure|caption|header|nombre|marginal
  reading_order   int              # 段組・脚注を含む読み順の線形化
  char_span       -> source_text_revision (start,end)   # 論理テキストへの橋
  toc_node_id     -> biblio.toc_nodes                   # 構造への橋（任意）
  content_hash                     # asset 版検証（自己修復の鍵, §6）
  confidence
  status          raw|observation|alignment|candidate|current
  provenance      §4
```

幾何面があると AI は：
- 「この一文を画面でハイライト」= char_span → bbox → light page 投影。
- 「これは脚注/図/表で本文ではない」= block_type で判別（誤読防止）。
- 「段組をまたいで正しい順に読む」= reading_order。
- 「画像のこの領域＝何の文字列か」= bbox → char_span 逆引き。

### 3.1 `toc_locator`（①を内包）

```text
toc_locator                        # 派生・release scoped
  toc_node_id   -> biblio.toc_nodes
  asset_ref / asset_variant
  printed_page  # = toc_nodes.page（出所）
  physical_page # 範囲可（page_span 起点）
  page_offset   # printed → physical 実測オフセット
  content_hash / confidence / status
```
※ `toc_locator` は `page_block`（toc_node_id を持つ block 群）から導出可能だが、**目次タップ→該当ページ**の UI 経路を軽く引くための投影として独立に保持する。

---

## 4. 生成経路（両方を first-class・owner 指示「2は両方」）

`provenance` に生成経路を型付けし、**複数経路を併存**させる（一方が他方を上書きしない）。

```text
provenance:
  generation_method   bbox_ocr | retrofit_from_existing_ocr | manual | imported_external
  engine / engine_version
  generated_at
  source_text_revision_ref         # どの本文世代に対する幾何か
  asset_content_hash               # どの asset 版に対する幾何か
  provenance_family                # 多源・多数決の禁止判定用
```

- **A: bbox-OCR（主）** … 将来の OCR 再処理で本文と座標を同時出力（char_span と bbox が同源 → 整合が最も高い）。
- **B: retrofit（従だが first-class）** … 既存 OCR 資産（座標なし本文）＋ light/heavy 画像から後付けでブロック/bbox を推定し char_span に整列。**A を待たず既存蔵書に幾何を付けられる**。
- A と B は同一ページに**併存可能**。`current view` 選択は confidence/provenance で解決（§5）。**B を A が出たら捨てるのではなく、両方を観測として残す**。

---

## 5. 更新・追加・修正パターン（owner 指示「色々パターンありそう」）

幾何面は**一度作って終わりではない**。append-only 観測＋ current-view resolver で、破壊的上書きを避けて多パターンを吸収する（DD-TOCDRIFT/監査台帳と同流儀）。

| パターン | 扱い |
|---|---|
| **更新（情報の更新）** | 新 observation を追記し、resolver が current を切替。旧 observation は status 降格で**残す**（消さない）。 |
| **付け加え（不足ブロック補充）** | 既存ページに block を追加。reading_order は再採番でなく**間挿入可能な実数/再整列キー**で衝突回避。 |
| **修正（誤抽出訂正）** | manual observation を高 confidence で追記。元 observation は `superseded_by` で lineage 保持。 |
| **本文世代更新（再OCR）** | `source_text_revision` が変わると char_span が動く → 幾何は当該 revision にひも付くため**新 revision 用の observation を別途生成**、旧 revision 用は保持。 |
| **asset 版更新（軽量版作り直し）** | §6 自己修復。`asset_content_hash` 不一致の幾何だけ再整列。 |

- 共通原則: **append-only / 上書き禁止 / current は view で選ぶ / lineage を切らない**。
- `status` 遷移は前進のみ前提（raw→observation→alignment→candidate→current）。降格は新イベント追記で表現。

---

## 6. 自己修復（崩れても追従）

- ページ番号を同一性にしない。真は **char-offset（テキストスパイン）** と **content_hash**。
- 軽量版を作り直して**ページが結合/分割/回転/再圧縮**しても、`asset_content_hash` 不一致を検知 → **その asset の幾何（bbox/physical_page）だけ再整列**。char_span・toc_node・chunk・embedding は無傷。
- 整列は 1:1 を仮定しない（範囲対応可）。低 confidence は review（candidate 止まり）。

---

## 7. 本文(LIT)と書式(FORMOBJ)の共有基盤

`page_block` は **LIT chunk も FORM witness も“消費する”共通面**。
- LIT: chunk.char_span → page_block（bbox 群）で本文位置を可視化。
- FORM: `form_witness.page_span/toc_node` を **同じ page_block で bbox 接地**（FORMOBJ の bbox 欠落を本 DD が補完）。
→ 書式の条項位置と本文の論点位置を**一つの座標系**で扱える。「書式で構造の議論をしたが本文も同じ」＝幾何面の共通基盤化、という結論の実装。

---

## 8. ゲート

- **G_LAYOUT_DERIVED**: 幾何面は派生。canonical truth にしない。
- **G_LAYOUT_NO_CLAIM_SUPPORT**: bbox/locator/reading_order は **`claim_support_eligible=false`**（UI/位置決め専用。証拠・claim 支持に使わない）。
- **G_LAYOUT_APPEND_ONLY**: 上書き禁止・lineage 保持・current は view 選択（§5）。
- **G_LAYOUT_ASSET_HASH_VERIFIED**: 幾何は `asset_content_hash` 検証下でのみ current 化（§6, gate_witness_edition_verified 相当）。
- **G_LAYOUT_MULTISOURCE**: 同一 provenance_family の多数決で canonical 化しない（FORMOBJ 継承）。
- **G_LAYOUT_RELEASE_SCOPED**: catalog 露出は release 単位投影・active_release pointer 経由。

---

## 9. open items（ratify 前に解く）

```text
O1. H 側ローカルに DD-LAYOUT 相当（座標/レイアウト面）が既存でないかの突合。← ratify 前ゲート（再発見回避）
O2. bbox 正規化座標系の規約（原点・y 軸向き・回転表現）の確定。
O3. block_type の最小語彙の確定（語彙オブジェクト DD-TOCVOCAB/語彙側と整合）。
O4. reading_order の挿入耐性キー（実数 or LexoRank 等）の選定。
O5. catalog 投影スキーマ（現 catalog.toc_index は page を持たない。locator/幾何の投影先）。
O6. retrofit(B) の抽出器選定と confidence 規約。
O7. canonical 配置（docs/tmplstruct 昇格 or H 側）＝ CANONICAL_MAP 決定に従属。
```

## 10. HOLD（本 DD では一切行わない）

DDL / DB 投入 / backfill / mint / Box mutation / OCR 実行 / embedding 生成 / production mapping / single-source からの canonical 化 / `docs/tmplstruct` への昇格。

## 11. 最小性の主張

net-new は実質 **`page_block`（幾何面）＋ `toc_locator`** の 1 レイヤのみ。テキスト/構造/意味/関係/資産は既存スパインに既存。**最小追加で AI の縦横無尽アクセスが開く**。
