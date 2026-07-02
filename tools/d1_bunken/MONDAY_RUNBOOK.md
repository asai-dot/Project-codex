# 戻ってきた後の手順（D1文献編 全雑誌スイープ 後処理）

スイープ（`~/d1_full_sweep.log`）が回り切った後、Mac で**上から順に**流すだけ。
全部 `~/Project-codex` 直下のツールで完結。元データは触らない（追加生成のみ）。

前提パス（環境変数で上書き可）:
- downloader: `~/.gemini/antigravity/scratch/d1_bunken_downloader.py`
- parser: `~/ALOBookDX/事務所内本棚DX化計画/scripts/d1_bunken_parse_all.py`
- build: `~/ALOBookDX/事務所内本棚DX化計画/build/d1_bunken_article_meta_20260611/`
- repo: `~/Project-codex`（このリポを最新化: `cd ~/Project-codex && git pull`）

---

## 0. スイープが終わったか確認
```bash
pgrep -fl d1_bunken_downloader || echo "完走 or 停止"
grep -c '^###' ~/d1_full_sweep.log          # 何誌処理したか（目標 896+）
tail -5 ~/d1_full_sweep.log
```
まだ走っていたら、終わるまで待つ（このまま放置でOK）。

## 1. 0件をトリアージ（本当に検討すべき誌だけ抽出）
```bash
cd ~/Project-codex && git pull
python3 tools/d1_bunken/triage_sweep_log.py ~/d1_full_sweep.log --tsv /tmp/d1_triage.tsv
```
出力の `② 真ゼロ＝要・表記当て直し` が本命。`③ Timeout由来` は再試行候補。
`①括弧別名` と `データ安全` は無視可。

## 2. ②真ゼロ誌を別表記でリトライ（owner_sanction 範囲内）
```bash
bash tools/d1_bunken/retry_truezero.sh
cat /tmp/d1_retry_truezero.log    # ✅HIT=取得できた / ❌=非収録確定
```
- 手当て候補は `tools/d1_bunken/truezero_retry_candidates.tsv`（慶應「法学研究」旧字、商事法務研究→商事法務 等）。
- 候補に無い誌は自動で「括弧除去ベース名」を試す。
- ③Timeout誌が気になれば個別に `python3 ~/.gemini/antigravity/scratch/d1_bunken_downloader.py "<誌名>" 0` で再試行（フレーキーなだけなので大抵取れる）。

## 3. 確定（再パース→ラベル→カバレッジ差分）
```bash
bash tools/d1_bunken/step4_finalize.sh
```
これ1本で: 再パース → v0.2.1ラベル → 0件トリアージ再実行 → **カバレッジ差分**（333,206/74.1% → ?）を表示。

## 4. RESULT を書いて完了
`docs/worker_queue/done/W-20260626-010_RESULT.md`（先頭行 `WORKER_PASS`）に転記:
- before/after: unique_articles（333,206 → ?）・カバレッジ%・canonical誌数
- 取得できた誌数 / ②リトライでHITした誌 / ❌非収録確定の誌一覧
- 896外（D1カタログ探索）の結果 or 「要カタログ源」
- 元データ無改変（追加のみ）の明記

その後 `doing/W-20260626-010_PROGRESS.md` を done 化（`alo-worker complete W-20260626-010`）。
最終数値は status報告（`docs/status/20260619_D1bunken_acquisition_status.md`）に反映。

---

### 補足: 全部 assistant に投げたい場合
このスレに `~/d1_full_sweep.log`（と 2 のリトライ後なら `/tmp/d1_retry_truezero.log`）の中身を貼れば、
トリアージ結果の解釈・カバレッジ差分の計算・RESULT草案まで assistant 側でやる。
取得/パース/ラベルの**実行**だけは Mac 側（assistant は Mac に触れないため）。
