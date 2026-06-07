# INSTRUCTION: legallib → biblio 取込 inspect & ingest（headless 自動実行用 v1.0）

- 宛先: **Mac CC ワーカー（claude-planner, headless）** ＝ `~/alo-ai/work/legallib_dl/` と Supabase
  service_role を持つインスタンス
- 発信: Claude（浅井さん担当・リモートセッション）/ 2026-06-07
- 上位: `project-codex` の `docs/legallib-seed-build-plan.md` **v0.5**（GPT お目付け役監査 INGEST gate 投函済・返答待ち）
- 状態: instruction → **Phase 0 は即着手可（ゲート不要）** / Phase 1 は監査 PASS でアンロック
- 想定所要: Phase 0 ＝ 5〜10分 / Phase 1 ＝ 約3〜5分（bencom 55万TOC 実測 ≈3分）

---

## 0. 一行サマリ（成功条件）

`~/alo-ai/work/legallib_dl/*.json` の実フィールド名を `load_legallib.py --inspect` で確定し、
未解決キーがあれば候補に追記して**全フィールドが解決**する状態にする（＝Phase 0 完了）。
その後、GPT 監査 `INGEST_PASS`/`PASS_WITH_NOTES` ＋ owner ratify が出たら **Phase 1（実投入）**へ進み、
`source='legal-library'` の bib_records が **2,751冊**（雑誌を含めるなら +422号）入り、`sanity_checks.sql` 全項目 PASS。

---

## 1. 前提資産（実行前に存在確認）

- 入力: `~/alo-ai/work/legallib_dl/*.json`（書籍2,751 + 雑誌422、ファイル名 stem = legallib 内部 book_id、
  書籍/雑誌は `content_type` で区別）
- コード: `asai-dot/Project-codex` の `loaders/load_legallib.py` + `loaders/sanity_checks.sql`
  （ブランチ: main にマージ済なら main、未マージなら `claude/legal-library-metadata-impact-HBoXn`）
  ※ ローダ正本の最終置き場は private `asai-biblio-ingest`。本手順はドラフトを取得して走らせる。
- 認証（環境変数）: `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_SCHEMA=biblio`
  （**Phase 0 では不要**。Phase 1 でのみ使用。service_role キーは Box 等に出さない）

---

## 2. セットアップ（冪等）

```bash
set -euo pipefail
WORK=~/alo-ai/work/legallib_dl
REPO=~/alo-ai/work/_project-codex
# コード取得（あれば pull、無ければ clone）
if [ -d "$REPO/.git" ]; then
  git -C "$REPO" fetch origin && git -C "$REPO" checkout claude/legal-library-metadata-impact-HBoXn && git -C "$REPO" pull --ff-only
else
  git clone -b claude/legal-library-metadata-impact-HBoXn <project-codex remote URL> "$REPO"
fi
python3 -m pip install -q supabase   # Phase 1 用。Phase 0(--inspect/--dry-run)は無くても動く
cd "$REPO"
```

---

## 3. Phase 0 ―― inspect & dry-run（ゲート不要・即実行）

### 手順
```bash
# 3-1. 書籍・雑誌それぞれのキー検出
python3 loaders/load_legallib.py --inspect --limit 5 --source-dir "$WORK"

# 3-2. dry-run（DB 触らない）で射影件数を確認
python3 loaders/load_legallib.py --dry-run --source-dir "$WORK"            # 全体
python3 loaders/load_legallib.py --dry-run --book-only --source-dir "$WORK" # 書籍のみ
```

### 未解決キーがあったら（self-decide で修正）
`--inspect` 出力で `<- None` と表示されたフィールドは候補キーに実キーが無い。
`loaders/load_legallib.py` 冒頭の対応する `*_KEYS` タプル**先頭**に実キー名を追記して再実行する。
対象タプル: `TITLE_KEYS / ISBN_KEYS / AUTHOR_KEYS / PUBLISHER_KEYS / PUB_YEAR_KEYS / PUB_DATE_KEYS /
CONTENT_TYPE_KEYS / BOOK_ID_KEYS / SOURCE_URL_KEYS / TOC_KEYS / TOC_TEXT_KEYS / TOC_PAGE_KEYS / TOC_LEVEL_KEYS`。
修正は最小差分で。判断は §6 フォーマットで report に記録。

