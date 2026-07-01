# RESULT — ORCH-AUTHORITY-APPLY-20260701(確定分 authority 反映・候補v-next生成)

- orch_id: ORCH-AUTHORITY-APPLY-20260701 / channel: apply / hand: ワーカーちゃん(Worker Claude Code)
- 種別: **候補(v-next)生成のみ**。live/canonical昇格なし。router: worker=draft_write 上限に適合。
- 継続性(DD-ORCH-CONTINUITY-001 v0.3): read_log_commit=`c659b12` / read_digest_id=`HOL-20260701-007` /
  read_standing_ids=`HOS-001,HOS-002,HOS-003,HOS-004,HOS-005,HOS-006,HOS-007`(global_required: 001/002/003/005 を全読)
- 非破壊確認: 元 `判例_identity_keys_20260605.csv`(mtime 6/8)・`..._backfill6yr_20260617.csv`(mtime 6/17)・`v14`(git clean)
  すべて**読取のみで不変**。held項目には一切未タッチ。

## サマリ
| 対象 | 状態 | 出力 |
|---|---|---|
| **B. journal authority** | ✅ **完了**(確定349件・924行・全reg合格) | `d1_journal_issn_authority_ALL_resolved_v15_candidate.csv` + `journal_apply_changelog_20260701.csv` |
| **A. 判例 authority** | ⚠️ **NEEDS_DECISION で停止**(期待行数の算術不一致) | `..._vnext_candidate_20260701_PROPOSAL.csv`(211,988) + `hanrei_apply_changelog_20260701.csv` + `hanrei_apply_NEEDS_DECISION_20260701.md` |

---

## B. journal authority(完了)

適用(確定分349件・= 発注 §29「journal349件」一致):
- **NORMALIZE 341**: journal_canonical を正規化名へ(in-place・末尾サフィックス除去等)。
- **MERGE_TO_EXISTING 7**: 実在誌へ統合(source行削除・article_count 合算・target note に `merged<-… apply_20260701` 退避)。
- **ISSN_RESOLVED 1**: 税理 → key_type=issn / key_value=`0514-2512` / source=`ndl_sru:apply_20260701`。

除外(held・未タッチ): MISASSIGN 1 / NEEDS_DECISION 1(norm) ＋ AMBIGUOUS 11 / ISSN_NOT_EXIST 10(NCID維持) / COLLISION 2(jissn)。

### 回帰検査(全合格)
| 検査 | 結果 |
|---|---|
| 候補行数 | **924**(931−7 merge) ✓ 一致 |
| journal_canonical 重複 | 0(924 unique) ✓ |
| 変更件数 = 確定分349 | NORMALIZE341+MERGE7+ISSN1=**349** ✓ |
| dup-ISSN(同ISSN→別誌)非増加 | **22 → 18**(減少) ✓ |
| NORMALIZE 後 新規過分割 | **0**(normalized_name は全て v14 未存在・衝突0・1:1 rename) ✓ |
| 税理 ISSN=別誌未使用 | `0514-2512` 使用は税理のみ ✓ |

- 備考(head確認・軽微): 税理行の `status` は発注指定3フィールド外のため `seed_ncid_fallback` のまま(key_type=issn と字面不整合)。発注厳守で status 未変更。要すれば段2で `resolved` 等へ。

---

## A. 判例 authority(NEEDS_DECISION で停止)

**journal と独立の A のみ**の停止。詳細は `hanrei_apply_NEEDS_DECISION_20260701.md`。

### 争点(deterministic self-verification 済・再現可能)
発注 §15 は「TRUE_DUP 1,038 → 212,602−1,038 = **211,564行 期待**」。
しかし preview の pure_identical 850 は **同一物理ペアの二重issue計上**(DUP_HANREI_ID 425 と DUP_IDENTITY_KEY 425 が同一2行)で、
実 distinct 削除は **425**。加えて DUP_IDENTITY_KEY に size-3 群1件(3→1=2削除)。
→ **正しい統合の distinct 削除は 614 行 = 候補 211,988 行**。

