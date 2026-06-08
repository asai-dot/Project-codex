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

### 合言葉 `/dd` と日次収集（ワンクリック）

- **見る側（どこでも）**: Claude セッションで `/dd`（または「DD全体の現状教えて」）と言うと、
  コミット済み snapshot を描画して **HTML を画面に出し、サマリ＋要注目をチャットに要約**する。
  定義は `.claude/commands/dd.md`。read-only 観測のみ。
- **採る側（Mac）**: `scripts/dd_collect.command`（Finder ダブルクリック可）が
  実フォルダを走査 → `pipeline/pipeline_snapshot.json`（tracked）へ採取 → 描画 → コミット。
  `--push` で push まで、`--no-commit` で試走。root は `ALO_BOOKDX_ROOT` / `ALO_ALO_ROOT`
  で上書き可（無い root のステージは todo 表示になるだけ）。
  これを日次で回すと `/dd` が常に前日比つきの最新を出せる。

> **manifest 検証は両経路で効く（v0.2.1 / N1）**: 上の「収集」も「収集+描画を一発で」も
> 内部で `collect()` を通る。`collect()` 自体が不正 manifest（重複 id / 未知依存 / 循環 /
> 未知 root / 不正 probe type）を**既定で拒否**（`ManifestError` → exit 1, 出力は書かない）
> ので、どちらの入口でも壊れた地図のまま走らない。既存 snapshot を渡す `--snapshot` 経路は
> 収集しないため、`manifest_errors` をバナー表示するだけ（描画は参考値）。

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

## v0.2.1（v0.2 差分再監査 N1/N2 クローズ）

GPT Pro の v0.2 差分再監査は **`DDPROGRESS_PASS_WITH_NOTES`**（F1/F2/F3/F5/F6 = CLOSED、
F4 = PARTIAL）。F4 の穴2点を v0.2.1 で閉じた:

- **N1（検証ゲートの分岐漏れ）**: v0.2 では `pipeline_probe.py main()` だけが probe 前に
  `validate_manifest()`→拒否していたが、`pipeline_dashboard.py --root` の**収集+描画一発実行は
  `collect()` を直接呼ぶため検証拒否が効かなかった**。doc が「収集+描画を一発で」と案内している
  以上これは実害。修正は **`collect()` 自体を manifest 不正時に拒否（`refuse_on_invalid=True`
  既定 → `ManifestError`）** にして、両経路を**単一ソース**で塞いだ。`main()` 側の重複検証は撤去。
  観測目的で壊れた manifest でも走らせたい場合のみ `collect(..., refuse_on_invalid=False)`。
- **N2（重複 request_id の silent dedupe）**: roundtrip で同一 `request_id` の重複送信を
  黙って捨てていた。`duplicate` / `duplicate_count` として surface し、dashboard は
  サマリに `重{n}`、明細に「⚠ 重複 request_id」セクションを出す（件数自体は distinct のまま）。
