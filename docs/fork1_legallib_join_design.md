# Fork 1 — legallib 詳細TOC × canonical 接合の実装設計

**作成**: 2026-06-06 / Claude Code
**ブランチ**: `claude/legallib-integration-design-Jgrtf`
**目的**: legallib 詳細TOC を本番ブックJSON（canonical）へ**安全に**接合する。
resolver の 3 層（auto_accept / human_review / defer_new）を本番処理へどう落とすかを確定し、
最初の一歩 ①②③ を runnable な形で実装する。

---

## 0. 一行サマリ

legallib の `{l,p,t,level}` を本番 TOC ノード schema に変換し（①）、
**「人手/NDL > legallib・simple のみ昇格上書き可」** の優先順位ポリシー（②）に従って、
auto_accept 新規分を**書き込みゼロのドライラン diff**（③）で検証する。
検収「非simple を1件も劣化させない／誤マージ0」を**コードの不変条件**として固定した。

---

## 1. 前提資産と現状把握（Box 実データで確認済み）

| 資産 | 実体 | 確認した要点 |
|---|---|---|
| canonical schema | `app/bookdx_canonical_schema_v1.json` (Box 2217714412089) | `bib_extra.toc` は `{depth(1-6), label, page}` のフラット配列。NDL canonical 原則（設計書 §0） |
| 本番 TOC | `app/data/toc/isbn_*.json`（5,206 ファイル） | ノードは下記 schema。`toc_source`/`toc_status` 付き。simple はフラット |
| 既存マージ | `app/scripts/merge_toc_updates.py` + `app/data/toc_merge_policy.json` | rank ベースの `replace_if_higher_source`。manual 保護あり |
| 既存同期 | `CODEX/scripts/sync_safe_codex_toc_into_app.py` / `build_toc_canonical_registry.py` | book_id / `isbn_{ISBN}` の二系統 key。安全行のみ取り込み |
| legallib | `~/alo-ai/work/legallib_dl/*.json`（422号 / 124,529 nodes） | 各ノードに `level` とラベル。雑誌は「タイトル　著者」連結（別タスクで論文 parser 済） |
| resolver 出力 | auto_accept 1,839（既merge 344 → 新規≈1,495）/ human_review 305 / defer_new 616 | 誤マージ0ガード前提 |

### 1.1 本番 TOC ノード schema（実ファイルより確定）

```json
{
  "l": 1, "p": null, "t": "第一章 …",
  "toc_node_id": "alo:book:isbn:9784000616072:toc:001",
  "depth": 1, "parent_toc_node_id": "", "toc_path_id": "c01",
  "page_start": null, "toc_source": "books_or_jp", "toc_status": "simple"
}
```

- `l` == `depth`（1始まり）。`parent_toc_node_id` はトップで `""`。
- 既存の `toc_source` 実値: `manual / publisher / openbd / books_or_jp / bencom / codex_ocr` 等。
- `toc_status`: フラット低精度は `"simple"`。OCR/人手などは非 `"simple"`。

---

## 2. 最初の一歩 ① — 変換器（`scripts/legallib_to_canonical.py`）

`convert_legallib_nodes(raw_nodes, isbn)` が legallib `{l,p,t,level}` を本番ノードへ変換。

- **`parent_toc_node_id` を level 入れ子から再構築**: 祖先スタックを持ち、
  各ノードの親 = 自分より浅い直近ノード。
- **level 飛びのクランプ**: `1→3` のような飛びは depth を `親+1` に矯正し木を妥当に保つ
  （飛びは warning として記録）。
- **`toc_path_id`**: 階層パス（`c01` / `c01.01` / `c01.02` / `c02` …）を生成。
- **`toc_node_id`**: `alo:book:isbn:{ISBN}:toc:{連番}`。決定的・冪等。
- 生成ノードの **`toc_source="legallib"` / `toc_status="legallib"`（=非simple）**。
  → 一度入った legallib TOC は以降フラット系（openbd等）から上書きされない。
- `to_canonical_bib_extra_toc()` で canonical `{depth,label,page}` へ射影（books.json/Sheet 用）。

変換のみを担い、書き込み判定は持たない（関心の分離）。

## 3. 最初の一歩 ② — 優先順位ポリシー（`scripts/legallib_join_policy.py` + `data/toc_merge_policy_legallib.json`）

既存 `toc_merge_policy.json` を踏襲し `ndl` と `legallib` を追加:

```
manual > ndl > publisher > toc_pdf > legallib > openbd > books_or_jp > bencom > codex_ocr > unknown
```

ただし legallib は **rank ベースの一般置換を使わない**。専用の **simple-only ゲート**:

| 既存ファイル状態 | legallib auto_accept の動作 |
|---|---|
| 既存なし | `create`（新規作成） |
| 全ノード `simple` かつ保護ソースなし | `overwrite_simple`（昇格上書き） |
| 既に `legallib` | `skip_idempotent`（冪等・既merge 344 件想定） |
| 非simple を1つでも含む／保護ソース（manual/ndl/publisher/toc_pdf） | `route_human_review`（**上書き禁止**） |

`decide_join_action()` だけで検収を担保する: 保護対象（非simple または保護ソース）は
**必ず** `route_human_review` になり、書き込み系 action（`create`/`overwrite_simple`）には
**決して入らない**。

> 設計判断: legallib は外部由来で誤接合リスクがあるため、generic な
> `replace_if_higher_source`（openbd が simple でなくても rank で置換しうる）より
> **厳しい simple-only** を課す。人手/NDL/出版社/PDF目次を1件も劣化させないため。

## 4. 最初の一歩 ③ — ドライラン diff（`scripts/legallib_join_dryrun.py`）

実ファイル（`app/data/toc/`）を**一切変更せず**、接合結果を `--out` に出力:

