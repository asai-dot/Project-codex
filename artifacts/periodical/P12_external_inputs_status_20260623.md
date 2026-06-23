# P12: 外部入力待ち3件の進捗 + 本流反映経路の所見

```yaml
artifact: P12_external_inputs_status
generated_at: 2026-06-23 JST
context: registry完成後、外部入力待ち項目を調査し、取れた値を反映。本流反映経路を確認。
```

## 1. 外部入力待ち3件 — 各タスクの実体と進捗
registry完成により、**値が確定すれば適用は1行UPDATE → リゾルバが該当行を自動昇格**。各タスクの実体は「値を1個確定させる」こと。

| 項目 | 必要な値 | 調査結果 | 状態 |
|---|---|---|---|
| **人事の地図** | ISSN/NCID/NDLBibID を1つ | 公開ISSN無し（2022創刊トレード誌）。**NDL書誌ID 032430930** 取得 | ✅**反映済**（24行→canonical_ym, `ndlbib:032430930#YYYY-MM`） |
| **法と哲学** | 2188-711X の正否検証 | Web調査で**確証得られず**。別物「法と哲学新書」(NCID BC03650510)や無関係 2453-711X がヒットし桁衝突риск実証 | ⏸ 据置（ISSN Portal/出版社の一次確認待ち） |
| **税経通信2026** | 2026各月の実通号×12 | NDL書誌が403。代替源/人手が必要 | ⏸ 据置（12行 canonical_ym。取得後crosswalk追補でcanonical化） |

→ 「人事の地図のISSNを調べる」は **NDLBibIDで解決**。残2件は値そのものが外部一次情報に依存。

## 2. 本流反映の経路（"audit only" 問題）の所見
**確認した事実**:
- periodical のオブジェクトは **`staging_periodical` スキーマにのみ存在**（`periodical.*` 本番スキーマ・issuesテーブルは無し）。
- `issue_stage` のコメントは "audit only"。リポジトリ内に `issues_with_id_staged.jsonl` の**生成/ロードコードは見当たらず**（取込パイプラインは本リポジトリ外 or 手動の可能性）。

**設計上の安全性（重要）**:
- registry/alias/crosswalk/resolver は **issue_stage とは別テーブル/ビュー**。
  → `issue_stage` を再ロードしても **registry系は消えない**。
- 昇格内容は **resolver から完全再生可能**（`resolver_drift=0` で実証済）。
  → 再ロード後も **冪等リコンサイル1回** で全昇格が復元する。
- よって「再ロードで昇格が消える」リスクは、**post-reload に resolver リコンサイルを1回流す**運用で解消できる。

**残る確定事項（真に人に聞くべき1点）**:
- `issues_with_id_staged.jsonl` の**生成元と再ロード頻度**はどこか（本リポジトリ外）。
  - 一回限りロードなら：現状の手当てで永続。追加対応不要。
  - 定期再ロードなら：(a) パイプラインの issue_id 採番を **resolver(registry)に置換**、または (b) **post-reload reconcile** をパイプライン末尾に追加。

## 3. 最終状態
| status | 件数 |
|---|--:|
| canonical | 2,479 |
| canonical_ym | 187 |
| provisional_no_issn | 56 |
| provisional_ym | 12 |
| unassigned | 113 |
| **被覆(canonical+ym)** | **2,666 / 2,847 = 93.6%** |

全監査クリーン（false_merge/false_split/key_collision/tsuukan_monotonic/resolver_drift = 0）。
