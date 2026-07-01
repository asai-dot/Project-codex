# ORCH-AUTHORITY-APPLY order 20260701 — 確定分の authority 反映(候補v-next生成・非破壊・live昇格しない)

- orch_id: ORCH-AUTHORITY-APPLY-20260701 / channel: apply
- 親: 段1/段2 検証(受入合格済) hanrei=83ced88 / journal norm=78d27b2 / jissn=277fa52
- owner GO: 2026-07-01「確定分Go」。**held は全除外**。
- 種別: **候補(v-next)生成のみ**。v14/現版は保全。**liveへのcanonical昇格はしない**(head受入検査→owner最終GOで別途)。router: worker=draft_write上限に適合。

## 適用する確定分(これだけ・他は触らない)

### A. 判例authority
入力: `.../wk-hanrei:artifacts/periodical/hanrei_authority_fix_preview_v0.1.csv`(1,063行verdict) ＋ 現authority `/Users/yuta/alo-ai/work/d1law_dl/_parsed_hanrei/判例_identity_keys_20260605.csv` + `..._backfill6yr_20260617.csv`(212,602行)
- **REDERIVABLE 15**: court_key を復元後値へ置換(4日市簡→四日市簡 等)。
- **TRUE_DUP 1,038**: 重複統合。採用値ルール厳守=pure_identical(850)どちらでも / docket_consolidation(169)は**full docket採用** / normalized_equal(13)正規表記 / field_inconsistency(6)正しいcourt_key。
- **除外(触らない)**: DISTINCT 6(統合禁止) / SOURCE_CHECK 4(原本確認要=held)。
- 出力: `artifacts/periodical/判例_identity_keys_vnext_candidate_20260701.csv`(212,602−1,038=**211,564行 期待**) ＋ `hanrei_apply_changelog_20260701.csv`(行ごと before/after/理由) ＋ raw保全(元2ファイルは読取のみ・変更禁止)。

### B. journal authority
入力: `.../wk-journal:artifacts/periodical/journal_authority_norm_preview_v0.1.csv`(370) ＋ `.../wk-jissn:artifacts/periodical/journal_issn_resolve_proposal_v0.1.csv`(24) ＋ 現版 `d1_journal_issn_authority_ALL_resolved_v14.csv`(931行)
- **NORMALIZE 341**: journal_canonical を正規化名へ(末尾補完のみ)。
- **MERGE_TO_EXISTING 7**: 実在誌へ統合(article_count合算・元行はnoteに退避)。
- **ISSN_RESOLVED 1**: 税理 に key_type=issn,key_value=0514-2512(source=ndl_sru:apply_20260701)。
- **除外(触らない)**: MISASSIGN 1 / NEEDS_DECISION 1 / AMBIGUOUS 11 / ISSN_NOT_EXIST 10(NCID維持) / COLLISION 2。
- 出力: `artifacts/periodical/d1_journal_issn_authority_ALL_resolved_v15_candidate.csv`(931−7=**924行 期待**) ＋ `journal_apply_changelog_20260701.csv` ＋ v14保全。

## 回帰検査(必須・reportに記載)
- 判例: 候補の 判例ID重複=0 / identity_key重複が減少 / court化けcourt_key=0 / 行数=211,564一致。
- 判例(効果): 復元後court_keyでL5 court突合を再計算し court_miss 改善数を記載(read-only)。
- journal: 候補の dup-ISSN(同一ISSN→別誌)が**増えていない**こと / NORMALIZE後の新規過分割=0 / 税理ISSN=別誌未使用。
- 変更件数が確定分(判例1,053件相当/journal349件)と一致。想定外の差分は NEEDS_DECISION で停止。

## 安全(厳守)
- **候補生成のみ。live/canonical authorityファイルを上書きしない**(元d1law 2ファイル・v14 は不変)。
- append-only的に新ファイルへ。changelog で全変更を追跡可能に。
- 除外項目(held)には一切触れない。想定外差分は停止して head へ(silent禁止)。
- 出力は本ブランチにcommit/push。P##番号不使用。
