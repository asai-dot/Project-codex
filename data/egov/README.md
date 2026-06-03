# e-Gov 条見出しデータ + 法令索引

## egov_article_captions_7laws.jsonl（綺麗な権威データ）
e-Gov 7法令（民法/会社法/刑訴/地方自治法/国家公務員法/国税通則法/民事訴訟法）の
**条番号→条見出し** を tag ツリー解析で抽出（Article/ArticleCaption）。4,367条・見出し3,267件。
用途: 引用ラベリング、B2判定、定義の概念ラベル付け、enrichment。`phases/quote_check_egov.py` と同じ
e-Gov JSON 由来。全158法令へ拡張可（ローカル一括が効率的）。

## gakuyo_law_index.json
学陽 引用法令→law_id（a2b＋依存グラフ合成索引で解決＝引用の27%）。

## B2_citation_disagreement_adjudicated.jsonl（要 caveat）
同一見出し語で学陽/有斐閣が同一法令を異なる条番号で引く候補を、条見出しで判定。
**信頼度低**: 「片方が正」判定の大半は有斐閣引用パースの artifact（付則/経過措置の括弧を
条番号化＝条2/3「経過措置」に誤解決）。B2を実用化するには有斐閣引用抽出の精緻化
（付則・経過措置除外、項枝番の厳密処理）が前提。現状は「両方関連/不明」が大半。

## headword_to_article_links.jsonl（綺麗な enrichment データ）
辞書見出し語 × e-Gov 条見出し一致で、見出し語→正典条文をリンク。**1,731リンク / 326見出し語**
（検証→民訴232, 抗告→民訴328, 秘密→民訴92 等）。「きれいな辞書データ」の中核（概念↔条文リンク）。
※7法令ぶん。全158法令へ拡張で被覆増。

## gakuyo_citation_miss_candidates.jsonl（誤り検出＝低収量）
学陽が当該法令を引くのに見出し一致条を外す95候補。**大半は正当な別条引用**（辞書が見出しと別の
妥当な条を引くのは誤りでない）。引用クロスチェックは誤り発見器として弱い、と実証。

## egov_statutory_definitions_7laws.jsonl（ゴールデンデータ＝法定定義）
e-Gov 7法令から「定義条項（用語→法定定義）」を抽出。**89定義**（会社法49 等）。
`phases/egov_definition_extract.py`。各定義に ALO URI（egov:{law_id}:art:{n}[:item:{n}]）・
`scheme=jp_statutory_definition`・`authority_rank=100`・source=egov。
= 語彙レイヤ §1.1 の最上位権威 term（用語ノードの錨）。辞書gloss(有斐閣/学陽)・JLT訳が
これに exact/close で刺さる。
### 被覆ムラ（要追加パターン）
号建て定義条項（会社法2条型・Column構造）は完全抽出。一方 民法/民訴は括弧書き定義
（「（以下「X」という。）」）でその場定義するため未抽出（民訴0/民法2）。第2パターン追加で被覆向上。
全158法令はローカル一括（alo_statutes 既存コーパス）が効率的。

## 定義条項エクストラクタ v2（括弧書きパターン追加）
`phases/egov_definition_extract.py` に文中・括弧書き定義を追加し**錨を増やした**:
- `item_definition`(号建てColumn・会社法2条型) / `inline_toha`(「X」とは…をいう) / `paren_definition`(X（…をいう）) = **high**
- `paren_abbreviation`(…（以下「X」という）) = **medium**（用語Xは綺麗・定義句の前方境界がfuzzy）
golden 定義: **89 → 203**（民法 2→85, 民訴 0→31）。high 114 / medium 89。
※他5法令(会社法/刑訴/地自/国公/国税)は現状 item_definition のみ。括弧書きは**全文フル再走で増える**
（ファイルがローカルにある環境で一括）。
