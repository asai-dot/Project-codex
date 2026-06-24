# WO-SILVER-TOCSECTION-001（草案）: TOC 階層 → 論点セクションの構造化

> doc_kind: WORK ORDER 草案 / **設計のみ・実行承認ではない** / status: DRAFT（owner GO 未）
> author: Claude / date: 2026-06-18 / owner: 浅井
> 親: DD-DATAARCH-001 v0.2（意味層④c 論点 = harvest）/ DD-LRINDEX-001 v0.3〜v0.4訂正待ち（G_HARVEST_NOT_MANUFACTURE）/ harvest_paradigm_correction_20260616
> 優先度: **silver 順序 #2** — silver-1 と並行可。論点 harvest 創発の土台。
> gate: 既存 TOC/エッジの構造化・集計のみ（read-only 派生）。**本番 write・論点 canonical 化・人手 seed は HOLD/禁止**。

## 0. 一行
`toc_row_reports_hanrei`（7,039 strong）の同一書籍 weight-1 共起（89,358 ペア・無意味）を、
**同一論点セクション（TOC subtree）単位の共起**へ精緻化するため、toc_node の parent/subtree を論点見出しに解決する。

## 1. 問題（measured）
- 同一書籍粒度の共起 89,358 ペアは **全て weight-1**（188 判例収録の実務書が全ペアを link＝"同じ本"でしかない）。
- 意味ある関係 = 同一**論点セクション**内の共起。これには TOC 階層（toc_node → parent → 論点見出し）の解決が要る。
- 論点ラベルは**人手で作らない**。文献 TOC 見出し＝実務界が既に書いた論点タイトルを **harvest** する
  （実証: 賃貸借/解除で 659 判例が論点タイトル付きで人手ゼロ起立）。

## 2. 出力（candidate のみ・本番 write なし）
- `silver_toc_section_candidates.jsonl`: toc_node → `issue_section_id` / `section_heading`（論点タイトル harvest）/
  `parent_path` / `depth` / `member_hanrei_ids` / `decision_status`(strong|review) / `evidence` / `honest_empty`(trace_absent)。
- `silver_issue_cooccurrence_candidates.jsonl`: 同一 issue_section 内の判例ペア（weight = 論点section共起 / 評釈密度）。
- `silver_toc_section_report.md`: section 化前後の共起ペア数・weight 分布・無評釈（trace_absent）割合。

## 3. 手順（dry-run / read-only）
1. toc_node の parent/subtree を辿り、**論点見出しレベル**（書名/章でなく論点粒度）を判定する規則を起こす。
2. 各 issue_section の member 判例を `toc_row_reports_hanrei` から束ねる。
3. 同一 issue_section 内ペアのみを共起辺にする（書籍全体の weight-1 全結合を**捨てる**）。
4. weight = 論点section 共起回数 × 評釈密度（hyoshaku.jsonl 61,153 を重要度に使う・harvest、人手重み付けしない）。
5. 評釈/TOC 痕跡の無い判例は `trace_absent`（db_unbuilt と区別）として honest_empty に隔離。

## 4. 受入基準（dry-run 完了条件）
- section 化で「意味のある共起ペア（論点section単位）」が同一書籍 weight-1 から分離・定量化されている。
- 論点見出しが harvest 由来（文献TOC見出し）であり、人手 seed / D1#15 分野分類での代替が無い（G_ELEMENT_PREDICATE_NOT_FIELD_CLASS）。
- strong（評釈密度の高い section）と review が二層分離。trace_absent が明示区別。

## 5. 本 WO で決めない / やらない（別ゲート）
- 論点 section の **canonical 化・accepted 化**（owner review 後の別パケット）。
- 引用グラフからの論点創発（HNMFk×citation×LLMラベル）= silver 完了後の後続（DD-DATAARCH §1 ④c probe）。
- 人手アノテーション層（WO-LRINDEX-ELEM-001 は supersede/破棄済）。

## 6. ゲート
- read-only。candidate は staging のみ。canonical graph・論点 ontology へ書かない。
- DD-LRINDEX-001 v0.4（G_HARVEST_NOT_MANUFACTURE）の GPT 確認パス確定前は、本 WO 出力を accepted 論点として扱わない。
