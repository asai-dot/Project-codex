# DD-L5-DISAMBIGUATION v0.1 — 評釈→判例ID 接合(L5主鍵)の判例DB当事者照合

- decision_id: DD-L5-DISAMBIGUATION
- 起案: head (Claude Code) / 2026-07-01
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

| 工程 | 指標 | 値 |
|---|---|---|
| A 真偽判定 | SPLIT_confirmed / MERGE_party_alias / unresolved | **246 / 71 / 807**（/1,124）|
| B 確定照合 | variant→判例ID 確定 | **24件**（バケット）|
| B edge化 | article→判例ID accepted edge | **34件**（distinct判例ID 23 / article 34）|
| C マップ | 一意確定 / うち通称↔正式名ペア | **199 / 141**（束ねる評釈 609）|

**検証例（高精度）**: ハマキョウレックス事件→`28262467`(平成29(受)442) / 三井倉庫港運事件→`27805325` /
レペタ事件→「メモ採取不許可国家賠償請求事件」`27803181` / コインハイブ事件⇔不正指令電磁的記録保管 `28300096`。
**MERGE例**: 石油価格協定刑事事件/日産自動車事件＝事件番号1＝当事者別名（私の過併合フラグの過剰分）。

## 4. caveat（honest_report）

1. 工程A: **court 空欄バケットは同日全判決とマッチし docket 数が過大**（大阪国際空港=12 等）。「≥2判決が存在」までの一次信号で、確定にはB(名称照合)が要る。
2. 工程B: 被覆 24/247≈10%。**通称(ハマキョウレックス)単独は正式名(地位確認等請求事件)と文字列が違い未照合**。
3. 工程C: unresolved 5,102（判例DB未収載=下級審/古い/非訟 or court/date 正規化未一致）。被覆 199/5,821≈3.4%。
4. edge化34は **file artifact**（owner_ratified・db_load=not_loaded）。本番DB投入は未実施。
5. 起案者=検証者が同 Claude family。独立監査不在。

## 5. 求める判定（独立監査・迎合不要）

1. **工程A の真偽判定ロジックは妥当か**: distinct 事件番号数 ≥2→SPLIT / =1→MERGE は正しい推論か。court空欄の過大カウントを SPLIT と誤認していないか（B未通過のSPLIT候補をどう扱うべきか）。
2. **34 accepted edge は正しいか**: 正式事件名のタイトル内一致→判例ID は false linkage を生まないか。owner ratify→本番DB投入の前提として安全か。
3. **141 通称↔正式名ペア**: 判例DB一意一致からの導出に誤りはないか（同名異判決の取りこぼし/誤接続）。
4. **被覆の壁**: 通称↔正式名の被覆拡大に、判例DB自己ブートストラップ以外の妥当な資源・手法は。
5. **L5主鍵設計**: 「過併合はフラグ化し判例権威で確定」方針は、CASENAME を canonical L5 主鍵に昇格させる前提として十分か。load-bearing な欠陥は。

## 6. 参照（commit / artifact）

- 判定: `l5_disambiguation_proposal_v0.1.csv` + summary（code `2fd173b`）
- 確定照合: `l5_assignment_proposal_v0.1.csv` + summary（code `76c1d0b`）
- edge化: `l5_accepted_edges_v0.1.jsonl`（code `385649f`）
- マップ: `l5_nickname_formal_map_v0.1.csv` + summary（code `fae6097`）
- フラグ: `case_name_dict_v0.2.csv`（is_possibly_overmerged, code `a0fa2ca`）
