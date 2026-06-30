# L5 owner review packet v0.1 — 評釈→判例ID 確定候補(T1)の owner 判断用

- 生成: head / read-only / 2026-07-01（GPT L5 v0.3 = DESIGN_PASS_WITH_NOTES の GO 物）
- source: `l5_accepted_edges_v0.3.jsonl`  **sha1=`cfac7f3d7e66a53747e43cde70e2cd062b9a9019`**  rows=85
- 本packet: tier=T1_distinctive **23件**（high_risk 6）/ distinct判例 19
- packet csv: `l5_owner_review_packet_v0.1.csv`（owner_decision列に approve_as_annotates / reject / hold を記入）

## 重要な前提（GPT 監査反映）
- **これは accepted edge ではない**（DB投入前）。二軸 = `edge_candidate_tier`(T1) ＋ `edge_status`(candidate_for_review)。[L5 v0.3 binding#1]
- **edge_role は未検証**: これら T1 は「正式事件名がタイトルに一致」で判例IDを確定したが、
  その判例が **評釈対象**か **引用/比較/脚注**かは未判定。owner は各行が評釈対象かを確認のこと。[PERIODICAL-003 MF-1]
- T2(map含む)615件は medium/high candidate、T3 922は review queue、REJECT 38は negative fixture（本packet対象外）。

## 列定義
| 列 | 意味 |
|---|---|
| edge_candidate_tier | T1=厳密一致＋distinctive名＋裏取り |
| edge_status | candidate_for_review（accepted でない）|
| edge_role | UNVERIFIED（owner が 評釈対象/引用 を確定）|
| case_name_popular | 評釈側の通称 |
| matched_formal_name | 一致した判例側 正式事件名 |
| formal_name_freq_in_db | 正式名の判例DB頻度（小=distinctive）|
| hanrei_id / 事件番号 | 接続先 判例 |
| article_id / article_title | 評釈記事 |
| high_risk | 境界注意（非distinctive/複数束ね）|
| owner_decision | approve_as_annotates / reject / hold |

## サンプル（先頭8件）
- 日本メール・オーダー事件 → 判例27000014(昭和５０年（行ツ）７７号／昭和５０年（行ツ）７８号) ／ 一致『救済命令取消請求上告事件』freq=2 ／ 記事: 生産性向上協力の条件付回答と不当労働行為――日本メール・オーダー救済…
- ハンセン病国家賠償訴訟 → 判例28061048(平成１０年（ワ）７６４号／平成１０年（ワ）１０００号／平成１０年（ワ）１２８２号／平成１１年（ワ）３８３号) ／ 一致『「らい予防法」違憲国家賠償請求事件』freq=1 ／ 記事: ハンセン病国家賠償訴訟熊本地裁判決（「らい予防法」違憲国家賠償請求事…
- 神奈川県臨時特例企業税条例事件 → 判例28210886(平成２２年（行ヒ）２４２号) ／ 一致『神奈川県臨時特例企業税通知処分取消等』freq=1 ／ 記事: 神奈川県臨時特例企業税通知処分取消等請求事件（平成２５．３．２１最高… ⚠同一判例に複数article束ね
- 神奈川県臨時特例企業税条例事件 → 判例28210886(平成２２年（行ヒ）２４２号) ／ 一致『神奈川県臨時特例企業税通知処分取消等』freq=1 ／ 記事: 臨時特例企業税条例が地方税法に違反し違法・無効であるとされた事例――… ⚠同一判例に複数article束ね
- 杉並区住基ネット訴訟 → 判例28111458(平成１６年（行ウ）３７２号) ／ 一致『住基ネット受信義務確認等請求事件』freq=1 ／ 記事: 行政主体相互間の紛争と主観訴訟――杉並区・住基ネット受信義務確認等請…
- 東京都銀行税訴訟 → 判例28080770(平成１４年（行コ）９４号／平成１４年（行コ）２４５号／平成１４年（行コ）２４６号／平成１４年（行コ）２４７号／平成１４年（行コ）２４８号等) ／ 一致『東京都外形標準課税条例無効確認等請求』freq=1 ／ 記事: 東京都外形標準課税条例無効確認等請求控訴事件（平成１５．１．３０東京…
- 訴訟上の救助の決定に対し訴訟 → 判例28092031(平成１６年（行フ）４号) ／ 一致『訴訟救助決定に対する抗告審の取消決定』freq=1 ／ 記事: 訴訟救助決定に対する抗告審の取消決定に対する許可抗告事件（平成１６．…
- 予防訴訟 → 判例28112109(平成１６年（行ウ）５０号／平成１６年（行ウ）２２３号／平成１６年（行ウ）４９６号／平成１７年（行ウ）２３５号) ／ 一致『国歌斉唱義務不存在確認等請求事件』freq=2 ／ 記事: 国歌斉唱義務不存在確認等請求事件――東京地裁判決（平成１８．９．２１…
