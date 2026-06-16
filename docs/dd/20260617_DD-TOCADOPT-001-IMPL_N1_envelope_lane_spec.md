# DD-TOCADOPT-001-IMPL N1 仕様: book-envelope / node-lane 二層セマンティクス

status: implemented (report-only / HOLD 継続)
date: 2026-06-17
governs: `scripts/toc_adopt.py` (`adopt_book`)・`scripts/toc_adopt_gates.py` (`gate8_lane_separation`)
origin: DD-TOCADOPT-001-IMPL-REAUDIT (GPT-5.5) N1 を blocker 昇格 → 本仕様で確定。

## 0. 原則

採用は **二層**で表現する。apply の単位 (book) と、採否の単位 (node) を混同しない。
canonical apply の単位は **book-level envelope**。ただし apply 対象は **accepted node set のみ**。
pending / human_review / non_adoptable / rejected の node を accepted projection に混ぜてはならない。

## 1. node-level lane (4 値・排他)

各 TOC node はちょうど1レーンに入る。割当は**優先度順** (上が強い)。

| lane | 意味 | 入る条件 (実装) | apply 対象か |
|---|---|---|---|
| `rejected` | 構造上 TOC 本文でない | partinfo `kind ∈ reject_kinds` (volume_structure) | ✗ (step3 で除外) |
| `non_adoptable` | provenance 完全性が無く採用不能 | `source_snapshot_missing` (source_sha256 欠落) | ✗ |
| `pending_human_review` | 採用余地はあるが人手判断が要る | `non_consensus` / partinfo `mixed_small` / `needs_offset` | ✗ (人手承認後に再評価) |
| `accepted` | 合議成立かつ provenance 健全 | 上記いずれにも該当せず consensus 成立 | ✓ |

割当の優先度: `rejected` > `non_adoptable` > `pending_human_review` > `accepted`。
1 node が複数要因を持つ場合 (例: 非合議かつ offset 不明) は **最も強いレーン1つ**にのみ入り、
`lane_reason` に全要因を列挙する。

不変条件 (gate8 が保証):
- `projection` は `lanes.accepted` と同一実体。
- accepted ∪ pending ∪ non_adoptable の `toc_node_id` は重複なし (各 node は1レーン)。
- accepted の全 node が `consensus=True` かつ `source_hash` 実値かつ `snapshot_missing=False` かつ `needs_offset=False`。
- non_adoptable の全 node が `snapshot_missing=True`。
- rejected の `title_norm` は accepted/pending に出現しない。

## 2. book-level envelope (apply 単位)

```
envelope = {
  edition_identity:   step1 の同一性 status,
  base_source:        基底源,
  projection_sha:     accepted node 集合の順序非依存 sha,
  policy_version:     実装契約 policy version,
  base_source_distribution: accepted の由来源分布,
  apply_unit:         "book_envelope",
  apply_target:       "accepted_node_set",     # ← apply するのは accepted のみ
  apply_eligibility:  { adoptable, conditions, blockers },
}
```

### apply 可否 (`adoptable`) = 5 名前付き条件の AND

| 条件 | True の定義 | False 時 blocker |
|---|---|---|
| `identity_ok` | step1.status ∈ APPLY_OK (resolved_same/manual_same) | `identity_unresolved` |
| `provenance_ok` | accepted の全 node が source_hash 実値 | `provenance_incomplete` |
| `consensus_ok` | accepted≥1 かつ non_consensus node が 0 | `non_consensus_or_empty` |
| `authority_resolved` | book authority ≠ human_review | `authority_human_review` |
| `no_hard_blocker` | non_adoptable node が 0 | `non_adoptable_nodes_present` |

`adoptable = identity_ok ∧ provenance_ok ∧ consensus_ok ∧ authority_resolved ∧ no_hard_blocker`。

## 3. なぜ二層か (設計根拠)

- **apply の原子性は book 単位**: projection_sha・base 源・policy version は book で1つ。
  部分 apply で book の projection が不整合になるのを防ぐ。
- **採否の粒度は node 単位**: 1 冊の中に「3源裏取り済の章」と「1源のみ・offset 不明の節」が
  混在する。これを book 単位の可否だけで扱うと、良い node を巻き添えで捨てるか、
  弱い node を巻き込んで採用するかの二択になり、どちらも不正。
- したがって **envelope が apply 可否を握り、apply 対象は accepted node に限定**する。
  pending は人手承認レーン、non_adoptable は provenance 修復待ち、rejected は構造除外。

## 4. HOLD 境界

本仕様は **投影層の表現と検査のみ**を定義する。production apply / canonical projection /
RDB write / source snapshot mutation / policy 本番切替は **HOLD 継続**。本実装は何も書かない。
