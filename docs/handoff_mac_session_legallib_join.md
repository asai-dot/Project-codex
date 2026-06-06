# 発注書: Mac セッション（番頭/ワーカー）への legallib 接合ドライラン依頼

**宛先**: Mac Claude Code セッション（`~/alo-ai/` と Box 同期フォルダにアクセス可）
**発信**: web セッション（本リポジトリ `Project-codex`）/ 2026-06-06
**前提**: 本リポジトリ `claude/legallib-integration-design-Jgrtf` ブランチを clone 済み。
Python 3.9+。外部依存なし（stdlib のみ）。

---

## 0. 一行サマリ

実 resolver 出力と `legallib_dl/*.json`・本番 `app/data/toc/`・`books.json` に対して
**ドライラン（書き込みゼロ）**を回し、生成された**小さな差分バンドル**を本リポジトリへ
コミットで戻す。これだけで web 側がレビュー・トリアージ・次工程を進められる。
**本番 `app/data/toc/` には一切書き込まない**（本適用は別途、人手承認後）。

## 1. 入力（Mac 側の実体）

| 役割 | 想定パス | 備考 |
|---|---|---|
| resolver 出力 | `~/alo-ai/work/legallib_dl/resolver_decisions.jsonl` | 1行1件 `{legallib_book_id, isbn, bucket, confidence}`。CSV 可 |
| legallib 取得物 | `~/alo-ai/work/legallib_dl/*.json` | STEP A 成果物（422号 + 書籍）。各ノードに `level` |
| 本番 TOC | Box 同期 `…/app/data/toc/` | `isbn_*.json`（5,206 ファイル） |
| 本番書誌 | Box 同期 `…/app/data/books.json` | ISBN 突合の真偽判定に使用（読み取りのみ） |

> パスが違う場合は引数で差し替え可。resolver 出力の実ファイル名/形式が違えば
> §2 の preflight で即判明する。

## 2. 手順（この順に実行）

### STEP 1 — preflight（壊れた入力を深部で踏む前に弾く）

```bash
# resolver 出力の契約検証（件数も突合）
python scripts/validate_resolver.py \
  --resolver ~/alo-ai/work/legallib_dl/resolver_decisions.jsonl \
  --expect "1839,305,616"

# legallib_dl のスキーマ点検（converter の前提と合うか）
python scripts/inspect_legallib_dir.py \
  --legallib-dir ~/alo-ai/work/legallib_dl --json
```

**ゲート**: `validate_resolver.py` が `OK`（exit 0）でなければ着手しない。
`inspect_legallib_dir.py` の出力で以下を確認し、乖離があれば web 側へ差し戻し:
- `node_list_keys` が `toc`（または直リスト）であること。
- `level_keys` が `level`（または `l`）中心であること。
- `title_keys` が `t`/`title`/`label` のいずれか。
- `content_types` の book/journal 内訳（**journal は本接合の対象外**。§4 参照）。

### STEP 2 — ドライラン（書き込みゼロ）

```bash
python scripts/legallib_join_dryrun.py \
  --resolver     ~/alo-ai/work/legallib_dl/resolver_decisions.jsonl \
  --legallib-dir ~/alo-ai/work/legallib_dl \
  --toc-dir      "<Box>/app/data/toc" \
  --books        "<Box>/app/data/books.json" \
  --policy       data/toc_merge_policy_legallib.json \
  --out          build/legallib_dryrun
```

**ゲート（L1 self-verify）**: 次が全て満たされること。1 つでも崩れたら差し戻し。
1. exit code 0（= `invariant_violations` 0 = 保護対象への書き込み候補ゼロ）。
2. `build/legallib_dryrun/report.md` の「不変条件違反 0 件 ✅」。
3. `actions.jsonl` の `overwrite_simple` 件数 + `create` 件数が妥当
   （新規 auto_accept ≈1,495 の範囲。既merge 344 は `skip_idempotent`）。
4. `blocked_*`（誤マージ防止）件数を report に記録。

## 3. 戻す成果物（本リポジトリへコミット）

`build/legallib_dryrun/` から**以下の小さいファイルだけ**を
`handoff/legallib_dryrun_<YYYYMMDD>/` 配下に置いてコミット・push:

| ファイル | 用途（web 側） |
|---|---|
| `report.md` | 全体サマリ・検収ガード |
| `actions.jsonl` | 全判定（book_id/isbn/action） |
| `overwrites_bundle.jsonl` | **旧+新ノード**入り。`render_proposed_diff.py` で差分レビュー |
| `review_bundle.jsonl` | 保護衝突の**既存+候補**。`triage_review_queue.py` でトリアージ |
| `review_queue.jsonl` / `defer_staging.jsonl` | レビュー待ち / defer の一覧 |

> `proposed/`（提案 TOC 本体）と `books.json`・`legallib_dl/` は**戻さない**
> （大きい・機微）。バンドルだけで web 側のレビューは完結する。

## 4. スコープ外（やらないこと）

- **journal（雑誌 422 号）の本接合**: 雑誌は periodical で号単位。論文 entity 化は
  別タスク（`cc_instruction_legallib_journal_article_parser`）。本接合は
  `content_type == "book"`（ISBN を持つ書籍）のみ対象。resolver が雑誌を
  auto_accept に混ぜている場合は web 側へ報告。
- **本適用（実書き込み）**: 人手レビュー承認後に `legallib_join_apply.py --commit`
  で別途。ドライランでは絶対に書かない。

## 5. 進めかた・判断ログ

auto-decide で進めてよい。判断ポイントは戻りの `report.md` 末尾に
「観測 / 選択肢 / 採択 / 理由」で記録。preflight が乖離を示したら、それ自体を
web 側への質問として戻す（converter / loader の調整は web 側で行う）。
