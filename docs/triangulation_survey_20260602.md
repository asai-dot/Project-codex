# 法律用語 3点測量（triangulation）— 2026-06-02 開始

指示「JLT語彙 × 学陽書房OCR × 三省堂法律学用語辞典 の3点測量を開始」への着手記録。

## 0. 第3脚の実体（要 head 確認）
当初指示は「**三省堂**法律学用語辞典」だが、Box の構造化辞書実体は **有斐閣『法律用語辞典』
(ISBN 9784641000308)** の `term_dict/sources/dict_ocr/all_entries.jsonl`。三省堂版は
構造化データとして**未取得**（PDF/自炊スキャンも無し）＝必要なら要OCR。本測量は実在データ＝
有斐閣で実施。三省堂が必須かは head 判断。

## 1. 3脚（すべて実体ベース）
| 脚 | 一意見出し語 | 出所 / provenance |
|---|---|---|
| JLT v19.0 | **3,869** | byte-exact 正典 `jlt_dict_v19.0_utf8.csv`（sha256 3a2b0612…）→ `build_jlt_authority.py`。term-set sha256 `51d767a0…` |
| 学陽 法令用語辞典 | **2,652** | byte-exact `final_hourei_jiten.md`（4,298,886 B）→ `phase1_5_parse_md.py`。収録2,603と+1.9%整合 |
| 有斐閣 法律用語辞典 | **13,280** | 構造化済 `dict_ocr/all_entries.jsonl`（file 2185088113728, 13,344行）の headword |

## 2. 在不在マトリクス（union 15,654）
| 組合せ | 件数 | 解釈 |
|---|---|---|
| **JLT+学陽+有斐閣** | **922** | 3源一致＝最高確度の canonical core |
| JLT+有斐閣 | 1,137 | |
| 学陽+有斐閣 | 1,062 | |
| JLT+学陽 | 104 | |
| 有斐閣のみ | 10,159 | 有斐閣は最大(13,280)。網羅が広い |
| JLTのみ | 1,706 | JLTは日英対訳語彙で範囲が異なる |
| 学陽のみ | 564 | 学陽固有 or 抽出 artifact（下記） |

## 3. 方法
exact 集合演算 ＋ delete-1（SymSpell式）索引による ed≤1 近接検出。`phases/triangulate_terms.py`。

## 4. 正直な所見 — near-miss は誤り検出器として弱い（自動適用禁止）
- ed≤1 近接は raw 33,735 / 学陽起点focus 3,421 出るが、**大半は正当な別語**：
  `公立大学法人`≠`国立大学法人`、`先渡取引`≠`先物取引`、`勤労条件`≠`労働条件`、
  `施行規程`≠`施行規則`。日本語法令用語は1字違いの稠密近傍を持ち、**編集距離だけでは
  OCR化けと別語を分離できない**。→ `near_miss_review_queue` は**レビュー候補**に留め、
  自動修正は禁止（review_queue 129件の「派生物を正本扱い」轍を踏まない）。
- 真の garble 局在は **次の本命**（§6）で行う。

## 5. 学陽脚の校正（実 md で2回）
3,102 → 2,820 → **2,652**。除去した artifact：
- `類語`(×86) 等サブセクション見出し、番号点 `1)`〜`6)`、`例N)`、書名・凡例見出し。
- 定義テキストが見出し化したもの（`1) 事業要件` 等、番号始まりを先頭一致で除外）。
- 残課題：md に**ページマーカ無し**→索引(p.815-838)分離が不可。empty-def 135件(5.0%)。
- ※ellipsis パターン語（`…してはならない`等）は JLT にも在る正当語として保持。

## 6. 次の本命：定義一致ゲート（3点測量の核）
見出し語 ed≤1 **かつ 定義文が高類似** の時のみ garble と判定する。学陽・有斐閣とも
定義文を保持（gakuyo_all_entries.jsonl / 有斐閣 all_entries）→ 実装可能。これにより
「3源中2源で一致・1源で1字違い＋定義一致」= 高確度の誤り局在が得られる。

## 7. 成果物
- `data/gakuyo/gakuyo_all_entries.jsonl`（2,684 entries＝学陽 Phase1.5 出力）/ `gakuyo_terms.txt`（2,652）
- `data/triangulation/`：`core_all3_20260602.txt`(922) / `gakuyo_only_20260602.txt`(564) /
  `yuhikaku_terms.txt`(13,280) / `near_miss_review_queue_20260602.jsonl`(3,421, **noisy**)
- `phases/triangulate_terms.py`

## 8. 未決（head 判断）
1. 第3脚は三省堂か有斐閣か。三省堂必須なら要OCR（現状は有斐閣で代替実施）。
2. 学陽 `all_entries` は cloud 産出（byte-exact md 由来）。Windows CC の Phase1.5 計画と
   二重化しないための正本化（同一決定的パーサなので結果は再現一致するはず）。
3. Box 一時コピー `_TMP_yuhikaku_all_entries_read.txt`（file 2259970602095, docs/alo）は
   読取用の派生コピー。削除可。
