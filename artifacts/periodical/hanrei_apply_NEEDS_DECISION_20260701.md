# NEEDS_DECISION — 判例authority apply の期待行数不一致(head判断要)

- orch: ORCH-AUTHORITY-APPLY-20260701 / channel: apply / worker=ワーカーちゃん
- 発生箇所: A.判例authority TRUE_DUP 統合の**行数**。**journal(B)は正常・確定分349件・924行で完了**(本件はAのみ)。
- 種別: 想定外差分(silent禁止 → 停止して head へ)。安全規約 §29/§34 準拠。
- 状態: **候補は生成済みだが `_PROPOSAL` 名で保留**。live/canonical/元2ファイル/v14 は不変(非破壊)。

## 現状(deterministic self-verification 済・再現可能)

発注書は「TRUE_DUP 1,038 → 212,602−1,038 = **211,564行 期待**」としているが、
preview の TRUE_DUP 1,038 行を**正しく重複統合すると distinct 削除は 614 行**で、候補は **211,988行**になる。

### なぜ 1,038 ではなく 614 なのか(2点の機械的事実)

1. **pure_identical 850 は「850削除」ではなく「425物理ペア(=425削除)」**
   - preview の pure_identical 850 は、**同一の物理ペアが DUP_HANREI_ID と DUP_IDENTITY_KEY の両issueで二重計上**されている。
   - 実測: DUP_HANREI_ID(600) のうち **425** は 2行が同一 identity_key を共有し、その identity_key が **DUP_IDENTITY_KEY(438) 側の425キーと一致**(＝同じ2行を指す)。両issueで同一判例IDを共有=完全重複行。
   - 425ペア → keep1/remove1 = **425削除**(850ではない)。
2. **DUP_IDENTITY_KEY に size-3 群が1件**
   - key=`名古屋地|20190926|h31(わ)451`、判例ID=`28274161/62/63` の3行が(判例IDのみ差の)完全重複。3→1 で **2削除**。

内訳(distinct物理群 613 / 削除614):
| 種別 | preview行 | 物理群 | 削除行 |
|---|---|---|---|
| pure_identical | 850 | 425 | 425 |
| docket_consolidation | 169 | 169 | 169 |
| field_inconsistency | 6 | 6 | 6 |
| normalized_equal(identity-only) | 13 | 13 | 14(内1群がsize-3) |
| **計** | **1038** | **613** | **614** |

212,602 − 614 = **211,988**。

### 正しさの傍証(強い一致)
- 正しく統合後の候補で **identity_key 重複(非空)= 444 → 6 に減少**。
- 残る **6件は DISTINCT(統合禁止・held)の6件と完全一致**。＝「触ってはいけない6件」だけが残り、TRUE_DUPは過不足なく解消。これは 614 が正解で、1,038 が二重計上由来の誤りであることを示す。
- 判例ID重複 600→**0**、court化けcourt_key **0**、REDERIVABLE 22行修正済(15 court_key)。

## 論点
発注書の「211,564(=1,038削除)」は preview 行数をそのまま物理削除数と見なした**算術上の重複計上**と判断。
正しい重複統合の候補は **211,988(614削除)**。どちらを正本の期待値とするか head の確認が要る。

## 私の見解
- **211,988(614削除)が正しい**。preview の pure_identical は二重issueで計上されており、850削除は「実在する別判決を消す過削除」になり不可(データ破壊)。
- 生成済み PROPOSAL 候補 `判例_identity_keys_vnext_candidate_20260701_PROPOSAL.csv`(211,988) は上記regを全て満たす。head 受入検査で妥当なら、これを正式 `..._vnext_candidate_20260701.csv` に採用可。

## 不確かなこと
- 発注書 §29「判例1,053件相当」= TRUE_DUP物理群613 + REDERIVABLE15 + …の意図か、preview行1038+15=1053の意図か。後者(preview行数基準)なら「変更操作1053件」は満たすが「削除行数」は614。用語(件数=preview行 / 削除=行)の定義確認要。

## head への1入力(A/B/C)
- **A.** 211,988(614削除)を正本期待値として承認 → PROPOSAL を正式候補名にrename、段2(owner GO)へ。**(推奨)**
- **B.** 211,564 の再確認が要る(発注の算術見直し) → head が期待値を訂正して再発注。
- **C.** 別途 GPT Pro 監査に回してから確定。

> 添付: PROPOSAL候補・`hanrei_apply_changelog_20260701.csv`(全614削除+22 REDERIVABLE の before/after)。
> 非破壊: 元 `判例_identity_keys_20260605.csv`/`..._backfill6yr_20260617.csv` は読取専用で不変。
