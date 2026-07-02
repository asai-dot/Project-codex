---
worker_task_id: W-20260629-001
status: queued
priority: P1
owner: claude-code-worker
created_at: 2026-06-29
owner_sanction:
  - rule: external_api_bulk_call
    status: APPROVED
    date: 2026-06-29
    by: owner（浅井）
    note: D1文献編メタ取得は owner 承認済みの正規取得パイプライン（追加のみ・冪等・レート制御内蔵・単一書き手）。本タスクに限り既定 forbidden `external_api_bulk_call` を上書きし、discovery スイープ + downloader 実行を許可する。他の既定 forbidden（DB write/canonical/削除/schema 等）は引き続き有効。
request: docs/worker_queue/done/W-20260626-010_RESULT.md
goal: 896誌スイープ後も残る 91,520件（20.4%）の未取得記事の誌名を発掘し、新規誌を完取得する。検索結果サイドバー「掲載誌」ファセットをキーワードスイープで収集 → 既存ラベル済みJSONLと差分 → 未知誌を downloader で取得 → 再パース＋ラベル → カバレッジ差分報告。
mode: acquisition
requires_systems:
  - mac_local
  - d1_bunken_downloader
  - d1_login_session
  - project_codex_repo
depends_on:
  - W-20260626-010   # 完了済み（358,157件/79.6%）
allowed_paths:
  - ~/alo-ai/work/d1law_dl/bunken/
  - ~/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/
  - /tmp/d1_discovery/
  - /tmp/
  - docs/worker_queue/done/
  - docs/worker_queue/blocked/
allowed_actions:
  - run_year_discovery_script
  - run_sanctioned_d1_downloader
  - run_parser
  - run_labeler
  - read_only_diagnostics
forbidden_actions:
  - production_db_write
  - canonical_promotion
  - destructive_delete
  - raw_source_mutation
  - file_move_rename_delete
  - schema_migration
  - concurrent_download
  - box_write_move_rename_delete
exit_criteria:
  - catalog_discovery スイープ（15キーワード）が完走し /tmp/d1_discovery/unknown_journals.txt を生成した
  - 未知誌を downloader で冪等に取得した（全頁=0 指定）
  - 0件で返る誌（D1非収録/表記差）は /tmp/d1_year_discovery_acquire.log に列挙した
  - 再パース→label_journals_v0.2.1.py を1回実行し unique_articles と canonical誌数を更新した
  - RESULT に before/after（358,157/79.6% → ?）を記載した
  - 元データ（既存RTF/manifest）を一切改変していない（追加のみ）
deliverables:
  - /tmp/d1_discovery/unknown_journals.txt
  - /tmp/d1_discovery/all_found_journals.txt
  - /tmp/d1_year_discovery_acquire.log
  - ~/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/article_meta_all.jsonl
  - ~/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/labeled_v0.2.1/article_meta_labeled.jsonl
  - docs/worker_queue/done/W-20260629-001_RESULT.md
max_attempts: 2
result_expected_filename: W-20260629-001_RESULT.md
---

# Task — D1文献編 年別スイープによる未知誌発掘＋完取得

## 背景

W-20260626-010（完了）で 896誌の全件スイープを実施し 358,157件/79.6% を達成。
残り **91,520件（20.4%）** は 896誌リストに含まれない誌（被引用ゼロ誌・長尾誌）。

**年別RTF取得は不採用**: 発行年月日フィールドが薄く（1年あたり35件程度）、
カタログ探索手段として機能しないことが判明。

**新方針**: 検索結果サイドバーの「掲載誌」ファセットをキーワードスイープで収集。
RTFダウンロード不要で D1 収録誌名を網羅的に取得できる。

## 方針

- `d1_catalog_discovery.py --sweep` で民法・刑法・商法・紀要 等 15キーワードを順次検索
- 各検索結果の左サイドバー「掲載誌」ファセットから誌名を全件回収
- 既存ラベル済みJSONLとの差分で「未知誌」を特定
- 未知誌を既存downloader で取得（追加のみ・冪等・単一書き手）

## STEP 1 — 動作テスト（空検索でファセット確認）

```bash
cd ~/Project-codex && git pull
python3 tools/d1_bunken/d1_catalog_discovery.py --facet
```

誌名が1件以上出力されれば OK。

## STEP 2 — 本番スイープ（15キーワード）

```bash
cd ~/Project-codex
nohup python3 -u tools/d1_bunken/d1_catalog_discovery.py --sweep \
  > /tmp/d1_catalog_discovery.log 2>&1 &
echo "PID=$!"
```

進捗確認: `tail -f /tmp/d1_catalog_discovery.log`

完走後に確認:
```bash
wc -l /tmp/d1_discovery/unknown_journals.txt
head -30 /tmp/d1_discovery/unknown_journals.txt
```

## STEP 3 — 未知誌を downloader で取得

```bash
DL=~/.gemini/antigravity/scratch/d1_bunken_downloader.py
LOG=/tmp/d1_year_discovery_acquire.log
: > "$LOG"

while IFS= read -r j; do
  echo "### $j" | tee -a "$LOG"
  python3 -u "$DL" "$j" 0 2>&1 | grep -E "総件数|完了|失敗|Timeout|スキップ" | tee -a "$LOG"
done < /tmp/d1_discovery/unknown_journals.txt

echo "ACQUIRE_DONE" | tee -a "$LOG"
```

進捗: `tail -f /tmp/d1_year_discovery_acquire.log`
中断したらそのまま再実行（冪等）。

## STEP 4 — 確定（再パース＋ラベル＋カバレッジ差分）

```bash
cd ~/Project-codex
bash tools/d1_bunken/step4_finalize.sh
```

`step4_finalize.sh` が:
1. 再パース (`d1_bunken_parse_all.py`)
2. ラベル v0.2.1
3. 0件トリアージ再実行
4. カバレッジ差分（358,157/79.6% → ?）を表示

## RESULT に書くこと（done/W-20260629-001_RESULT.md, 先頭行 `WORKER_PASS`）

| 指標 | Before (2026-06-29) | After | 差分 |
|---|---|---|---|
| unique_articles | 358,157 | ? | ? |
| カバレッジ（/449,677） | 79.6% | ?% | ? |
| canonical 誌数 | 1,248 | ? | ? |
| 年別スイープで発見した誌 | 0 | ? | — |
| 取得した新規誌数 | 0 | ? | — |

- 取得0件だった誌の一覧（/tmp/d1_year_discovery_acquire.log より）
- 元データ無改変（追加のみ）の明記
- 残課題（さらに広い年範囲 or 別アプローチが必要な場合）

## Do Not

- 既存RTF/manifest/フォルダの改変・削除・改名
- 複数プロセス同時DL（単一書き手厳守）
- DB投入・canonical昇格・Box/外部書き込み
- 誌個別の0件/timeoutでタスク全体を止める（ログ記録して継続）
- /tmp/d1_discovery/ 以外への中間RTF保存
