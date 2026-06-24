---
worker_task_id: W-20260625-001
status: queued
priority: P1
owner: claude-code-worker
created_at: 2026-06-25
owner_sanction:
  - rule: external_api_bulk_call
    status: APPROVED
    date: 2026-06-25
    by: owner（浅井）
    note: D1文献編メタ取得は owner 承認済みの正規取得パイプライン（追加のみ・冪等・レート制御内蔵・単一書き手）。本タスクに限り既定 forbidden `external_api_bulk_call` を上書きし、downloader 実行を許可する。他の既定 forbidden（DB write/canonical/削除/schema 等）は引き続き有効。
request: docs/status/20260619_D1bunken_acquisition_status.md
goal: D1文献編の未取得誌（評釈価値の低い長尾＝大学紀要・実務誌を含む全誌）を冪等に完取得し、雑誌オブジェクトの誌名メタを取り切る。評釈言及数ではなく「雑誌オブジェクト網羅」が目的（将来のCiNii本文取り込みで誌名が結合キーになるため、3割の取りこぼしを許さない）。取得後 再パース＋誌名ラベル付与v0.2.1まで回し、カバレッジ差分を報告する。
mode: acquisition
requires_systems:
  - mac_local            # 下記はMac上でのみ可能。クラウドワーカー不可
  - d1_bunken_downloader # ~/.gemini/antigravity/scratch/d1_bunken_downloader.py
  - d1_login_session     # ~/.gemini/antigravity/scratch/d1_state.json が生きていること
  - project_codex_repo   # tools/d1_bunken/label_journals_v0.2.1.py (main)
depends_on: []
allowed_paths:
  - ~/alo-ai/work/d1law_dl/bunken/        # 追加のみ（新規誌フォルダ＋頁RTF＋manifest）
  - ~/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/  # 再生成（パース／ラベル出力）
  - /tmp/                                  # 作業ログ・中間tsv
  - docs/worker_queue/done/                # RESULT
  - docs/worker_queue/blocked/             # RESULT(失敗時)
allowed_actions:
  - run_sanctioned_d1_downloader   # owner承認済みの正規取得パイプライン。追加のみ・冪等・レート制御内蔵・単一書き手
  - run_parser                     # d1_bunken_parse_all.py（文献番号で重複排除）
  - run_labeler                    # Project-codex tools/d1_bunken/label_journals_v0.2.1.py
  - read_only_diagnostics
forbidden_actions:
  - production_db_write
  - canonical_promotion
  - destructive_delete             # 既存フォルダ/RTF/manifest の削除禁止
  - raw_source_mutation            # 既存RTFの改変禁止（取得は追加のみ）
  - file_move_rename_delete        # 既存成果物の移動・改名・削除禁止
  - schema_migration
  - concurrent_download            # 複数プロセスで同時DL禁止（multi-writer禁止）
  - box_write_move_rename_delete
exit_criteria:
  - 真の未取得リスト /tmp/d1_truemissing.tsv を生成した（掲載誌等由来の実誌名も保有扱いにし偽陽性=法曹時報等を除外済み）
  - 未取得誌を downloader で冪等に取得した（全頁=0指定）。途中エラー誌はBLOCKEDにせずログに記録して継続
  - 0件で返る誌（D1非収録/表記差）は /tmp/d1_tail_acquire.log に列挙（取得不能として明記）
  - 取得完了後にパーサ→label_journals_v0.2.1.py を1回実行し、unique_articles と誌別を更新した
  - RESULT に before/after（unique_articles・canonical誌数・取得した誌数・0件誌一覧）を記載した
  - 元データ（既存RTF/manifest）を一切改変していない（追加のみ）
deliverables:
  - /tmp/d1_truemissing.tsv
  - /tmp/d1_tail_acquire.log
  - ~/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/article_meta_all.jsonl
  - ~/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/labeled_v0.2.1/article_meta_labeled.jsonl
  - docs/worker_queue/done/W-20260625-001_RESULT.md
max_attempts: 2          # ※「2回試して無理ならBLOCKED」は誌単位ではなくタスク全体。誌個別の0件/timeoutはログ記録して継続（BLOCKED化しない）
result_expected_filename: W-20260625-001_RESULT.md
---

# Task — D1文献編 未取得長尾の完取得＋確定（雑誌オブジェクト網羅）

発注元: `docs/status/20260619_D1bunken_acquisition_status.md`（状況報告）。現状 unique_articles=302,130 / 67.2%。
残り32.8%は評釈価値の低い長尾（大学紀要・実務誌）だが、**雑誌オブジェクトとしては取り切る**方針に確定
（将来CiNii本文取り込みで誌名が結合キー。価値順カバレッジは既に達成済み、ここは網羅性のための取得）。

