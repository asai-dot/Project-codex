# 語彙Hub 構築 dry-run レポート (read-only / DBに書かない)

> DD-DICT-008 Stage1-3(+5). 全 hub_status=provisional. canonical 昇格なし.
> 定義重なり率 閾値: 0.6 (Q2: 暫定. Wave0 実測で再校正)

- Term 総数: **10**  (bedrock 9 / specialty 1)
- 生成 hub: **7**  (exact統合 2 / canonical昇格可(rank≤102のみ) 7)
- 同綴異義 homograph_conflict(統合せず別hub): **1**
- 読み欠落 bedrock: **0**  (定義一致で hub へ救済 **0** / 単独hub 0)
- specialty attach(rank≥103, attachのみ): **1**

## hub member数 分布
| member | hub数 |
|---|---|
| 1 | 5 |
| 2 | 2 |

## 監査整合の確認
- exact_match は normalized_pref+reading 一致かつ定義重なり≥閾値のみ(表層一致merge なし).
- 同綴異義は統合せず homograph_split(別hub). 重なり率を保存.
- specialty(rank≥103)は attach のみ. canonical 昇格しない.
- anchor は中立規則(e-Gov優先→scheme_id→term_id). 優劣ではない.

_dry-run. candidate JSONL 出力のみ. DB write/canonical mint なし._