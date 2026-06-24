---
request_id: 20260606_codexprogress_v0.1_DDPROGRESS
topic: codexprogress
gate: DDPROGRESS
source_hash: sha256:33860dbf80a61445679bfb29af288a030eb9c375f7708731d52ea7514750d7cb   # pipeline.json + scripts/pipeline_probe.py + scripts/pipeline_dashboard.py + docs/pipeline_dashboard.md
git_commit: 8edf8bdf03d3ddc1a4191a712967ca5ba8b06fe4
git_branch: claude/legallib-integration-design-Jgrtf
git_pr: https://github.com/asai-dot/Project-codex/pull/5
supersedes: null
result_expected_filename: 20260606_codexprogress_v0.1_DDPROGRESS_RESULT.md
status: queued
---

# GPT Pro お目付け役 監査依頼: Codex 進捗可視化レイヤ（pipeline dashboard）DDPROGRESS

- gate: **DDPROGRESS** / topic: codexprogress / version: v0.1 / 起票: 2026-06-06 / 番頭: web CC
- RESULT 先頭行: `DDPROGRESS_PASS` / `DDPROGRESS_PASS_WITH_NOTES` / `DDPROGRESS_MODIFY_REQUIRED` / `DDPROGRESS_FAIL` / `DDPROGRESS_NEED_MORE`
- requested_verdict: ① この「運用進捗の観測レイヤ」を status-registry / codexgov governance とは**別レイヤ**として持つ方向が妥当か ② probe/status モデルの過不足 ③ accept 可否＋v0.2 必須修正

## 趣旨（なぜ別family監査か）
静的DB（蔵書 canonical / BookDX / legaldb）と動的DB（ALOナレッジ/matter/Gmail/lawtime）の構築が**多数のワークストリーム並行**で進み、全体像（何が終わり・どこが詰まり・どこから入れるか・GPT 往復が戻っているか）が見えにくい、という浅井さんの課題に対し、番頭(web Claude)が**進捗可視化レイヤ**を実装した。同 family Claude は blind spot を共有し独立監査が成立しないため（DD-CLAUDEHEAD A-1）、GPT Pro に、**この設計が既決原則（DB=Git投影 / 状態語彙の一軸原則）と整合し、過剰設計・盲点・他DDとの重複がないか**を地に足の付いた事実で検証してほしい。

## これは何か（仕組みの要約）
3 部品・stdlib のみ・決定的:
1. **manifest（地図）** `pipeline/pipeline.json`: ステージ／依存(`depends_on`)／進捗の測り方(`probes`)を宣言した DAG。静的・動的の2トラックを実ワークストリームで初期化。
2. **probe/コレクタ** `pipeline_probe.py`: 実FS（複数 root: bookdx=Box / alo=~/alo-ai / repo=checkout）を走査し `snapshot.json`（純データ）を出力。probe 種別:
   - `count`  : glob 件数 vs expected（取得率。「出せてない/未取得」）
   - `exists` : 成果物の有無
   - `roundtrip`: `to_gpt/*REQUEST` と `from_gpt/*RESULT` をキー突合 → `pending`(未戻り) / `stale`(古い未戻り=詰まり) / `orphan`(送信なしの戻り)
3. **dashboard** `pipeline_dashboard.py`: manifest+snapshot から status を導出し Markdown / 単一HTML を描画。

### status 軸（重要・自己申告）
dashboard の status は **`done / in_progress / waiting / blocked / todo / error`** の **「実行・運用状態」軸**。
これは **DD-STATUS-REGISTRY-001 の lifecycle 軸（draft/candidate/conditional_accept/accepted/canonical/superseded/withdrawn）とは別軸**であり、混在させていない（一軸原則 P0-PATCH-1 の精神を踏襲したつもり）。導出規則:
- `blocked` = `depends_on` に未完ステージあり（入れない）
- `done` = 全 probe 完了 / `waiting` = roundtrip に pending あり / `in_progress` = 部分進捗 / `todo` = 進捗ゼロ / `error` = probe エラー
- snapshot に status は持たせず**描画時に導出**（DB=Git投影原則④：正本は manifest、snapshot は派生で再構築可能）。

## 番頭の自己申告（過信・盲点を独立検証してほしい）
- A: 「運用進捗を status-registry/codexgov とは別レイヤで持つ」のが正しいと判断したが、**重複・責務越境**の疑い（status-registry の status 語彙、codexgov の quality_status と混線していないか）。
- B: `roundtrip` のキー突合を「末尾の REQUEST/RESULT/RESPONSE… を落として一致」で実装。命名規約に依存し、`_v0.2` のような版差や別命名で**誤対応/取りこぼし**しないか（実 to_gpt には `..._DDSTATUS_REQUEST.md` / `..._RESULT.md` 等が混在）。
- C: manifest は手書きの「地図」。**実態とのドリフト**（path/expected が古い、ステージ追加忘れ）を検知する仕組みが無い。
- D: 進捗% を `exists`-only ステージにも 0/100 で出す。**部分進捗を持たない段階で % を見せる誤誘導**はないか。
- E: ETA/throughput/履歴トレンドを持たない（snapshot 日次コミットの差分で代替）。Phase1 でこれで十分か。

