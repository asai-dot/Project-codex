# Golden Term Card — 用語ノードの最終形（実証 2026-06-02）

法令ゴールデンデータ（e-Gov法定定義）を錨に、辞書・JLTを刺した「用語ノード」の最小実例。
ALO 語彙レイヤ（ConceptScheme→Term→**Hub**）の Hub に相当。`data/cards/golden_term_card_子会社.json`。

## カード: 【子会社】

```
読み: JLT=こがいしゃ / 有斐閣=こがいしゃ          ← 多源一致で確定

◆[錨] 法定定義  authority_rank=100  scheme=jp_statutory_definition
   会社法  egov:417AC0000000086:art:2:item:3
   「会社がその総株主の議決権の過半数を有する株式会社その他の当該会社が
     その経営を支配している法人として法務省令で定めるものをいう。」

・有斐閣 gloss : 親会社に従属し、その支配を受ける会社。会社法は、「会社がその総株主の
                議決権の過半数を有する株式会社…」（＝錨を逐語引用＝相互検証）
・学陽   gloss : 「親会社」（参照エントリ＝学陽は子会社を親会社へ送る）
・JLT    英訳  : subsidiary company
```

## このカードが示すこと
- **錨＝e-Gov法定定義**（authority_rank=100・URI付き）。辞書gloss/JLT訳/読みがそこに刺さる。
- **組み方＝綺麗なキー（見出し語）で各源を join し、e-Gov権威で錨を打つだけ**
  （鶏卵の解：汚いデータを事前クレンジングせず、繋いで錨に当ててズレを炙り出す）。
- **検証が回っている**: 読み「こがいしゃ」JLT=有斐閣一致／有斐閣glossが会社法を逐語引用＝錨と相互確認。

## スキーマ対応（既存ALO設計）
| カード要素 | 既存スキーマ |
|---|---|
| 錨（法定定義） | `alo_terms` scheme=`jp_statutory_definition` authority_rank=100 / URI=egov:… |
| 有斐閣 gloss | scheme=`jp_core_dictionary`（Tier1 seed） |
| 学陽 gloss | scheme=`jp_legislative_dictionary`（exact/close overlay） |
| JLT 英訳・読み | scheme=`bridge_translation` |
| カード自体 | `alo_hubs`（同一概念の統合結節点。hub_status provisional→canonical） |

## 「ちゃんと作る」次手
1. 括弧書き定義パターン追加（民法/民訴の錨回復） 2. 全158法令で錨量産（ローカル一括）
3. 全用語でカード自動生成 → scheme別に alo_terms/alo_hubs 投入（provisional→接続→canonical昇格）。
