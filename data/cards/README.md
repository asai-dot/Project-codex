# Golden Term Card（用語ノードの最終形・実証）

e-Gov法定定義（錨・authority_rank=100・URI）＋ 有斐閣/学陽 gloss ＋ JLT英訳 ＋ 読みconsensus を
1ノードに集約。綺麗なキー（見出し語）で各源を join し、e-Gov権威に錨を打つ＝鶏卵議論の実装。
ALO 語彙レイヤ（ConceptScheme→Term→Hub）の Hub に相当。

## ★ golden_term_cards_high.jsonl（全high錨でバッチ生成＝本番）
high 5,882錨のユニーク見出し語 **3,063語**ぶんを1ノード=1行に集約。
`phases/assemble_term_card.py --from-gold --jsonl-out`（錨=ALL_high / 有斐閣13,344 / 学陽2,684 /
JLT読み）。
- **有斐閣gloss付き 571 / 学陽gloss付き 289 / 読みあり 755（多源一致 740）**。
- **リッチカード 554**（錨＋有斐閣gloss＋読み一致）＝相互検証済みの中核。有斐閣が錨と同じ法令を明示引用
  （例: ばい煙「大気汚染防止法において…」、レコード「著作権法上は…」）。
- **錨単独ノード 2,288**＝辞書未収載の専門語（例: アイ・ピー・アドレス＝電気通信事業法、オープン型の
  証券投資信託＝所得税法、エネルギー消費効率＝地方税法）。法定定義だけの権威ノードとして有効。
- 各カード: `concept / readings{源:読み} / reading_agreement / statutory_definitions[]（uri・authority_rank=100・
  definition_type・confidence・本文） / glosses{有斐閣,学陽} / jlt{reading,en}`。

個別 json（`golden_term_card_子会社.json` 等）は型ごとの実例見本。

### スキーマ投入（次）
1行=1 Hub 候補。scheme別に `alo_terms`（jp_statutory_definition=authority100 / jp_core_dictionary=有斐閣 /
jp_legislative_dictionary=学陽 / bridge_translation=JLT）→ `alo_hubs`（provisional→接続→canonical）。
「子会社」等の汎用語は複数法令の錨を束ねる（各 authority_rank=100、最一般=会社法を primary に）。
medium 9,741 の paren_abbreviation は境界精緻化後に追補。
