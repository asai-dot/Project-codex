# D1KOS ベースライン（検収基準点） — 2026-05-25 ビルド時点

> 目的: D1-Law の「判例をどう並べているか」の体系（D1KOS = D1-Law Knowledge Organization System）の
> 現時点の形を、検収の **diff 基準点** として固定する。新しい記録（ワーカーちゃんが現在記録中）が
> land したら、本ベースラインと突き合わせて差分を判定する。
>
> - status: baseline snapshot (read-only record)
> - 数値の出所: `D1-Law_D1KOS_OPAC-CiNii_PostgreSQL育成_作業報告_20260526.md`（Box, 2026-05-26）
>   ＋ `DD-CASE_current_reality_check_..._20260611.md`（2026-06-11 再確認）
> - 実体の所在: ワーカーちゃんのローカル alo-ai リポジトリ ＋ ローカル PostgreSQL `d1kos` スキーマ
>   （`app/data/pacsigny/iteration/...`）。**クラウド Supabase の2プロジェクトには未投入。**
>   Box には報告書(.md)のみ同期、summary JSON / SQL の実体は未同期。

## 0. D1KOS とは

D1-Law が判例を並べている体系（法分野 → 論点 → そこに並ぶ判例）を、ALO が自前で握るための
知識組織体系。2系統で構築している:

- **① WEBページから**: D1-Law の判例体系ナビを直接取得 → 法分野→論点の「並べ方の骨格（ツリー）」。
- **② 判例から**: 判例 RTF / 評釈から論点へ紐付け → 「そこに並ぶ判例」（evidence / article_cites_case）。

正本ではなく **static KOS candidate**（証拠台帳・検索面・レビューキュー）として扱う。
D1KOS node は法令条文そのものではなく、D1 体系上の分類・論点ノード。

## 1. ① 体系ツリーの骨格（法分野 → 論点の並び）

| 指標 | 値 | 意味 |
|---|---:|---|
| canonical_node | 9,449 | 論点 / 分類ノード総数 |
| canonical_edge | 9,412 | 親子パス（≒ node − 1、ほぼ単一ツリー） |
| root_support_summary_v2 | 37 | 最上位 root ＝ 法分野 / 体系の数 |
| case_root_evidence_summary_v2 | 16 | 判例 evidence が実際に着いている root 数 |
| review_path_diagnostics_v2 | 6,118 | レビュー対象パス |
| direct full path unmatched | 2,995 | 現 KOS node に直接一致しないパス（要再接続） |
| P1 direct full path unmatched | 0 | P1 ではフルパス不一致ゼロ（最重要層は整合） |

特性: `path identity 維持`・`label-only merge なし`。serving views v2 で root（法体系）/ path（論点）/
evidence（判例）を意味分離。`gate_passed = true, error 0, warning 0`。

serving views v2: `v_node_overview_v2` / `v_case_root_evidence_summary_v2` /
`v_review_path_diagnostics_v2` / `v_review_unmatched_path_diagnostics_v2` /
`v_root_support_summary_v2` / `v_serving_qa_v2`。

## 2. ② 論点に並ぶ判例（evidence）

| 指標 | 値 |
|---|---:|
| evidence_link | 57,315（論点ノード ↔ 判例・評釈） |
| retrieval_surface | 37,796 |
| review_queue | 6,118 |
| article_cites_case 候補 | 5,010（P1 3,569 / P2 1,427 / P3 8 / HOLD 6） |
| P1 reviewer worksheet | 1,648 行（9 バッチ, batch size 200, last 48） |
| decision overlay import | 0 |
| accepted edge preview | 0（全件 pending_review） |

許可される reviewer decision: `pending_review` / `accept_article_cites_case` /
`reject_not_same_case` / `needs_more_evidence` / `defer`。

## 3. ③ 法令参照レーン（参考）

| 指標 | 値 |
|---|---:|
| statute_ref_key | 4,893 |
| candidate rows | 23,280（strong 281 / weak 22,999） |
| matched_statute_ref_keys | 3,900 |
| strong review queue | 281（P1 75 / P2 137 / P3 69） |

candidate shell INSERT なし・canonical 反映なし。`金商法21条→商法21条` のような suffix parsing リスクは
P1→P2 に降格して検出。

## 4. 維持しているガード

- D1-Law raw / OPAC raw / CiNii raw は上書きしない。
- canonical `bib_*` には書かない。
- D1KOS は正本ではなく staging candidate。
- D1KOS node と statute / law / article object は別物。
- `accept_article_cites_case` 相当の決定なしに canonical へ昇格しない。

## 5. 関連データ母数（判例 DL 側）

- D1-Law 契約母数: 249,863 件
- 取得済 distinct 判例 ID: 67,966 件（27.2%, 2026-06-01 基準）／`判例一覧.csv` 68,077 行
- 2026-06-05 バッチ ingest（2026-06-11 実行）: distinct RTF 3,627 → extracted 178,318 → NEW 124,805 を
  非破壊 append（canonical 追記後の最新値は再集計が必要）

## 6. 新レコード land 時の照合軸（diff チェックリスト）

1. **体系ツリー**: node / edge と **root 数(37)** の増減 ＝ WEB 側スクレイプで法分野カバレッジが
   広がったか。
2. **判例の並び**: evidence_link(57,315) が判例 DL 増加（distinct 判例 ID 67,966 →）を反映して増えたか。
3. **未接続の解消**: `direct full path unmatched 2,995` が減ったか。
4. **レビュー進捗**: `accepted edge 0` / `decision overlay 0` が動いたか。
5. **正本名寄せ**: D1KOS ↔ case_spine（判例正本キー = 裁判所＋判決年月日＋事件番号）の名寄せが進んだか。

---

_本ファイルは検収の基準点としての記録であり、D1KOS 実体（ローカル PostgreSQL / alo-ai）への変更は含まない。_
