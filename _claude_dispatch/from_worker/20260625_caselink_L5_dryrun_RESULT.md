# CASELINK L5 dry-run RESULT — magazine 判例評釈 subset（pilot）

- task: W-20260626-501 / WORKER_20260625_CASELINK_L5_DRYRUN_002
- mode: read-only dry-run（stance列DDL / alo_edges write / canonical昇格 / accepted edge化 すべて HOLD）
- engine: `scripts/case_link_corpus_dryrun.py`（`case_citation_span`/`case_link_extract`/`case_link_map`）。`python3 scripts/test_case_citation_span.py` = PASS。
- 入力: magazine pilot 判例評釈 subset（`article_type_local_pilot_v0.1.csv` type=判例評釈, 790件）× `title`（`article_join_dryrun_v0.1.csv`, D1-bunken 文献編由来）を `body_text` proxy。**RECONCILE 準拠で新規抽出器は実装せず本 engine を呼んだ**。

## 1. 件数・分布（as-is = D1 標題そのまま投入）
| 指標 | 値 |
|---|---|
| pilot 全行 | 2000 |
| 判例評釈 subset | 790 |
| title join | 790 / 790 (100%) |
| articles | 790 |
| edges_emitted | 8 |
| articles_with_any_edge | 6 |
| edge_type_counts | compares=8 |
| route_distribution | review=8 |
| stance_counts | neutral=8 |

## 2. なぜ as-is で激低か（核心所見）
- 標題の **97.8%（773/790）** に 被評釈判決らしき元号トークンが存在 = データは在る。
- しかし `CITATION_RE` ヒットは **6件（recall 0.78%）**。
- 書式内訳: **B 全角ドット区切り「令和５．１１．２７」形式 = 722件**、A 元号年月日（CITATION_RE想定）= 6件、C その他 = 45件。
- → 律速は**データ欠落でなく `CITATION_RE` の日付書式被覆**（全角ドット区切り＋小法廷略記「最高二小判」＋年月日漢字なし が文法外）。

## 3. 感度確認（入力のみ正規化・engine 未改変）
`body_text` 内の `令和Y．M．D` を `令和Y年M月D日` に正規化してから**未改変 engine** に投入:
- articles_with_any_edge: **6/790 (0.8%) → 728/790 (92.2%)**
- edges_emitted: 8 → 772
- 結論: 評釈→判例リンクは本 corpus で **~92% 機械抽出可能**。残るは書式被覆の問題のみ。

## 4. span 取りこぼしメモ（§5, ≤20件・番頭領分＝報告のみ）
- 支配的取りこぼし書式: **「（令和Y．M．D最高N小判）」全角ドット区切り = 722件**。
- 推奨修正（`case_citation_span.CITATION_RE`, owner=番頭）: (a) 全角/半角ドット区切り日付 `令和\d+．\d+．\d+` (b) `最高[一二三四五]小判`/小法廷接尾辞 を追加 → 本 corpus recall ~92% 見込み。
- 二次: C その他45件（日付欠落 or 別書式・要個別確認）。

## 5. 未達・HOLD
- route 分布（auto vs review）: 現状すべて review。被評釈判決を `masthead_citation` に構造化すれば auto/evaluates に振れるが、それには §4 の span 書式修正が前提。**HOLD**。
- 実 precision（N=100）: as-is 6エッジで標本化不能。span 書式修正後に別タスク推奨。
- L2 本文(fulltext/OCR)層: **未実装（DD-PERIODICAL-002 は design-only=「空白」, owner GO 必須）**。本文内の比較判例（compares/review_chain）は本文層が出来るまで測定不可。被評釈判決(masthead)自体は標題から ~98% 復元可。

## 6. 次手提案（head が hold/ から queue する用）
1. **[番頭]** `CITATION_RE` に全角ドット日付＋小法廷接尾辞を追加（§4）→ 本 dry-run を再走。
2. **[L5]** 標題の `（…判）` parenthetical を `masthead_citation` に構造化 → auto/evaluates route 分布を測定。
3. **[eval]** §1,2 完了後に N=100 gold（記事→被評釈判決）を付け `case_link_eval.py` で実 precision。
4. **[magazine上流]** L2 本文層（DD-PERIODICAL-002）が ratify されれば本文由来エッジを追加測定。

## 7. 成果物
- `artifacts/caselink/caselink_L5_input.jsonl`（790, body_text=標題 proxy）
- `artifacts/caselink/L5_dryrun_report.json`
- 本ファイル
