# ★HANDOFF: ローカルちゃん 次タスク切替（最優先で読む）— 2026-06-24

```yaml
from: codex(head, cloud)
to: ローカルちゃん(Yuta@Mac)
priority: これを誌解決の続行より優先
reason: L3誌解決は収穫逓減域に到達。次の主戦場は記事/本文層。発注が未読のまま誌解決が続いていた。
```

## 状況（事実）
- authority v8 で被覆 **96.49%**。未解決は **425誌=7,734記事(2.6%)** の細切れロングテール → **収穫逓減**。誌解決はここで一旦十分。
- 一方、owner が **全GO承認＋ライセンス確認クリア済**（WO-PERIODICAL-OWNER-GO-REQUEST）。記事接合・初出・OCR が承認済なのに未着手。

## 名前空間ルール（衝突防止・今後）
- **`P##` 系 = ローカルちゃんの誌解決(authority)専用**。君が採番を進める。
- **`ORCH-*` / `DD-*` / `WO-*` = codex(head)の設計・発注**。Pカウンタは使わない。
- → 以後 P22/P23 の二重採番のような衝突を避ける。

## 次にやること（順に）
### 1. ORCH-ARTICLE-JOIN（GO-1, read-only, 最優先）
`artifacts/periodical/ORCH-ARTICLE-JOIN_order_20260624.md` の仕様で
**記事↔issue_id 接合 dry-run**。入力は最新 authority **v8** ＋ `article_meta_labeled.jsonl`。
出力 `article_join_dryrun_v0.1.csv` ＋ `article_orphan`/`article_collision` 0件確認＋被覆率。

### 2. ORCH-HIGHHOLD-INGEST（GO-3/4/5）
`artifacts/periodical/ORCH-HIGHHOLD-INGEST_order_20260624.md`。
- GO-4 OCR は **1誌数号パイロット先行** → codex(head)監査合格後に全量（PCが熱くなるのはここ）。
- GO-3 pacsigny 初出 / GO-5 legal_thought。locator(GO-0)で実パス確認してから。

## 重要: 命令チャネルの確認
Git push だけでは君は気づかない（実際この発注は未読だった）。
**owner が Mac 側で君にこのハンドオフを読ませる**のが起動トリガ。読んだら着手し、結果は `P##` ではなく
返却サマリとして push（ファイル名衝突しないよう日付付き）。codex が衝突/orphan/OCR境界を独立監査する。

## codex(head)側の宿題（並行）
- 監査を v8 に再ベースライン（私はv4基準だった）。
- 返却物の回帰検査規格（article_collision/orphan/firstpub_conflict/edge_falselink/OCR境界）。
