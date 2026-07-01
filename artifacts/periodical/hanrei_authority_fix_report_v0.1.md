# 判例authority整合性 段1 dry-run 検証レポート v0.1（read-only）

- orch_id: ORCH-HANREI-AUTHORITY-FIX-20260701 / channel: hanrei
- 親WO: `docs/alo/WO-HANREI-AUTHORITY-FIX_v0.1_20260701.md`（branch: claude/t10-d1-full-sweep, commit 14caa08）
- 種別: **read-only / dry-run**。authority本体・canonical・DB・外部公開へは一切書いていない（段2=owner GO の対象）。
- 実行日: 2026-07-01 / 実行ブランチ: wk-hanrei

## 入力（read-only）
- 修正候補: `worktree-casename-dict:artifacts/periodical/hanrei_authority_corrections_v0.1.csv`（commit 39783df・**1,063件**）
- 判例authority: `/Users/yuta/alo-ai/work/d1law_dl/_parsed_hanrei/判例_identity_keys_20260605.csv`（178,318行）+ `..._backfill6yr_20260617.csv`（34,284行）= **212,602行**
- 再現スクリプト: `artifacts/periodical/_verify_hanrei_authority.py`（本発注で同梱）

## 結論（verdict 内訳）

| verdict | 件数 | 意味 |
|---|---:|---|
| TRUE_DUP | 1,038 | 同一判決の重複登録（統合候補） |
| DISTINCT | 6 | 別判決が同一 identity_key に衝突（**統合禁止**・identity_key 精緻化候補） |
| REDERIVABLE | 15 | court_key を機械再導出可（新値併記） |
| SOURCE_CHECK | 4 | date_key 再導出不能・原本確認要 |
| NEEDS_DECISION | 0 | — |
| **計** | **1,063** | 全件 verdict 付与（欠けなし）✓ |

issue 別: DUP_HANREI_ID 600件=全 TRUE_DUP / DUP_IDENTITY_KEY 444件=TRUE_DUP 438 + DISTINCT 6 / BAD_DATE 4件=全 SOURCE_CHECK / COURT_KEY_MANGLED 15件=全 REDERIVABLE。

### TRUE_DUP 1,038件の内訳（統合してよいが、採用値の別あり）
| サブ種別 | 件数 | 統合時の推奨 |
|---|---:|---|
| pure_identical（全列完全一致） | 850 | どちらを残しても同一 |
| docket_consolidation（被併合・lead一致で番号追加のみ） | 169 | **full docket を採用**（例 `h26(オ)1020` ← `h26(オ)1020h26(受)1295`） |
| normalized_equal（空白/表記ゆれ・第/号差のみ） | 13 | 正規表記を採用 |
| field_inconsistency（court_key の支部粒度/化け差） | 6 | **正しい court_key を採用**（下記 high-risk 参照） |

> 判定方針: DUP_HANREI_ID は同一 判例ID＝定義上同一判決のため、docket/court の差は「別判決」ではなくデータ不整合として扱い、統合禁止（DISTINCT）とはしない。DISTINCT は **事件名が実質的に異なる** 場合のみ付与（WO の DISTINCT トリガ準拠）。

## COURT_KEY_MANGLED 15件（受入基準: 全て REDERIVABLE で衝突0）
**15/15 REDERIVABLE・衝突0 を確認**（既存の別裁判所名が同一 court_key を使用する例は0件）。先頭アラビア数字→漢数字復元:

| mangled | 復元後 | 裁判所名 | 衝突 |
|---|---|---|---|
| 4日市簡 | 四日市簡 | 四日市簡易裁判所 | 0 |
| 1関区 | 一関区 | 一関区裁判所 | 0 |
| 4日市区 | 四日市区 | 四日市区裁判所 | 0 |
| 7尾区 | 七尾区 | 七尾区裁判所 | 0 |
| 8幡簡 | 八幡簡 | 八幡簡易裁判所 | 0 |
| 8幡浜簡 | 八幡浜簡 | 八幡浜簡易裁判所 | 0 |
| 8王子簡 | 八王子簡 | 八王子簡易裁判所 | 0 |
| 7尾簡 | 七尾簡 | 七尾簡易裁判所 | 0 |
| 5所川原簡 | 五所川原簡 | 五所川原簡易裁判所 | 0 |
| 1宮簡 | 一宮簡 | 一宮簡易裁判所 | 0（既存に正 court_key も併存＝一部行のみ化け） |
| 8戸簡 | 八戸簡 | 八戸簡易裁判所 | 0（同上） |
| 3次区 | 三次区 | 三次区裁判所 | 0 |
| 8女簡 | 八女簡 | 八女簡易裁判所 | 0（同上） |
| 3次簡 | 三次簡 | 三次簡易裁判所 | 0 |
| 6日町簡 | 六日町簡 | 六日町簡易裁判所 | 0 |

※「一部行が正」= 同一裁判所の一部行が既に正しい court_key を持ち、化け行のみが別 key に散っている状態。復元で正 key へ統一される（別裁判所との衝突ではない）。CONFLICT: **0件**。

---

