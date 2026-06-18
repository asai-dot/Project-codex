# 起点メモ: 語彙オブジェクト現ボトルネック = build側 silver 解決（背景情報の収集）

> doc_kind: 計画起点メモ（背景集約・report-only） / **DD でも WO でもない・apply なし・全 HOLD 据置**
> author: Claude / date: 2026-06-18 / owner: 浅井
> 目的: 「辞書から語彙を作る（語彙オブジェクト = Meaning Backbone）」の現ボトルネックと、その背景情報を、
>       次に書く「ボトルネック解消計画」の起点として一枚に集約する。
> 親決定: DD-D1TAXO-003 v0.3 (ACCEPTED) / DD-LRINDEX-001 v0.3 (ACCEPTED, design-only) / DD-DATAARCH-001 v0.2 (DRAFT, GPT監査 pending)
> 一次ソース（Box, 正本）:
>   - DD-VOCAB-000 語彙総論 v0.1-draft (2026-06-10)
>   - DD-D1TAXO-003 KOS クロススキーム・マッピング規律 v0.3 (2026-06-15 accepted)
>   - DD-LRINDEX-001 リーガルリサーチ三軸インデックス v0.3 (2026-06-16 accepted)
>   - DD-DATAARCH-001 AI-ready データ層 v0.2-draft (2026-06-17)
>   - analysis: 15×16 case pivot / harvest_paradigm_correction / relationship_layer_status (2026-06-16〜17)

---

## 0. 一行

語彙オブジェクトの下流（概念層クロススキーム機構・論点 harvest・serve）は**すべて、引用/関係層が raw のまま
silver（同定解決）に達していないこと**で止まっている。**次の主戦場は手法の novelty でも人手アノテーションでもなく、
build側の silver 解決**である。

## 1. プロジェクトの現在地（語彙オブジェクト = Meaning Backbone）

- 語彙は文字列でなく**意味接続基盤**。Term 粒度 = sense、Hub = 意味結節点、mention→Term は write時 legal WSD。
- ソース構造: canonical bedrock 辞書（e-Gov定義 / 基本法律辞典 / 法令用語辞典＝DD-DICT-008）を骨格に、
  **交換可能な satellite KOS**（#15 D1判例体系目次 / #16 D1文献編事項索引 / NDLSH / 判例百選 …）を SKOS で横付け。
- INVARIANT（DD-D1TAXO-003 / DD-LRINDEX-001 で確定）: **いかなる単一ベンダー KOS も backbone/pivot にしない**。
  source-independent な概念層へ多対一マップ。どの satellite を外しても概念 identity・検索・推論は縮退するが壊れない。

## 2. ボトルネック（収束済み・実測）

> **意味付き citation（論点・要件事実に紐づき、かつ判例ID まで解決された引用）の在庫が実測ゼロ。**
> **関係層が raw のままで silver に達していない。**

- DD-LRINDEX-001 §4 look-before-build（賃料不払解除）: 判例 178,332 / ranked 候補 13,398（評釈付 882）/
  citation エッジ 55,978 だが **treatment 列 = 0・element 列 = 0 → claim_support 層は実測ゼロ**。
- DD-DATAARCH-001 §4 がリスク順位を是正: **第一・確実なブロッカーは「意味付き citation の在庫ゼロ・silver が前提」**。
  手法 novelty（層間引用からの論点創発）は中リスクに格下げ。**手法以前に入力データが無い**。
- 設計ピボット（harvest_paradigm_correction）: 論点・評価は**人手でタグ付けしない**。実務界が既に書いた痕跡
  （評釈→判例 / 文献TOC見出し＝論点タイトル / 判例間引用）から **harvest** する。実証＝賃貸借/解除で
  **659 判例が人手ゼロで論点タイトル付きで自動起立**。→ DD-LRINDEX-001 v0.4（G_HARVEST_NOT_MANUFACTURE）が GPT 確認パス待ち。

## 3. 関係層 3-tier の実測（全 287,298 エッジ）

| tier | 内容 | 件数 | 状態 |
|---|---|---|---|
| **A 解決済（使える）** | `article_annotates_hanrei`（評釈→判例） | 7,956 strong | ✅ |
| | `toc_row_reports_hanrei`（文献TOC→判例） | 7,039 strong | ✅ |
| | `case_ref_candidates`（雑誌TOC→判例参照） | 6,633 | ✅（曖昧含む） |
| **B 未解決（silver前）** | lic `cites_judgment_via_journal` | 23,914 | ⚠ 引く先が掲載位置文字列で判例ID未解決 |
| | lic `cites_judgment_by_date` | 5,571 | ⚠ court+date 未照合 |
| **C 不在（要取得）** | **判例→判例 直接引用（参照判例）** | **0** | ❌ D1 raw は判例"一覧"export で参照判例フィールド無し |

