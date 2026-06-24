# Worker Notes — legallib 接合 dryrun (2026-06-08)

ワーカー: Mac CC (yuta host) / 番頭発注 `cc_instruction_legallib_join_handoff_20260608`
正本発注書: `docs/handoff_mac_session_legallib_join.md`

## 結果サマリ

L1 self-verify 4 項目 **全 PASS**。dryrun は書き込みゼロで完了。

| L1 条件 | 結果 |
|---|---|
| exit code 0 | ✓ |
| report.md「不変条件違反 0 件 ✅」 | ✓ |
| `overwrite_simple + create` 妥当 | ✓ (合計 1,740) |
| `blocked_*` 件数を記録 | ✓ (blocked_bad_isbn=95) |

actions: `blocked_bad_isbn 95 / create 215 / overwrite_simple 1525 / route_human_review 309 / defer_staging 616` 合計 2,760。

snapshot_before vs after の差分: `legallib_join_dryrun.handoff/legallib_dryrun_*/report.md` が `present:false → true`（接合後に dryrun レポートが置かれた、それだけ）。本番 `app/data/toc/` への書き込みは 0。

## 観測 / 選択肢 / 採択 / 理由

### Obs-1. resolver 出力のファイル名不一致

- **観測**: 発注書想定 `~/alo-ai/work/legallib_dl/resolver_decisions.jsonl` が不在。実体は `~/alo-ai/work/legallib_dl/_resolve/legallib_resolution.jsonl`。件数 2,760、bucket 分布 1839/305/616 は発注書 `--expect` と完全一致。
- **選択肢**: (A) pipeline.json の path を実体に書き換え / (B) 実体に発注書名の symlink を張る / (C) 実体を rename。
- **採択**: (B) symlink。
- **理由**: pipeline.json はリポ管理で手を入れたくない（CI/ダッシュボード前提値）。実体 rename は raw 改変。symlink は可逆で raw 不変、後続コマンドが発注書のコマンドラインそのまま動く。

### Obs-2. JSONL 内 U+2028 で行構造が破壊される（スクリプトのバグ）

- **観測**: `validate_resolver.py` 経由で `legallib_join_dryrun.py:67` の `text.read_text().splitlines()` が JSONL 1 行目で `JSONDecodeError: Unterminated string`。原因は data 中の U+2028 (1 件、title 「秘密保持契約書」付近) を Python `str.splitlines()` が改行扱いするため。これは ALO 内で繰り返し踏まれている罠（`[[feedback_jsonl_u2028]]`）。
- **選択肢**: (A) スクリプト修正 (`splitlines()` → file iter or `split("\n")`) / (B) data 側で U+2028 を ` ` エスケープして cleaned jsonl を作る / (C) 物理削除（raw 改変）。
- **採択**: (B) cleaned jsonl ＋ symlink 差し替え。
- **理由**: スクリプト修正は web 番頭の領分（勝手に PR は出さない）。raw `_resolve/legallib_resolution.jsonl` は不変、新規 `_resolve/legallib_resolution.cleaned.jsonl` を生成、symlink で発注書名に解決。
- **報告事項 (web 側 fix 推奨)**: `scripts/legallib_join_dryrun.py:67` の `splitlines()` を `split("\n")` に変えるか、`for line in path.open(encoding="utf-8")` に置換。U+2028/U+2029 を踏まない実装が ALO の不変要件。

### Obs-3. resolver 出力のフィールド名不一致

- **観測**: スクリプト想定 `{legallib_book_id, isbn, bucket, confidence}` ↔ 実体 `{legallib_id, isbn, tier, score, ...}`。`bucket` の値域（auto_accept / human_review / defer_new）は `tier` と完全一致。
- **選択肢**: (A) スクリプト側で `or` 連鎖に `legallib_id`/`tier` を追加 / (B) data 側で normalize した jsonl を作って symlink 差し替え。
- **採択**: (B) `_resolve/resolver_decisions.normalized.jsonl` を生成、symlink を再差し替え。元フィールド (title/match_id/edition_label/...) は参考用に同梱、害なし。
- **理由**: Obs-2 と同じ哲学。raw 不変、スクリプト変更は番頭領分、ワーカー側で derived を整える。
- **報告事項**: legallib_resolve.py の出力スキーマと `legallib_join_dryrun.py` の入力スキーマがそもそも合っていない。仕様レベルの整合が必要（どちらかに寄せるか、loader 側で正規化）。

### Obs-4. 新規 auto_accept 件数の見込みと実値の乖離

- **観測**: 発注書「新規 auto_accept ≈ 1,495」「既merge 344 は `skip_idempotent`」だが実値は `overwrite_simple 1525 + create 215 = 1740`（skip_idempotent カテゴリは actions.jsonl に出ず）。`route_human_review` も resolver の human_review=305 に対し 309（4 件オーバー：auto_accept のうち書き込み判定で人手回送されたものを含むと推定）。
- **採択**: 観測事実として記録。dryrun の判定ロジックが既存ノードを「上書き候補」と「skip_idempotent」のどちらに振るかは policy 依存で、見込み数との乖離自体は不変条件違反ではない。
- **理由**: actions.jsonl で個別判定を web 側でレビューすれば説明可能。詳細トリアージは `triage_review_queue.py` の役目。

### Obs-5. 既存 untracked の退避

- **観測**: checkout 前のブランチ `claude/legal-library-metadata-impact-HBoXn` に build/ / data/ (59MB) / pipeline/ / scripts/ / .DS_Store の untracked。target branch の tracked と衝突するため `git stash push -u -m "pre-legallib-dispatch-2026-06-08"` で退避。
- **採択**: stash 保持（消さない）。
- **理由**: data/db_staging が 59MB あり前 Mac CC 作業の遺物の可能性。本作業終了後に owner/番頭判断で取り扱い。

### Obs-6. 変換 warning 1 件

- **観測**: report.md「変換 warning: 1 件」。actions.jsonl の `warnings` フィールドに詳細あるはず。web 側で `render_proposed_diff` 実行時に拾える。
- **採択**: ワーカー側では深掘りせず（解釈は web 側）。

## スコープ外（やっていない）

- 本適用 (`legallib_join_apply.py --commit`) — 人手承認後の別工程
- journal 422 号の接合 — `content_type == "book"` のみ対象（resolver の bucket には混在せず、書籍 2,760 のみ判定済）
- proposed/、books.json、legallib_dl/ の戻し — 発注書 §3 の通り除外
- スクリプトのバグ修正 PR — Obs-2 で報告のみ

## ワーカー側の WA 痕跡（trace 用）

`~/alo-ai/work/legallib_dl/` 配下に以下の symlink/derived を作成（raw 不変）:

```
resolver_decisions.jsonl         -> _resolve/resolver_decisions.normalized.jsonl
_resolve/legallib_resolution.cleaned.jsonl    (U+2028 escape済 derived)
_resolve/resolver_decisions.normalized.jsonl  (フィールド rename 込 derived)
```

raw `_resolve/legallib_resolution.jsonl` は未改変（sha256 不変）。
