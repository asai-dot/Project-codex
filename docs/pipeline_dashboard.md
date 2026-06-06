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

- **status**: `done ✅` / `in_progress 🔄` / `waiting ⏳`(GPT/OCR 戻り待ち) /
  `blocked ⛔`(依存未完で入れない) / `todo ⬜` / `error ❗`。
- **probe 種別**:
  - `count` — glob 件数 vs `expected`（取得率。「出せてない/未取得」）。
  - `exists` — 成果物の有無。
  - `roundtrip` — `sent`(例 `to_gpt/*REQUEST`) と `returned`(`from_gpt/*RESULT`) を
    キーで突合。`pending`(戻ってない) / `stale`(古いまま戻らない=詰まり) / `orphan`。

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
