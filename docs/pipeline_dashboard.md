# パイプライン進捗ダッシュボード

静的DB（蔵書 canonical / BookDX）と動的DB（ALOナレッジ / matter / Gmail / lawtime）の
**全体像と進捗を 1 枚で可視化**する。何が終わり・どこが詰まり・どこから入れるか、
そして **to_gpt→from_gpt の GPT 往復が戻っているか**を表示する。

## 仕組み（3 部品）

```
pipeline/pipeline.json   ← 地図 (ステージ/依存/進捗の測り方=probe) を宣言
        │
scripts/pipeline_probe.py  ← 実ファイルシステムを走査して snapshot.json を出力
        │  (重い走査は Mac。snapshot は小さいので web へ戻せる)
        ▼
scripts/pipeline_dashboard.py ← manifest+snapshot から status を導出し MD/HTML 描画
```

- **runtime_status**: `done ✅` / `in_progress 🔄` / `waiting ⏳`(GPT/OCR 戻り待ち) /
  `blocked ⛔`(依存未完で入れない) / `todo ⬜` / `error ❗`。
  これは **実行・運用状態**の軸であり、DD-STATUS-REGISTRY の artifact lifecycle
  （draft/candidate/accepted/canonical…）とは**別軸**（混同しないこと）。
- **probe 種別**:
  - `count` — glob 件数 vs `expected`（取得率。「出せてない/未取得」）。
  - `exists` — 成果物の有無（% は出さず `有/無/一部` 表示）。
  - `roundtrip` — `sent`(例 `to_gpt/*REQUEST`) と `returned`(`from_gpt/*RESULT`) を
    **front-matter の `request_id` / `result_expected_filename` を優先**して突合（無ければ
    filename stem fallback）。`pending`(戻ってない) / `stale`(古いまま戻らない=詰まり) / `orphan`。
  - `orphan` — `scan` glob にあって `declared` globs に無い「未宣言成果物」を出す（manifest ドリフト検知）。

## 使い方

```bash
# 1) Mac 側で状態収集 (roots は複数指定可)
python scripts/pipeline_probe.py --manifest pipeline/pipeline.json \
  --root bookdx="<Box>/事務所内本棚DX化計画" \
  --root alo="$HOME/alo-ai" \
  --root repo="$(pwd)" \
  --out build/pipeline_snapshot.json

# 2) どこででも描画 (snapshot だけあれば web 側で OK)
python scripts/pipeline_dashboard.py --manifest pipeline/pipeline.json \
  --snapshot build/pipeline_snapshot.json \
  --out-md build/dashboard.md --out-html build/dashboard.html

# 収集+描画を一発で:
python scripts/pipeline_dashboard.py --manifest pipeline/pipeline.json \
  --root bookdx=... --root alo=... --root repo=... --out-html build/dashboard.html
```

snapshot は純データなので、**日次でコミットして差分を見れば進捗の動き**も追える。

## マニフェストの育て方

`pipeline/pipeline.json` が「地図」。stage を足す・`expected` や `path` を実環境に
合わせる・`depends_on` で順序を表すだけ。probe の `root` は `roots` の名前
（`bookdx`/`alo`/`repo`）を指す。実ファイル名が分かったら `path` を実体へ寄せる
（NDL レポート名・matter 完了ログ名など `note` に TODO を残してある）。

## 設計メモ

- stdlib のみ・決定的。snapshot に status を持たせず描画時に導出するので、
  同じ snapshot から MD/HTML どちらも・いつでも再描画できる。
- `roundtrip` のキー化は既定で末尾 `REQUEST/RESULT/RESPONSE…` を落として突合。
  特殊命名は probe の `key_pattern`(正規表現, group1) で上書き可。
- `stale` の閾値は probe の `max_age_hours`（既定 24h）。

## v0.2（GPT DDPROGRESS 監査反映）

GPT Pro DD レビュー（`from_gpt/20260606_codexprogress_v0.1_DDPROGRESS_RESULT.md`）の
判定は **`DDPROGRESS_PASS_WITH_NOTES`**（方向性は採用可・独立した「観測 dashboard」
として扱う）。指摘6点を v0.2 で反映:

1. **runtime_status 命名**: lifecycle 軸と混同しないよう `runtime_status` と明示し、表に脚注。
2. **roundtrip キーの堅牢化**: front-matter `request_id` / `result_expected_filename` 優先突合。
   版差（v0.1↔v0.2）・再投函・別名 RESULT でも誤対応しない。stale 基準も front-matter
   `submitted_at/created_at` → `request_id` 先頭日付 → mtime の順で確度の高い時刻を採用。
3. **manifest 検証**: `validate_manifest()` が duplicate id / unknown dependency / cycle /
   unknown root / invalid probe type を検出。`pipeline_probe.py` は probe 前に検証し、
   壊れていれば走らせない（exit 1）。dashboard はエラーをバナー表示。
4. **orphan probe**: 未宣言成果物（manifest が拾っていない handoff 等）を炙り出す。
5. **exists-only の % 廃止**: 連続 % ではなく `有/無/一部` を表示（誤誘導回避）。
6. **snapshot メタ**: `generated_at_jst` / `manifest_hash` / `probe_version` を付与。

## v0.2.1（DDPROGRESS v0.2 監査 PASS_WITH_NOTES の追修正）

差分再監査（`from_gpt/20260607_codexprogress_v0.2_DDPROGRESS_RESULT.md`）は
**`DDPROGRESS_PASS_WITH_NOTES`**（F1/F2/F3/F5/F6 CLOSED、F4 PARTIAL）。指摘を反映:

- **N1（F4 を完全に閉じる）**: manifest 検証を `collect()` 自体に移し、不正なら
  `ManifestError` を送出（`refuse_on_errors=True` 既定）。これにより
  `pipeline_probe.py` だけでなく **`pipeline_dashboard.py --root` の一発経路でも
  probe 前に拒否**（exit 1）。snapshot だけ描画したい場合のみ
  `collect(..., refuse_on_errors=False)`。
- **N2（重複 request_id）**: roundtrip は同一 `request_id` の再送信を silent dedupe
  せず `duplicate_count` / `duplicates`（expected 不一致フラグ付き）で表に出す。
- **N3（命名の正道）**: filename stem fallback は最後の逃げ道として残すが、正規運用は
  front-matter `request_id` / `result_expected_filename` を正とする
  （`.processed.md` 等の混在で stem 頼みは誤対応の元）。