## 特に問う論点
1. **レイヤリングの是非**: 進捗観測を独立レイヤにするか、status-registry/codexgov governance に畳むか。一軸原則・DB=Git投影に照らした正解。
2. **状態軸の独立性**: 実行状態軸(done…)と lifecycle 軸(draft…canonical)を別に持つのは健全か、命名衝突（特に "blocked/done" 等）の禁止規則が要るか。
3. **probe モデルの過不足**: count/exists/roundtrip で「インデックスベースのディレクトリ進捗」と「GPT 往復の戻り」を表すのは十分か。roundtrip の堅牢化（key_pattern 必須化？ orphan/stale の扱い）。
4. **manifest ドリフト対策**: 地図と実態のズレを検知する最小機構（未宣言 root 配下の孤児成果物検出、expected の自動推定 等）。
5. **盲点**: 並行多数ステージ・循環依存・複数 root・大量ファイル走査でのスケール/事故。
6. accept 可否＋v0.2 で閉じるべき必須修正。

## 返却様式（PROTOCOL準拠）
- 書き戻し先: `from_gpt/20260606_codexprogress_v0.1_DDPROGRESS_RESULT.md`
- **先頭行 = `DDPROGRESS_<LABEL>`**（LABEL ∈ {PASS, PASS_WITH_NOTES, MODIFY_REQUIRED, FAIL, NEED_MORE}）
- 以降: load-bearing な指摘を「箇所 / 問題 / 根拠 / 推奨修正」で列挙。各判断に確度＋反証条件。PASS 時のみ owner ratify 待ち。

## 監査対象（GitHub コネクタで直接読めます）
- PR: https://github.com/asai-dot/Project-codex/pull/5 / commit `8edf8bd`
- 中核ファイル: `pipeline/pipeline.json` / `scripts/pipeline_probe.py` / `scripts/pipeline_dashboard.py` / `docs/pipeline_dashboard.md`
- 関連（接合本体）: `scripts/legallib_*.py` / `docs/fork1_legallib_join_design.md` / `docs/handoff_mac_session_legallib_join.md`
- 照合アンカー: DD-STATUS-REGISTRY-001 v0.2 / codexgov v0.1 IMPL（同 to_gpt 内）/ DD-CLAUDEHEAD v1.0

## 守秘
設計・状態語彙・スキーマ名・ファイル構成レベルのみ。実案件・依頼者データ・実シークレットなし（fixture は合成）。

---
# 現物① manifest（pipeline/pipeline.json 全文）

```json
{
  "version": 1,
  "title": "ALO 静的/動的DB 構築 パイプライン",
  "roots": {"bookdx": "Box .../事務所内本棚DX化計画", "alo": "~/alo-ai", "repo": "Project-codex checkout"},
  "tracks": {"static": "静的DB (蔵書 canonical / BookDX)", "dynamic": "動的DB (ALOナレッジ/matter/Gmail/lawtime)"},
  "stages": [
    {"id": "toc_baseline", "track": "static", "depends_on": [], "probes": [{"type": "count", "root": "bookdx", "path": "app/data/toc/isbn_*.json", "expected": 5206}]},
    {"id": "legallib_fetch", "track": "static", "depends_on": [], "probes": [{"type": "count", "root": "alo", "path": "work/legallib_dl/*.json", "expected": 422}]},
    {"id": "resolver", "track": "static", "depends_on": ["legallib_fetch", "toc_baseline"], "probes": [{"type": "exists", "root": "alo", "path": "work/legallib_dl/resolver_decisions.jsonl"}]},
    {"id": "legallib_join_dryrun", "track": "static", "depends_on": ["resolver"], "probes": [{"type": "exists", "root": "repo", "path": "handoff/legallib_dryrun_*/report.md"}]},
    {"id": "legallib_review", "track": "static", "depends_on": ["legallib_join_dryrun"], "probes": [{"type": "exists", "root": "repo", "path": "handoff/legallib_dryrun_*/approved_isbns.txt"}]},
    {"id": "legallib_apply", "track": "static", "depends_on": ["legallib_review"], "probes": [{"type": "exists", "root": "bookdx", "path": "app/data/legallib_apply_log.jsonl"}]},
    {"id": "gpt_dd_roundtrip", "track": "dynamic", "depends_on": [], "probes": [{"type": "roundtrip", "root": "alo", "sent": "to_gpt/*.md", "returned": "from_gpt/*.md", "max_age_hours": 24}]}
  ]
}
```
（実ファイルは hasToc/索引/defer_new/lawtime/matter 等を含む全 14 ステージ。上記は抜粋。）

# 現物② status 導出規則（pipeline_dashboard.py: derive）

```
for stage in manifest.stages (順次):
  results = snapshot[stage].probes
  ratio   = mean(probe ごとの count.ratio または done?1:0)
  all_done= results 非空 かつ 全 probe done
  waiting = いずれかの roundtrip に pending>0（stale= pending かつ mtime 経過 > max_age_hours）
  unmet   = depends_on のうち done でないもの
  status  = error    if probe エラー
            blocked  elif unmet
            done     elif all_done
            waiting  elif waiting
            in_progress elif ratio>0
            todo     else
  done_map[stage] = (status == done)   # 後続ステージの blocked 判定に使用
```

# 現物③ 出力例（合成途中状態での描画・抜粋）

```
## サマリ
✅done 1  🔄in_progress 1  ⏳waiting 1  ⛔blocked 9  ⬜todo 2  ❗error 0

## 要注目
⏳ 戻り待ち: GPT DD 往復 (DD 戻1/送3(未2)) — ⚠stale 1
⛔ 依存待ちで入れない: resolver ← 未完: legallib_fetch ; legallib 接合 ドライラン ← 未完: resolver ...
▶ いま入れる (依存done・未着手): NDL 正本照合・正規化 ; matter ID 解決

## 未戻り明細 (to_gpt → from_gpt)
- [gpt_dd_roundtrip] 20260601_old (送信: 20260601_old_REQUEST.md)
- [gpt_dd_roundtrip] 20260606_matterX (送信: 20260606_matterX_REQUEST.md)
```
