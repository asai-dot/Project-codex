# DD-TOCADOPT-001 — 統一TOC採用ルール 実装ステータス (report-only)

- 日付: 2026-06-16
- 親: `20260615_DD-TOCADOPT-001_v0.2_ACCEPTED.md` (owner ratify 済 design-only / DDTOCADOPT_PASS_WITH_NOTES)
- 実体: branch `claude/legallib-integration-design-Jgrtf`
- 不変: **production apply / canonical projection apply / RDB write / source snapshot mutation /
  policy 本番切替 / Fork1 即廃止 = HOLD 継続**。本実装は投影 (projection) を返すだけで何も書かない。

## やったこと — 設計を実装に落とした

ACCEPTED の 5 ステップ採用ルールと §4 の 7 required gate を、実コードとして実装し
合成多源 golden で固定した。これまで「DRAFT policy + 設計文書」までだったものを、
**実際に動く採用関数 + gate 検査**にした。

### 採用エンジン `scripts/toc_adopt.py` (5 ステップ)

| Step | 実装 |
|---|---|
| 1 同一性ゲート | priority 最上位 source を基準に pairwise `classify_edition_identity_v2` で判定。`cluster_only_status`(resolved_same/manual) のみ合議、別版疑い/不足は human_review へ除外 |
| 2 基底選択 | 粒度(ノード数) 一次 → ページ被覆 二次 → priority tie-break。`granularity_guard`(最富源比0.2・source別override) 未満は base 不可。`legallib_simple_only`/protected 源保護を吸収 |
| 3 ノード補完 | `append_missing_only`(既存 title_norm は上書きしない)。各ノードに provenance 5 項目 + sticky `toc_node_id`。pdf_page は検証済本単位 offset で print に整合。章執筆者を ndl_partinfo から付与 |
| 4 保護と合議 | votes を **provenance_origin 単位**で集計(同一 origin 二重計上なし)。independent 3 origin で consensus。`authority_resolver` で PDF/consensus/human_review |
| 5 記録 | 投影層のみ。snapshot 不変・projection_sha は **入力順非依存**・base_source_distribution を記録 |

### 7 gate 検査 `scripts/toc_adopt_gates.py`

| gate | 状態 | 備考 |
|---|---|---|
| 1 既存 projection 完全再現 | **比較器 green** | 順序非依存 sha + base 分布一致の比較器を実装。golden で自己再現を実証。**実 631 クラスタ再現は ALOBookDX baseline export を要する**(下記) |
| 2 edition phase0 回帰 | **green** | known_conflict 実10冊を v2 で再判定し APPLY_OK へ昇格0件 |
| 3 詳細→浅い劣化0 | **green** | guard-blocked 源が base になっていないことを検査 |
| 4 node provenance 完全 | **green** | 全採用ノードに source_system/provenance_origin/locator/page_basis/source_hash |
| 5 invention 禁止 | **green** | 全 locator が source snapshot に実在 |
| 6 votes=provenance_origin | **green** | votes が distinct origin 数を超えない |
| 7 report_only | **green** | 書込フラグなし |

### golden / テスト
- `scripts/make_tocadopt_golden.py` + `tests/golden/tocadopt/synthetic_multisource.jsonl`:
  7 シナリオ (merge_richest_base / guard_block / edition_exclude / consensus3 / pdf_offset /
  protected_base / single_source_insufficient) を多源で網羅、観測値を回帰ロック。
- `tests/test_tocadopt.py` (143 checks): 回帰ロック + 安全不変条件 + projection_sha 順序非依存 + **7 gate 実走**。
- stdlib 全体 **778 checks green / 0 failed**。

## 唯一まだ外部依存が残る点 (正直な境界)

gate 1 の **「既存 tocattach_projection_dryrun(631クラスタ/116,727ノード)を完全再現」** は、
本流 **ALOBookDX** の projection harness が出力する baseline を入力に要する。その baseline 実データは
本 repo に無い (別コードベース)。

→ 現状: 比較器は実装・検証済みで、**baseline JSON(`{isbn: {projection_sha, base_source, node_count}}`)
が供給され次第そのまま実行できる**。残るのは「他コードベースからの baseline export」という
データ受け渡しだけで、採用ロジック側の実装は完了している。

## 次の一手

1. **ALOBookDX から baseline projection を export** (`{isbn: {projection_sha, base_source, node_count}}`)
   → gate1 を実 631 クラスタで実行。← これだけが残作業。export 様式は本 repo の
   `adopt_book().projection_sha / base_source / projection_node_count` と一致させれば即比較可。
2. gate1 実データ green + 本記録を owner 最終 ratify → 初めて policy 本番切替 / apply を検討。
3. それまで Fork1 policy は併存維持 (OQ-4: 即廃止不可)。

> 本記録時点まで canonical/legallib/final_toc/source/policy 本番への書込は一切なし (report-only)。
