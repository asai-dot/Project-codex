# Fork 1 ロードマップ — 接合の前後と「その先」

web セッション（本リポジトリ）と Mac セッション（`~/alo-ai/`・Box）の役割分担と、
週明けに Mac へ入る前／入った後に何ができるかの全体像。

## 全体フロー

```
[web] 設計・ツール作成 ──→ [Mac] preflight + dryrun ──→ [web] レビュー/トリアージ
   (済: 本ブランチ)          (発注書 §2)                 (バンドル消費)
        │                                                      │
        └────────────── 承認 ISBN 確定 ←──────────────────────┘
                              │
                   [Mac] 本適用 apply --commit --only-isbns
                              │
                   [後続] hasToc 整合 / 索引再構築 / Sheet 再生成 / defer 処理
```

## A. いま（Mac に入る前）web 側でできること — 状況: ほぼ完了

- [x] ① 変換器 / ② 優先順位ポリシー / ③ ドライラン（本ブランチ・CI green）
- [x] 本適用器（dry-run 既定・二重ガード）
- [x] preflight バリデータ（resolver / legallib_dir）
- [x] ドライラン自己完結バンドル（overwrites / review）
- [x] 下流レビューツール（差分 render / 衝突トリアージ）
- [x] Mac セッション発注書（`handoff_mac_session_legallib_join.md`）
- [ ] **残: 実データ無しでは確定できない項目**（converter の実スキーマ追従、
  実件数での閾値調整）→ preflight の戻りで対応。

### さらに web 側で前倒しできる候補（任意・低リスク）
- `merge_toc_updates.py` への legallib 分岐統合案（設計のみ。本実装は実データ後）。
- `bib_extra.toc` 射影を books.json へ書く経路の設計（hasToc 整合とセット）。
- toc_search_index への legallib ノード取り込み方針（全文検索に効く）。

## B. Mac セッションに頼むこと（発注書に集約済み）

1. preflight 2 本 → ゲート通過確認。
2. ドライラン → L1 self-verify（exit 0 / 不変条件 0 / 件数妥当）。
3. **小さいバンドルだけ**を `handoff/legallib_dryrun_<date>/` に戻す。
4. journal 混入・スキーマ乖離があれば質問として戻す。

## C. バンドルが戻った後、web 側で引き受けること

1. **差分レビュー**: `render_proposed_diff.py --bundle overwrites_bundle.jsonl`
   → `enrich`（安全）と `replace`（要確認）を仕分け。replace の「失われるタイトル」を精査。
2. **衝突トリアージ**: `triage_review_queue.py --bundle review_bundle.jsonl`
   → `conflict`（突合疑い＝resolver 再確認）/ `candidate_richer`（人手版を補強できる）/
   `near_duplicate`（既存維持）に分類し、人が裁定する順に整列。
3. **承認 ISBN リスト確定**: enrich + 問題なしを承認 → `approved_isbns.txt`。
4. **本適用の発注**: Mac へ `legallib_join_apply.py --commit --only-isbns approved_isbns.txt`
   を依頼（書き込み直前ゲート再適用で保護対象は物理的に拒否）。

## D. その先（接合完了後の後続タスク）

| # | タスク | 概要 | 担当 |
|---|---|---|---|
| 1 | hasToc 整合 | 接合した ISBN の `books.json.hasToc` を立てる（apply の manifest を入力に、既存 `books_write_lock`/`atomic_write_json` で） | Mac |
| 2 | toc_search_index 再構築 | legallib ノードを全文検索索引へ取り込み（`build_toc_search_index.py` 系） | Mac |
| 3 | Sheet ビュー再生成 | canonical → Sheet 再生成で TOC カバレッジ更新 | Mac |
| 4 | defer_new 処理 | 616 件（canonical 未収録）。OCR 奥付→ISBN 復元→再 NDL 照合の別パイプライン | 別タスク |
| 5 | journal（雑誌）系 | periodical として号単位・論文 entity 化（article parser の後段） | 別タスク |
| 6 | 回帰監視 | 接合後に「非simple 劣化 0」を定期 assert（CI/バッチに本テスト同型を組込み） | web |

## 設計上の不変条件（全工程で守る）

- 人手/NDL/出版社/PDF目次（非simple・保護ソース）は legallib で**上書きしない**。
- book_id↔ISBN の誤マージ 0（missing/ambiguous/bad は全 block）。
- ドライラン・本適用ともに**冪等**（再実行で diff 0）。
- 本番への書き込みは**人手承認した ISBN のみ**（`--only-isbns`）。
