# PROFILING_REPORT_20260627 — bib_toc 異常分布 read-only 実測（v1.1 設計の根拠）

```yaml
doc_id: PHASE2-PROFILING-20260627
status: read-only profiling 完了（DB mutation 0 / DDL 0）
created_at: 2026-06-27 JST
author: Claude（Phase 2 DDDESIGN_MODIFY_REQUIRED 対応）
gate: SELECT のみ。3クエリで決定的事実を取得、相関サブクエリ系は計時都合で割愛
       （v1.1 実装段階で関数内 1パスで計測可能）
target: biblio.bib_toc（弁コム 552,544 + lionbolt 236,674 = 789,218行）
audit_response_to: 20260626_phase2_silver_projection_v1_DDDESIGN_RESULT.md (Box 2312213059089)
                   M1 / M2 / M3 の実データ閉鎖
```

## 1. M1（ordinal 制約）— クリーン

| source | rows | ordinal_null | level_null | min_ord | max_ord | min_lvl | max_lvl |
|---|---:|---:|---:|---:|---:|---:|---:|
| bencom-library | 552,544 | 0 | 0 | 0 | 1,409 | 1 | 4 |
| lionbolt | 236,674 | 0 | 0 | 0 | 1,178 | **0** | **9** |

`(source, bib_id, ordinal)` 重複: **両ソース共に 0 件**。

> **判定**: M1 のpreflight (ordinal_null / ordinal_duplicate / ordinal_non_comparable) は実データ上クリーン。ordinal_gap は数値列としては問題なし。

## 2. M3（親決定の異常系）— per-book 分布

| source | books | root_not_min_level_books | multi_root_books | max_roots_in_a_book | avg_depth_span | max_depth_span |
|---|---:|---:|---:|---:|---:|---:|
| bencom-library | 3,802 | **0** | **3,802 (100%)** | 493 | 1.97 | 3 |
| lionbolt | 4,135 | **365** | **3,727 (90%)** | 433 | 0.76 | **9** |

> **重大知見**:
> - **multi_root はバグではなく normal**（弁コム 100% / lionbolt 90%）。「単一root想定」は破綻している。1冊あたり最大 **493 root**（=コンメンタールの条文単位）。
> - **lionbolt 365冊で「先頭行が最浅 level ではない」**（root_not_min_level）。
> - **lionbolt depth span 最大 9**：浅い本と深い本が混在。M2 が現実に効く。

## 3. M3.2 / M2（level_gap）— level飛びの存在と深刻度

| source | level_gap_down_rows | books_with_gap | max_gap |
|---|---:|---:|---:|
| bencom-library | 1 | 1 | 2 |
| lionbolt | **111** | **71** | **7** |

> **判定**: 弁コムは事実上 gap なし → `source_level ≈ tree_depth` でも壊れない。
> **lionbolt は 71冊で gap、最大 7 段飛ぶ** → M2「source_level と tree_depth の分離」は実データ必然。

## 4. 代表サンプル（v1.1 fixture 素材）

> lionbolt の level≥3 ジャンプ箇所のコンテキスト（前後行）:

| bib_id | ordinal | level | text（先頭60字） |
|---|---:|---:|---|
| lionbolt:NPP0000542 | 679 | 3 | 第四百六十八条　債権の譲渡における債務者の抗弁 |
| lionbolt:NPP0000542 | 680 | **0** | 第四百六十九条　債権の譲渡における相殺権 |
| lionbolt:NPP0000542 | 681 | 3 | 旧第469条～旧第473条の削除に関する前注… |
| lionbolt:NPP0000542 | 682 | 4 | 第四百六十九条(旧)　改正に伴い削除 |
| lionbolt:SJH0000036 | 385 | 2 | 第126条　上場廃止の届出等 |
| lionbolt:SJH0000036 | 386 | 2 | 第127条　上場廃止等の命令 |
| lionbolt:SJH0000036 | 387 | **9** | 第128条　売買の停止等の届出 |
| lionbolt:SJH0000036 | 388 | 2 | 第129条　売買停止命令等 |
| lionbolt:SJH0000157 | 144 | 0 | 第二部　各論（民事訴訟法） |
| lionbolt:SJH0000157 | 145 | 3 | Q9　第二条において、裁判所と当事者の責務… |
| lionbolt:YHK0000018 | 1 | 0 | 第2巻（§§165～198〔株式会社の設立〕）増補… |
| lionbolt:YHK0000018 | 3 | 3 | 前注(§§ 230/10~280 [会社ノ機関]) ――本節の… |

> **解釈**: lionbolt の `level` は論理階層ではなく**見出しスタイル指定（タイトル/小見出し/条文番号など）**として使われている節がある。同じ「第◯◯条」が level=2 と level=9 で混在 → level を tree_depth と等視できない。

## 5. v1.1 への含意（M1-M9 への閉鎖材料）

| Patch | profiling で得た材料 | v1.1 での閉じ方 |
|---|---|---|
| M1 ordinal 制約 | NULL 0 / duplicate 0（クリーン）| preflight クエリを実装、上記基準で fail（実データではほぼ通過）|
| **M2 source_level/tree_depth 分離** | **lionbolt max gap=7、SJH0000036=2→9→2 等**　| **必須採用**。`source_level_raw`/`source_level_normalized`/`tree_depth=parent.tree_depth+1` の3列分離 |
| M3 親決定異常系 | multi_root は normal / root_not_min_level lionbolt 365冊 / level_gap 111行 | 決定表で「multi_root=accept」「root_not_min_level=accept w/log」「level_gap=accept, tree_depthはparent+1で算出」 |
| M4 正規化 | （未測定）| `title_raw` 完全保持＋`title_norm`は profile_id/version 付き |
| M5 embedding stale | （未測定）| `embedding_input_hash`/`embedding_status (missing|active|stale)` 追加 |
| M6 DDL gate 分離 | — | 関数作成は READ_ONLY_STRICT 外として明示 |
| M7 可逆性 | — | `projection_run_id` / manifest テーブル |
| M8 bencom非接触 | — | `p_source='lionbolt'` 必須化 + 実行前後 bencom checksum 比較 |
| **M9 受入メトリクス** | rows/books/multi_root/level_gap が測定可 | dry-run関数の返り値で全項目出す |

## 6. ガバナンス記録

- 本profilingは Supabase MCP `execute_sql` 経由の SELECT のみ。書き込み 0。
- 関数作成（CREATE FUNCTION）も行っていない（M6 を尊重）。
- 計時都合で M2 の「親決定後 depth vs normalized_level の乖離行数」は per-book 相関サブクエリ
  を含むため SQL 段階でタイムアウト。**v1.1 設計関数内で 1パス計算可能**（CTE で親 ordinal を join 取得）。
