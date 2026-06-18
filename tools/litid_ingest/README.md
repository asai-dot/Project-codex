# litid_ingest — raw_intake 投入前ツール (read-only)

DD-LITID-PLAN 4ルート版同定パイプラインの **Phase 0 ゲート** 用ユーティリティ。
監査判定 `DESIGN_PASS_WITH_NOTES`（INGEST_SPEC v0.2 §7-A）の field-profile ゲートを実装。

**スコープ厳守**: ここにあるのは「読むだけ」のプロファイラのみ。
突合・正規化・promote・DDL・backfill は **HOLD**（監査 §7-E）。本ツールはそれらを一切しない。

## field_profile.py

JSONL/NDJSON を1行ずつストリーム（505MB級でも定数メモリ）し、投入前に知りたい事実だけ出す:

- 各フィールドの present% / nonempty% と例値（ネスト2段までドット記法）
- **ISBN**: 被覆率・チェックサム妥当率・重複行（key/isbn/toc は未指定なら候補名から自動推定）
- **キー一意性**: distinct / unique% / 重複行
- **TOC**: 被覆率・平均項目数
- `--manifest-stub` で §2 manifest の下書きを出力（取得時メタは TODO 印、要手当て）

### 使い方

```bash
# 自動推定（先頭200行でフィールド名を確定）
python3 field_profile.py CATALOG.jsonl --source bengo4

# 明示指定 + レポート/manifest stub 出力
python3 field_profile.py CATALOG.jsonl --source lionbolt \
    --key book_id --isbn-field isbn --toc-field toc \
    --out-md report.md --out-json report.json --manifest-stub manifest.stub.json
```

`--source` は `lionbolt | bengo4 | legallib | self_scan`。

### 実行場所

実カタログは Box/Mac 側（LION BOLT 61MB / 弁コム 505MB / legallib フル版は Mac ローカル）。
本スクリプトは **stdlib のみ**なので Mac でそのまま動く。Box Drive 同期パス or `raw_intake/` の
ドロップ先に対して直接かける。リポジトリ側のコンテナには実データを持ち込まない。

### legallib フル版の投入前チェック（v0.2 §7-A 投入ゲート）

Mac→`raw_intake/legallib/` ドロップ後、突合より先にこれをかけて
ISBN形式・TOC構造・キー充足率を確認 → 問題なければ `isbn_ndl_lane` に合流。

## manifest_gate.py — §7-A 契約ゲート (enforcement)

`field_profile.py --manifest-stub` が出すのは下書き。取得時メタ（TODO 印）が埋まらないまま
投入されると append-only でも永久に取り戻せない（監査 must_fix #1）。本ゲートは manifest.json を
検証し、**必須欠落／TODO 残り／値域違反／sha256 不正があれば exit 1 で投入をブロック**する。

```bash
python3 manifest_gate.py raw_intake/legallib/20260618/manifest.json
# PASS -> exit 0,  FAIL -> 違反列挙 + exit 1
```

ワークフロー: `field_profile --manifest-stub` で stub 生成 → 人が TODO を埋める →
`manifest_gate` 通過（exit 0）して初めて ingest 可。stub のまま投げると必ず止まる。

## テスト

```bash
python3 -m pytest tools/litid_ingest/tests/ -q   # 15 passed
```
