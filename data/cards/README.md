# Golden Term Card（用語ノードの最終形・実証）

e-Gov法定定義（錨・authority_rank=100・URI）＋ 有斐閣/学陽 gloss ＋ JLT英訳 ＋ 読みconsensus を
1ノードに集約。綺麗なキー（見出し語）で各源を join し、e-Gov権威に錨を打つ＝鶏卵議論の実装。
ALO 語彙レイヤ（ConceptScheme→Term→Hub）の Hub に相当。

`golden_term_card_子会社.json`: 試作1枚。
- 錨: 会社法2③ `egov:417AC0000000086:art:2:item:3`（法定定義）
- gloss: 有斐閣（statute逐語引用あり＝相互検証）、学陽（参照=親会社）
- JLT: subsidiary company / 読み こがいしゃ（JLT=有斐閣 一致）

次: (1) 括弧書き定義パターン追加で錨を増やす、(2) 全158法令で錨を量産、(3) 全用語でカード自動生成
→ alo_terms/alo_hubs へ投入（scheme別・provisional→canonical）。
