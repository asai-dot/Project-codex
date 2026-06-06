# legaldb v0.5 — candidate ステータスと昇格ブロック

判例・法令・文献DB（legaldb）の本体スキーマを、本ガバナンスの landing/staging/prod の型で
起こした。ただし **現状は candidate であり、staging/prod への昇格は物理的にブロックしている。**

## なぜブロックするか

- 出所: `STATIC_DB_INTEGRATION_PLAN v0.5`（番頭/Mac CC 提案・ratify 前 draft）
- 独立監査（別family = GPT Pro お目付け役）の判定:
  **`DESIGN_MODIFY_REQUIRED`**（`from_gpt/20260606_legaldb_v0.5_DESIGN_RESULT.md`）
- 監査の核心: 方向は是だが、**研究示唆を accepted schema と誤読して実装するのは事故**。
  owner ratify と v0.6 必須パッチの前に本番投入してはならない。

これは本ガバナンスの原則そのもの（clean-only / candidate≠truth / 昇格前レビュー）の適用例。
**構造は用意するが、ゲートは閉じている。**

## いま在るもの

| 場所 | 内容 |
| ---- | ---- |
| `supabase/staging/migrations/0005_legaldb_candidate_landing.sql` | landing(候補)ゾーンの全候補テーブル。GPT指摘 F1–F7 の構造修正を反映 |
| `supabase/staging/migrations/0006_legaldb_staging_and_block.sql`  | staging 目標形の骨格 ＋ 昇格ブロック関数 `landing.promote_legaldb_to_staging()` |
| `supabase/staging/tests/test_legaldb_block.sql` | 昇格がブロックされ、landing→staging へ漏れないことのテスト |

landing の行は既定で `quality_status='unverified'`（candidate）。prod テーブルは**作らない**
（prod = ratify 済みのみ、という原則を守る）。

## 反映済みの GPT 構造修正（F1–F7）

- **F1** anchor lifecycle: 不変 `stable_anchor_id`(= 行の opaque uuid) ⊥ 可変 `human_locator`、`supersedes_anchor_id`/`mint_basis` で発番系譜を保持。
- **F2** 識別子責務分離: `alo_work_uri`(正準) と `work_identifier`(ECLI/ELI/e-Gov/NII/DOI…)を分離。自然キーは `is_candidate_key` で衝突テスト前と明示。
- **F3** offset は版固有 locator: `standoff_annotation` は `text_version_id` と複合。同一性には使わない。
- **F4** 法令時間軸は BLOCKED: `element_version_period`(版期間) と `legal_effective_period`(効力期間)を分離。`as_of_date` は unknown 可。**DD-LAWTIME v0.2 完了に依存**。
- **F5** 文献ID: `legal_work.id`(article_work_id) が一意。DOI/NDL/CiNii/巻号頁は `work_identifier` へ。
- **F6** citation 状態機械: `raw_citation_text` 常時保存＋`parse_status`(raw→…→promoted)・`treatment_status`(unclassified/candidate/reviewed)を別軸で。treatment 語彙は粗いものに留置。
- **F7** KG安全則: LLM 由来は candidate のみ。本番昇格は別ゲート（このブロック関数が体現）。

## ブロック解除（昇格可能化）の条件

GPT が挙げた v0.5.1 / v0.6 必須パッチを反映し、owner ratify を得ること:

1. DD-LAWTIME v0.2 完了（法令効力モデルの確定）
2. 識別子責務表の確定（`alo_work_uri / external_work_id / expression_id / manifestation_id / locator`）
3. anchor lifecycle 規約（mint/merge/split/supersede/confidence）の確定
4. citation 状態機械（raw→parsed→resolved→reviewed→promoted）の昇格条件確定
5. treatment 正式語彙の別DD定義（未レビュー treatment を claim_support に使わない）
6. over-reach ラベル（research-backed / primary-verified / grey-lit / design-synthesis）付与
7. 判例自然キー・文献巻号頁キー・法令 stable_anchor の collision/再現性テスト

上記が揃ったら、`landing.promote_legaldb_to_staging()` を例外送出から本実装（検査＋昇格）へ
差し替え、staging→prod の昇格マイグレーションを PR レビューに乗せる。
