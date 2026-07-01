# ORCH-JOURNAL-AUTHORITY-FIX order 20260701 — journal authority 段1 誌名正規化 dry-run（read-only）

- orch_id: ORCH-JOURNAL-AUTHORITY-FIX-20260701 / channel: journal
- 親WO: `docs/alo/WO-JOURNAL-AUTHORITY-FIX_v0.1_20260701.md`（branch: claude/t10-d1-full-sweep）
- 種別: **read-only / dry-run のみ**。authority本体に書かない。識別子補完(段2)・canonical・DB反映は本発注の対象外(owner GO)。

## 何をするか（段1のみ）
head の read-only QA が出した journal 修正候補 **370件** を検証し、各候補に verdict＋正規化名を付け、**preview（書き込まない）**を出す。

### 入力（read-only）
- 修正候補: worktree `worktree-casename-dict` の `artifacts/periodical/journal_authority_corrections_v0.1.csv`（commit 85a7bd2・列 issue,canonical_group,recommend）
- journal authority: `/Users/yuta/Project-codex/.claude/worktrees/casename-dict/artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v14.csv`（931行・列 journal_canonical,article_count,key_type,key_value,status,source,note）

### 検証ルール（issueごと）
1. **CITATION_FRAGMENT(169)**: `』所収p` `,p` `創刊号,` `別冊付録,` 等の掲載位置サフィックスを除去→core誌名/venue名抽出。
   - 除去後名が既存 journal_canonical に一致 → verdict=`MERGE_TO_EXISTING`（統合先併記）
   - 一致せず正当venue(記念論文集等) → verdict=`NORMALIZE`（正規化名併記）
2. **TRUNCATED_PAREN(179)**: `(別冊ジュリスト` 等末尾切れ→シリーズcanonical名へ正規化（号数不明は欠落フラグ）。verdict=`NORMALIZE`。**破壊的統合はしない（名補完のみ）**。
3. **DUP_ISSN(22)**: 同一ISSN→複数誌を `TRUE_SAME`(同一誌異表記/増刊) / `MISASSIGN`(別誌への誤付与) に分類。

### 出力（成果物・commit して push）
- `artifacts/periodical/journal_authority_norm_preview_v0.1.csv`: 370行 = 元候補 + verdict + 正規化名/統合先 + evidence
- `artifacts/periodical/journal_authority_norm_report_v0.1.md`: verdict内訳、MERGE_TO_EXISTING件数、**破壊的統合ゼロの確認**、high-risk一覧（別誌誤統合疑い・号数欠落・MISASSIGN）
- 出力先ブランチ: この発注を実行したブランチ（magazine）。P##系番号は使わない。

## 受入基準
- 370件すべてに verdict（欠けなし）。
- CITATION_FRAGMENT の MERGE_TO_EXISTING は統合先が実在（架空の統合先を作らない）。
- TRUNCATED_PAREN は破壊的統合ゼロ（名補完のみ）。
- report に high-risk が列挙される。

## 安全（厳守）
- **段1は read-only / dry-run**。authority本体・canonical・DB反映・外部publishは本発注の対象外（段2=owner GO）。
- 識別子補完(CiNii/NDL照合)は段2で、本発注では**やらない**。
- 判定に迷う候補は verdict=`NEEDS_DECISION` にして report の high-risk に上げ、head へ戻す（silentに流さない）。
