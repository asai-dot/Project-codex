# INSTRUCTION: legallib 接合ドライラン 実行依頼（Mac CC ワーカー宛 / dispatch）

- 宛先: Mac Claude Code セッション（`~/alo-ai` と Box 同期にアクセス可）
- 発信: web CC（番頭）/ 2026-06-08
- 種別: 接合ドライラン（**本番書き込みゼロ**）＋ パイプライン snapshot 採取
- 全文発注書（正本）: リポジトリ `Project-codex` の
  `docs/handoff_mac_session_legallib_join.md`（本書はその dispatch 要約）

---

## 0. 前提（最初にこれをやる）

```bash
# 1) リポジトリと作業ブランチを取得（PR #5）
git clone <Project-codex>        # asai-dot/Project-codex
cd Project-codex
git checkout claude/legallib-integration-design-Jgrtf   # 最新 head: 9556fea 系
```

Python 3.9+・外部依存なし（stdlib のみ）。実 resolver 出力・`legallib_dl/*.json`・
本番 `app/data/toc/`・`books.json` は `~/alo-ai` / Box 同期側の実体を指す。

## 1. STEP 0 — パイプライン snapshot（全体像）

```bash
python scripts/pipeline_probe.py --manifest pipeline/pipeline.json \
  --root bookdx="<Box>/claude/事務所内本棚DX化計画" \
  --root alo="$HOME/alo-ai" --root repo="$(pwd)" \
  --out build/pipeline_snapshot_before.json
```

`pipeline.json` の `path`/`expected` が実環境とズレていたら直して web へ知らせる。

## 2. STEP 1 — preflight（壊れた入力を深部で踏む前に弾く）

```bash
python scripts/validate_resolver.py \
  --resolver ~/alo-ai/work/legallib_dl/resolver_decisions.jsonl \
  --expect "1839,305,616"            # OK(exit 0) でなければ着手しない

python scripts/inspect_legallib_dir.py \
  --legallib-dir ~/alo-ai/work/legallib_dl --json
```

`inspect` で `node_list_keys=toc` / `level_keys=level|l` / `title_keys=t|title|label`、
`content_types` の book/journal 内訳を確認。乖離があれば web へ差し戻し。

## 3. STEP 2 — ドライラン（書き込みゼロ）

```bash
python scripts/legallib_join_dryrun.py \
  --resolver     ~/alo-ai/work/legallib_dl/resolver_decisions.jsonl \
  --legallib-dir ~/alo-ai/work/legallib_dl \
  --toc-dir      "<Box>/app/data/toc" \
  --books        "<Box>/app/data/books.json" \
  --policy       data/toc_merge_policy_legallib.json \
  --out          build/legallib_dryrun
```

**L1 self-verify（全て満たすこと）**:
1. exit 0（= 保護対象への書き込み候補ゼロ）。
2. `build/legallib_dryrun/report.md` の「不変条件違反 0 件 ✅」。
3. `actions.jsonl` の `overwrite_simple`+`create` が妥当（新規 auto_accept ≈1,495。
   既merge 344 は `skip_idempotent`）。
4. `blocked_*`（誤マージ防止）件数を report に記録。

## 4. 戻す成果物（本リポジトリへコミット）

`handoff/legallib_dryrun_<YYYYMMDD>/` に**小さいファイルだけ**:
- `report.md` / `actions.jsonl`
- `overwrites_bundle.jsonl`（旧+新ノード）/ `review_bundle.jsonl`（既存+候補）
- `review_queue.jsonl` / `defer_staging.jsonl`

加えて STEP 0 の `pipeline_snapshot_before.json`（接合後にもう一度採って
`_after.json` も）を `handoff/` に。
**`proposed/`・`books.json`・`legallib_dl/` は戻さない**（大きい/機微）。

## 5. スコープ外（やらない）

- journal（雑誌 422 号）の本接合（別タスク）。`content_type=="book"` のみ対象。
- **本適用（実書き込み）**: 人手レビュー承認後に
  `legallib_join_apply.py --commit --only-isbns approved_isbns.txt` で別途。
  ドライランでは絶対に書かない。

## 6. 進めかた

auto-decide で可。判断ポイントは戻りの `report.md` 末尾に「観測/選択肢/採択/理由」で記録。
preflight が乖離を示したら、それ自体を web への質問として戻す
（converter/loader の調整は web 側で行う）。守秘: 設計・件数レベルのみ、実依頼者データなし。
