# P1: 雑誌 staging レーン分類（lane_hint）read-only 成果物

```yaml
artifact: P1_lane_split
wo: WO-PERIODICAL-ISSN-SEED-EXPANSION-20260618 (v0.2)
generated_at: 2026-06-19 JST
source: staging_periodical.issue_stage (2,847行 / dataset_version DD-PERIODICAL-001_v0.2_20260611)
gate: READ_ONLY (SET TRANSACTION READ ONLY / production mutation 0 / DDL 0)
note: 本成果物は read-only SELECT の集計。issue_stage への列追加・更新は行っていない（監査条件2,3遵守）。
```

## lane_hint 判定規則（v0.2 §C 確定）

評価順: (1)unknown[journal_norm空] → (2)newsletter[`newsletter|ニュースレター`] → (3)yearbook[`年版/令和N年/平成N年/20XX年版`] → (4)real_journal[残り]

## 分類結果（全2,847号）

| lane_hint | 号数 | issn済 | 未issn(jp:等) | unassigned(id=NULL) | 誌数 | 扱い |
|---|--:|--:|--:|--:|--:|---|
| real_journal | 2,740 | 1,923 | 798 | 19 | 58 | ★ISSN seed 対象母集団 |
| yearbook | 91 | 0 | 3 | 88 | 83 | 書籍/yearbookレーンへ（seedしない） |
| newsletter | 14 | 0 | 10 | 4 | 3 | ISSN無しが通常（seedしない） |
| unknown | 2 | 0 | 0 | 2 | — | 要review |

- seed対象 = real_journal の未同定 **約817号**（798 jp: + 19 unassigned）/ 既confirmed 11誌を除く **47誌**。

## provisional_uri フラグ（必須パッチ P-1）

- `issn:%` 形式 = `provisional_uri=false`（canonical）
- `jp:%` / id=NULL = `provisional_uri=true`（仮・後続で置換され得る）
- 本フラグは P4 の `issue_id_v2` 出力・全view・全レポートに必須列として持たせる。

## lane_hint 漏れ（v0.2追補・要ルール強化）

`real_journal` に書籍（年度版・体系書）が混入していることを確認。seed対象から除外し `needs_review` 隔離:

- 現代法律実務の諸問題(下)<昭和62年度版> / <昭和63年度版>
- 設例と申告書記載例で理解する[最新]賃上げ促進税制のすべて2024-2027年度版（表記揺れ2件）
- 事業者必携 訪問販売・通信販売など…最新特定商取引法と消費者契約の実践法律知識
- 知財侵害の民事案件の審理における懲罰的賠償に関する司法解釈他

→ P1確定版では「`年度版` パターン」「書名長 > 閾値」を yearbook 寄せ＋`needs_review`。自動ISSN付与の対象にしない。
