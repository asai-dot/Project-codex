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
