# 判例オブジェクト 俯瞰 ＆ production 移行チェックリスト（Mac CC 引き継ぎ）

- 作成: 2026-06-23 JST ／ 番頭: Claude Code (remote)
- 目的: 判例オブジェクト（判例ノード／ID確定／精度）の **accepted 設計一覧** と、**production へ進める際に Mac CC 側でやる作業** を1枚に集約。
- 原則: ここまでは **すべて設計 accept（design-level）かつ read-only**。production（DDL/DB write/canonical mint/serving/embedding/export）は **全て HOLD**。本書はその HOLD を解く順序と前提を示す。

---

## 1. DD インベントリ

### 1.1 エンティティ／ID（accepted）
| DD | 役割 | 状態 | accepted正本 Box | 設計本体 Box |
|---|---|---|---|---|
| DD-CASE-001 | 判例ノード母型（3軸分離 A1識別/A2解釈/A3出口・case_type正準enum） | **accepted v1.0** | 2297878432511 | 2295258030670 |
| DD-CASEID-001 | ID確定システム（特定とID確定の分離・自然キー＋名寄せ採番） | **accepted v1.0** | 2295209891981 | — |
| DD-CASEID-002 | 符号正規化 N1-N5 ＋ display romaji（2表分離・多docket） | **accepted v1.0** | 2302667391959 | 2302088591886 |
| DD-CASEID-003 | forum registry（forum_code 体系・123 seed・支部162保留） | **accepted v1.0** | 2302667982396 | 2301069549462 |
| DD-CASEID-005 | jufu 取込境界（identity可・出口遮断） | **監査投函中** | — | 2303458384177 |

### 1.2 精度レイヤ（accepted・①〜⑤）
| DD | 役割 | 状態 | accepted正本 Box |
|---|---|---|---|
| DD-CASEEVAL-001 | ①計測（false_merge_rate 主指標・gold＋ハード負例） | **accepted v1.0** | 2303436743437 |
| DD-CASEBIND-001 | ②false-merge ガード（G1-G6・gold で false_merge=0） | **accepted v1.0** | 2303444876411 |
| DD-CASECORROB-001 | ③多源コロボ（L1/L2/L3 分離・非merge・recall回収） | **accepted v1.0** | 2303438658002 |
| DD-CASECITE-001 | ④引用検証ゲート（V1-V8・ハルシネーションcite 0） | **accepted v1.0** | 2303436892293 |
| DD-CASEREVIEW-001 | ⑤サンプル監査（層化・drift→gold 閉ループ） | **accepted v1.0** | 2303439302089 |
| 精度 v0.2 notes closure | ①bcubed/②G6/④V8/⑤sample-size | **監査投函中** | 2303445523158 |

## 2. 不変則クロスリファレンス（恒久則・実装が守るべき拘束）
- **N-1**: `case_key`(判例) ≠ `alo_matter_id`(受任案件)。混在・相互代入・FK 禁止。
- **N-2**: `case_type` 定義は DD-CASE-001 が唯一。CASEID は参照のみ。
- **N-3**: 出口可否は DDCASESOURCE 一次所有。
- **N-4**: DD-CASE-001=母型 / CASEID-001=ID確定上流。重ねない。
- **AN-2**: merge 禁止＝別判断は別 case_key、関係は `alo_edges` link。
- **AC-3（出口）**: global egress は `confidentiality_class==open ∧ redistribution==public` のみ。jufu/商用/有償/matter は不可。
- **AN-4 / 精度**: false_merge が最大の害。precision 優先・初回 split 寄り。主KPI=`false_merge_rate`。