- `report.md` — action 内訳・検収ガード集計・**不変条件違反の有無**。
- `proposed/isbn_*.json` — 書き込み候補の提案ファイル（人が diff 確認）。
- `review_queue.jsonl` / `defer_staging.jsonl` / `actions.jsonl`。

```bash
python scripts/legallib_join_dryrun.py \
  --resolver ~/alo-ai/work/legallib_dl/resolver_decisions.jsonl \
  --legallib-dir ~/alo-ai/work/legallib_dl \
  --toc-dir app/data/toc --books app/data/books.json \
  --out build/legallib_dryrun

# 実データ不要の素振り（同梱フィクスチャ）:
python scripts/legallib_join_dryrun.py --demo --out build/legallib_dryrun_demo
```

---

## 5. resolver 3層 → 本番マッピング

| 層 | 件数 | 本番処理 | 書き込み先 |
|---|---|---|---|
| `auto_accept` | 1,839（新規≈1,495 / 既merge 344） | 誤マージ0ガード通過後、policy ゲートで create / overwrite_simple / skip / review | `isbn_{ISBN}.json`（書き込み系のみ） |
| `human_review` | 305 | レビューキューへ退避（**書き込みなし**） | `review_queue.jsonl` |
| `defer_new` | 616 | canonical 対応書籍なし。book_id 名前空間へ退避 | `defer_staging.jsonl`（**ISBN名前空間に書かない**） |

既merge 344 件は既存ファイルが既に `legallib` のため `skip_idempotent` に落ち、再実行しても diff 0（冪等）。

### 5.1 誤マージ0ガード（book_id ↔ ISBN）

auto_accept でも次は**書き込み候補から完全除外**:

- `blocked_bad_isbn` — ISBN-13 として不正。
- `blocked_missing_isbn` — books.json に存在しない ISBN。
- `blocked_ambiguous_isbn` — 同一 ISBN に複数 legallib_book_id。
- `blocked_ambiguous_book` — 同一 book_id に複数 ISBN。

resolver が明示的に book_id→唯一の既知 ISBN を auto_accept で束ねた時だけ書く。

---

## 6. 検収条件と機械的証明

| 検収 | 実装上の保証 | テスト |
|---|---|---|
| 既存の人手/NDL TOC を1件も劣化させない（非simple は上書き前後 diff 0） | 保護対象は `route_human_review` に固定。`run_dryrun` が `invariant_violations`（保護対象への書き込み）を再走査し 0 を保証 | `test_policy_gate` / `test_dryrun_invariants` |
| book_id↔ISBN の誤マージ0 維持 | `detect_mismerge` が missing/ambiguous/bad を全 block | `test_mismerge_guard` |
| simple のみ昇格上書き | `decide_join_action` の simple-only ゲート | `test_policy_gate` |
| level 入れ子の正しい再構築 | 祖先スタック + クランプ | `test_parent_reconstruction` / `test_level_jump_clamp` |
| 冪等 | 連番・順序固定 | `test_deterministic` |

```bash
python tests/test_legallib_join.py   # → 46 passed, 0 failed
```

`report.md` の「不変条件違反 0 件 ✅」が、非simple を1件も劣化させていない機械的証明。

---

## 7. ロールアウト手順（推奨）

1. **ドライラン**: 実 resolver 出力で `legallib_join_dryrun.py` を実行。
   `report.md` の不変条件違反 0・blocked 件数・overwrite 候補件数を確認。
2. **人手レビュー**: `proposed/` を既存と目視 diff（特に overwrite_simple）。
   `review_queue.jsonl`（305 + 保護衝突分）を浅井さんが裁定。
3. **本適用** (`scripts/legallib_join_apply.py`): ドライランで承認された ISBN のみ
   `app/data/toc/` へ反映。**既定は dry-run**（`--commit` 必須）、`--only-isbns` で
   承認ホワイトリストを渡せる。書き込み直前にライブの既存へ `decide_join_action` を
   **再適用**し、書き込み系でなければ `refused_protected` で拒否（保護対象を物理的に
   上書き不可能にする二重ガード）。atomic write・冪等（既 legallib は skip）。
   hasToc 反映は既存パイプラインへ委譲（manifest 出力）。
4. **defer_new**: `defer_staging.jsonl` を別途キュー化（OCR奥付→再NDL照合 等、別タスク）。

## 8. 既存 `merge_toc_updates.py` との関係

- 優先順位の**思想は踏襲**（manual 保護・source rank）。`legallib` と `ndl` を priority に追加。
- legallib は generic な rank 置換を使わず **simple-only ゲート**を独自に課す点が差分。
- 本適用器は将来 `merge_toc_updates.py` に legallib 分岐として統合可能。本 Fork では
  まず接合設計とドライランを**独立に**提供し、本番ファイルへ影響を出さない。

## 9. 成果物

```
docs/fork1_legallib_join_design.md         本設計書
scripts/legallib_to_canonical.py           ① 変換器
scripts/legallib_join_policy.py            ② 優先順位ポリシー + simple-only ゲート
scripts/legallib_join_dryrun.py            ③ ドライラン diff CLI（--demo 同梱）
scripts/legallib_join_apply.py             本適用器（dry-run 既定・二重ガード）
data/toc_merge_policy_legallib.json        拡張ポリシー（ndl / legallib 追加）
tests/test_legallib_join.py                検収テスト（72 checks, stdlib のみ）
.github/workflows/ci.yml                    CI（compile + テスト + ドライラン素振り）
```

> 注: 実 resolver 出力と `legallib_dl/*.json` は `~/alo-ai/` 側（本リポジトリ外）。
> 本リポジトリの成果物は合成フィクスチャで自己完結検証でき、`--demo` と
> テストで CI / web セッション上でも常に再現可能。
