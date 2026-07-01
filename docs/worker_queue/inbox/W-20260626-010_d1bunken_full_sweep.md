---
worker_task_id: W-20260626-010
status: queued
priority: P1
owner: claude-code-worker
created_at: 2026-06-26
owner_sanction:
  - rule: external_api_bulk_call
    status: APPROVED
    date: 2026-06-26
    by: owner（浅井）
    note: >
      D1文献編メタの取得は owner 承認済みの正規取得パイプライン（追加のみ・冪等・レート制御内蔵・
      単一書き手）。本タスクに限り既定 forbidden `external_api_bulk_call` を上書きし downloader 実行を許可。
      他の既定 forbidden（DB write/canonical/削除/schema/Box書込）は維持。
request: docs/status/20260619_D1bunken_acquisition_status.md
mode: acquisition
goal: >
  D1文献編の「雑誌・記事の完全網羅」。価値順(評釈言及)での打ち切りを撤廃し、D1にある雑誌を
  端から全部取り切る。目的は判例研究に限らず、将来 CiNii 本文等を全誌に紐付ける知識基盤の網羅。
  現状 333,206/449,677=74.1%(canonical 1,058誌)。残り約25.9%(=被引用の薄い長尾雑誌)を取り切り、
  カバレッジを可能な限り100%へ。
requires_systems:
  - mac_local: d1_bunken_downloader.py + 生きた d1_state.json セッション
  - mac_local: ~/alo-ai/work/d1law_dl/bunken（取得先・追加のみ）
  - repo: Project-codex tools/d1_bunken（parse/label）
allowed_actions:
  - run_d1_downloader（owner_sanction済・全頁0スイープ）
  - parse（d1_bunken_parse_all.py）
  - label（label_journals_v0.2.1.py）
forbidden_actions:
  - production_db_write
  - canonical_promotion
  - destructive_delete
  - raw_source_mutation   # 既存RTFを書き換えない（追加のみ）
  - file_move_rename_delete
  - schema_migration
  - box_write
exit_criteria:
  - 列挙できた全未取得誌をスイープ完了（各誌 総件数=取得頁×50 まで）
  - 再パース＋v0.2.1ラベルで新 unique_articles と新カバレッジ%を算出
  - 取得不能誌（0件/非収録/表記不一致）を一覧化
  - 896外の誌をD1カタログ探索で何誌追加できたか（できなければ「要カタログ源」と明記）
  - done/ に RESULT、またはサイクル跨ぎなら doing/ に進捗メモ
max_attempts: 2
result_expected_filename: W-20260626-010_RESULT.md
---

# Task — D1文献編 全雑誌 完全網羅スイープ（価値順撤廃）

owner方針（2026-06-26）: **目標は「判例→評釈グラフ」に矮小化しない。D1文献編の雑誌・記事を完全網羅する。**
評釈言及は優先順位の道具であって到達目標ではない。価値順は尽きた＝**端から全部取る**。

現状: 333,206/449,677 = 74.1%（canonical 1,058誌）。残り25.9%は被引用の薄い長尾雑誌（大学紀要・零細専門誌・被引用ゼロ誌）。

## 方針（重要）
- ✅ owner_sanction 済（front-matter）。downloader の bulk 実行をブロックせず実行してよい。
- downloader は **追加のみ・冪等・レート制御内蔵（30〜75秒+長休止）・単一書き手**。長丁場(数百誌×低速=数日)。
- 落ちても `doing/` に残し、同スイープ再実行で続きから（冪等）。誌個別の0件/timeoutはログして継続、タスク全体をBLOCKEDにしない。

## STEP 1 — 未取得誌リストを作る（価値で切らない）
1. 優先JSON `d1_bunken_journal_acquisition_priority_20260612.json` の **全896誌**を対象集合にする（価値順だが**全部**取る）。
2. 取得済みフォルダ `~/alo-ai/work/d1law_dl/bunken/` と突合し、未取得 or 不完全（総件数>取得頁×50）な誌を抽出。
   - 偽陽性除去: 既収誌の別名（例 法曹時報=法曹）は `掲載誌等` 由来名も「保有」に算入して弾く。
3. 抽出結果を `doing/W-20260626-010_PROGRESS.md` に誌数とともに記録。

## STEP 2 — 全未取得誌を端からスイープ（value-blind）
```
DL=~/.gemini/antigravity/scratch/d1_bunken_downloader.py
# STEP1の未取得誌それぞれに対し:
python3 $DL "<誌名>" 0      # 全頁・冪等
```
- 0件で返る誌は `〔〕（）` 等を外したベース名で1回再試行 → なお0なら「取得不能(表記/非収録)」としてログ。
- 進捗は逐次 PROGRESS とログ(`/tmp/d1_full_sweep.log`)へ。

## STEP 3 — 896の外（被引用ゼロで価値ランキングに載らない誌）の探索
- D1に **雑誌一覧/索引のブラウズ経路**があるか確認（Playwrightで雑誌マスタを列挙できるか）。
  - 可能なら全誌名を取得 → 既取得と差分 → 未取得を STEP2 と同様にスイープ。
  - 不可能なら RESULT に「896外の完全網羅には D1雑誌カタログ源が必要」と明記（owner判断事項として残す）。

## STEP 4 — 再パース＋ラベル＋報告
```
python3 ALOBookDX/事務所内本棚DX化計画/scripts/d1_bunken_parse_all.py
python3 ~/Project-codex/tools/d1_bunken/label_journals_v0.2.1.py "$HOME/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/article_meta_all.jsonl"
```
- 新 `unique_articles` と **新カバレッジ%（/449,677）** を算出。
- `done/W-20260626-010_RESULT.md`（先頭 WORKER_PASS）に: before/after件数・カバレッジ・canonical誌数・
  取得不能誌一覧・896外探索の結果（追加誌数 or 要カタログ源）を記載 → `alo-worker complete`。

## Do Not
- 元RTF/既存データを書き換えない（追加のみ）。Box書込・DB投入・canonical昇格・削除はしない。
- 「価値が低いから」を理由に誌を**スキップしない**（網羅が目的）。取得不能のみ除外し理由を残す。
- 確認待ちで全体を止めない。許可範囲（取得・パース・ラベル）は実行する。