## 4. silver 解決の機会サイズ（実測）

- `hanrei_published_in`（判例→号）索引 = 掲載位置 **76,643**。
- lic via_journal 23,914（ユニーク掲載位置 12,169）のうち **解決可能 概算 5,849 = 24%**
  （24%止まりの理由 = 誌名正規化未済・頁レベル照合ロス）。誌名正規化＋号レベル fallback で歩留まり向上余地。
- → 掲載位置→判例ID の silver で、解説→判例の judgment-level 引用が **+約6k**（tier A 22k に上積み）。
- 共起グラフは、同一書籍粒度だと 89,358 ペアが **全て weight-1**（188判例収録の実務書が全ペアを link＝"同じ本"でしかない）。
  意味ある関係 = **同一論点セクション（TOC subtree）単位の共起** → TOC 階層解決という silver が前提。

## 5. 2つのデータ取得ギャップ（外部アクセス = owner GO 案件）

1. **#16 D1文献編事項索引が未取得**。#15 は取得済（21法編・55,074ノード・深さ10）。
   #16 は標本実査のみ（大分類 33・中分類 210、事項索引 pairs 123,209 / distinct 57,422、多重分類 43%）。
   DD-D1TAXO-003 の次手 = ratify 後に **#16 取得 WO**、その後に機構DD（DD-D1TAXO-004）。
2. **判例→判例 直接引用が D1 raw に無い** → 「反例が引く反例」を入れるには **D1 全レコード再取得 WO**
   （D1 セッション干渉注意）。

## 6. ボトルネックを解く正しい順序（関係層所見の結論）

1. **掲載位置→判例ID の silver 解決**（誌名正規化＋号/頁照合）→ lic 解説引用を judgment-level 化（+6k〜）。
   … → `WO-SILVER-CITEID-001`（本スイートで草案化）
2. **TOC 階層→論点セクションの構造化**（toc_node の parent/subtree を論点見出しに解決）→ 論点-section 共起
   ＋ harvest 論点創発の土台。 … → `WO-SILVER-TOCSECTION-001`（本スイートで草案化）
3. **判例→判例 直接引用の取得** = D1 全レコード再取得 WO。 … → `WO-D1HANREI-REFETCH-001`（本スイートで草案化）
4. 1–3 が揃って初めて、引用グラフからの論点創発（HNMFk×citation×LLMラベル）が乗る。**今は土台の silver が先**。

## 7. silver が立った後に効くアセット（先行投資の回収先）

- 判例 canonical 192,998 / 評釈密度 hyoshaku.jsonl 61,153 / #15 55,074 ノード。
- silver 後に展開可能（15×16 case pivot §6）:
  判例中心の二方向 論点フットプリント（上＝#15 path / 下＝#16 分類・事項）/ 概念層の多源シード /
  ずれ検出（上下不一致＝真の複数分野 or 分類ミスのレビュー対象が自動浮上）/ カバレッジ地図（無評釈＝学説的空白の可視化）。

## 8. 計画づくりに向けた未決の論点（次工程で owner 判断）

- silver-1 の着手単位: 1 claim_type（賃料不払解除・882 件 seed）の canary→batch か、掲載位置正規化の横断先行か。
- 外部取得 WO の順序とゲート: #16 取得 vs D1 再取得（参照判例）— どちらを先に owner GO するか / D1 セッション干渉回避。
- 監査ループ依存: DD-LRINDEX-001 v0.4（harvest 訂正）の GPT 確認パス、DD-DATAARCH-001 v0.2 の GPT 独立意味監査。
  計画はこの 2 つの結果に依存する。
- harvest の carverage バイアス（無評釈判例 = trace_absent）を honest_empty でどう扱うか。

## 9. ゲート（本メモの射程）

- 本メモは read-only 集約 = 分析記録のみ。candidate 生成・本番 write・外部取得なし。
- 継続 HOLD: DDL / DB write / production mapping / canonical mint / bulk fetch / D1 再取得（外部アクセス）/ MCP publication。
- 本メモは設計判断の採用ではない。下流の WO 草案（本スイート同梱）は**設計のみ**であり、実行承認ではない。
