# A1 実相談検索観測ベースライン — 結果 (asof 2026-06-05)

> 観測のみ。gold無し。`biblio.bib_terms=0` 時点の **before スナップショット**。
> 生成: `docs/search_bench/measure_consultation_reach.py --asof 20260605`（決定的・再実行同一）。
> 機械可読: `build/search_bench/a1_summary.json`。

## 0. 母集団と除外（隠さず明示）
- SF 相談 **230件**（全件）。
- noise除外 **3** / no_delimiter **42** / outline_missing **129** / pii_risk表示抑制 **126** / 汎用matterでprobe除外 **34**。
- 構造事実: `bib_terms=0`（→ `book_reach_via_terms` 全件0）, `terms=554`(全て法定定義語), `bib_records=10,326`, `bib_toc=555,887`。

## 1. 結果分布（230件）
| outcome | 件数 | 意味 |
|---|--:|---|
| **non_stop_term_hit** | **8** | 実テキストが、汎用語でない canonical 語に到達 |
| stoplist_only_hit | 104 | 汎用語（会社/株式/法律/請求 等）だけに反応 |
| raw_probe_hit_but_no_term_hit | 58 | 蔵書側に生全文で当たる材料があるが、語彙橋が無く正式到達できない |
| no_term_no_raw_probe | 57 | 語彙にも蔵書にも届かない |
| noise_record | 3 | テスト/サンプル等（集計外） |

term match の型内訳: non_stop=8 / stoplist_only=110 / short(≤2字)=46 / compound_embedded=3。

## 2. 意味ある到達 8件の中身（全て matter 由来・偶然 法定定義語と一致）
`後見人`(成年後見人), `後見監督人`(任意後見監督人), `不動産`(不動産売買), `不動産`(不動産相続相談),
`再生計画`(法人事業再生計画策定支援), `破産管財人`(破産管財人事件), `被害者`×2(犯罪被害者相談)。
→ いずれも「事件種別名そのものが法定定義語だった」ケース。語彙が相談の**論点**に届いたわけではない。

## 3. 種別別（ALO_Inferred）— 主力領域はことごとく non_stop=0
| n | 分類 | non_stop | zero/stop |
|--:|---|--:|--:|
| 29 | 契約法務 | **0** | 29 |
| 21 | 債務整理 | **0** | 21 |
| 13 | 損害賠償（交通） | **0** | 13 |
| 13 | 一般民事 | **0** | 13 |
| 10 | 廃業支援（法的+私的） | **0** | 10 |
| 7 | M&A支援 | **0** | 7 |
| 2 | 後見 | 1 | 1 |
| 1 | 不動産 / 事業再生（私的） | 各1 | — |
（109件は ALO_Inferred 未分類。うち non_stop=3）

**事務所の主力相談（契約・債務整理・交通・一般民事・廃業・M&A）は、現状語彙に意味あるかたちで1件も届いていない。**

## 4. 代表例（report-safe・PIIリスク行は抑制）
| outcome | 分類 | 匿名クエリ | raw_probe(toc/rec) |
|---|---|---|--:|
| non_stop | 不動産 | 不動産売買 | 53 / 5 |
| non_stop | 破産管財事件 | 破産管財人事件 | 1 / 0 |
| stoplist_only | 一般民事 | 損害賠償請求事件 交通事故弁護士特約案件 | 20 / 0 |
| stoplist_only | 契約法務 | 法律相談 | 0 / 0 |
| **raw_probe_hit_but_no_term_hit** | 損害賠償（交通） | 交通事故 … | **149 / 185** |
| **raw_probe_hit_but_no_term_hit** | 離婚 | 離婚事件 … | **13 / 22** |
| raw_probe_hit_but_no_term_hit | 著作権 | 著作権侵害事件 … | 4 / 0 |
| no_term_no_raw_probe | 契約法務 | 企業法務 | 0 / 0 |

## 5. 判断軸（観測から読める事実）
1. **語彙密度が極めて低い**: 実相談の事件種別・概要は生活語/実務語で書かれ、法定定義語554とほぼ重ならない（意味到達 8/230 = 3.5%）。
2. **概要は寄与していない**: with_outline 群の non_stop 到達率 ≈2.0% は without_outline ≈4.8% を下回る。短い概要は語彙到達を増やさない（むしろ matter 名のほうが当たる）。
3. **stoplist 依存**: 反応の大半は 会社/株式/法律/請求 等の汎用語のみ（stoplist_only 104件）。term presence は弁別器として機能していない。
4. **`raw_probe_hit_but_no_term_hit` が58件**: 蔵書・目次側には関連文字列があるのに語彙橋が無い。**bib_terms 投入が最も効く領域**＝交通事故(toc149/rec185)・相続・離婚・債権回収・不当利得・私的整理 等。
5. outline あり(101)/なし(129)は分けて表示（混ぜると値が薄まる）。

## 6. 次段
- 同一スクリプトで bib_terms 投入後に再走 → outcome 分布の前後差で橋の価値を実測。
- gold（owner 監修「引きたい本/条文/語」）は Stage2。`owner_review_scaffold_20260605.md` に空欄台紙のみ用意。