## 3. 実装インベントリ（repo `scripts/`・全 read-only・テスト green）
| script | 対応DD | テスト |
|---|---|---|
| `case_number_norm.py` | CASEID-002 | `test_case_number_norm.py` |
| `build_case_symbol_tables.py` / `check_case_symbol_tables.py` | CASEID-002 | C1-C9 |
| `build_forum_registry_seed.py`（Mac専用）/ `check_forum_registry_seed.py` | CASEID-003 | K1-K8 selftest |
| `case_eval.py`（+bcubed） | ① | `test_case_eval.py` |
| `case_bind_guard.py`（G1-G6） | ② | `test_case_bind_guard.py`（gold false_merge=0） |
| `case_corroborate.py` | ③ | `test_case_corroborate.py` |
| `case_cite_gate.py`（V1-V8） | ④ | `test_case_cite_gate.py` |
| `case_review_sample.py` | ⑤ | `test_case_review_sample.py` |
| `jufu_intake.py` | CASEID-005 | `test_jufu_intake.py` |
| `build_source_registry_seed_recon.py` ほか seed 群 | CASE-001 recon | — |
> 一括回帰: 各 `python3 scripts/test_*.py`（exit 0）。`test_case_precision_v02.py` で v0.2 note を一括検証。

## 4. production 移行チェックリスト（Mac CC・順序つき）

### P0 台帳・登録（マウント必須・単一書き手）
- [ ] accepted 各 DD を `DESIGN-01 登録簿` / `DD_REGISTRY.json` に `accepted_v1.0_with_notes`（recon は `recon_status` 併記）で登録。
- [ ] `_AUDIT_LEDGER.jsonl` に reflect/closed 追記、approval_queue カード clear（`alo_gpt_audit.py reflect <id> --apply`）。

### P1 データ確定（read-only 生成）
- [ ] `build_forum_registry_seed.py` を実行（local `hanrei.ttl`＋`判例一覧.csv`）→ seed123 生成、`check_forum_registry_seed.py` で K1-K8、再現ログ＋SHA を Box へ（RUNBOOK 完備）。
- [ ] 支部162 `romaji_TODO` を権威表で確定（独立検証必須）→ 再生成。
- [ ] CASEID-002 公式 doc（裁判所「符号の説明」）を **web で取得・version/hash 固定** → semantics の `pending_source_fixation`→`confirmed`（無いものは review 据置）。
- [ ] gold set 実構築：NII∩D1 12,661 正例＋ハード負例4型 → `case_eval` で baseline 計測。

### P2 閾値・KPI 確定（owner 判断）
- [ ] Tier A precision 目標（既定 0.99）と margin・信頼（既定 ±0.02/95%）を確定 → `required_sample_size`。
- [ ] unsure_rate KPI の許容値。
- [ ] D1-LIC 5,475 / OPAC 1,648 を実 link 化 → `case_corroborate` で recall 改善 vs false_merge=0 維持を計測。

### P3 production-readiness gate（G2・別審査）
- [ ] DDL（cases 拡張 / alo_forum_registry / case_observation / fn_generate_case_uri_v2）。
- [ ] `cases.forum_code` 移行 migration note（cases 未投入なら影響なし）。
- [ ] canonical case mint（AN-4：高信頼サブセットから少量・split寄り）。
- [ ] `case_cite_gate` を runtime ゲート化（known_cases=②confirmed、matter 認可 V8）。
- [ ] `alo_edges` accepted（OPAC review-first・現状 accepted 0 から）。
- [ ] jufu access policy 統合（CASEID-005：identity可・出口5点 fail-closed）。

## 5. HOLD（gate 通過まで禁止）
production DDL / DB write / backfill / canonical mint / seed serving / global embedding / MCP serve / export / claim_support / romaji を identity 利用 / multi-docket alias 本番確定 / `__REVIEW__` 採番 / 支部162 未検証投入 / jufu global 配信 / pending_source_fixation を分類供給。

## 6. in-flight 監査（戻り待ち）
- `20260623_caseprecision_v0.2_notes_closure`（DDCASE）
- `20260623_caseid_v0.1_DDCASEID005`（DDCASEID）

## 7. 参照
- reality_check: `DD-CASE_current_reality_check_D1_LIC_OPAC_CaseBundle`（Box 2286208816472）
- RUNBOOK: `RUNBOOK_forum_registry_seed_generation_maccc`
- reconcile: `DD-CASE-001_DDCASEID_reconcile_20260618.md`
