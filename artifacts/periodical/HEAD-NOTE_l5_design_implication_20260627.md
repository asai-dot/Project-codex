# HEAD-NOTE: L5発注書設計への含意 — 2026-06-27 (L5-FEASIBILITY速報より)

```yaml
based_on: be557268 ログ(commit pending, push待ち) の速報
status: L5本発注書を起こす前の設計反映ノート
```

## 速報数字
- (court, date) 抽出率: 94.05%（元年正規表現 修正後）
- (court, date) match率: hanrei側と 85.06% → Grade A
- **title-level unique resolution: 31.65%**（重要な発見）
  - (court, date) 単独では **422件が同日同裁判所で多重マッチ**＝曖昧
  - 事件番号を含むタイトル: 26/790件のみ
  - 事件名(例: 名古屋自動車学校事件)を含むタイトルが多い ← L5 disambiguation の鍵
- no_extract 91件のうち
  - 45件: 元年(令和元/平成元) → regex拡張で吸収済
  - 44件: 行政機関裁決(公取委命令/排除措置/審判所裁決) → 健全な落ち(hanrei対象外)

## L5本発注書への設計含意
1. (court, date) 単独接合は使わない。多重マッチ422件を放置すると評釈→判例の誤接合が大量発生。
2. アーキテクチャ: (court, date) でバケツ化 → **事件名トークン照合**で disambiguate。
   事件番号があれば最優先(26件は確実接合)。
3. hanrei オブジェクト側に「事件名(case_name)」列があることが前提。無い場合は前段で抽出が必要。
4. confidence階層:
   - A: (court, date, 事件番号) 完全一致
   - B: (court, date, 事件名トークン一致)
   - C: (court, date) のみ・1件のみマッチ(=元の85%のうち多重でない分)
   - D: (court, date) のみ多重 → 候補リスト併記、自動接合せず

## 次アクション
- L5-FEASIBILITY正式出力(origin push後)を head監査
- 上記設計を盛り込んだ ORCH-L5-LINK を起こす(全量分類完了 ＋ L4完了の後)
