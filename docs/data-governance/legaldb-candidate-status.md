# legaldb v0.5 — candidate ステータスと昇格ブロック

判例・法令・文献DB（legaldb）の本体スキーマを、本ガバナンスの landing/staging/prod の型で
起こした。ただし **現状は candidate であり、staging/prod への昇格は物理的にブロックしている。**

## current_design_gate_result（最新の設計ゲート結果を常にここで追跡）

> 解除条件が古い DESIGN 結果に固定されないよう、**現在の設計ゲート結果**をここで追う
> （GPT IMPL監査 note 5）。後続の DESIGN_RESULT が出たら必ず更新する。

- **current_design_gate_result**: `from_gpt/20260607_legaldb_v0.5.1_DESIGN_RESULT.md` = `DESIGN_MODIFY_REQUIRED`
  → **v0.6 → `DESIGN_PASS_WITH_NOTES`（2026-06-08）**: phantom-accept 撤回を「監査レーンへの誠実な再接地」と
  評価。残notes＝F4 文言を「dependency_rebased_pending_ratify」へ緩和／treatment gate を「単純resolved引用は可・
  treatment付きは reviewed 必須」に分岐／collision gate を複合自然キー(natural_key_hash)対応／ratify＋branch
  gate まで実装・backfill・canonical 反映は HOLD。
  → **その後 legaldb は legallibjoin として継続**: v0.2→v0.3→**v0.3.1(DDLEGALLIBCONCORD)**＋IMPL status review
  （2026-06-13）。**legaldb 系の現在頭は legallibjoin v0.3.1**（着手前に from_gpt の当該 RESULT を読むこと）。
- **判定（v0.5.1）**: `DESIGN_MODIFY_REQUIRED`（唯一の核心ブロッカーは F4 = DD-LAWTIME 依存の未検証）。
- **未PASSの核心**: F4 が前提とする **DD-LAWTIME v0.2.1 accepted の証跡が監査レーンで未確認**
  （既存 `DDLAWTIME_MODIFY_REQUIRED` と矛盾）。よってブロック継続。
- **命名の含意**: v0.5.1 は本体テーブル名を既存ALOスキーマ（`legal_source_object` 系）へ寄せた。
  本リポジトリ `0005` の候補テーブル名（`legal_work` 系）は**暫定**で、解除時に突き合わせる。
  candidate＝ブロック中ゆえ prod への実害はない。

## なぜブロックするか

- 出所: `STATIC_DB_INTEGRATION_PLAN v0.5`（番頭/Mac CC 提案・ratify 前 draft）→ v0.5.1 で改訂中。
- 独立監査（別family = GPT Pro お目付け役）の判定:
  **`DESIGN_MODIFY_REQUIRED`**（v0.5: `20260606_legaldb_v0.5_DESIGN_RESULT.md` →
  v0.5.1: `20260607_legaldb_v0.5.1_DESIGN_RESULT.md`、いずれも未PASS）
- 監査の核心: 方向は是だが、**研究示唆を accepted schema と誤読して実装するのは事故**。
  owner ratify と必須パッチの前に本番投入してはならない。

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

### v0.5.1 監査で追加された必須パッチ（current_design_gate_result 由来）

8. **DD-LAWTIME の accept**（F4 の本丸）。**事実確認の結果、v0.5.1 が前提とした「v0.2.1 accepted」は存在しなかった**
   （accepted レーン上の結果は v0.1 = `DDLAWTIME_MODIFY_REQUIRED` のみ）。
   - 対応: v0.1 の必須7点を反映した **DD-LAWTIME v0.2 → `DDLAWTIME_PASS_WITH_NOTES`**（approval_queue 済・ratify 候補）。
   - **N1–N4 ＋ v0.5.1 が参照していた richer 構造を統合した DD-LAWTIME v0.2.1 → `DDLAWTIME_PASS_WITH_NOTES`**
     （`from_gpt/20260607_lawtime_v0.2.1_DDLAWTIME_RESULT.md`, owner ratify 可）。N1–N4 全クローズ。
     GPT は「未監査の自称 v0.2.1 を追認せず実監査ラインへ統合した判断は正しい」と是認。
     production DDL 前 notes P1–P5（article_path 明記／edge_id FK・gate／relation_type 正規化表／
     claim_support 導出 gate／merge・split event 整合 gate）は**設計受理を止めない**。
   - **P1–P5 を反映した DD-LAWTIME v0.2.2（production-DDL パッチ）→ `DDLAWTIME_MODIFY_REQUIRED`（P0-1〜P0-4）。**
     → **後続セッションで v0.2.3 が起票され `DDLAWTIME_PASS_WITH_NOTES`（2026-06-11）**：P0-1〜P0-4 を全クローズ
     （既存 edge の `NOT VALID→backfill→VALIDATE` 順序／`[valid_from,valid_to)` 両端検査／claim_support を
     current・superseded に限定／succession overlap gate）＋ LAWSUBTRANS 用 resolved lawtime view(R-1) を追加。
     **lawtime の現在頭 = v0.2.3。** 次段 P1（LAWSUBTRANS）＋ branch dry-run ＋ owner ratify 待ち。
   - **重要（phantom-accept の摘発）**: v0.5.1 §3 の「DD-LAWTIME v0.2.1 は 2026-06-05 accepted」は
     **監査レーンに証跡が無い自己申告**だった（実在は v0.1=MODIFY と v0.2=PASS のみ）。v0.6 で撤回し、
     依存先を実在・監査済ラインへ確定。
   - したがって F4 は **設計クローズ（v0.2 PASS）・v0.2.1 差分監査＋owner ratify＋実装ゲート待ち**。
     legaldb 昇格は v0.6 design accept ＋ ratify 完了まで引き続きブロック。
9. **anchor 責務分界の DDL 明文化**: opaque ULID `anchor_id`(不変主キў) と
   `stable_locator_key`(表示/互換 locator) の責務を分け、新規 mint 経路を一本化、merge/split が
   既存 `UNIQUE(source_object_uri, anchor_type, stable_locator_key)` と衝突しない DDL を示す。
10. **treatment の claim_support 物理化**: 「`treatment_status <> reviewed` の edge は
    claim_support view に出さない」を DB の view / CHECK / gate で物理化（文書規約だけにしない）。
11. **claim_confidence ラベルのサンプル適用**: research-backed / primary-verified / grey-lit /
    design-synthesis を各主張に最低限付与し、design-synthesis が確定スキーマに固定されないことを示す。
12. **collision gate の仕様明記**: gate_id だけでなく、合格条件と対象テーブルを明記。

上記（1–12）が揃ったら、`landing.promote_legaldb_to_staging()` を例外送出から本実装（検査＋昇格）へ
差し替え、staging→prod の昇格マイグレーションを PR レビューに乗せる。
**昇格時には staging 側で FK / NOT NULL / unique / resolved-only を必ず閉じる**（landing の緩さを
clean target に持ち込まない。GPT IMPL監査 note 3）。
