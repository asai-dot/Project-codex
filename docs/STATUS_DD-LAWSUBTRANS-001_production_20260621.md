# STATUS — DD-LAWSUBTRANS-001 production deploy（2026-06-21 セッション）

- branch: `claude/lawsubtrans-production-deploy-b15nmp`（PR #19 の成果物をマージ済み）
- 前スレ引き継ぎ（PLAN v0.1 / MILESTONE 20260611 / 各 migration・script）を起点に、
  **環境の事実確認**と**安全に実行可能なところまでの前進**を行った記録。

---

## 1. このセッションで確定したこと（事実）

### 1.1 §6「法令レイヤの所在」= 解決：**どちらの Supabase project にも未 materialize**
`list_projects` / 全スキーマ走査の結果：

| project | ref | 法令レイヤ | 備考 |
|---|---|---|---|
| alo-connect | `vlsunmqpjhzbhipiehzs` | **無し** | public 空。`scratch_canary_1313`(11 tbl) のみ |
| asai-dot's Project | `nixfjmwxmgugiiuqfuym` | **無し** | ALO 本体（biblio/authority/dynamic/formobj/bookdx/control/serving）はあるが、`law\|provision\|revision\|statute\|lawtime\|substan` に一致するテーブルは **0 件** |

→ `alo_law_work` / `alo_statutes` / `alo_edges`（lawtime 土台）は**どこにも存在しない**。
  前スレ末尾の「未特定のまま終了」は「未 materialize（まだ作られていない）」が正。

### 1.2 lawtime v0.2.2 **base DDL がリポジトリに無い**
本リポジトリ全 branch を走査しても `migrations/lawtime/` や lawtime base の `.sql` は無い。
あるのは **patch 設計ドキュメント** `docs/dd/DD-LAWTIME-001_v0.2.3_production_patch.md` のみ
（v0.2.2 の D1/D3/D4・列追加を「既にある」前提で差分を書いている）。
→ STEP A「v0.2.2+v0.2.3 patch を apply」は、**patch の土台となる v0.2.2 base DDL が無い**ため
  そのままでは実行不能。base（テーブル/列/resolver 関数/eval_event/succession）の在処特定 or
  起こし直しが先。

### 1.3 実装監査 RESULT（タスク#1）= リポジトリに無い
`from_gpt/20260616_lawsubtrans_v0.1.3_impl_DDLAWSUBTRANS_RESULT.md` は本リポの**どの branch にも無い**
（他レーンの RESULT 群は存在）。GPT お目付け役ループの外部成果物と思われる。
→ PASS/MODIFY_REQUIRED の取り込み（P0 修正）は RESULT 本文が無いと判断できない。**要共有**。

### 1.4 代替検証として実装健全性は確認済み
- **unit tests: 69 passed**（`pytest tests/`）。PR #19 の producer 5 段は green。
- **SQL 構造スモーク: PASS**（`migrations/lawsubtrans/smoke_local/run_smoke.sh`、下記 §2）。

---

## 2. 実施した安全な前進

1. PR #19（`claude/law-substantive-transition-dd-TvrQR`）の全成果物を本 branch にマージ。
2. `tests/` 69 件 green を確認。
3. **ローカル構造スモークテストを新設**（`migrations/lawsubtrans/smoke_local/`）。使い捨て
   ローカル Postgres 16 で実機検証：
   - 001→005 ＋ stub R-1 view が**順序通りエラー無く apply**（列名・依存・構文の健全性）
   - 16 gate view が全て queryable（無データ → `verify_dry_run.sql` = ALL GATES EMPTY）
   - **gate 検知力**：仕込んだ 4 違反を該当 gate が 1 件ずつ捕捉
   - **安全弁**：append-only トリガが UPDATE/DELETE で RAISE、`ck_subchg_claim` が
     evidence 無し claim_support を拒否
   - ⚠️ これは**構造スモークであって本番 dry-run ではない**。backfill / formal_status 整合 /
     lawtime_resolved 結合の**実データ検査**は materialize 済み法令レイヤを要する（`README.md` 既述の偽陽性ゾーン）。

> DB への書き込みは**一切していない**（両 Supabase project は read-only 走査のみ）。
> 安全弁「P1 本番 apply まで DB 書込みゼロ」を維持。

---

## 3. 実行順（STEP A–F）の現在地と blocker

| STEP | 状態 | blocker / 次の一手 |
|---|---|---|
| #1 impl RESULT 取り込み | **BLOCKED** | RESULT 本文の共有（外部 GPT 成果物） |
| #2 lawtime v0.2.3 owner ratify | owner 専権 | ratify 判断（メモ案は patch doc 末尾にあり） |
| A lawtime apply | **BLOCKED** | lawtime **v0.2.2 base DDL が不在**。在処特定 or 起こし直し → materialize 先（branch）決定 |
| B lawsubtrans dry-run | **構造のみ PASS** / 本番 dry-run は BLOCKED | A 完了後、materialize 済み branch で 001→005 + 実 fixture + verify_dry_run |
| C ingest (P2) | 未着手（A/B 依存） | dedup_key UPSERT 層は新規設計の最大物 |
| D 較正 (P3) | 未着手 | コーパス所在（`alo-kg/raw/egov_revisions/` 3,506 rev、判例テキスト）の特定 |
| E curation (P4) | 未着手 | — |
| F MCP (P5) | 未着手 | — |

---

## 4. owner に確認したい意思決定（次アクションを決める鍵）

1. **lawtime v0.2.2 base DDL の所在**：別リポ（`alo-kg` 等）/ 別 project / 旧 branch のどれか？
   無ければ「patch doc から base を起こし直す」を本 branch でやってよいか。
2. **materialize 先**：法令レイヤ＋lawtime を **どの project/branch に作るか**
   （案: alo-connect に Supabase dev branch を切って dry-run。branch 作成は課金が出るため要承認）。
3. **impl 監査 RESULT** の共有（タスク#1 の前提）。
4. **コーパス所在**（P3 較正）：e-Gov raw・判例コーパスのパス。

> 1〜4 のいずれかが入手でき次第、A→B を実データで前進させる。それまでは構造スモークと
> base DDL 起こし（承認時）が安全に進められる範囲。
