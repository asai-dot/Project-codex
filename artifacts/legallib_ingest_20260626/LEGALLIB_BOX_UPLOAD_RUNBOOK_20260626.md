# LEGALLIB_BOX_UPLOAD_RUNBOOK_20260626 — legal-library を Box に上げる実行キット

```yaml
doc_id: LEGALLIB-BOX-UPLOAD-RUNBOOK-20260626
status: ready_to_run (Mac側で実行 → 完了したらクラウドで投入設計を再開)
created_at: 2026-06-26 JST
author: Claude (claude.ai head) — 浅井さん指示「legal-library の Box アップロード進めよう」
gate: クラウド側は宛先フォルダ作成のみ実施。バイト転送は Mac 側（現物が Mac にしか無いため）。
supersedes_dest_note: LEGALLIB_HANDOFF_20260622.md §2-3（"02_文献配下" は誤り。lionboltは実際ルート直下）
```

## 0. 宛先（クラウド側で作成済み・確定）

| 項目 | 値 |
|---|---|
| Box 宛先フォルダ | **`LEGALLIB_法律ライブラリ_20260626`** |
| **folder id** | **`394166766544`** |
| 場所 | Box ルート直下（`すべてのファイル`/0）＝ lionbolt `388659455439` の兄弟 |
| 所有者 | 浅井 悠太 (asai@asai-lo.com) |

→ **このフォルダに Mac の `~/alo-ai/work/legallib_dl/` の中身を上げるだけ**。フォルダ作成は不要。

## 1. なぜ Mac 側なのか

現物（投入元 JSONL・目次データ）は **Mac `~/alo-ai/work/legallib_dl/` にしか存在しない**。
Box にも無く、クラウド実行環境からは到達できない（添付でも届いていない）。
よってバイト転送は Mac 側でしか実行できない。承認の問題ではなく所在の問題。

## 2. アップロード前の棚卸し（Mac で先に確認）

lionbolt の現物に倣って、上げる前に以下を控える（投入ローダ設計の一次ソースになる）:

```bash
cd ~/alo-ai/work/legallib_dl/
ls -la                                   # 何があるか（JSONL/CSV/REPORT等）
wc -l *.jsonl                            # 件数。台帳v1.1では 4,051冊 / TOC 662,717ノード
head -n 1 *dedup*.jsonl | python3 -m json.tool | head -60   # 1レコードのスキーマ
```

確認ポイント（lionbolt との差分がローダ改修点になる）:
- 投入元になる dedup 済み JSONL はどれか（lionbolt の `catalog_dedup.jsonl` 相当）
- 1レコードのフィールド名（isbn/title/author/publisher/pub_date/page_count）
- **目次の構造**（lionbolt は `toc.items[].{text,level,startHeadlinePage}`。legallib の形は？）
- 件数が台帳（4,051冊 / 662,717ノード）と一致するか

可能なら lionbolt 同様の `REPORT.md`（取得元・スキーマ・件数・制約）を1枚作って同梱する。

## 3. 実行 — パスA（推奨）: Mac 側 Claude Code（Box MCP 付き）に丸投げ

Mac の Claude Code セッションに以下をそのまま貼る:

> `~/alo-ai/work/legallib_dl/` の中身を Box のフォルダ id `394166766544`
> （`LEGALLIB_法律ライブラリ_20260626`）にアップロードして。対象は投入元の
> dedup JSONL・INDEX・REPORT.md・チェックサム。各ファイルの Box file id と SHA256 を
> 一覧で返して。巨大ファイル（数十MB〜）はそのまま上げてよい。本文PDF等は対象外、
> 書誌+目次データのみ。

## 4. 実行 — パスB（フォールバック）: シェル（lionbolt を上げた手段を流用）

lionbolt を上げた方法（rclone / box CLI 等）があればそれを使う。例（rclone 設定済みの場合）:

```bash
# remote 名は各自の設定に合わせる。宛先は作成済みフォルダ id 394166766544。
rclone copy ~/alo-ai/work/legallib_dl/ box:/LEGALLIB_法律ライブラリ_20260626/ \
  --include "*.jsonl" --include "*.csv" --include "*.md" -P
cd ~/alo-ai/work/legallib_dl && shasum -a 256 *.jsonl *.csv *.md > SHA256SUMS.txt
# SHA256SUMS.txt も同フォルダへ上げる
```

## 5. 完了後にクラウド側へ渡すもの（次セッションの起点）

最低限これだけあれば lionbolt と同枠で投入設計に入れる:
- アップロードした **Box file id 一覧**（特に投入元 dedup JSONL）
- 1レコードのスキーマサンプル（目次構造を含む）
- 件数（冊数 / TOCノード数）

## 6. 上がった後にクラウドでやること（lionbolt と同枠）

1. read-only fingerprint で **正味ユニーク冊数**を見積り（既存 33,170 行 = asai+bencom+lionbolt と
   どれだけ重複するか）。662,717 の額面に対する"上積み実数"を数字で確定 → 投入価値の最終判断。
2. `biblio.library_sources` に `legal-library` を1行登録。
3. `load_legallib.py`（`tools/lionbolt_ingest/load_lionbolt.py` を雛形に、目次構造マッピングだけ差替）
   + マイグレーションを **PR提出**（実行は ratify 後、lionbolt と同じ作法）。
4. dedup は ISBN/fingerprint で **レポートのみ**、biblio_item mint は HOLD。

## 7. 投入後の到達点（参考・台帳の設計総量に接近）

| source | 冊数 | bib_toc |
|---|---:|---:|
| asai-bookshelf | 6,524 | 0（PDF-TOC未抽出） |
| bencom-library | 3,802 | 552,544 |
| lionbolt | 22,844 | 236,674（投入済・現況実測） |
| **legal-library（本アップロード後）** | **4,051** | **662,717（額面。正味は§6.1で確定）** |
| 合計 | 37,221 | 約 1,451,935 |
```
注: legal-library 662,717 はカタログ額面。重複ぶんは投入時に整理（mintはHOLD）。
事務所PDF由来TOC（611本ぶん）は別工程で未抽出。
```
