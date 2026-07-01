# ORCH-HANREI-AUTHORITY-FIX order 20260701 — 判例authority整合性 段1 dry-run検証（read-only）

- orch_id: ORCH-HANREI-AUTHORITY-FIX-20260701 / channel: hanrei
- 親WO: `docs/alo/WO-HANREI-AUTHORITY-FIX_v0.1_20260701.md`（branch: claude/t10-d1-full-sweep, commit 14caa08）
- 種別: **read-only / dry-run のみ**。authority本体に一切書かない。canonical/実反映/DB投入は本発注の対象外（段2=owner GO）。

## 何をするか（段1のみ）
head の read-only QA が出した修正候補 **1,063件** を判決データと突合し、各候補に verdict を付け、**preview（before/after・書き込まない）**を出す。

### 入力（read-only）
- 修正候補: worktree `worktree-casename-dict` の `artifacts/periodical/hanrei_authority_corrections_v0.1.csv`（commit 39783df・列 issue,key,detail,recommend,sample）
- 判例authority: `/Users/yuta/alo-ai/work/d1law_dl/_parsed_hanrei/判例_identity_keys_20260605.csv` および `..._backfill6yr_20260617.csv`（計212,602行・列 判例ID,court_key,date_key,docket_key,identity_key,裁判所名,判決年月日,事件番号,事件名）

### 検証ルール（issueごと）
1. **DUP_HANREI_ID(600)** / **DUP_IDENTITY_KEY(444)**: 該当の2+行を全列比較。
   - 全列一致 or 軽微差(空白/表記ゆれ) → verdict=`TRUE_DUP`（統合候補）
   - 事件名/事件番号/当事者が実質的に異なる → verdict=`DISTINCT`（統合禁止・identity_key精緻化候補）
2. **BAD_DATE(4)**: 判決年月日(和暦漢字)から date_key を再導出。
   - 一意に導出可 → verdict=`REDERIVABLE`（新date_key併記）
   - 存在しない日(昭和38.2.29等)/月のみ → verdict=`SOURCE_CHECK`（原本確認要フラグ）
3. **COURT_KEY_MANGLED(15)**: 裁判所名フルから court_key を再導出（先頭漢数字復元 4→四 等）。
   - 復元後 court_key が既存の正規 court_key と衝突しない → verdict=`REDERIVABLE`（新court_key併記）
   - 衝突する → verdict=`CONFLICT`（要 head 判断）

### 出力（成果物・commit して push）
- `artifacts/periodical/hanrei_authority_fix_preview_v0.1.csv`: 1,063行 = 元候補 + verdict + 復元後値(あれば) + evidence(比較した列/差分要約)
- `artifacts/periodical/hanrei_authority_fix_report_v0.1.md`: verdict内訳、TRUE_DUP/DISTINCT の件数、court復元の衝突0確認、**high-risk一覧**（DISTINCT混入疑い・SOURCE_CHECK・CONFLICT）
- 出力先ブランチ: この発注を実行したブランチ（magazine）。P##系の番号は使わない。

## 受入基準
- 1,063件すべてに verdict が付く（欠けなし）。
- COURT_KEY_MANGLED 15件は全て REDERIVABLE で衝突0、でなければ CONFLICT を明示。
- report に high-risk（統合してはいけない DISTINCT、原本確認要）が列挙される。

## 安全（厳守）
- **段1は read-only / dry-run**。judgment本文・当事者名の生payloadは出力に載せない（識別キー/事件名/事件番号までの整合判定に限定）。
- authority本体・canonical・DB反映・外部公開は**本発注の対象外（段2=owner GO）**。
- 判定に迷う候補は verdict=`NEEDS_DECISION` にして report の high-risk に上げ、head へ戻す（silentに流さない）。
