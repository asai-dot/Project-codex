---
request_id: 20260701_DD-L5-DISAMBIGUATION_v0.3
decision_id: DD-L5-DISAMBIGUATION
request_type: 設計再監査 / blocking_addressed 確認 (DESIGN gate)
gate: DESIGN
topic: 評釈→判例ID 接合(L5主鍵) v0.3 — DESIGN_MODIFY_REQUIRED の Must-Fix 7点反映確認
作成日: 2026-07-01
監査対象: docs/alo/DD-L5-DISAMBIGUATION_v0.1_20260701.md
source_hash: sha256:ae1a587d2b6259978d4469242238b2751e00d58febcda7d3db7edd2c95d20a9d
target_mode: inline_embedded
result_expected_filename: 20260701_DD-L5-DISAMBIGUATION_v0.3_RESULT.md
status: queued
supersedes: 20260701_DD-L5-DISAMBIGUATION_v0.2 / v0.1 (DESIGN_MODIFY_REQUIRED)
prior_verdict: DESIGN_MODIFY_REQUIRED
review_scope:
  include: [Must-Fix 7点の閉鎖確認, status弱体化の妥当性, generic guard, edge証跡, map tiering, canonical設計#7]
  exclude: [CASENAME v0.1抽出器再設計, 判例本体スキーマ, 本番DB投入手順]
regression_anchors:
  - "ORCH-CASENAME-DICT(PASS_WITH_NOTES) / ORCH-L5-FEASIBILITY(Grade A)。矛盾不可"
  - "全工程 read-only。accepted edge は file artifact・production load 未実施。canonical昇格/DB投入は owner GO"
decision_requested: Must-Fix 7点が閉じたか / DESIGN_PASS_WITH_NOTES 可否
---

# GPT Pro お目付け役 再監査依頼: DD-L5-DISAMBIGUATION v0.3

## 0. これは何か（再監査）

前回 `DESIGN_MODIFY_REQUIRED` の Must-Fix 7点を反映した v0.3。判定名の過強・generic title 誤接続・証跡不足の
指摘を受け、status を弱体化し、generic guard・tiering・item-level 証跡・canonical 設計改訂を入れた。
**起案=検証が同 Claude family** のため独立監査依頼。迎合せず、残る load-bearing 欠陥を厳しく指摘してほしい。

## 1. Must-Fix 反映状況（自己申告・正は source_hash の現物 §7）

| # | Must-Fix | v0.3 反映 |
|---|---|---|
| 1 | status 弱体化 | confirmed_split **8**（distinct固有名一致のみ）/ split_signal 516 / single_docket_visible 247（=1は当事者別名と断定せず）/ unresolved 323。「≥2→確定」「=1→MERGE」撤回 |
| 2 | court空欄除外 | court_blank 30 を confirmed系・edge から物理除外 |
| 3 | generic title guard | 判例DB内 事件名頻度≥10 を generic 判定（地位確認等請求事件 等）|
| 4 | edge item-level 証跡 | l5_accepted_edges_v0.3.jsonl（title/formal名/freq/事件番号/判例ID 同梱）|
| 5 | edge 全件 owner review | l5_edge_owner_review_v0.3.csv（85件・owner_decision列）|
| 6 | map tiering | T1 32 / T2 583 / T3 922 / REJECT 38 |
| 7 | canonical 設計 | canonical target = 判例ID/docket/court/date、CASENAME は alias/fingerprint/resolver input |

**確定の正直な範囲**: edge T1_distinctive **23** / map T1+T2 **615** が高/中信頼。generic名経由は T3=要 owner review。

## 2. 確定済み前提（監査の枠）

全工程 read-only。accepted edge は file artifact（production load 未実施）。canonical 昇格・DB投入は owner GO（対象外）。

## 3. 求める判定（この3点）

1. **Must-Fix 7点が設計レベルで閉じたか**（DESIGN_PASS_WITH_NOTES 可否）。
2. status の弱体化（confirmed を distinct固有名一致のみに限定、=1 を断定しない）は十分保守的か。over-claim が残っていないか。
3. canonical 設計#7（判例ID主鍵・CASENAME alias化）は L5 昇格の前提として妥当か。残る load-bearing 欠陥は。

## 4. 1行目の書式指定

RESULT 1行目 = `DESIGN_<LABEL>`。本文先頭付近に `request_id: 20260701_DD-L5-DISAMBIGUATION_v0.3` を含めること。

---

## APPENDIX — 監査対象 DD v0.3 全文

<!-- 以下は docs/alo/DD-L5-DISAMBIGUATION_v0.1_20260701.md(v0.3本文) の全文（source_hash 一致） -->
# DD-L5-DISAMBIGUATION v0.3 — 評釈→判例ID 接合(L5主鍵)の判例DB当事者照合

- decision_id: DD-L5-DISAMBIGUATION
- 起案: head (Claude Code) / 2026-07-01
- version: **v0.3** — GPT Pro `DESIGN_MODIFY_REQUIRED`(v0.1/v0.2監査)の Must-Fix 7点を反映（§7）。
  要点: 判定名を弱体化(confirmed→signal/candidate/confirmed)、court空欄除外、generic formal title guard、
  edge全件 item-level 証跡、map tiering(T1/T2/T3/REJECT)、**canonical target を判例ID/docket とし CASENAME は alias/resolver input**。
- version: **v0.2** — owner 指摘「名のある判例は50倍あるやろ」を受け **court 正規化バグを発見・修正**して全工程再実行。
  根因: `normalize_court` が末尾の判決種別(判/決)を残し、下級審 court が判例DB(東京地 等)と全不一致→大量取りこぼし(court_miss 3,653)。
  修正(東京地判→東京地)で全被覆が一桁改善（数字は §3）。
- 種別: ANALYSIS/DESIGN 監査（全工程 read-only。accepted edge は file artifact・本番DB投入は未実施）
- 親: ORCH-CASENAME-DICT（PASS_WITH_NOTES）/ ORCH-L5-FEASIBILITY（Grade A）
- 正本ブランチ: head infra = `claude/magazine-object-analysis-seg9cr` / L5データ = `worktree-casename-dict`

---

## 0. 一行要約

CASENAME辞書(L5主鍵)の「(court,date)キーによる同日別事件の過併合」を、判例側 identity keys
（212,604行・**事件番号/事件名**）で照合し、(1)真の別事件 vs 当事者別名を機械確定、(2)正式事件名一致で
評釈→判例ID を高精度接続、(3)通称↔正式名マップを判例権威から導出。**全て read-only**、accepted edge は可逆 file。

---

## 1. 問題と先行（確定済み前提）

- CASENAME-DICT は事件を `(case_name, court, date)` で集約するが、**dated bucket は `(date, court_class)` キーで名前を無視**するため、
  同日同裁判所の別事件（ハマキョウレックス事件＋長澤運輸事件）が1 case に過併合される（head検証で発見・PASS_WITH_NOTES）。
- v0.2 で `is_possibly_overmerged` フラグ（1,124件）を付与済（誤分割を避け、文字列では当事者別名と別事件が区別不能なため）。
- L5-FEASIBILITY: `(court,date)` 粗結合は Grade A(85%)、但し matched_multi は事件名/docket で一意化要、と試算済。

## 2. 方法（read-only・3工程）

### 工程A: 過併合の真偽判定（distinct 事件番号 count）
過併合1,124バケットの `(court,date)` で判例DBの **distinct 事件番号数**を数える:
- ≥2 → 真の別事件（**SPLIT_confirmed**）/ =1 → 当事者別名（**MERGE_party_alias**）/ =0 → unresolved。

### 工程B: variant→判例ID 確定照合
SPLIT候補の variant のうち**正式事件名を含むもの**を、同(court,date)の判例側『事件名』へ完全/包含一致→判例ID/事件番号へ確定。

### 工程C: 通称↔正式名マップ導出
非過併合(単発)バケットが判例DBで**一意一致**(同court,date に判決1件)する所で `通称 ↔ 正式事件名 ↔ 判例ID` を確定。

## 3. 結果

（v0.2・court正規化修正後。括弧内は修正前の過少値）

| 工程 | 指標 | 値 |
|---|---|---|
| A 真偽判定 | SPLIT_confirmed / MERGE_party_alias / unresolved | **554 / 247 / 323**（旧 246/71/807）|
| B edge化 | article→判例ID accepted edge | **66件**（distinct判例ID 50・旧34）|
| C マップ | 通称→判例ID 確定 | **1,575件**（旧199・束ねる評釈 3,479）|

母数: 名のある判例(○○事件/訴訟 固有名) = **8,511**（date+court有 5,431）。court修正で court_miss 3,653→558。

**検証例（高精度）**: ハマキョウレックス事件→`28262467`(平成29(受)442) / 三井倉庫港運事件→`27805325` /
レペタ事件→「メモ採取不許可国家賠償請求事件」`27803181` / コインハイブ事件⇔不正指令電磁的記録保管 `28300096`。
**MERGE例**: 石油価格協定刑事事件/日産自動車事件＝事件番号1＝当事者別名（私の過併合フラグの過剰分）。

## 4. caveat（honest_report）

1. **court正規化バグ(v0.1)を修正済**。これが最大の取りこぼし要因だった(owner 指摘で発見)。残課題は以下。
2. 工程A: **court 空欄バケットは同日全判決とマッチし docket 数が過大**（大阪国際空港=12 等）。「≥2判決が存在」までの一次信号で、確定にはB(名称照合)が要る。
3. マップ残: **multi_unresolved 2,266**（同日複数判決で通称が正式名と文字列不一致）。マップ自己bootstrap＋title docket抽出で更に回収可。no_date_in_db 1,032（下級審/非訟で判例DB未収載 or 古い）。
4. accepted edge 66 は **file artifact**（owner_ratified・db_load=not_loaded）。本番DB投入は未実施。
5. 起案者=検証者が同 Claude family。独立監査不在。

## 5. 求める判定（独立監査・迎合不要）

1. **工程A の真偽判定ロジックは妥当か**: distinct 事件番号数 ≥2→SPLIT / =1→MERGE は正しい推論か。court空欄の過大カウントを SPLIT と誤認していないか（B未通過のSPLIT候補をどう扱うべきか）。
2. **66 accepted edge は正しいか**: 正式事件名のタイトル内一致→判例ID は false linkage を生まないか。owner ratify→本番DB投入の前提として安全か。
3. **1,575 通称→判例IDマップ**: 判例DB一意/name照合からの導出に誤りはないか（同名異判決の取りこぼし/誤接続）。
4. **残被覆(multi 2,266)**: 通称↔正式名の被覆拡大に、判例DB自己ブートストラップ・title docket抽出 以外の妥当な資源・手法は。
5. **L5主鍵設計**: 「過併合はフラグ化し判例権威で確定」方針は、CASENAME を canonical L5 主鍵に昇格させる前提として十分か。load-bearing な欠陥は。

## 6. 参照（commit / artifact・v0.2 court修正版 = code `c4aa073`）

- 判定: `l5_disambiguation_proposal_v0.1.csv` + summary（SPLIT554/MERGE247/unresolved323）
- edge化: `l5_accepted_edges_v0.1.jsonl`（66件）
- マップ: `l5_nickname_formal_map_v0.2.csv` + summary（1,575件）
- フラグ: `case_name_dict_v0.2.csv`（is_possibly_overmerged 1,124, code `a0fa2ca`）
- court修正: `l5_feasibility_build.py:normalize_court`（末尾 判/決 除去, code `c4aa073`）

## 7. Must-Fix 反映（v0.3・GPT DESIGN_MODIFY_REQUIRED 対応・code `a4a64aa`）

| # | Must-Fix | 反映 |
|---|---|---|
| 1 | status 弱体化 | `confirmed_split 8`（distinct固有名一致のみ）/ `split_signal 516` / `single_docket_visible 247`（=1 は当事者別名と**断定しない**）/ `unresolved 323`。「≥2→SPLIT確定」「=1→MERGE」を撤回 |
| 2 | court空欄除外 | `court_blank 30` を confirmed系・edge から物理除外（同日全判決マッチの過大を排除）|
| 3 | generic title guard | 判例DB内の**事件名頻度≥10 を generic**と判定（地位確認等請求事件 等）。generic は低 tier へ |
| 4 | edge item-level 証跡 | `l5_accepted_edges_v0.3.jsonl`: title / matched formal名 / freq / 事件番号 / 判例ID を同梱→false linkage 検証可 |
| 5 | edge 全件 owner review | `l5_edge_owner_review_v0.3.csv`（85件・owner_decision列）|
| 6 | map tiering | `l5_nickname_formal_map_v0.3.csv`: **T1 32 / T2 583 / T3 922 / REJECT 38** |
| 7 | **canonical 設計** | **canonical target = 判例ID / docket / court / date**。CASENAME は単独主鍵にせず **alias / fingerprint / resolver input** として扱う。canonical 昇格はこの構造で行う |

**正直な確定**: edge は **T1_distinctive 23件**、map は **T1+T2 615件**が高/中信頼。generic名経由（ハマキョウレックス→地位確認等請求事件 等）は T3=要 owner review。

## 8. HOLD（v0.3・全て owner GO）

production DB load / `alo_edges` accepted・canonical 昇格 / CASENAME単独の canonical L5主鍵化 /
court_blank・generic_title の自動 accepted / downstream MCP serving / map の一括 canonical alias 化。
