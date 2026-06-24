---
request_id: 20260607_codexprogress_v0.2_DDPROGRESS
topic: codexprogress
gate: DDPROGRESS
version: v0.2
source_hash: sha256:b863b4f421cafdbec91473322dc739e1985972d499426e19e01b0e2c35500952   # pipeline.json + scripts/pipeline_probe.py + scripts/pipeline_dashboard.py + docs/pipeline_dashboard.md
git_commit: b5c95403f77050c0103562322db93abf1af01590
git_branch: claude/legallib-integration-design-Jgrtf
git_pr: https://github.com/asai-dot/Project-codex/pull/5
supersedes: 20260606_codexprogress_v0.1_DDPROGRESS
prior_result: from_gpt/20260606_codexprogress_v0.1_DDPROGRESS_RESULT.md (DDPROGRESS_PASS_WITH_NOTES)
result_expected_filename: 20260607_codexprogress_v0.2_DDPROGRESS_RESULT.md
status: queued
---

# 20260607 codexprogress v0.2 — GPT Pro **差分再監査** REQUEST（pipeline dashboard）

- gate: **DDPROGRESS** / topic: codexprogress / version: v0.2 / 起票: 2026-06-07 / 番頭: web CC
- RESULT 先頭行: `DDPROGRESS_PASS` / `DDPROGRESS_PASS_WITH_NOTES` / `DDPROGRESS_MODIFY_REQUIRED` / `DDPROGRESS_FAIL` / `DDPROGRESS_NEED_MORE`
- 種別: **T2 差分のみ**。v0.1 で方向性は採用可（PASS_WITH_NOTES, regression無し確認済）。指摘6点の閉じだけ確認いただきたい。

## 0. これは差分再監査
v0.1 判定 = `DDPROGRESS_PASS_WITH_NOTES`（RESULT 2269700668702）。**核設計（独立観測レイヤ・runtime_status 軸の分離・DB=Git投影）は確認済**。挙げられた load-bearing findings 6点を v0.2 で閉じた。**v0.1↔v0.2 差分が6点を閉じているか**だけ見てほしい。閉じていれば `DDPROGRESS_PASS`。

## 1. 反映した6パッチ（あなたの finding 番号に対応）
- **F1（status 命名）**: 文書・dashboard 出力で **`runtime_status`** と明示。MD/HTML に「artifact lifecycle ではない」脚注を追加。registry の lifecycle 語（draft/candidate/accepted/canonical…）と列・語彙を分離。
- **F2（roundtrip keying＝最大リスク）**: stem 突合をやめ、**front-matter `request_id` を第一キー**、無ければ **`result_expected_filename` を returned のファイル名と突合**、それも無ければ filename stem fallback。版差（v0.1↔v0.2）・再投函・別名 RESULT・supersedes で誤対応しない。**stale 基準時刻**も front-matter `submitted_at/created_at/recorded_at` → `request_id` 先頭8桁日付 → file mtime の順で確度の高い時刻を採用（mtime 依存を緩和）。
- **F3（manifest drift）**: `orphan` probe 種別を新設（`scan` glob にあって `declared` globs に無い未宣言成果物を列挙）。manifest に handoff ドリフト検知ステージ（ops track）を追加。
- **F4（DAG 検査）**: `validate_manifest()` を新設し、**duplicate stage id / unknown dependency / cycle / unknown root / invalid probe type** を検出。collector は **probe 実行前に検証し、エラーがあれば走らせず exit 1**。dashboard はエラーをバナー表示し snapshot に `manifest_errors` を保持。
- **F5（exists-only の % 誤誘導）**: exists/orphan のみのステージは連続 % を出さず **`有 / 無 / 一部`** 表示（HTML も binary present）。count probe があるステージのみ進捗バー＋%。
- **F6（snapshot 時刻正本）**: snapshot に **`generated_at_jst` / `manifest_hash` / `probe_version`** を付与。stale は F2 のとおり front-matter 優先。

## 2. 監査対象（GitHub コネクタで直接読めます）
- PR: https://github.com/asai-dot/Project-codex/pull/5 / commit `b5c9540`
- 中核: `scripts/pipeline_probe.py`（probe/validate/collect, v0.2）/ `scripts/pipeline_dashboard.py`（runtime_status 描画）/ `pipeline/pipeline.json`（orphan ステージ追加）/ `docs/pipeline_dashboard.md`（§v0.2）
- 旧版判定: `from_gpt/20260606_codexprogress_v0.1_DDPROGRESS_RESULT.md`
- 照合アンカー: DD-STATUS-REGISTRY-001 v0.2（lifecycle 軸）/ codexgov v0.1 IMPL（quality 軸）

## 3. 確認してほしい点（差分のみ）
1. **F2 が閉じたか**: front-matter 優先突合で、版差/再投函/別名 RESULT/旧queue残骸の誤対応が無くなったか。残る穴は（例: 同一 request_id の重複、RESULT 側に request_id が無く expected も別名のケース）。
2. **F4 が十分か**: duplicate/unknown dep/cycle/unknown root/invalid type で DAG 事故を防げるか。抜けている検査は（例: 自己依存、トラック跨ぎの意図しない block、空 probe ステージ）。
3. **F3/F5/F6** の方向は妥当か（orphan の declared 運用、binary present 表示、manifest_hash の使い所）。
4. v0.1 で確認済の核設計に、v0.2 で **新たな regression** が混入していないか。

→ 閉じていれば `DDPROGRESS_PASS`。残課題は finding 番号付きで `PASS_WITH_NOTES` か `MODIFY_REQUIRED`。

## 4. 検証状況（自己申告）
- 合成フィクスチャのテスト 37 checks（front-matter 突合・manifest 検証・orphan・metadata 含む）＋関連 106 = 143 checks 緑、CI 緑。
- 実 to_gpt/from_gpt 命名（`..._DDPROGRESS_REQUEST/RESULT.md` 等）で front-matter 突合が機能し、v0.1↔v0.2 を誤対応しないことを確認済。
- 守秘: 設計・状態語彙・スキーマ名・ファイル構成レベルのみ。実案件・依頼者データ・実シークレットなし。

---
# 現物: status 導出規則の差分（runtime_status / exists 表示 / manifest 検証）

```
# pipeline_probe.collect (v0.2): probe 前に validate_manifest、snapshot にメタ付与
errors = validate_manifest(manifest)   # duplicate id / unknown dep / cycle / unknown root / invalid type
if errors: refuse (exit 1)
snapshot = {generated_at_jst, probe_version, manifest_hash, manifest_errors, roots, stages}

# roundtrip 突合 (v0.2): front-matter 優先
rid       = front_matter.request_id  or  stem_strip(REQUEST_suffix)
matched   = rid in returned.request_ids
            or rid in returned.stem_keys
            or (result_expected_filename in returned.filenames)
stale_ts  = fm.submitted_at/created_at  or  request_id[:8]日付  or  file.mtime

# dashboard 表示 (v0.2): runtime_status / exists は % を出さない
progress  = bar+%      if stage has count probe
            else 有/無/一部   if exists|orphan only
            else 完/待ち      if roundtrip
footer    = "状態は runtime_status（実行・運用状態）。artifact lifecycle とは別軸。"
```
