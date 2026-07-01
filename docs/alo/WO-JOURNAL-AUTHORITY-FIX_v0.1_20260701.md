# WO-JOURNAL-AUTHORITY-FIX v0.1 — journal authority 2段修正（誌名正規化→識別子補完・dry-run先行）

- wo_id: WO-JOURNAL-AUTHORITY-FIX-V01-20260701
- from: head (CC) / to: periodical pipeline producer (Mac)
- priority: 中（全評釈→誌 join の根・L3/L4 誌解決の土台）
- 入力(read-only):
  - journal authority `.../artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v14.csv`（931行・列 journal_canonical,article_count,key_type,key_value,status,source,note）
  - head QA成果: `hanrei` と同worktree(worktree-casename-dict, 85a7bd2) の
    `journal_authority_corrections_v0.1.csv`（370件）／`journal_authority_qa_summary_v0.1.json`
- result_to: periodical pipeline の from_producer / RPT_journal_authority_fix_v01_<日時>

## 背景（記事加重カバレッジ・head 実測）
総記事302,130。識別子カバレッジ = ISSN 77.3% + NCID(CiNii) 19.9% = **97.2%が既にjoin可能**。ID皆無は2.8%(8,367記事)のみ。
ただし誌“名”に parse garbage が混入し join を汚す: CITATION_FRAGMENT 169 / TRUNCATED_PAREN 179。
**順序が重要**: 先に誌名を正規化してから識別子補完しないと、garbage名のまま外部照合して手戻りが出る。

## scope（段階的・判例WOと同型）

### 段1: 誌名正規化 dry-run（read-only・owner GO 前に実施可）
1. **CITATION_FRAGMENT(169)**: `…』所収p` `…,p` `…創刊号,` 等の掲載位置サフィックスを除去し core 誌名/venue名を抽出。
   - 除去後名が既存 journal_canonical と一致 → verdict=`MERGE_TO_EXISTING`（統合先併記）
   - 一致しないが正当な venue（記念論文集等）→ verdict=`NORMALIZE`（正規化名併記）
2. **TRUNCATED_PAREN(179)**: `…(別冊ジュリスト` 等の末尾切れを検出。
   - 別冊ジュリスト/百選系は canonical シリーズ名へ正規化（号数は不明なら欠落フラグ）→ verdict=`NORMALIZE`
   - join は現状も有効なので破壊的統合はしない（名の補完のみ）
3. **DUP_ISSN(22)**: 同一ISSN→複数誌を「同一誌の異表記/増刊 vs 別誌への誤付与」に分類 → verdict=`TRUE_SAME`/`MISASSIGN`。
4. 出力は**提案のみ**。authority 本体に書かない。
- 出力: `journal_authority_norm_preview_v0.1.csv`（370行=元候補+verdict+正規化名/統合先+evidence）
  ＋ `journal_authority_norm_report_v0.1.md`（verdict内訳・MERGE件数・破壊的統合の有無・high-risk）

### 段2: 識別子補完（owner GO・段1レビュー後）
- 段1で正規化した誌のうち **ID皆無の定期刊行258誌/6,401記事** を対象に、CiNii/NDL(read-only 公開照合)で ISSN/NCID を解決 → 提案。
- 書籍系157誌は ISBN_per_issue/通号を対象（別枠）。
- **canonical への key 反映・DB投入は owner GO**。外部照合は read-only(publish しない=external_share不変)。

## 受入基準（段1）
- 370件すべてに verdict（欠けなし）。
- CITATION_FRAGMENT の除去が誌名の実体を壊していない（MERGE_TO_EXISTING は統合先が実在）。
- TRUNCATED_PAREN は破壊的統合ゼロ（名補完のみ）。
- report に high-risk（別誌への誤統合疑い・号数欠落・MISASSIGN）を列挙。

## 安全（厳守）
- 段1は read-only/dry-run。authority本体・canonical・DB反映・外部publishは対象外（段2以降 owner GO）。
- 段2の外部照合は公開メタの read-only lookup のみ（生payload取込・共有はしない）。
- 迷う候補は verdict=`NEEDS_DECISION` で head へ戻す（silentに流さない）。

## head 受入検査
- 段1 RPT を head 検査（verdict網羅・破壊的統合ゼロ・high-risk明示）。必要なら GPT 監査。
- 段2後、評釈→誌 join の被覆/精度の改善を head が回帰監査。
