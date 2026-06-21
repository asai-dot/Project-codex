# ⚠ THREAD SCOPE NOTE — このフォルダは「リーガルリサーチ silver」スレッド（語彙オブジェクトとは別）

> 追記: 2026-06-21 / owner 指示「別スレの話として残して」により明記

## このフォルダ/ブランチ/PR の正体

- ブランチ名 `claude/vocab-object-bottleneck-knzorh` と フォルダ名 `design/vocab_bottleneck/` は
  **`vocab`（語彙）に由来する名前だが、中身は語彙オブジェクトではない。**
- 実際の中身 = **リーガルリサーチ基盤（判例↔評釈↔条文↔論点をつなぐ）の silver 解決スレッド**。
  関連DD: `DD-LRINDEX-001`(legal_research_unit) / `DD-DATAARCH-001`(AI-ready data layer) /
  `DD-D1TAXO-003`(KOS cross-scheme) / SILVER-RESOLUTION-KICKOFF。
- 扱うボトルネック = 「意味付き citation 在庫ゼロ＝関係層が silver 未到達」。
  これは **claim_support / 論点グラフ**の話であって、辞書から語彙（Term=語義・Hub）を作る話ではない。

## 語彙オブジェクト（本来別スレ）との違い

| | このスレッド（残置） | 語彙オブジェクト（別スレ） |
|---|---|---|
| 目的 | 判例・評釈・条文・論点を意味で接続（リーガルリサーチ substrate） | **辞書 → Term(語義) → Hub → entity linking** を作る |
| 総論DD | DD-LRINDEX-001 / DD-DATAARCH-001 | **DD-VOCAB-000**（Meaning Backbone） |
| 各論DD | DD-D1TAXO / silver kickoff | DD-DICT-008(bedrock) / DD-EL-001(legal WSD) / DD-VOCAB-各論 |
| ボトルネック | citation silver 解決（本スレで実装・監査整合済） | 辞書→語義Term/Hub構築・legal WSD が未着手 |

## なぜ残すか

silver 側は Mac/Codex レーンで実データ完走済み（strong 12,064 等）で、本PRの設計/ツールは
その**read-only 検証実装・監査整合版**として価値が残る。語彙オブジェクトの作業は**別ブランチ/別PR**で行う。

## このスレッドの成果物（参考）

`00/01_*`(背景・計画) / `WO-SILVER-*`(WO草案) / `WORKER_TASK_PACKET_*`(実行指示) /
`ALIGNMENT_NOTE_*`(kickoff v0.1.1 整合) / `tools/silver_resolve/*`(P0/P1 dry-run ツール・31 tests)。