### L1 self-verify（全部通れば Phase 0 PASS）
1. **書籍1冊以上**で `title / author / publisher / content_type` が非None で解決
2. **雑誌1号以上**で `title / content_type(journal判定)` が解決
3. TOC ノードの `text / page / level` が両系統（生 legallib_dl・正規化後）で解決し、`extract_toc_nodes` が >0 行
4. `--dry-run --book-only` の bib_records 件数が **2,751 ±数件**（欠損/重複は report に列挙）
5. ローダ修正後、`--inspect` に `<- None`（必須フィールド）が残っていない

---

## 4. Phase 1 ―― 実投入（**ゲート: GPT `INGEST_PASS`/`PASS_WITH_NOTES` ＋ owner ratify 必須**）

> ゲート未達なら Phase 1 を**実行しない**。Phase 0 報告だけ出して待機。

```bash
export SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... SUPABASE_SCHEMA=biblio
# 4-1. 少量で本番経路を確認
python3 loaders/load_legallib.py --book-only --limit 20 --source-dir "$WORK"
# 4-2. 全件（書籍）。雑誌を含めるかは plan §6＝次スコープに従い既定では --book-only
python3 loaders/load_legallib.py --book-only --source-dir "$WORK"
# 4-3. 検証
psql "$DATABASE_URL" -f loaders/sanity_checks.sql   # または Supabase SQL エディタで実行
```

### L1 self-verify（Phase 1）
- `sanity_checks.sql` ①〜⑦が期待どおり（特に: legal-library 件数=2,751 / bib_toc 孤児0 / ordinal 0始連番 /
  既存 source 改変0 / 誤統合0）
- **再実行 diff 0（冪等）**: 4-2 を二度流して件数不変

---

## 5. 番頭への handoff（報告）= GPT 再監査 PASS の6点を満たす形で出す

`~/alo-ai/work/legallib_dl/REPORT_legallib_inspect_<YYYYMMDD>.md` を起票。
**INGEST_RESULT(NEED_MORE) が PASS_WITH_NOTES へ上げる条件＝下記6点をこの報告で充足させる**こと：
1. **legallib raw JSON 3サンプルの全文**（通常書籍1 / 巻末索引あり1 / TOC深い1）を貼付
2. **確定 mapping table**（top-level: title/author/publisher/isbn/pub_year/content_type/book_id・
   TOC: text/page/level・index: 索引語キー）← `--inspect` 出力から確定
3. `--dry-run --limit 3` の**出力例**（実コンソール）
4. （Phase 1 実行時）既存 asai-bookshelf/bencom に**差分0** test の結果（sanity `⑪` 前後突合）
5. （Phase 1 実行時）**再実行 diff 0**（sanity `⑥` 二回突合）
6. 著者**誤統合0**の初期ID戦略の確認（per-occurrence 既定。sanity `⑩` が0行）
- 加えて: ローダ修正差分（`*_KEYS` を触ったら）、L1 self-verify pass/fail、判断ログ（§6）
- 報告先: Mac ローカル ＋ Box `CODEX/handoff/`（実シークレットは貼らない）

> ↑この6点が揃えば、リモート Claude が plan を v0.5.2 として `supersedes:
> 20260606_legallibbiblio_v0.5_INGEST` で `to_gpt/` へ差分再投函し PASS を取りにいく。

報告先: 上記 Mac ローカル ＋ Box `CODEX/handoff/` に同名でアップロード（実シークレットは貼らない）。

---

## 6. 判断ログ・フォーマット（auto-decide 前提）

実装中の判断は self-decide で進め、下記で記録：
```
- 観測: <何が起きたか>
- 選択肢: <A vs B>
- 採択: <A or B>
- 理由: <なぜ>
```

---

## 7. 進めかた（suggested sequence）
1. §2 セットアップ → 2. §3 Phase 0（inspect/dry-run/未解決キー修正/L1）
3. §5 報告（Phase 0 分）を起票・Box 投函 → 4. ゲート確認（GPT 監査 RESULT）
5. PASS なら §4 Phase 1 → 6. §5 報告に Phase 1 追記

> 重要: Phase 0 は安全（読み取り＋dry-run のみ）。**ゲートを待たず即実行してよい**。
> Phase 1 は DB 書き込み。**ゲート未達では絶対に実行しない**。