## 方針（重要）
- ✅ **owner承認済み（2026-06-25, front-matter `owner_sanction` 参照）**: 既定forbidden `external_api_bulk_call` を
  本タスクに限り上書き済み。downloader実行を**ブロックせず実行してよい**。
- downloaderは**追加のみ・冪等・レート制御内蔵（30〜75秒+長休止）・単一書き手**。
- **元データ改変ゼロ**（取得は新規頁の追加のみ）。DB投入/canonical化/外部共有はしない（別ゲート）。
- 長時間ジョブ。`nohup`/別タブで走らせ、**冪等なので中断したら同スイープ再実行で続きから**。
  誌個別の0件・Playwright timeout は**ログに残して次へ**（タスク全体をBLOCKEDにしない）。

## STEP 1 — 真の未取得リスト生成（read-only・偽陽性除去）
```bash
PRI=~/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_journal_acquisition_priority_20260612.json
LAB=~/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/labeled_v0.2.1/article_meta_labeled.jsonl
python3 - "$PRI" "$LAB" > /tmp/d1_truemissing.tsv <<'PY'
import json,sys,unicodedata,re
def nfkc(s): return unicodedata.normalize("NFKC", s or "")
def bn(s):
    s=nfkc(s).replace("雑誌記事メタデータ","").replace("_"," ")
    s=re.split(r"[〔「『（(【\[]",s,1)[0]
    return re.sub(r"\s+"," ",s).strip()
def etc_j(e):
    s=nfkc(e).lstrip("『「（("); s=re.split(r"[0-9]",s,1)[0]
    return s.strip(" 　,，、。.・（(「『")
pri,lab=sys.argv[1],sys.argv[2]; have=set()
for l in open(lab):
    r=json.loads(l)
    have.add(bn(r.get("journal_canonical",""))); have.add(bn(r.get("journal_raw","")))
    have.add(bn(etc_j(r.get("掲載誌等",""))))
have.discard("")
for it in json.load(open(pri))["queue"]:
    if bn(it.get("journal","")) not in have:
        print(f"{it.get('hyoshaku_refs',0)}\t{it.get('journal','')}")
PY
echo "真の未取得: $(wc -l < /tmp/d1_truemissing.tsv) 誌"
```

## STEP 2 — 冪等 完取得スイープ（落ちても継続・0件は〔〕除去で再試行・全ログ）
```bash
DL=~/.gemini/antigravity/scratch/d1_bunken_downloader.py
LOG=/tmp/d1_tail_acquire.log; : > "$LOG"
cut -f2 /tmp/d1_truemissing.tsv | while IFS= read -r j; do
  echo "### $j" | tee -a "$LOG"
  out=$(python3 "$DL" "$j" 0 2>&1)
  echo "$out" | grep -E "総件数|完了|失敗|Timeout" | tee -a "$LOG"
  if echo "$out" | grep -q "総件数=0"; then
    base=$(printf '%s' "$j" | sed -E 's/[〔「『（(].*$//')
    [ -n "$base" ] && [ "$base" != "$j" ] && { echo "  ↻ base: $base" | tee -a "$LOG"; python3 "$DL" "$base" 0 2>&1 | grep -E "総件数|完了|Timeout" | tee -a "$LOG"; }
  fi
done
echo "SWEEP_DONE" | tee -a "$LOG"
```
進捗確認: `tail -f /tmp/d1_tail_acquire.log`。中断したらこのブロックを再実行（冪等）。

## STEP 3 — 確定（再パース＋誌名ラベル付与）
```bash
cd ~ && python3 ALOBookDX/事務所内本棚DX化計画/scripts/d1_bunken_parse_all.py
cd ~/Project-codex && git checkout main && git pull
python3 tools/d1_bunken/label_journals_v0.2.1.py "$HOME/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/article_meta_all.jsonl"
```

## RESULT に書くこと（done/W-20260625-001_RESULT.md, 先頭行 `WORKER_PASS`）
- before/after: unique_articles（302,130 → ?）、canonical誌数（931 → ?）、契約比%。
- 取得した誌数 / 0件・取得不能だった誌の一覧（/tmp/d1_tail_acquire.log から）。
- catch-all一覧・`?`=0 の維持確認。
- 残課題（あれば）。
- 元データ無改変（追加のみ）であることの明記。

## Do Not
- 既存RTF/manifest/フォルダの改変・削除・改名。
- 複数プロセス同時DL（単一書き手厳守）。
- DB投入・canonical昇格・Box/外部書き込み。
- 誌個別の0件/timeoutでタスク全体を止める（ログ記録して継続）。
