# DDSELFHEAL-C1 BodyShaRecompute write 候補パケット (owner 承認用・HOLD)

prepared: 2026-06-17
status: **C1 write は HOLD**。本パケットは T2(EDIDENT)+T1(corpus)+owner whitelist が揃った時点で
発火させる承認テンプレート。現時点では report-only の証拠提示のみ。
governs: `scripts/repair_sha.py` (BodyShaRecompute) / `scripts/repair_engine.py` / `tests/test_c1_readiness.py`
evidence_corpus: `tests/golden/repair/synthetic_corpus_30.jsonl` (合成 30冊・実依頼者データなし)

## 1. なぜ BodyShaRecompute が最初の C1 write 候補か

DDSELFHEAL-C0 PASS_WITH_NOTES の指名。4種の決定的 repairer のうち、BodyShaRecompute は
**canonical を書かず derived の `source_sha256` を resolved source_content から再計算するだけ**
(`repair_class = deterministic_no_canonical_write`)。raw(タイトル/PDF) は不変。最も影響範囲が狭い。

## 2. 安全証明 (合成 golden 30 実測・`test_c1_readiness.py` が CI 凍結)

BodyShaRecompute 対象 = 5冊。全 5 冊で:

| 不変条件 | 実測 |
|---|---|
| health_delta | **+5.1 (全5冊)** — 健全度を上げる (下げない) |
| 二度がけ no-op | True (冪等) |
| rollback 検証 | True (可逆・rollback bundle で原状復帰) |
| plan 決定的 | True |
| 新規 P0 defect | **0** (regression taxonomy: introduces_p0=False) |

engine 全体 (golden 30 / 4 repairer / 20 manifest): `writes_executed=0`・`all_no_op_second_run`・
`all_rollback_verified`・`all_health_non_decreasing`・`no_repair_introduces_p0`・`regression_free` = すべて True。

## 3. C1 write を阻む唯一の残条件 = T2 (EDIDENT) ← 重要

C1 phase + owner whitelist + rollback bundle を与えても、apply gate 7 条件のうち
**5 つは通過済**だが 2 つが残り write は依然不許可:

| gate | 状態 |
|---|---|
| whitelist_required | ✅ passed (whitelist 指定時) |
| pdf_authority_qualified | ✅ passed |
| rollback_bundle_present | ✅ passed |
| decision_log_append_only | ✅ passed |
| all_nodes_accounted_for | ✅ passed |
| **edition_identity_resolved** | ❌ refused ← **T2 (DD-EDIDENT-001 ratify+統合) 依存** |
| **no_unresolved_conflict** | ❌ refused ← conflict 解消依存 |

→ **BodyShaRecompute の C1 write 解禁は、EDIDENT が ratify+統合されて
`edition_identity_resolved` が立つこと**が前提。これは `test_c1_readiness.py` が
`edition_identity_resolved ∈ refusals` として CI で固定している。EDIDENT 監査
(`DD-EDIDENT-001-IMPL`) が通り pipeline 統合された時点で、この gate が解け本候補が発火可能になる。

## 4. owner 承認テンプレート (T2/T1 充足後に記入)

```
C1_unlock:
  repair_class: deterministic_no_canonical_write
  repairer: body_sha_recompute
  whitelist_isbns: [ ... ]          # owner が明示許可した ISBN のみ
  preconditions:
    - edition_identity_resolved: true   # T2 EDIDENT 統合後に充足
    - no_unresolved_conflict: true
    - rollback_bundle_present: true
    - real_golden_30_validated: true    # T1 実 corpus 到着後
  acceptance:
    - health_delta > 0 (全対象)
    - no_op_second_run = true
    - rollback_verified = true
    - no_repair_introduces_p0 = true
  owner_signoff: <date / owner>
```

## 5. 残ブロッカー (本パケットを発火できない理由)

| ブロッカー | 種別 | 解消条件 |
|---|---|---|
| T2 DD-EDIDENT-001 ratify+統合 | 監査中 | `DD-EDIDENT-001-IMPL` GPT 監査 → owner ratify → pipeline 配線 |
| T1 TOCADOPT 実 corpus | 実データ待ち | ALOBookDX 631クラスタ到着 → 実 30冊 golden 化 |
| owner whitelist | owner 判断 | repair_class ごとの ISBN 許可リスト |

## 6. HOLD 境界

C1 actual write / canonical mutation / RDB write / production apply = **HOLD**。
本パケットは承認テンプレートと安全証拠の事前提示のみ。現状の engine は `writes_executed=0` を保証。
