---
request_id: DD-TOCADOPT-001-IMPL-REAUDIT2
topic: 統一TOC採用ルール実装 v0.3.0 再々監査 (REAUDIT MODIFY_REQUIRED の証拠付き是正)
gate: implementation_review
supersedes: なし
parallel_related: [DD-TOCADOPT-001, DD-TOCADOPT-001-IMPL, DD-TOCADOPT-001-IMPL-REAUDIT]
current_governing_result: DD-TOCADOPT-001-IMPL-REAUDIT = MODIFY_REQUIRED (2026-06-17, GPT-5.5)
result_expected_filename: DD-TOCADOPT-001-IMPL-REAUDIT2_result.md
status: queued
queued_date: 2026-06-17
守秘: 設計・状態語彙・件数レベルのみ。実依頼者データ本文は含めない。合成データのみでテスト。
---

# DD-TOCADOPT-001 実装 v0.3.0 再々監査 (REAUDIT 指摘の証拠付き是正)

## 0. 前回 REAUDIT の核心と今回の対応

前回 REAUDIT は「green だけでは足りない / **構造分離を gate で保証せよ** / N1 を blocker 昇格 /
PASS には **commit・diff・敵対テスト・baseline export・equivalence report・N1 仕様**の証拠を出せ」。
→ 全要求を**証拠付き**で満たした。本書はその証拠インデックスである。

HOLD 継続・report-only・書込ゼロ・合成データのみ。

## 1. PASS 条件への証拠対応 (前回 §PASS条件 を1対1で充足)

| 要求された証拠 | 所在 |
|---|---|
| blocker ごとの修正コミット一覧 | 本書 §2 (commit `45ab9a7` = 初回是正 / `72df9a8` = REAUDIT是正) |
| policy diff | `git diff 6e2700d 45ab9a7 -- data/toc_merge_policy_unified_DRAFT.json` (rules 廃止明記) |
| engine diff | `git diff 6e2700d 72df9a8 -- scripts/toc_adopt.py` (+425 then +139 行) |
| gate diff | `git diff 6e2700d 72df9a8 -- scripts/toc_adopt_gates.py` (gate1 強化 + gate8 新設) |
| synthetic adversarial tests | `tests/golden/.../synthetic_multisource.jsonl` 12 シナリオ / `tests/test_tocadopt.py` 272 checks |
| baseline export sample | `docs/dd/evidence/tocadopt_reaudit/baseline_export_sample.json` |
| baseline equivalence report | `docs/dd/evidence/tocadopt_reaudit/baseline_equivalence_report.json` (gate1.pass=true) |
| N1 book-envelope / node-lane 仕様 | `docs/dd/20260617_DD-TOCADOPT-001-IMPL_N1_envelope_lane_spec.md` |
| (追加) 4-lane + envelope の全冊サマリ | `docs/dd/evidence/tocadopt_reaudit/lane_envelope_summary.json` |

## 2. blocker → 是正 → 証拠 (前回 §blocker を1対1で充足)

| # | 前回 blocker | 是正 | 検証 (test/gate) |
|---|---|---|---|
| N1 | book 単位 vs node 単位 adopt 未分離 | **二層化**: book-envelope(apply単位/apply_target=accepted_node_set) + node-lane 4値排他。仕様書を追加 | `gate8_lane_separation` / test `N1/*` (projection==accepted・1node1lane・envelope整合) |
| 1 (C1) | snapshot hash 無し node を accepted 不可 | 欠落は **non_adoptable レーン** (hard blocker)。捏造 hash 廃止。accepted は実 sha のみ | test `C1` (non_adoptable_node_count==1 / blocker present) |
| 2 (C4) | partinfo kind filter | contents のみ採用候補・volume_structure=**rejected**・mixed_small=**pending** を実装 | scenario `partinfo_volume_structure`(rej=1) / `partinfo_mixed_small`(pend=1) |
| 3 (D1/D2) | 非合議/HR を accepted に混ぜない・AND 化 | accepted は consensus∧provenance のみ。adoptable = 5 名前付き条件 AND | `gate8` (3)(4) / test `D2`・envelope.conditions |
| 4 (E1) | legacy rules と append_missing_only の関係 | policy で `replace_if_higher_source=false`・`_deprecated` 明記 (廃止) | policy diff / `confidence_usage` も明記 |
| 5 (F2) | baseline 比較が sha のみ | gate1 を **node集合・親子(parent)・page locator・base分布**まで比較 | `baseline_equivalence_report.json` / gate1 実走 (反転入力で同値) |
| 6 (A1) | priority 1点 anchor | **全ペア identity graph の connected component** で edition 集合。anchor は node 持ち源優先 | scenario `edition_exclude`(別版を component 外へ) |
| 7 (B1/B2) | granularity / simple-only を policy・engine・gate で一致 | 粒度=(深さ,ノード数,ページ被覆)複合。guard を engine と gate3 で同一 policy 値から読む。simple-only 張替え意味論を実装 | `gate3`(policy値参照) / scenario `guard_block`・`protected_base` |

## 3. 是正後の観測 (lane_envelope_summary.json より)

合成 12 冊で **adoptable=1** (`consensus3` のみ: 3 独立 origin 一致)。残り11冊は:
- `non_consensus_or_empty` (2源本は3 origin 裏取りに届かず pending_human_review)、
- `identity_unresolved` (別版/単一源を component 外)、
- `authority_human_review`、
- `non_adoptable_nodes_present` (`missing_source_hash`: snapshot 欠落 node が non_adoptable)。

→ accepted projection には **3源裏取り済 node のみ**が入り、保留・非採用・拒否は構造上分離。
gate8 がこの分離を機械保証する。

## 4. 今回の是正で残る自己申告 (正直開示・赤入れ対象)

- **N1-a (M)** apply_eligibility の `consensus_ok` を「non_consensus node が 0」と定義した。
  これは「全 node が3 origin 裏取り」を要求し、2源本は常に非 adoptable。安全側だが、
  **node 単位 apply (accepted node set だけ apply し book は partial-adoptable とする)** を許すべきか、
  という運用判断が残る (現状は book を all-or-nothing で adoptable 判定)。
- **N1-b (M)** lane 優先度を rejected>non_adoptable>pending>accepted で固定した。
  例えば「volume_structure かつ snapshot 欠落」は rejected に倒れ non_adoptable 計上されない。
  優先度の順序自体は妥当と考えるが、二要因 node の計上方針に異論があれば請う。
- **N1-c (L)** parent_id は accepted 列の深さスタック近似のまま (append node の親子は厳密でない)。
  baseline_export_sample の parent_id はこの近似値。
- **N1-d (L)** 敵対 fixture は title_collision / duplicate_origin / mixed_small / volume_structure /
  missing_hash の5種。循環親子・multi-offset・unicode 異形は未カバー。

## 5. 判定してほしいこと

1. N1 二層 (envelope/lane) と gate8 構造分離保証で **N1 blocker は解消**したか。
2. C1/C4/D1/D2/E1/F2/A1/B1/B2 の証拠 (§2) で各 blocker は閉じたか。
3. §4 N1-a (book all-or-nothing vs node 単位 apply) は **再 MODIFY 級か / NOTE 級か**。
4. PASS / PASS_WITH_NOTES に上げられるか。

HOLD 不変・report-only・合成データのみ。赤入れ歓迎。
