# 判例オブジェクト 統一性・安定性 監査（実データ流入前ゲート）

- 実施: 2026-06-23 JST ／ 番頭: Claude Code (remote)
- 動機: DD を時系列で別々に作成したため、多重定義語彙の **ドリフト** が疑われた（owner 指摘）。実データ流入前に統一性・安定性を確認。
- 結論: **ドリフト4件を検出、うち実害2件を修正**。唯一の正本語彙 `case_vocab.py` を新設し、整合テスト＋統合テストで恒久ゲート化。**全 green。**

---

## 1. 検出したドリフト（実コードから抽出）
| # | 種別 | 内容 | 重大度 |
|---|---|---|---|
| D1 | **実害(crash)** | `case_eval` の per-tier RISK 表が `{A,B,C}` のみ。ガードが emit する `prov` tier を渡すと **KeyError 落ち** | 🔴 |
| D2 | **実害(参照不能)** | `case_corroborate` の判例DB集合 `CASELAW` が関数ローカル変数で、外部から検証・再利用不可。`NII` 等が source registry と突合されていなかった | 🟡 |
| D3 | 語彙二系統 | `forum_type` が DD-CASEID-003=granular 7値 と DD-CASE-001 §2=粗い5値(court/tribunal/administrative/advisory/adr)で混在。コード(checker)は7値に統一済だが **DD-CASE-001 §2 の表記が未整合**（doc-level） | 🟡 |
| D4 | 未登録 source | `NII` が corroborate / gold で source として使われるが **source registry seed(31)に不在**（recon の欠落10行の一つと推定） | 🟡 |

confidentiality 4値（open/matter_scoped_only/matter_confirmed/lawyer_client_confidential）は **一致**（`confirmed_private`/`no_export` は negative test の拒否対象のみ＝正常）。

## 2. 修正
- **D1 修正**: `case_eval` RISK 表に `prov` を追加（`case_vocab.TIER_RISK` と一致）。prov tier ペアでも crash しない。
- **D2 修正**: `case_corroborate` の `CASELAW_SOURCES` をモジュール定数化（整合テストで検証可能に）。
- **D4 解消**: `case_vocab.REGISTERED_SOURCES` に `NII` を判例DB源として登録（seed への追記は Mac CC、`NII` は recon 欠落分として `missing_recon_sources` 既出）。
- **D3**: コードは統一済。DD-CASE-001 §2 の「既定 forum_type」表記の修正は **doc-level follow-up**（v0.2、forum_type は granular 7値が正準・粗い5値は forum group ヒント）。

## 3. 統一性アンカー（新設）
**`scripts/case_vocab.py`** = 判例オブジェクトの唯一の正本語彙：
confidentiality / redistribution / **EGRESS_SINKS(5点)** / **FORUM_TYPES(7)** / **CASE_TYPES(6)** / **FORUM_LEVELS(6)** / **BIND_TIERS(A/B/C/prov)** / TIER_PRECISION_TARGET / TIER_RISK / **CASELAW_SOURCES / REGISTERED_SOURCES** / `can_global_index()`。

設計方針: 各モジュールは Box 個別配布のため **自己完結**を維持。`case_vocab` を *仕様* とし、**整合テストが値一致を強制**（drift を CI で止める）。

## 4. ゲート（恒久）
- **`scripts/test_case_consistency.py`** = 13項目。各モジュール/データ(seed/gold/semantics)の語彙が `case_vocab` と一致するか検査。**PASS**。
- **`scripts/test_case_pipeline_e2e.py`** = ①〜⑤を共有 fixture で連結。bind→eval(false_merge=0)→cross-source→corroborate→cite-gate→review が **破綻なく通る**。**PASS**。
- 既存単体テスト（norm/symbol/eval/bind/corroborate/cite/review/jufu/v0.2）= 全 **OK**（回帰なし）。

## 5. 残（実データ前の前提・Mac CC）
- D3 doc 修正（DD-CASE-001 §2 forum_type 表記）。
- D4: source registry seed に `NII` 行を追加（proposed→accepted）。
- 実 corpus での gold 検証（合成 fixture の false_merge=0 は **自己無矛盾の確認に過ぎない**）。
- 公式 doc hash 固定（CASEID-002 MF-2、no-web）。

## 6. 安定性の到達点（正確な表現）
- **語彙はドリフトしていない**（正本＋整合ゲートで保証）。
- **チェーンは連結して動く**（e2e 緑）。
- ただし **「正しい」は未証明**（実データ・実 gold・公式 facts は Mac CC/web 待ち）。本監査は *無矛盾性と連結性* の確認であって、*正確性* の確認ではない。
