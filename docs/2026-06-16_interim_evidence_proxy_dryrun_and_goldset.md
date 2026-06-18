# 暫定エビデンス報告: 属性観測層 v0.2 ＋ FP強化 — proxy dry-run ＆ gold mini-set 2026-06-16

- 作成: 2026-06-16 / Claude（リモート）/ **read-only・DB無変更**
- 位置づけ: お目付け役 (1) 属性観測層 `DESIGN_PASS_WITH_NOTES`（Box 2286160319588）と (2) FP強化 `DESIGN_PASS_WITH_NOTES`（Box 2287192002732）の **dry-run結果(暫定)**。
- **本番ではない**: ここで示すのは **proxy（蔵書↔弁コム・書名一致・2ソース）**。canonical な 501×{弁コム・LION BOLT・legal-library・NDL} dry-run は **Mac起動待ち**（WO 2286268562080）。
- 同梱: `..._attr_layer_proxy_dryrun_result.md` / `..._edition_suspected_gold_miniset.md`（repo branch claude/library-data-reanalysis-7fg7ib）。

## 1. proxy dry-run 結果（積層ロジックの動作確認）
biblio 内 蔵書↔弁コム 書名一致で属性projectionを当てた（read-only）。
- 書名一致 1,470 / **分類(NDC/NDLC)＋詳細TOC を両取りで厚化した本 847**。
- 共有スカラー衝突: 出版社 **2.7%** / 出版年 **2.3%**（→ triage）。
- **ungrounded 採用値 = 0**（全採用値が実観測に接地＝anti-hallucination 構造を確認）。

→ v0.2 の中核（観測→triage→採用→接地）は実データで破綻せず、**積層効果・低disputed・接地100%**。

## 2. gold mini-set（edition_suspected 29件の手動分類）＝FP must-fix の実証
| バケット | 件数 | 含意 |
|---|---|---|
| A 同版/日付種別差（年差≤2・版表示なし） | **12 (≈41%)** | **ハード年一致なら全て false-split** ＝ pub_date_precision/kind・soft比較が必須（FP must-fix #1） |
| B 真の別版（第2版明記 or 年差大） | 12 | 別item＋同work。版/刷の弁別が必要（#5） |
| C review（年差4〜5） | 3 | TOC delta/page basis で判定 |
| D 同名異本/データ誤り（年差大） | 2 | `子どもと学校`は副題一致で同一work救済＝evidence family計数の効き（#4） |

→ FP must-fix（pub_date soft化・版/刷分離・family計数・TOC主証拠化）が**実データで支持**された。確定は両側TOC delta（本番501）で解像度向上。

## 3. 確認できたこと / まだのこと
- **確認**: 属性projectionの動作・接地100%・disputed非爆発（proxy）。FP4信号の必要性（gold set）。
- **未（Mac起動待ち）**: ①独立evidence family計数の実装（FP next #3）②canonical 501 dry-run（両側TOC・NDL全量・provenance_family・multi分類合議）③その結果の再投函。

## 4. お目付け役に伺いたい点（軽め・early signal）
1. このproxy＋gold setを、501本番前の**前進的エビデンスとして受容**してよいか（本番判定は501後で可）。
2. gold set の A/B 境界（年差≤2を「同版疑い」初期しきい値）と、A群の `same_edition_impression_variant` 既定処理は妥当か。
3. 501本番 dry-run の**必須出力**に、本proxyのメトリクス（接地100%・triage後disputed・厚化数）＋ family計数結果 を含める指定でよいか。

## 5. 返答様式
```text
status: ACK | PASS_WITH_NOTES | MODIFY
proxy_evidence_accepted: yes/no（本番501前の前進エビデンスとして）
gold_set_thresholds: コメント
required_501_outputs: コメント
notes:
```

## banto自己申告
- read-only・DB/DDL/backfill 無し。proxy は2ソース・書名一致＝**同定の確認でなく積層/必要信号の動作確認**。
- canonical 判定は Mac側 本番501（pub_date_kind＋両側TOC delta＋family計数）後。
