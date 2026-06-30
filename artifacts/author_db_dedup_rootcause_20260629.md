# 著者DB 重複の根本原因と名寄せ方針 (2026-06-29)

## TL;DR
著者DB(`authority.person` 128,081人)の重複のほぼ全ては **KAKEN scholar の
CiNii識別子トレース取込**に起因。「科研をリッチに取れ」の指示に対し、実際に
入ったのは**識別子層のみ**で、所属機関・研究分野・科研プロジェクトは未取込。
ただし `researchmap` が人物固有キーとして使え、**17,507行→1,402人**を
安全に名寄せ可能(誤紐付けなし)。

## スコープ(修正後)
- `authority.person`: 128,081行 → 正規化名 106,626種
- 重複クラスタ(同名>1 person_id): 2,832クラスタ / 24,287行 / 最大208
- ソース別:
  | source | 人数 | 重複行 | 所属の中身 |
  |--------|------|--------|-----------|
  | scholar:kaken | 73,155 | ~22,637 | "CiNii scholar identifier anchor"(プレースホルダ) |
  | lawyer:nichibenren | 48,690 | 875 | 弁護士会(実値) |
  | judge:yamanaka | 6,236 | 24 | 裁判所+在籍年(実値) |

## 根本原因(実データで確定)
`person_affiliation` 全KAKEN行: `organization_name='CiNii scholar identifier
anchor'`, `organization_type='scholar_identifier_anchor'`,
`source_system='cinii_identifier_traces'`。

`person_history` のKAKEN取込内容:
- `scholar_nrid` (source: cinii_identifier_traces) 73,155 — **トレース毎に別値**
  (星野豊=208 person_idで208 distinct nrid)。これが断片化=重複の元凶。
- `cinii_literature_count` 73,155
- `researchmap_profile` 17,613 — **人物固有**
- `orcid_id` 279 — 人物固有

→ 取込は **CiNii の identifier-trace 層**(名前+トレースID+外部リンク)を
person_id 化したもの。CiNiiは1人を多数アンカーに断片化するため、同一研究者が
最大208レコードに膨張した。**所属機関・研究分野・科研課題は取得されていない**
(所属は定数プレースホルダ)。これが「リッチに取れたはず」とのギャップ。

## 名寄せキーの評価
| キー | 被覆(重複scholar行) | 収束力 | 安全性 |
|------|------|--------|--------|
| scholar_nrid | 100% | **無し**(トレース毎にユニーク=重複の原因) | × |
| **researchmap** | 17,516 / 22,637 | 22,637→約1,415人 | ◎(固有) |
| orcid_id | 279 | 高 | ◎(固有) |

安全性検証: 全1,513 researchmap中、複数正規化名に跨るのは6件のみ(max2名)
=表記揺れ(漢字/ローマ字・空白)の統合であり誤りではない。

## 実施した安全な名寄せ(本コミット)
`artifacts/author_dedup_kaken_researchmap_20260629.tsv`
- researchmap共有(>=2 person_id)の **1,402グループ / 17,507 person行**
- → **1,402 canonical person**(16,105行を重複解消)
- canonical選定: cinii_literature_count最大 → 1始まりID → person_id最小
- 名変種跨ぎ6グループは `confidence=review_name_variant` でフラグ
- これは candidate レベルの **提案マップ**(DB書込なし、監査ゲートはHOLD)

## 残課題
1. **researchmap無しの重複 5,126行**: nridは使えない(トレース毎)、orcidも僅少。
   → 要エンリッチ。DB内に各person_idの `scholar_nrid` があるので、**KAKEN/CiNii
   研究者レジストリ(nrid)から所属機関・研究分野を再取得**すれば解消可能
   (盲目クロールでなく、保有識別子を鍵にした補強)。
2. **所属機関・研究分野の欠落(全KAKEN)**: 指示された"リッチ"取得の本体が未実施。
   researchmap URL(17,613)とnridを鍵に再取得するのが筋。
3. lawyer(875)/judge(24)の重複: 実所属あり。別途名寄せ可(小規模)。
4. 著作紐づきクラスタ(117): 別ワークフロー(著作ベース)で並行処理中。

## ガバナンス
全て candidate レベルの観測 artifact。DB書込/DDL/外部公開は実施せず。
researchmapによる統合提案も `claim_status=candidate` 相当で、確定は監査ゲート。