### 生成物(PROPOSAL・保留)
安全規約(§32-34)により、期待値を満たさぬ候補を正式名で確定しない。正しい統合結果を `_PROPOSAL` 名で保留出力:
`判例_identity_keys_vnext_candidate_20260701_PROPOSAL.csv`(211,988行)。

### 回帰検査(PROPOSAL候補・行数以外は全て良好)
| 検査 | 結果 |
|---|---|
| 候補行数 | **211,988**(614削除)。発注期待211,564(1,038削除)と**不一致→停止** |
| 判例ID重複 | **600 → 0** ✓ |
| identity_key重複(非空) | 444 → **6** ✓(残6件=DISTINCT held の6件と完全一致=TRUE_DUP過不足なく解消の傍証) |
| court化けcourt_key | **0**(15 court_key・22行を復元) ✓ |
| REDERIVABLE 効果 | court_key 22行を復元(4日市簡→四日市簡 等)。**court化け由来 court_miss の上限22件を直接解消**。full L5 court突合の再計算(read-only)は段2で(現時点はcourt化け=0を確認) |
| 変更件数 | dedup物理群613 + REDERIVABLE15 = 628 操作 / preview行基準では 1038+15=1053 |
| REDERIVABLE∩dedup 重複 | 0(独立・安全) |
| 元2ファイル | 読取のみ・不変 ✓ |

### 採用値ルール(§13 厳守・changelog に全614+22行 before/after)
- pure_identical(425群): どちらでも→先頭保持。
- docket_consolidation(169群): **full docket 採用**(長い docket_key の行を保持)。
- normalized_equal(13群): 同 identity_key・最小判例ID 保持(内1群 size-3)。
- field_inconsistency(6群): **正しい court_key 採用**(支部粒度の詳しい・非化けを保持。例 広島高松江支 / 津地四日市支)。

### head への1入力(A/B/C)
- **A(推奨)**: 211,988(614削除)を期待値承認 → PROPOSAL を正式候補にrename・段2(owner GO)。
- **B**: 211,564 の算術を head 再確認 → 期待値訂正して再発注。
- **C**: GPT Pro 監査へ回してから確定。

---

## 成果物一覧

### commit/push 済(本ブランチ wk-apply)= レビュー正本
- `journal_apply_changelog_20260701.csv`(356・全349変更の before/after 行)
- `hanrei_apply_changelog_20260701.csv`(636・全614削除+22 REDERIVABLE の before/after 行)
- `hanrei_apply_NEEDS_DECISION_20260701.md` / `ORCH-AUTHORITY-APPLY_result_20260701.md`(本書)
- 入力 preview 3点(`hanrei_authority_fix_preview_v0.1.csv` / `journal_authority_norm_preview_v0.1.csv` / `journal_issn_resolve_proposal_v0.1.csv`)
- 決定論的再生成スクリプト `apply_scripts_20260701/build_journal.py` / `build_hanrei.py`

### ローカル生成・未commit(理由: 大容量 authority blob の repo 方針)= 再生成可能
- `d1_journal_issn_authority_ALL_resolved_v15_candidate.csv`(924) — **`.gitignore:6` が `..._resolved_v[0-9]*.csv` を除外**(v14 基底は force-add 済の例外)。repo 方針を尊重し force-add せず。`python3 apply_scripts_20260701/build_journal.py` で再生成。
- `判例_identity_keys_vnext_candidate_20260701_PROPOSAL.csv`(211,988・44MB・**保留**) — 巨大 derived blob のため未commit。`python3 apply_scripts_20260701/build_hanrei.py` で再生成。head の A/B/C 決定後に正式名で確定。

> changelog に全変更の before/after を記録済のため、候補CSV未commitでも head 受入検査は changelog+preview+script で完全に可能。候補実体が必要なら上記1コマンドで再生成(元2ファイル・v14 は読取のみ)。

P##番号不使用。live/canonical 昇格・DB投入・外部公開は未実施(owner GO 案件・HOS-003)。