## HIGH-RISK 一覧（silent に流さず head へ戻す）

### A. DISTINCT 6件 — **統合禁止**（別判決が identity_key に衝突。identity_key 精緻化候補）
いずれも 事件名が実質的に異なる別判決。うち3件は docket_key が空欄のため座標が縮退して衝突している（identity_key に docket が乗らない事件）。

| identity_key | 事件名A | 事件名B | 判例ID |
|---|---|---|---|
| 名古屋地\|20050524\|h14(ワ)2398の8 | 所有権移転登記抹消登記手続等請求事件 | 損害賠償等請求事件 | 28224801 / 29008826 |
| 最高第2小法廷\|20101006\|**(docket空)** | 協力金請求事件 | 相続税更正処分取消請求上告受理事件 | 28211932 / 28211933 |
| 横浜地\|20100324\|**(docket空)** | 告知処分取消請求事件 | 更正処分取消請求事件 | 28211753 / 28211754 |
| 名古屋高\|20170412\|**(docket空)** | 信用毀損損害賠償請求控訴事件 | 租税法律主義違反並びに国税不服審判決定取消請求控訴事件 | 28271800 / 28271803 |
| 東京地\|20201216\|r1(ワ)27900 | 損害賠償請求事件 | 損害賠償請求事件（被告Ｙ１関係） | 28292778 / 28292779 |
| 東京地\|20201211\|r2(ワ)16756 | 損害賠償請求事件 | 損害賠償請求事件（16756号）、損害賠償請求反訴事件（23461号） | 28292780 / 28292781 |

推奨: これら6ペアは統合せず、identity_key に docket（空欄3件）や本訴/反訴・被告別の枝番を織り込んで分離する（段2・要 owner/head 判断）。

### B. SOURCE_CHECK 4件 — date_key 再導出不能・原本確認要
| 判例ID | 判決年月日 | 理由 |
|---|---|---|
| 27450568 | 昭和３４年５月 | 日欠落（年月のみ） |
| 27483057 | 昭和２７年４月 | 日欠落（年月のみ） |
| 28264342 | 昭和３８年２月２９日 | 存在しない日（1963-02は28日まで） |
| 28213915 | 昭和４８年２月２９日 | 存在しない日（1973-02は28日まで） |

推奨: 機械では確定不可。D1-Law 原本の判決年月日を確認して補完（段2）。

### C. field_inconsistency（TRUE_DUP だが court_key 要修正）6件
同一 判例ID の重複行間で court_key のみが不整合。統合はしてよいが、採用する court_key を要確定。特に `28241681` は本タスクの化け（4日市→四日市）そのもの。

| 判例ID | court_key の差 | 推奨採用 |
|---|---|---|
| 28231433 | 広島高 / 広島高松江支 | 支部粒度の細かい方（広島高松江支） |
| 28232347 | 広島高 / 広島高松江支 | 同上 |
| 28242488 | 札幌家 / 札幌家滝川支 | 札幌家滝川支 |
| 28244520 | 名古屋高 / 名古屋高金沢支 | 名古屋高金沢支 |
| 28243525 | 仙台高 / 仙台高秋田支 | 仙台高秋田支 |
| 28241681 | 津地4日市支 / 津地四日市支 | **津地四日市支（化け修正）** |

---

## 受入基準チェック
- [x] 1,063件すべてに verdict（欠け0・NEEDS_DECISION 0）
- [x] COURT_KEY_MANGLED 15件は全て REDERIVABLE・衝突0（CONFLICT 0）
- [x] report に high-risk 列挙（統合禁止 DISTINCT 6 / 原本確認要 SOURCE_CHECK 4 / court_key 要修正 6）

## 安全（厳守事項の遵守）
- 段1は **read-only / dry-run**。authority本体・canonical・DB・外部公開へは書き込みなし。
- 出力は識別キー・事件名・事件番号までに限定。judgment本文・当事者名の生payloadは載せていない（DISTINCT表の事件名は authority の 事件名 列＝公開メタの範囲）。
- 実反映（統合・court_key/date_key 補正・identity_key 精緻化）は **段2=owner GO** の対象。

## 判定ロジック（監査用サマリ）
1. 候補 key で authority を突合し、共有行群を取得（DUP_HANREI_ID=判例ID / DUP_IDENTITY_KEY=identity_key）。
2. 識別列 `court_key,裁判所名,date_key,判決年月日,docket_key,事件番号,事件名` のみで差分判定（判例ID/identity_key の差は同一判決の想定内として除外）。正規化=NFKC＋空白/区切り/第・号除去。
3. 事件名が実質差→DISTINCT。docket が被併合（lead一致で番号追加）→TRUE_DUP。docket 非包含→NEEDS_DECISION（本データでは0）。court/date のみ差→TRUE_DUP(field不整合)。
4. BAD_DATE=和暦漢字を西暦へ再導出し暦検証（存在しない日/月のみ→SOURCE_CHECK）。
5. COURT_KEY_MANGLED=先頭アラビア数字→漢数字復元し、復元 court_key を他裁判所名が使用していないか衝突検査。
