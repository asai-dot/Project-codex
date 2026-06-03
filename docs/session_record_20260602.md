# 辞書クリーニング・セッション記録 — 2026-06-02（v4 全体版）

`DISPATCH-HEADLESS-MIGRATE-001` 起点。JLT v19.0 着地 → 学陽 Phase1.5 → 3点測量 →
多型OCRミス検出（読み／引用／本文）→ 読み訂正適用、までの確定記録。
実装は repo `asai-dot/Project-codex` ブランチ `claude/gakuyo-headless-migrate-AuGAM`（PR #2）。
**生データ非改変・訂正は台帳/提案層（auto_apply=false）**。

## 1. 基盤データ
| 資産 | 実体 | 状態 |
|---|---|---|
| JLT v19.0 正典 | Box `05＿語彙レイヤー/jlt_v19_0`(386440014344) golden8 | byte-exact 着地・8/8 sha1検証 |
| JLT 権威見出し語 | repo `data/jlt/` 3,869 | term-set sha256 51d767a0… |
| 学陽 all_entries | repo `data/gakuyo/` 2,684 | byte-exact md→phase1_5（収録2,603+1.9%） |
| 有斐閣 all_entries | Box `dict_ocr/all_entries.jsonl`(2185088113728) 13,344 | 既存・構造化済（読み99%） |

## 2. 3点測量（JLT×学陽×有斐閣）
union 15,654 / **3源一致 core 922** / 学陽のみ564 / 有斐閣のみ10,159。
`phases/triangulate_terms.py`、`docs/triangulation_survey_20260602.md`。

## 3. 多型OCRミス検出 — 結果
| 型 | 信号 | 成果 |
|---|---|---|
| **読み化け** | 読み × JLT権威 ＋ 多数決(5源) | **確定訂正 44件**（有斐閣中心）→ §4 |
| 引用誤字(A1) | 引用句 × e-Gov本文 | 7法令で実証。**学陽≒有斐閣**（§5） |
| 引用収縮 | 令+4桁 | 学陽3件確定（令9921/5710/2210） |
| 見出し語化け | ed≤1 × 定義類似 | 低収量＝負 |
| C2 文字perplexity | trigram surprisal | **負**（語境界に埋没） |

## 4. 読み訂正（本日の最高歩留まり・5ソース多数決）
ソース: JLT(権威100%) / 有斐閣(99%) / 学陽(2%) / **法律用語がわかる辞書**(EX-word抽出2,694) /
**法律用語IME辞書**(Togi Lab、1,510)。
- **確定訂正 計44件**（台帳 `data/readings/reading_corrections_ledger_20260602.jsonl`）。
  有斐閣33パッチ＋学陽4適用済＋多数決追加。例: 機関訴訟そうしょう→そしょう、被疑者ひきぎしゃ→ひぎしゃ、
  過誤納かごうのう→かごのう、親等いっしんとう→しんとう。
- **JLTが少数派＝誤りの2件**発見（保健所ほけんじょ・商事会社がいしゃ＝有斐閣が正）。JLTも万能でない。
- 連濁系の残39件は2源のみで未決。学陽truncation6件はartifact。
- `phases/reading_triangulate.py` / `reading_adjudicate.py`。

## 5. A1（引用×e-Gov）と「学陽≒有斐閣」結論
- 7法令（民法/会社法/刑訴/地自/国公/国税/民訴。law_id は a2b＋依存グラフ合成索引で解決、
  各 law_title を実ファイル検証＝地方自治法=322AC0000000067 自己確認）。
- 学陽: 144帰属引用→97 verbatim clean、候補は送り仮名/版差中心。
- 有斐閣: blob照合で実誤り **信義誠実「従わ」→民法1②「行わ」(従→行)** を検出。略語帰属(法令略語tsv)で
  精密化＝58帰属/33clean/候補3（版差・ルビ・境界＝非OCR、偽陽性除去）。
- **結論（head観測の裏取り）**: 学陽≒有斐閣。引用本文の実OCR誤りは両者**少数・同水準**。
  当初「学陽は綺麗」は方法バイアス（学陽=厳密帰属法／有斐閣=広いblob法）。apples-to-apples で
  学陽もblob法なら同数19候補・同偽陽性。**同系統OCRなら誤り率は近い**。
- 運用知見: 精密(略語帰属)=偽陽性0だが出典非隣接を取りこぼす／再現(blob)=拾うが偽陽性。**両者併用**。
- 被覆: 合成索引で law_id 解決=引用の27%。長尾73%は e-Gov 未取得＝フル走はローカルが効率的。

## 6. 発見した資産・空振り
- **法律用語がわかる辞書 第2版**（Box `decrypted/法律用語辞書.txt`、EX-word抽出）: 見出し語+読み2,694対
  クリーン（定義は暗号化で不可）→ `data/wakaru/`。
- **法律用語IME辞書**（Togi Lab「法律用語辞書 IME版」、浅井提供、1,510対）→ `data/legal_ime/`。再配布許諾は要確認。
- **法令略語表**（有斐閣 `dict_ocr/law_abbreviations.tsv` 約340）= A1の引用帰属に使用。
- **空振り**: BKUP.TXT/JSIBKRS.* = ジャストシステムのバックアップツール（辞書データでない）。
  有斐閣公式ATOK辞書=販売終了。EX-word法律用語辞書の**定義**は暗号化（復号は別タスク）。

## 7. ツール（repo `phases/`）
phase1_5_parse_md / build_jlt_authority / triangulate_terms / garble_localize /
reading_triangulate / reading_adjudicate / cross_reference_web / quote_check_egov /
perplexity_scan(負). 索引 `data/egov/gakuyo_law_index.json`。

