# レビュー票 — source registry 追加候補10件（owner 確認用）

- 対象: `alo_source_registry_proposed_additions_20260620.jsonl`（Box 2299548232193 / repo）
- 文脈: 原本想定41行 − 再構成31行 = **欠落10行**の充足候補（should_fix#1）。**これらは原本復元ではなく新規候補**。
- 確認後: `yes` → 正式採用（`recon_status` を `accepted_addition` へ昇格し source registry 本体へマージ）。`no` → 除外。`modify` → 出口分類等を訂正。
- 出口ポリシー（AC-3）: `can_global_index = open ∧ public`。商用ライセンス・有償は **false**（機密ではなく再配布制約）。

## 記入欄（各行 yes / no / modify＋コメント）

| # | source_system | 内容 | 提案 redistribution | can_global_index | 判定(yes/no/modify) |
|---|---|---|---|---|---|
| 1 | `kakyu-saibansho-hp` | 下級裁判所 裁判例（裁判所HP） | public | **true** | ☐ |
| 2 | `chizai-kosai-hp` | 知的財産高裁HP 裁判例 | public | **true** | ☐ |
| 3 | `shomu-geppo` | 訟務月報（法務省） | restricted | false | ☐ |
| 4 | `lexdb-tkc` | LEX/DB インターネット（TKC） | commercial_licensed | false | ☐ |
| 5 | `westlaw-japan` | Westlaw Japan | commercial_licensed | false | ☐ |
| 6 | `hanrei-jiho` | 判例時報 | commercial_licensed | false | ☐ |
| 7 | `roudou-hanrei` | 労働判例（産労総研） | commercial_licensed | false | ☐ |
| 8 | `roukei-soku` | 労働経済判例速報（経団連） | commercial_licensed | false | ☐ |
| 9 | `kinyu-shoji-hanrei` | 金融・商事判例（経済法令） | commercial_licensed | false | ☐ |
| 10 | `hanrei-chiho-jichi` | 判例地方自治（ぎょうせい） | commercial_licensed | false | ☐ |

## 確認ポイント（判断材料）
- **1・2（公的HP）だけ global index 可**。残り8は商用/有償ゆえ index 不可（出典・引用は可、本文の global 配布は不可）。
- **契約有無**: 4〜10 のうち事務所が実際に購読/契約しているものは？（契約していない source は `no`、または `subscribed=false` 注記で identity 補助のみ）。
- **重複**: 既存31行（D1/判タ/判秘/LIC）と機能重複する商用DB（LEX/DB・Westlaw）は、採用方針（多重 source 許容か一本化か）を要決定。
- **欠落の真因**: もし原本10行が「裁判所支部別 source 細分」や「同一機関の record-level 分割」だった場合、本候補（別 source 主体）とは別物。**原本がローカルから出た場合は原本優先**で差し替え。

## 反映手順（yes 確定後・私が実施）
1. yes 行を `recon_status: accepted_addition` で `alo_source_registry_seed` 本体へマージ（generator に ACCEPTED リスト追加 → 再生成）。
2. `check_forum_registry_seed.py` K4 突合の対象集合は forum（準司法23）と独立なので影響なし。
3. DD-CASE-001 accepted §4 should_fix#1 を closed に更新。
