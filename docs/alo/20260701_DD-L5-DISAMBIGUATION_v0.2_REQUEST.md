---
request_id: 20260701_DD-L5-DISAMBIGUATION_v0.2
decision_id: DD-L5-DISAMBIGUATION
request_type: 分析/設計監査 (ANALYSIS/DESIGN gate)
gate: DESIGN
topic: 評釈→判例ID 接合(L5主鍵)の判例DB当事者照合 v0.2(court正規化バグ修正後)
作成日: 2026-07-01
監査対象: docs/alo/DD-L5-DISAMBIGUATION_v0.1_20260701.md
source_hash: sha256:a9c8b3163c48e89fb5e44c85f43609117c187b8b5867be6d462512c8dd5b21e6
target_mode: inline_embedded
result_expected_filename: 20260701_DD-L5-DISAMBIGUATION_v0.2_RESULT.md
status: queued
supersedes: 20260701_DD-L5-DISAMBIGUATION_v0.1 (court正規化バグ修正前・投函せず hold)
review_scope:
  include: [真偽判定ロジックの妥当性, 66 accepted edgeの正しさ, 1575通称マップの正しさ, 残被覆(multi2266)の手法, L5主鍵昇格の可否]
  exclude: [CASENAME-DICT v0.1抽出器の再設計, 判例オブジェクト本体スキーマ, 本番DB投入手順]
regression_anchors:
  - "ORCH-CASENAME-DICT verdict(PASS_WITH_NOTES) / ORCH-L5-FEASIBILITY(Grade A)。矛盾不可"
  - "全工程 read-only。accepted edge は file artifact・本番DB投入未実施(canonical昇格/DB投入は owner GO)"
decision_requested: 真偽判定ロジック妥当性 / 66 edge と1575マップの正否 / 残被覆手法 / L5主鍵昇格の可否
---

# GPT Pro お目付け役 監査依頼: DD-L5-DISAMBIGUATION v0.2（評釈→判例ID 接合）

## 0. これは何か（v0.2・独立監査・迎合不要）

owner 指摘「名のある判例は50倍あるやろ」を受け、**court 正規化バグ**（末尾の判決種別 判/決 を残し下級審 court が
判例DB と全不一致＝court_miss 3,653）を発見・修正して全工程を再実行した版。被覆が一桁改善した。
起案・検証が同 Claude family のため独立性が無い。別 AI family の視点で前提を疑い、**load-bearing な欠陥**
（accepted edge の false linkage、過併合判定の誤り）を厳しく指摘してほしい。

## 1. 背景

CASENAME-DICT（評釈→事件名辞書・L5主鍵候補）は `(date,court_class)` キーで同日別事件を過併合する欠陥がある。
判例側 identity keys（212,604行・事件番号/事件名）で照合し、(A)真の別事件 vs 当事者別名、(B)正式事件名一致で
評釈→判例ID、(C)通称↔正式名マップ を導出。v0.2 で court 正規化を修正（東京地判→東京地）。

## 2. 確定済み前提（監査の枠・変更不可）

- 全工程 read-only（判例本体/edge への書込なし・当事者名非出力）。accepted edge 66件は file artifact（owner_ratified・db_load=not_loaded）。
- 本番DB投入・canonical 昇格は owner GO 必須（本監査の対象外）。CASENAME v0.1 抽出器の再設計は対象外。

## 3. 主要数字（v0.2・court修正後／旧=修正前）

- 名のある判例 母数 = 8,511（date+court有 5,431）
- 過併合判定: SPLIT 554 / MERGE 247 / unresolved 323（旧 246/71/807）
- accepted edge: 66（判例ID 50・旧34）/ 通称→判例IDマップ: 1,575（旧199・評釈3,479束ね）
- 残: multi_unresolved 2,266（同日複数判決×通称が正式名と不一致）/ no_date_in_db 1,032

## 4. 求める判定（5点・DD §5 と同じ）

1. **工程A 真偽判定**: distinct 事件番号数 ≥2→SPLIT / =1→MERGE は妥当か。court空欄の過大カウントを SPLIT と誤認しない扱いは。
2. **66 accepted edge**: 正式事件名のタイトル内一致→判例ID は false linkage を生まないか。owner ratify→本番投入の前提として安全か。
3. **1,575 通称マップ**: 判例DB一意/name照合導出に誤接続/取りこぼしは。
4. **残被覆(multi 2,266)**: 通称↔正式名の被覆拡大に妥当な資源・手法は。
5. **L5主鍵昇格**: 「過併合フラグ化＋判例権威で確定」は canonical L5 主鍵昇格の前提として十分か。load-bearing 欠陥は。

## 5. 1行目の書式指定

RESULT の1行目は `DESIGN_<LABEL>`（PASS / PASS_WITH_NOTES / MODIFY_REQUIRED / FAIL / NEED_MORE）。
本文先頭付近に `request_id: 20260701_DD-L5-DISAMBIGUATION_v0.2` を含めること。

---

## APPENDIX — 監査対象 DD 全文

<!-- 以下は docs/alo/DD-L5-DISAMBIGUATION_v0.1_20260701.md(v0.2本文) の全文（source_hash 一致） -->
# DD-L5-DISAMBIGUATION v0.2 — 評釈→判例ID 接合(L5主鍵)の判例DB当事者照合

- decision_id: DD-L5-DISAMBIGUATION
- 起案: head (Claude Code) / 2026-07-01
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