## 8. 残課題・次手
- 連濁 review 残39（より高被覆の読みソースが要る）。
- 有斐閣33読み訂正の canonical 適用（owner手順、verify2件=図画/競売 要確認）。
- A1 全158法令ローカル一括＋長尾 e-Gov 取得。
- EX-word「法律用語がわかる辞書」定義の復号（第3の定義辞書化）。
- 掃除: Box `docs/alo` の `_TMP_*`（egov/有斐閣 読取コピー多数）は削除可。

## 9. 設計原則（貫徹）
suspect/台帳層・自動修正なし／「派生物を正本扱いしない」(review_queue 129件の轍)／measure-then-build／
権威は万能でない（JLT少数派2件）。

---

## 10. 引用・定義・条見出しの探索（v3 追記）
### 定義本文の同一語比較 ＝ 低収量
学陽∩有斐閣で両定義あり1,895語、文字類似度 median 0.19/max 0.81/≥0.5は2%。高類似でも差は
**編集上の言い回し**でOCR誤りでない。定義全文の突合は鈍い。
### B2（同一語×引用条番号の辞書間不一致）＝ 低信頼
95候補。条見出しで判定 → 大半「両方関連/不明」。「片方が誤り」は有斐閣引用パースの artifact
（付則/経過措置の括弧を条番号化）が主因。実用化は有斐閣引用抽出の精緻化が前提。
### ✅ e-Gov 条見出しデータ ＝ 綺麗な権威データ（本命）
7法令の **条番号→条見出し 4,367条/見出し3,267件**（`data/egov/egov_article_captions_7laws.jsonl`）。
tag木解析(Article/ArticleCaption)。引用ラベリング・概念ラベル・enrichment に使える。
### ✅ 見出し語→正典条リンク層 ＝ 綺麗な enrichment（本命）
見出し語 × 条見出し一致で **1,731リンク/326見出し語**（`data/citations/headword_to_article_links.jsonl`）。
検証→民訴232、抗告→民訴328、秘密→民訴92。「きれいな辞書データ」の中核。
誤り検算（法令は引くが見出し条を外す）95候補は大半正当な別条引用＝低収量。

## 11. メタ結論
- 辞書の**引用・本文は概ね妥当**。引用クロスチェック系（A1・B2・条検算）の**誤り発見は薄い**
  （学陽≒有斐閣、両者少数）。
- **実際に誤りが取れた太い鉱脈＝読み**（有斐閣中心44訂正、5ソース多数決）。
- **e-Gov由来の権威データ（条見出し・リンク層）が綺麗で高価値** → 次の価値は誤り探しでなく
  **enrichment（リンク層の全158法令拡張・概念↔条文整備）**。
- 方法知見: 精密(帰属) vs 再現(blob)の併用／権威は万能でない／全文比較は鈍く、特定facts
  （読み・条見出し一致）で当てるのが鋭い。
ツール追加: `quote_check_egov`(A1)・条見出し抽出/リンクは `data/egov`,`data/citations` に成果。

---

## 12. ゴールデンデータ構築（既存ALO設計に整合）
30/34/35 層設計を確認 ＝ 今日の探索は**既存設計（SKOS 3層: ConceptScheme→Term→Hub、
e-Gov=authority_rank100、alo_edges）の再発見**だった。今日の本当の貢献＝**設計が待っていた
feedstock（辞書データ化・読み品質・e-Gov錨）の生成**。

### 鶏卵の解（process）
**キー（見出し語）は綺麗・中身（読み/定義/引用）は汚い**を分離。錨(e-Gov)は綺麗に固定、
衛星(辞書)を provisional で接続 → 不一致で炙り出し → 裁定 → canonical昇格。
（`__unresolved__`/`hub_status: provisional→canonical`/`authority_rank` で既存設計が encode 済）。

### e-Gov 定義条項エクストラクタ（錨の量産）
`phases/egov_definition_extract.py`。4書式（item_definition / inline_toha / paren_definition =high、
paren_abbreviation =medium）を URI(egov:…)・scheme=jp_statutory_definition・authority_rank=100 で抽出。
7法令で golden 定義 203件 → **定義リッチな6法令（著作権法/個人情報保護法/行政手続法/特許法/労基/
消費者契約）を Box e-Gov コーパスから追加取得して13法令へ拡張＝534件**（high216/medium318、
`data/egov/egov_statutory_definitions_13laws.jsonl`）。by law: 著作権114・民法85・特許77・個人情報68・
会社49・民訴31…。item_definition は完璧な法定定義（著作物/実演/レコード/公衆送信）。
**所見**: paren_abbreviation(medium)は定義句の前方境界がfuzzで截断ノイズ混在（特許「在外者←有しない者」等）
＝suspect層で受ける。錨の本命は high216件。全158法令フル再走はローカル alo_statutes が効率的。

### 用語カード（語彙レイヤ Hub の最終形）
`phases/assemble_term_card.py`。錨(e-Gov法定定義)＋有斐閣/学陽gloss＋JLT英訳・読みを綺麗なキーで join。
6カード実証（子会社/親会社/公開会社/物/不在者/制限行為能力者＝全アンカー型）。読み全件多源一致、
有斐閣glossが条文逐語引用＝錨↔gloss相互検証。`data/cards/`。
新法令でも実証（著作物/著作者/実演家/個人情報/公衆送信）＝著作物・個人情報は**学陽glossが
著作権法2条1項/個人情報保護法2条1項を逐語引用**で錨↔gloss相互検証が成立。

### 次（ローカル＝素材がある場所で）
全158法令フル再走で錨量産 → 全用語カード自動生成 → scheme別に alo_terms/alo_hubs 投入
（provisional→接続→canonical）。書誌軸（NDL錨＋bencom簡易TOC）は文献レイヤ仕様に整合させて並走。
